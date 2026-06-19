from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from common.decorators import household_permission
from planning.models import PlannedMeal

from .forms import InventoryItemForm, StorageLocationForm, WasteRecordForm
from .models import InventoryItem, InventoryTransaction, WasteRecord
from .services import confirm_meal_deductions, proposed_meal_deductions


@login_required
def inventory_list(request):
    household_ids = request.user.memberships.filter(is_active=True).values_list("household_id", flat=True)
    items = InventoryItem.objects.filter(household_id__in=household_ids).select_related("household", "location", "unit", "ingredient")
    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(product_name__icontains=query)
    return render(request, "inventory/list.html", {"items": items[:300], "query": query})


@login_required
@household_permission("inventory.edit")
def item_create(request, household_id):
    form = InventoryItemForm(request.POST or None)
    form.fields["location"].queryset = form.fields["location"].queryset.filter(household=request.household)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.household = request.household
        item.save()
        InventoryTransaction.objects.create(
            household=request.household, item=item, kind="added", quantity_delta=item.quantity,
            unit=item.unit, balance_after=item.quantity, actor=request.user,
        )
        return redirect("inventory:list")
    return render(request, "inventory/item_form.html", {"form": form, "household": request.household})


@login_required
@household_permission("inventory.edit")
def location_create(request, household_id):
    form = StorageLocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        location = form.save(commit=False)
        location.household = request.household
        location.save()
        return redirect("inventory:list")
    return render(request, "inventory/location_form.html", {"form": form, "household": request.household})


@login_required
def prepare_meal(request, meal_id):
    meal = get_object_or_404(PlannedMeal.objects.select_related("household", "recipe"), pk=meal_id)
    membership = request.user.memberships.filter(household=meal.household, is_active=True).first()
    if not membership or not membership.has_permission("inventory.edit"):
        raise PermissionDenied
    proposals = proposed_meal_deductions(meal)
    if request.method == "POST":
        deductions = []
        for proposal in proposals:
            value = request.POST.get(f"item_{proposal['item'].id}")
            if value:
                deductions.append((proposal["item"].id, value))
        confirm_meal_deductions(meal, request.user, deductions)
        meal.status = PlannedMeal.Status.PREPARED
        meal.save(update_fields=["status", "updated_at"])
        return redirect("planning:detail", plan_id=meal.meal_plan_id)
    return render(request, "inventory/prepare_meal.html", {"meal": meal, "proposals": proposals})


@login_required
@household_permission("inventory.edit")
def waste_create(request, household_id):
    form = WasteRecordForm(request.POST or None)
    form.fields["item"].queryset = form.fields["item"].queryset.filter(household=request.household)
    form.fields["location"].queryset = form.fields["location"].queryset.filter(household=request.household)
    if request.method == "POST" and form.is_valid():
        waste = form.save(commit=False)
        waste.household = request.household
        waste.recorded_by = request.user
        waste.save()
        return redirect("inventory:waste_report", household_id=household_id)
    return render(request, "inventory/waste_form.html", {"form": form, "household": request.household})


@login_required
@household_permission("inventory.view")
def waste_report(request, household_id):
    records = WasteRecord.objects.filter(household=request.household)
    return render(request, "inventory/waste_report.html", {
        "household": request.household,
        "records": records[:200],
        "total_value": records.aggregate(value=Sum("estimated_value"))["value"],
    })

