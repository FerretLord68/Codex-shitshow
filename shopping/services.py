from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from inventory.models import InventoryItem

from .models import ShoppingListItem


@transaction.atomic
def generate_items(shopping_list):
    requirements = {}
    for meal in shopping_list.meal_plan.meals.select_related("recipe").prefetch_related("recipe__recipe_ingredients"):
        if not meal.recipe:
            continue
        scale = meal.servings / meal.recipe.servings
        for line in meal.recipe.recipe_ingredients.all():
            if line.quantity is None or line.unit is None:
                key = (line.ingredient_id, None)
                entry = requirements.setdefault(key, {"quantity": None, "unit": None, "meals": [], "ingredient": line.ingredient})
            else:
                key = (line.ingredient_id, line.unit_id)
                entry = requirements.setdefault(key, {"quantity": Decimal("0"), "unit": line.unit, "meals": [], "ingredient": line.ingredient})
                entry["quantity"] += line.quantity * scale
            entry["meals"].append(meal)
    created = []
    for (_, _), requirement in requirements.items():
        available = Decimal("0")
        if requirement["unit"]:
            for stock in InventoryItem.objects.filter(
                household=shopping_list.household,
                ingredient=requirement["ingredient"],
                status__in=["available", "low", "expiring"],
            ).select_related("unit"):
                try:
                    available += stock.unit.convert(stock.quantity, requirement["unit"])
                except Exception:
                    continue
        needed = None if requirement["quantity"] is None else max(Decimal("0"), requirement["quantity"] - available)
        item, _ = ShoppingListItem.objects.update_or_create(
            shopping_list=shopping_list,
            ingredient=requirement["ingredient"],
            unit=requirement["unit"],
            defaults={
                "product_name": requirement["ingredient"].name_da,
                "required_quantity": needed,
                "available_quantity": available if requirement["unit"] else None,
                "category": requirement["ingredient"].category,
            },
        )
        item.source_meals.set(requirement["meals"])
        created.append(item)
    return created


@transaction.atomic
def check_item(item_id, actor, checked, expected_version):
    item = ShoppingListItem.objects.select_for_update().get(pk=item_id)
    if item.version != expected_version:
        raise ValueError("conflict")
    item.checked = checked
    item.checked_by = actor if checked else None
    item.checked_at = timezone.now() if checked else None
    item.version += 1
    item.save()
    item.shopping_list.events.create(item=item, actor=actor, kind="checked" if checked else "unchecked")
    return item

