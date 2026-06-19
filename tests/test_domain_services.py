from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from inventory.models import InventoryItem
from inventory.services import adjust_inventory
from planning.models import MealPlan, PlannedMeal
from recipes.models import Recipe, RecipeIngredient
from recipes.services import sanitize_raster_upload, validate_public_url
from shopping.models import ShoppingList
from shopping.services import check_item, generate_items


@pytest.mark.django_db
def test_metric_unit_conversion(units):
    gram, kilogram, _ = units
    assert kilogram.convert(Decimal("1.5"), gram) == Decimal("1500")
    assert gram.convert(Decimal("500"), kilogram) == Decimal("0.5")


@pytest.mark.django_db
def test_incompatible_unit_conversion_fails(units):
    gram, _, piece = units
    with pytest.raises(ValidationError):
        gram.convert(1, piece)


@pytest.mark.django_db
def test_inventory_never_becomes_negative(user, household, units, ingredient, location):
    item = InventoryItem.objects.create(
        household=household, product_name="Tomatoes", ingredient=ingredient,
        quantity=100, unit=units[0], location=location,
    )
    with pytest.raises(ValidationError):
        adjust_inventory(item.id, -101, user, kind="used")
    item.refresh_from_db()
    assert item.quantity == 100


@pytest.mark.django_db
def test_shopping_generation_subtracts_convertible_inventory(user, household, units, ingredient, location, meal_type):
    gram, kilogram, _ = units
    recipe = Recipe.objects.create(household=household, owner=user, name="Soup", servings=2)
    RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, quantity=1000, unit=gram)
    plan = MealPlan.objects.create(
        household=household, name="Week", start_date=date.today(),
        end_date=date.today(), created_by=user,
    )
    PlannedMeal.objects.create(
        household=household, meal_plan=plan, recipe=recipe, date=date.today(),
        meal_type=meal_type, servings=4, created_by=user,
    )
    InventoryItem.objects.create(
        household=household, product_name="Tomatoes", ingredient=ingredient,
        quantity=Decimal("0.5"), unit=kilogram, location=location,
    )
    shopping = ShoppingList.objects.create(household=household, name="List", meal_plan=plan, created_by=user)
    items = generate_items(shopping)
    assert len(items) == 1
    assert items[0].required_quantity == Decimal("1500")
    assert items[0].available_quantity == Decimal("500")


@pytest.mark.django_db
def test_shopping_optimistic_concurrency(user, household, units, ingredient):
    shopping = ShoppingList.objects.create(household=household, name="List", created_by=user)
    item = shopping.items.create(product_name="Tomato", ingredient=ingredient, required_quantity=1, unit=units[2])
    updated = check_item(item.id, user, True, expected_version=1)
    assert updated.version == 2
    with pytest.raises(ValueError, match="conflict"):
        check_item(item.id, user, False, expected_version=1)


def test_ssrf_blocks_private_addresses(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args: [(None, None, None, None, ("127.0.0.1", 0))])
    with pytest.raises(ValidationError):
        validate_public_url("http://example.test/recipe")


def test_upload_rejects_non_image(settings):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MAX_IMAGE_BYTES = 1024
    upload = SimpleUploadedFile("attack.svg", b"<svg onload='alert(1)'></svg>", "image/svg+xml")
    with pytest.raises(ValidationError):
        sanitize_raster_upload(upload)


def test_upload_reencodes_and_strips_metadata(settings):
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    settings.MAX_IMAGE_BYTES = 1024 * 1024
    source = BytesIO()
    Image.new("RGB", (16, 16), "red").save(source, format="PNG", pnginfo=None)
    upload = SimpleUploadedFile("safe.png", source.getvalue(), "image/png")
    cleaned = sanitize_raster_upload(upload)
    assert cleaned.read(2) == b"\xff\xd8"
