from django.contrib import admin

from .models import GroceryOffer, OfferProvider, OfferSyncRun, PriceRecord, ProductIngredientMatch

for model in (OfferProvider, GroceryOffer, ProductIngredientMatch, OfferSyncRun, PriceRecord):
    admin.site.register(model)

