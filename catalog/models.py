from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedModel, UUIDModel


class Unit(UUIDModel, TimeStampedModel):
    class Dimension(models.TextChoices):
        MASS = "mass", "Mass"
        VOLUME = "volume", "Volume"
        COUNT = "count", "Count"
        OTHER = "other", "Other"

    code = models.CharField(max_length=20, unique=True)
    name_da = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50)
    symbol = models.CharField(max_length=12)
    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    to_base_factor = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    def convert(self, quantity, target):
        if self.dimension != target.dimension or self.to_base_factor is None or target.to_base_factor is None:
            raise ValidationError("Units cannot be converted safely.")
        return Decimal(quantity) * self.to_base_factor / target.to_base_factor

    def __str__(self):
        return self.symbol


class Ingredient(UUIDModel, TimeStampedModel):
    name_da = models.CharField(max_length=150)
    name_en = models.CharField(max_length=150)
    category = models.CharField(max_length=100, blank=True)
    default_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True)
    allergens = models.JSONField(default=list, blank=True)
    dietary_tags = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name_da", "name_en"], name="unique_ingredient_names")
        ]

    def __str__(self):
        return self.name_da


class IngredientAlias(UUIDModel, TimeStampedModel):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="aliases")
    locale = models.CharField(max_length=10, default="da")
    alias = models.CharField(max_length=150)
    normalized = models.CharField(max_length=150, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["locale", "normalized"], name="unique_ingredient_alias")
        ]

    def save(self, *args, **kwargs):
        self.normalized = " ".join(self.alias.lower().split())
        return super().save(*args, **kwargs)


class NutritionalRecord(UUIDModel, TimeStampedModel):
    class Quality(models.TextChoices):
        VERIFIED = "verified", "Verified"
        IMPORTED = "imported", "Imported"
        CALCULATED = "calculated", "Calculated"
        ESTIMATED = "estimated", "Estimated"

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="nutrition_records")
    basis_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=100)
    basis_unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    calories_kcal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    protein_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohydrate_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fat_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fibre_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sugar_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodium_mg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    micronutrients = models.JSONField(default=dict, blank=True)
    quality = models.CharField(max_length=20, choices=Quality.choices, default=Quality.ESTIMATED)
    source = models.CharField(max_length=200, blank=True)


class Store(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=150)
    chain = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=20, blank=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    opening_hours = models.JSONField(default=list, blank=True)
    website = models.URLField(blank=True)
    provider_identifiers = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    supported_regions = models.JSONField(default=list, blank=True)
    currency = models.CharField(max_length=3, default="DKK")
    notes = models.TextField(blank=True)


class Product(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=100, blank=True)
    package_size = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True)
    barcode = models.CharField(max_length=50, blank=True, db_index=True)
    dietary_tags = models.JSONField(default=list, blank=True)
    allergens = models.JSONField(default=list, blank=True)


class ProductAlias(UUIDModel, TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=200)
    normalized = models.CharField(max_length=200, db_index=True)

    def save(self, *args, **kwargs):
        self.normalized = " ".join(self.alias.lower().split())
        return super().save(*args, **kwargs)
