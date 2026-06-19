from django.conf import settings
from django.db import models

from common.models import HouseholdOwnedModel, TimeStampedModel, UUIDModel


class HouseholdBudget(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    class Period(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        CUSTOM = "custom", "Custom"

    period = models.CharField(max_length=20, choices=Period.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="DKK")
    savings_priority = models.PositiveSmallIntegerField(default=3)
    convenience_priority = models.PositiveSmallIntegerField(default=3)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="valid_budget_range"),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="budget_nonnegative"),
        ]
        indexes = [models.Index(fields=["household", "start_date", "end_date"])]

