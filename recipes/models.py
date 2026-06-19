from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.models import HouseholdOwnedModel, TimeStampedModel, UUIDModel


class Recipe(UUIDModel, TimeStampedModel, HouseholdOwnedModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        HOUSEHOLD = "household", "Household"
        PUBLIC = "public", "Public"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recipes")
    servings = models.DecimalField(max_digits=7, decimal_places=2, default=4, validators=[MinValueValidator(Decimal("0.01"))])
    preparation_minutes = models.PositiveIntegerField(default=0)
    cooking_minutes = models.PositiveIntegerField(default=0)
    categories = models.JSONField(default=list, blank=True)
    cuisine = models.CharField(max_length=100, blank=True)
    allergens = models.JSONField(default=list, blank=True)
    dietary_tags = models.JSONField(default=list, blank=True)
    calories_kcal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    protein_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohydrate_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fat_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fibre_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sugar_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodium_mg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    nutrition_quality = models.CharField(max_length=20, default="missing")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    difficulty = models.CharField(max_length=20, choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")], default="easy")
    equipment = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    attribution = models.TextField(blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["household", "name"]),
            models.Index(fields=["household", "visibility"]),
        ]

    @property
    def total_minutes(self):
        return self.preparation_minutes + self.cooking_minutes

    @property
    def calories_per_serving(self):
        return self.calories_kcal / self.servings if self.calories_kcal is not None else None

    @property
    def cost_per_serving(self):
        return self.estimated_cost / self.servings if self.estimated_cost is not None else None


class RecipeIngredient(UUIDModel, TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey("catalog.Ingredient", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit = models.ForeignKey("catalog.Unit", on_delete=models.PROTECT, null=True, blank=True)
    preparation = models.CharField(max_length=200, blank=True)
    optional = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]


class RecipeInstruction(UUIDModel, TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="instructions")
    position = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["recipe", "position"], name="unique_recipe_step")]


def recipe_image_path(instance, filename):
    return f"households/{instance.recipe.household_id}/recipes/{instance.recipe_id}/{__import__('uuid').uuid4().hex}.jpg"


class RecipeImage(UUIDModel, TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=recipe_image_path)
    alt_text = models.CharField(max_length=250)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class FavouriteRecipe(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "recipe"], name="unique_favourite_recipe")]


class RecipeNote(UUIDModel, TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    household_visible = models.BooleanField(default=False)
    text = models.TextField()

