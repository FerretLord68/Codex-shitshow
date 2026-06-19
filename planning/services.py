from collections import Counter
from datetime import timedelta
from decimal import Decimal

from django.db import models, transaction

from inventory.models import InventoryItem
from offers.models import ProductIngredientMatch
from recipes.models import Recipe

from .models import PlannedMeal


def score_recipe(recipe, *, inventory_ingredients, offer_ingredients, recent_ids, max_minutes=None, max_cost=None):
    score = Decimal("0")
    reasons = []
    ingredient_ids = set(recipe.recipe_ingredients.values_list("ingredient_id", flat=True))
    if ingredient_ids & inventory_ingredients:
        score += Decimal("25")
        reasons.append("Uses ingredients already available")
    if ingredient_ids & offer_ingredients:
        score += Decimal("15")
        reasons.append("Matches a current grocery offer")
    if recipe.id not in recent_ids:
        score += Decimal("10")
        reasons.append("Adds variety")
    if max_minutes and recipe.total_minutes <= max_minutes:
        score += Decimal("8")
        reasons.append("Can be prepared quickly")
    if max_cost is not None and recipe.estimated_cost is not None and recipe.estimated_cost <= max_cost:
        score += Decimal("8")
        reasons.append("Fits the household budget")
    return score, reasons


@transaction.atomic
def generate_plan(meal_plan, user, *, only_empty=True, max_minutes=None, max_cost=None, prefer_inventory=True, prefer_offers=True):
    recipes = Recipe.objects.filter(household=meal_plan.household, archived_at__isnull=True).prefetch_related("recipe_ingredients")
    inventory_ids = set()
    if prefer_inventory:
        inventory_ids = set(
            InventoryItem.objects.filter(household=meal_plan.household, status__in=["available", "low", "expiring"])
            .exclude(ingredient=None)
            .values_list("ingredient_id", flat=True)
        )
    offer_ids = set()
    if prefer_offers:
        offer_ids = set(
            ProductIngredientMatch.objects.filter(approved=True, product__grocery_offers__is_active=True)
            .values_list("ingredient_id", flat=True)
        )
    recent_ids = set(
        PlannedMeal.objects.filter(household=meal_plan.household, date__gte=meal_plan.start_date - timedelta(days=28))
        .exclude(recipe=None)
        .values_list("recipe_id", flat=True)
    )
    meal_types = list(__import__("planning.models", fromlist=["MealType"]).MealType.objects.filter(
        models.Q(household=meal_plan.household) | models.Q(household=None)
    ).order_by("sort_order"))
    existing = {(meal.date, meal.meal_type_id): meal for meal in meal_plan.meals.select_for_update()}
    generated = []
    day = meal_plan.start_date
    usage = Counter()
    while day <= meal_plan.end_date:
        for meal_type in meal_types:
            current = existing.get((day, meal_type.id))
            if current and (current.locked or only_empty):
                continue
            ranked = []
            for recipe in recipes:
                score, reasons = score_recipe(
                    recipe,
                    inventory_ingredients=inventory_ids,
                    offer_ingredients=offer_ids,
                    recent_ids=recent_ids,
                    max_minutes=max_minutes,
                    max_cost=max_cost,
                )
                score -= usage[recipe.id] * 12
                ranked.append((score, str(recipe.id), recipe, reasons))
            if not ranked:
                continue
            _, _, recipe, reasons = max(ranked)
            values = {
                "household": meal_plan.household,
                "recipe": recipe,
                "servings": max(1, meal_plan.household.member_profiles.count()),
                "status": PlannedMeal.Status.SUGGESTED,
                "recommendation_reasons": reasons,
                "created_by": user,
                "estimated_cost": recipe.estimated_cost,
            }
            meal, _ = PlannedMeal.objects.update_or_create(
                meal_plan=meal_plan, date=day, meal_type=meal_type, defaults=values
            )
            usage[recipe.id] += 1
            generated.append(meal)
        day += timedelta(days=1)
    return generated


def nutrition_for_participant(meal, participant):
    if not meal.recipe:
        return None
    ratio = participant.portion_multiplier / meal.servings
    fields = ("calories_kcal", "protein_g", "carbohydrate_g", "fat_g", "fibre_g", "sugar_g", "sodium_mg")
    result = {}
    missing = []
    for field in fields:
        value = getattr(meal.recipe, field)
        if value is None:
            missing.append(field)
        else:
            result[field] = value * ratio
    result["missing"] = missing
    result["quality"] = meal.recipe.nutrition_quality
    return result
