from django.core.management.base import BaseCommand

from catalog.models import Ingredient, IngredientAlias, Unit
from offers.models import OfferProvider
from planning.models import MealType


class Command(BaseCommand):
    help = "Create idempotent global reference data. Safe in production."

    def handle(self, *args, **options):
        units = [
            ("g", "Gram", "Gram", "g", "mass", "1"),
            ("kg", "Kilogram", "Kilogram", "kg", "mass", "1000"),
            ("ml", "Milliliter", "Millilitre", "ml", "volume", "1"),
            ("l", "Liter", "Litre", "l", "volume", "1000"),
            ("tsp", "Teske", "Teaspoon", "tsk", "volume", "5"),
            ("tbsp", "Spiseske", "Tablespoon", "spsk", "volume", "15"),
            ("pc", "Styk", "Piece", "stk", "count", "1"),
        ]
        for code, da, en, symbol, dimension, factor in units:
            Unit.objects.update_or_create(code=code, defaults={
                "name_da": da, "name_en": en, "symbol": symbol,
                "dimension": dimension, "to_base_factor": factor,
            })
        for code, da, en, order in [
            ("breakfast", "Morgenmad", "Breakfast", 10),
            ("lunch", "Frokost", "Lunch", 20),
            ("dinner", "Aftensmad", "Dinner", 30),
            ("snack", "Mellemmåltid", "Snack", 40),
        ]:
            MealType.objects.get_or_create(household=None, code=code, defaults={"name_da": da, "name_en": en, "sort_order": order})
        gram = Unit.objects.get(code="g")
        piece = Unit.objects.get(code="pc")
        for da, en, category, unit, aliases in [
            ("Tomat", "Tomato", "Grøntsager", gram, ["tomater", "tomatoes"]),
            ("Løg", "Onion", "Grøntsager", gram, ["løg", "onions"]),
            ("Pasta", "Pasta", "Tørvarer", gram, ["spaghetti"]),
            ("Æg", "Egg", "Mejeri og æg", piece, ["æg", "eggs"]),
            ("Mælk", "Milk", "Mejeri og æg", Unit.objects.get(code="ml"), ["milk"]),
        ]:
            ingredient, _ = Ingredient.objects.get_or_create(name_da=da, name_en=en, defaults={"category": category, "default_unit": unit})
            for alias in aliases:
                IngredientAlias.objects.get_or_create(locale="da" if alias in {"tomater", "løg", "æg"} else "en", normalized=" ".join(alias.lower().split()), defaults={"ingredient": ingredient, "alias": alias})
        OfferProvider.objects.get_or_create(name="Development mock offers", kind="mock", defaults={"enabled": False, "attribution": "Synthetic development data"})
        OfferProvider.objects.get_or_create(
            name="Salling Group anti-food-waste offers",
            kind="salling_group",
            defaults={
                "base_url": "https://api.sallinggroup.com",
                "enabled": False,
                "configuration": {"zip": "8000"},
                "rate_limit_per_hour": 400,
                "attribution": "Salling Group Anti Food Waste API",
            },
        )
        self.stdout.write(self.style.SUCCESS("Reference data is ready."))
