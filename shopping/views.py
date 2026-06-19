from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from common.decorators import household_permission
from inventory.models import InventoryItem, InventoryTransaction

from .forms import ShoppingListForm
from .models import ShoppingList, ShoppingListItem
from .services import check_item, generate_items


@login_required
def shopping_list_index(request):
    household_ids = request.user.memberships.filter(is_active=True).values_list("household_id", flat=True)
    lists = ShoppingList.objects.filter(household_id__in=household_ids).select_related("household")
    return render(request, "shopping/list.html", {"lists": lists.order_by("-updated_at")[:100]})


@login_required
@household_permission("shopping.edit")
def create(request, household_id):
    form = ShoppingListForm(request.POST or None)
    form.fields["meal_plan"].queryset = form.fields["meal_plan"].queryset.filter(household=request.household)
    if request.method == "POST" and form.is_valid():
        shopping_list = form.save(commit=False)
        shopping_list.household = request.household
        shopping_list.created_by = request.user
        shopping_list.save()
        if shopping_list.meal_plan:
            generate_items(shopping_list)
        return redirect("shopping:detail", list_id=shopping_list.id)
    return render(request, "shopping/form.html", {"form": form, "household": request.household})


@login_required
def detail(request, list_id):
    shopping_list = get_object_or_404(ShoppingList.objects.select_related("household"), id=list_id)
    membership = request.user.memberships.filter(household=shopping_list.household, is_active=True).first()
    if not membership or not membership.has_permission("shopping.view"):
        raise PermissionDenied
    return render(request, "shopping/detail.html", {
        "shopping_list": shopping_list,
        "items": shopping_list.items.select_related("unit", "store", "offer").order_by("checked", "category", "product_name"),
        "membership": membership,
    })


@login_required
@require_POST
def toggle_item(request, item_id):
    item = get_object_or_404(ShoppingListItem.objects.select_related("shopping_list__household"), id=item_id)
    membership = request.user.memberships.filter(household=item.shopping_list.household, is_active=True).first()
    if not membership or not membership.has_permission("shopping.check"):
        raise PermissionDenied
    try:
        item = check_item(item.id, request.user, request.POST.get("checked") == "true", int(request.POST["version"]))
    except ValueError:
        return JsonResponse({"error": "conflict", "message": "Item changed by another household member."}, status=409)
    return JsonResponse({"checked": item.checked, "version": item.version})


@login_required
@require_POST
def purchase_item(request, item_id):
    item = get_object_or_404(ShoppingListItem.objects.select_related("shopping_list__household", "unit"), id=item_id)
    membership = request.user.memberships.filter(household=item.shopping_list.household, is_active=True).first()
    if not membership or not membership.has_permission("shopping.edit"):
        raise PermissionDenied
    quantity = request.POST.get("quantity") or item.purchase_quantity or item.required_quantity
    location_id = request.POST.get("location")
    if request.POST.get("add_to_inventory") == "yes" and quantity and location_id and item.unit:
        with transaction.atomic():
            stock = InventoryItem.objects.create(
                household=item.shopping_list.household,
                product_name=item.product_name,
                ingredient=item.ingredient,
                quantity=quantity,
                unit=item.unit,
                location_id=location_id,
                price_paid=request.POST.get("actual_price") or None,
                store=item.store,
                grocery_offer=item.offer,
            )
            InventoryTransaction.objects.create(
                household=stock.household, item=stock, kind="purchase", quantity_delta=stock.quantity,
                unit=stock.unit, balance_after=stock.quantity, actor=request.user,
            )
            item.purchase_quantity = quantity
            item.actual_price = request.POST.get("actual_price") or None
            item.checked = True
            item.checked_by = request.user
            item.version += 1
            item.save()
    return redirect("shopping:detail", list_id=item.shopping_list_id)

