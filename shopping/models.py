from django.conf import settings
from django.db import models

from common.models import HouseholdOwnedModel, TimeStampedModel, UUIDModel, VersionedModel


class ShoppingList(UUIDModel, TimeStampedModel, VersionedModel, HouseholdOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SHOPPING = "shopping", "Shopping"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=200)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    meal_plan = models.ForeignKey("planning.MealPlan", on_delete=models.SET_NULL, null=True, blank=True)
    store = models.ForeignKey("catalog.Store", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    estimated_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    confirmed_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["household", "status"])]


class ShoppingListItem(UUIDModel, TimeStampedModel, VersionedModel):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="items")
    ingredient = models.ForeignKey("catalog.Ingredient", on_delete=models.PROTECT, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    required_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    available_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    purchase_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    unit = models.ForeignKey("catalog.Unit", on_delete=models.PROTECT, null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    store = models.ForeignKey("catalog.Store", on_delete=models.SET_NULL, null=True, blank=True)
    preferred_brand = models.CharField(max_length=150, blank=True)
    priority = models.PositiveSmallIntegerField(default=3)
    notes = models.TextField(blank=True)
    checked = models.BooleanField(default=False)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    unavailable = models.BooleanField(default=False)
    estimated_regular_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    offer = models.ForeignKey("offers.GroceryOffer", on_delete=models.SET_NULL, null=True, blank=True)
    actual_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source_meals = models.ManyToManyField("planning.PlannedMeal", blank=True)

    class Meta:
        indexes = [models.Index(fields=["shopping_list", "checked"])]


class ShoppingListEvent(UUIDModel, TimeStampedModel):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="events")
    item = models.ForeignKey(ShoppingListItem, on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict, blank=True)

