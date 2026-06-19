from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.services import audit_event
from common.decorators import household_permission

from .forms import GeneratePlanForm, MealPlanForm, PlannedMealForm
from .models import MealPlan, PlannedMeal, PlannedMealParticipant
from .services import generate_plan, nutrition_for_participant


@login_required
def plan_list(request):
    household_ids = request.user.memberships.filter(is_active=True).values_list("household_id", flat=True)
    plans = MealPlan.objects.filter(household_id__in=household_ids).select_related("household").order_by("-start_date")
    return render(request, "planning/list.html", {"plans": plans[:100]})


@login_required
@household_permission("meal.edit")
def create(request, household_id):
    form = MealPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.household = request.household
        plan.created_by = request.user
        plan.save()
        return redirect("planning:detail", plan_id=plan.id)
    return render(request, "planning/plan_form.html", {"form": form, "household": request.household})


def _authorized_plan(request, plan_id, permission="meal.view"):
    plan = get_object_or_404(MealPlan.objects.select_related("household"), id=plan_id)
    membership = request.user.memberships.filter(household=plan.household, is_active=True).first()
    if not membership or not membership.has_permission(permission):
        raise PermissionDenied
    return plan, membership


@login_required
def detail(request, plan_id):
    plan, membership = _authorized_plan(request, plan_id)
    meals = plan.meals.select_related("recipe", "meal_type").prefetch_related("participants__profile")
    grouped = defaultdict(list)
    for meal in meals:
        grouped[meal.date].append(meal)
    return render(request, "planning/detail.html", {
        "plan": plan, "days": sorted(grouped.items()), "membership": membership,
        "generate_form": GeneratePlanForm(),
    })


@login_required
def meal_create(request, plan_id):
    plan, _ = _authorized_plan(request, plan_id, "meal.edit")
    form = PlannedMealForm(request.POST or None)
    form.fields["recipe"].queryset = form.fields["recipe"].queryset.filter(household=plan.household)
    form.fields["meal_type"].queryset = form.fields["meal_type"].queryset.filter(
        __import__("django.db.models", fromlist=["Q"]).Q(household=plan.household)
        | __import__("django.db.models", fromlist=["Q"]).Q(household=None)
    )
    if request.method == "POST" and form.is_valid():
        meal = form.save(commit=False)
        meal.meal_plan = plan
        meal.household = plan.household
        meal.created_by = request.user
        meal.save()
        for profile in plan.household.member_profiles.all():
            PlannedMealParticipant.objects.create(
                planned_meal=meal, profile=profile, portion_multiplier=profile.portion_multiplier
            )
        return redirect("planning:detail", plan_id=plan.id)
    return render(request, "planning/meal_form.html", {"form": form, "plan": plan})


@login_required
def meal_edit(request, meal_id):
    meal = get_object_or_404(PlannedMeal.objects.select_related("meal_plan", "household"), id=meal_id)
    membership = request.user.memberships.filter(household=meal.household, is_active=True).first()
    if not membership or not membership.has_permission("meal.edit"):
        raise PermissionDenied
    form = PlannedMealForm(request.POST or None, instance=meal)
    form.fields["recipe"].queryset = form.fields["recipe"].queryset.filter(household=meal.household)
    if request.method == "POST" and form.is_valid():
        submitted_version = int(request.POST.get("version", meal.version))
        with transaction.atomic():
            locked = PlannedMeal.objects.select_for_update().get(pk=meal.pk)
            if locked.version != submitted_version:
                form.add_error(None, "Meal was changed by another user. Reload and try again.")
            else:
                updated = form.save(commit=False)
                updated.version += 1
                updated.save()
                return redirect("planning:detail", plan_id=meal.meal_plan_id)
    return render(request, "planning/meal_form.html", {"form": form, "plan": meal.meal_plan, "meal": meal})


@login_required
@require_POST
def generate(request, plan_id):
    plan, _ = _authorized_plan(request, plan_id, "meal.edit")
    form = GeneratePlanForm(request.POST)
    if form.is_valid():
        generated = generate_plan(plan, request.user, **form.cleaned_data)
        audit_event("meal_plan.generated", actor=request.user, household=plan.household, target=plan, request=request, metadata={"count": len(generated)})
        messages.success(request, f"{len(generated)} meals generated.")
    return redirect("planning:detail", plan_id=plan.id)


@login_required
@require_POST
def meal_status(request, meal_id):
    meal = get_object_or_404(PlannedMeal, id=meal_id)
    membership = request.user.memberships.filter(household=meal.household, is_active=True).first()
    if not membership or not membership.has_permission("meal.edit"):
        raise PermissionDenied
    status = request.POST.get("status")
    if status not in PlannedMeal.Status.values:
        raise PermissionDenied
    meal.status = status
    meal.version += 1
    meal.save(update_fields=["status", "version", "updated_at"])
    return redirect("planning:detail", plan_id=meal.meal_plan_id)


@login_required
def nutrition(request, plan_id):
    plan, _ = _authorized_plan(request, plan_id, "meal.view")
    totals = defaultdict(lambda: defaultdict(lambda: 0))
    missing = defaultdict(set)
    for meal in plan.meals.prefetch_related("participants__profile").select_related("recipe"):
        for participant in meal.participants.all():
            data = nutrition_for_participant(meal, participant)
            if not data:
                continue
            for key, value in data.items():
                if key not in {"missing", "quality"}:
                    totals[participant.profile][key] += value
            missing[participant.profile].update(data["missing"])
    return render(request, "planning/nutrition.html", {"plan": plan, "totals": totals.items(), "missing": missing})

