from django.conf import settings
from django.db import models

from common.models import HouseholdOwnedModel, TimeStampedModel, UUIDModel, VersionedModel


class MealPlan(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="valid_meal_plan_range")]
        indexes = [models.Index(fields=["household", "start_date", "end_date"])]


class MealType(UUIDModel, TimeStampedModel):
    household = models.ForeignKey("households.Household", on_delete=models.CASCADE, null=True, blank=True)
    code = models.CharField(max_length=50)
    name_da = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["household", "code"], name="unique_household_meal_type")]


class PlannedMeal(UUIDModel, TimeStampedModel, VersionedModel, HouseholdOwnedModel):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        PLANNED = "planned", "Planned"
        CONFIRMED = "confirmed", "Confirmed"
        PREPARING = "preparing", "Being prepared"
        PREPARED = "prepared", "Prepared"
        EATEN = "eaten", "Eaten"
        SKIPPED = "skipped", "Skipped"
        REPLACED = "replaced", "Replaced"
        CANCELLED = "cancelled", "Cancelled"

    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name="meals")
    recipe = models.ForeignKey("recipes.Recipe", on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    meal_type = models.ForeignKey(MealType, on_delete=models.PROTECT)
    servings = models.DecimalField(max_digits=7, decimal_places=2, default=4)
    guests = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    locked = models.BooleanField(default=False)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    leftover_servings = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    recommendation_reasons = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["meal_plan", "date", "meal_type"], name="unique_meal_plan_slot")
        ]
        indexes = [models.Index(fields=["household", "date", "meal_type"])]


class PlannedMealParticipant(UUIDModel, TimeStampedModel):
    planned_meal = models.ForeignKey(PlannedMeal, on_delete=models.CASCADE, related_name="participants")
    profile = models.ForeignKey("households.HouseholdMemberProfile", on_delete=models.PROTECT)
    portion_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    ate = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["planned_meal", "profile"], name="unique_meal_participant")]


class MealPlanTemplate(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data = models.JSONField(default=dict)

