from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel, UUIDModel


class OfferProvider(UUIDModel, TimeStampedModel):
    class Kind(models.TextChoices):
        MOCK = "mock", "Mock"
        MANUAL = "manual", "Manual import"
        API = "api", "Official API"
        FEED = "feed", "Official feed"
        SALLING_GROUP = "salling_group", "Salling Group"

    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    base_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=False)
    configuration = models.JSONField(default=dict, blank=True)
    rate_limit_per_hour = models.PositiveIntegerField(default=60)
    attribution = models.TextField(blank=True)
    terms_reviewed_at = models.DateTimeField(null=True, blank=True)
    robots_reviewed_at = models.DateTimeField(null=True, blank=True)


class GroceryOffer(UUIDModel, TimeStampedModel):
    provider = models.ForeignKey(OfferProvider, on_delete=models.PROTECT, related_name="offers")
    store = models.ForeignKey("catalog.Store", on_delete=models.PROTECT)
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="grocery_offers")
    product_name = models.CharField(max_length=250)
    brand = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    package_size_text = models.CharField(max_length=100, blank=True)
    regular_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    offer_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default="DKK")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    source_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    retrieved_at = models.DateTimeField(default=timezone.now)
    raw_source_timestamp = models.DateTimeField(null=True, blank=True)
    source_identifier = models.CharField(max_length=200)
    product_identifier = models.CharField(max_length=200, blank=True)
    original_source_text = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "source_identifier", "starts_at"], name="unique_provider_offer")
        ]
        indexes = [models.Index(fields=["is_active", "ends_at"]), models.Index(fields=["store", "is_active"])]


class ProductIngredientMatch(UUIDModel, TimeStampedModel):
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    ingredient = models.ForeignKey("catalog.Ingredient", on_delete=models.CASCADE)
    confidence = models.DecimalField(max_digits=4, decimal_places=3)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=30, default="automatic")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "ingredient"], name="unique_product_ingredient_match")]


class OfferSyncRun(UUIDModel, TimeStampedModel):
    provider = models.ForeignKey(OfferProvider, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=[("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed")])
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    imported_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    error_type = models.CharField(max_length=100, blank=True)
    error_message = models.CharField(max_length=500, blank=True)


class PriceRecord(UUIDModel, TimeStampedModel):
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    store = models.ForeignKey("catalog.Store", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="DKK")
    observed_at = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=30)
    offer = models.ForeignKey(GroceryOffer, on_delete=models.SET_NULL, null=True, blank=True)
