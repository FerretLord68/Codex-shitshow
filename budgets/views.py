
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from common.decorators import household_permission
from shopping.models import ShoppingList

from .forms import BudgetForm
from .models import HouseholdBudget


@login_required
@household_permission("budget.view")
def overview(request, household_id):
    budgets = HouseholdBudget.objects.filter(household=request.household).order_by("-start_date")
    current = budgets.first()
    actual = ShoppingList.objects.filter(
        household=request.household, start_date__gte=current.start_date if current else None,
        end_date__lte=current.end_date if current else None,
    ).aggregate(total=Sum("confirmed_total"))["total"] if current else None
    estimated = ShoppingList.objects.filter(
        household=request.household, start_date__gte=current.start_date if current else None,
        end_date__lte=current.end_date if current else None,
    ).aggregate(total=Sum("estimated_total"))["total"] if current else None
    used = actual if actual is not None else estimated
    return render(request, "budgets/overview.html", {
        "household": request.household, "budgets": budgets, "current": current,
        "used": used, "remaining": current.amount - used if current and used is not None else None,
        "incomplete": used is None,
    })


@login_required
@household_permission("household.manage")
def create(request, household_id):
    form = BudgetForm(request.POST or None, initial={"currency": request.household.currency})
    if request.method == "POST" and form.is_valid():
        budget = form.save(commit=False)
        budget.household = request.household
        budget.created_by = request.user
        budget.save()
        return redirect("budgets:overview", household_id=household_id)
    return render(request, "budgets/form.html", {"form": form, "household": request.household})

