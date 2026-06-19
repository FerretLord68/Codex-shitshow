from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import HouseholdOwnedModel, TimeStampedModel, UUIDModel, VersionedModel


class StorageLocation(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    name = models.CharField(max_length=100)
    kind = models.CharField(
        max_length=30,
        choices=[
            ("refrigerator", "Refrigerator"), ("freezer", "Freezer"), ("pantry", "Pantry"),
            ("cupboard", "Cupboard"), ("basement", "Basement"), ("garage", "Garage"), ("custom", "Custom"),
        ],
        default="pantry",
    )
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["household", "name"], name="unique_storage_name")]


class InventoryQuerySet(models.QuerySet):
    def expiring_soon(self):
        today = timezone.localdate()
        return self.filter(
            models.Q(expiration_date__range=(today, today + timedelta(days=3)))
            | models.Q(best_before_date__range=(today, today + timedelta(days=3)))
        ).exclude(status__in=["empty", "discarded"])


class InventoryItem(UUIDModel, TimeStampedModel, VersionedModel, HouseholdOwnedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        LOW = "low", "Low"
        EMPTY = "empty", "Empty"
        RESERVED = "reserved", "Reserved"
        EXPIRING = "expiring", "Expiring soon"
        EXPIRED = "expired", "Expired"
        DISCARDED = "discarded", "Discarded"

    product_name = models.CharField(max_length=200)
    ingredient = models.ForeignKey("catalog.Ingredient", on_delete=models.PROTECT, null=True, blank=True)
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.CharField(max_length=150, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.ForeignKey("catalog.Unit", on_delete=models.PROTECT)
    package_size = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    packages = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    location = models.ForeignKey(StorageLocation, on_delete=models.PROTECT)
    purchase_date = models.DateField(null=True, blank=True)
    opened_date = models.DateField(null=True, blank=True)
    best_before_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    price_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    store = models.ForeignKey("catalog.Store", on_delete=models.SET_NULL, null=True, blank=True)
    grocery_offer = models.ForeignKey("offers.GroceryOffer", on_delete=models.SET_NULL, null=True, blank=True)
    barcode = models.CharField(max_length=50, blank=True)
    batch = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    objects = InventoryQuerySet.as_manager()

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=0), name="inventory_quantity_nonnegative")]
        indexes = [
            models.Index(fields=["household", "status"]),
            models.Index(fields=["household", "expiration_date"]),
            models.Index(fields=["household", "ingredient"]),
        ]


class InventoryTransaction(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="transactions")
    kind = models.CharField(
        max_length=30,
        choices=[
            ("added", "Added"), ("adjusted", "Adjusted"), ("used", "Used"), ("moved", "Moved"),
            ("opened", "Opened"), ("discarded", "Discarded"), ("purchase", "Purchase"), ("undo", "Undo"),
        ],
    )
    quantity_delta = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit = models.ForeignKey("catalog.Unit", on_delete=models.PROTECT)
    balance_after = models.DecimalField(max_digits=14, decimal_places=3)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    planned_meal = models.ForeignKey("planning.PlannedMeal", on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    reversed_transaction = models.OneToOneField("self", on_delete=models.SET_NULL, null=True, blank=True)


class WasteRecord(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.SET_NULL, null=True, blank=True)
    ingredient = models.ForeignKey("catalog.Ingredient", on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.ForeignKey("catalog.Unit", on_delete=models.PROTECT)
    date = models.DateField(default=timezone.localdate)
    reason = models.CharField(
        max_length=30,
        choices=[
            ("expired", "Expired"), ("spoiled", "Spoiled"), ("too_much", "Prepared too much"),
            ("disliked", "Disliked"), ("storage", "Storage problem"), ("damaged", "Damaged packaging"),
            ("unknown", "Unknown"), ("custom", "Custom"),
        ],
    )
    custom_reason = models.CharField(max_length=200, blank=True)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

