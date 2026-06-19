from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import InventoryItem, InventoryTransaction


@transaction.atomic
def adjust_inventory(item_id, delta, actor, *, kind="adjusted", planned_meal=None, metadata=None):
    item = InventoryItem.objects.select_for_update().get(pk=item_id)
    delta = Decimal(delta)
    new_quantity = item.quantity + delta
    if new_quantity < 0:
        raise ValidationError("Inventory cannot become negative.")
    item.quantity = new_quantity
    item.version += 1
    if item.quantity == 0:
        item.status = InventoryItem.Status.EMPTY
    item.save(update_fields=["quantity", "version", "status", "updated_at"])
    return InventoryTransaction.objects.create(
        household=item.household,
        item=item,
        kind=kind,
        quantity_delta=delta,
        unit=item.unit,
        balance_after=item.quantity,
        actor=actor,
        planned_meal=planned_meal,
        metadata=metadata or {},
    )


def proposed_meal_deductions(meal):
    proposals = []
    if not meal.recipe:
        return proposals
    scale = meal.servings / meal.recipe.servings
    for recipe_item in meal.recipe.recipe_ingredients.select_related("ingredient", "unit"):
        if recipe_item.quantity is None or recipe_item.unit is None:
            continue
        needed = recipe_item.quantity * scale
        candidates = InventoryItem.objects.filter(
            household=meal.household,
            ingredient=recipe_item.ingredient,
            status__in=["available", "low", "expiring"],
        ).select_related("unit").order_by("expiration_date", "best_before_date", "created_at")
        remaining = needed
        for item in candidates:
            try:
                available = item.unit.convert(item.quantity, recipe_item.unit)
            except Exception:
                continue
            take = min(available, remaining)
            source_take = recipe_item.unit.convert(take, item.unit)
            proposals.append({"item": item, "quantity": source_take, "unit": item.unit})
            remaining -= take
            if remaining <= 0:
                break
    return proposals


@transaction.atomic
def confirm_meal_deductions(meal, actor, deductions):
    transactions = []
    for item_id, quantity in deductions:
        transactions.append(adjust_inventory(item_id, -Decimal(quantity), actor, kind="used", planned_meal=meal))
    return transactions

