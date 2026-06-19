from django.contrib import admin

from .models import (
    Ingredient,
    IngredientAlias,
    NutritionalRecord,
    Product,
    ProductAlias,
    Store,
    Unit,
)

for model in (Unit, Ingredient, IngredientAlias, NutritionalRecord, Store, Product, ProductAlias):
    admin.site.register(model)

