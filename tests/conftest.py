
import pytest

from accounts.models import User
from catalog.models import Ingredient, Unit
from households.models import Household, Membership
from inventory.models import StorageLocation
from planning.models import MealType


@pytest.fixture
def user(db):
    return User.objects.create_user(email="owner@example.test", password="Strong test password 47!", display_name="Owner", is_email_verified=True)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@example.test", password="Strong test password 48!", display_name="Other", is_email_verified=True)


@pytest.fixture
def household(user):
    house = Household.objects.create(name="Test household", slug="test-household")
    Membership.objects.create(household=house, user=user, role=Membership.Role.OWNER)
    return house


@pytest.fixture
def other_household(other_user):
    house = Household.objects.create(name="Other household", slug="other-household")
    Membership.objects.create(household=house, user=other_user, role=Membership.Role.OWNER)
    return house


@pytest.fixture
def units(db):
    gram = Unit.objects.create(code="g", name_da="Gram", name_en="Gram", symbol="g", dimension="mass", to_base_factor=1)
    kilogram = Unit.objects.create(code="kg", name_da="Kilogram", name_en="Kilogram", symbol="kg", dimension="mass", to_base_factor=1000)
    piece = Unit.objects.create(code="pc", name_da="Styk", name_en="Piece", symbol="stk", dimension="count", to_base_factor=1)
    return gram, kilogram, piece


@pytest.fixture
def ingredient(units):
    return Ingredient.objects.create(name_da="Tomat", name_en="Tomato", default_unit=units[0], category="Vegetables")


@pytest.fixture
def meal_type(db):
    return MealType.objects.create(code="dinner", name_da="Aftensmad", name_en="Dinner", sort_order=30)


@pytest.fixture
def location(household):
    return StorageLocation.objects.create(household=household, name="Køleskab", kind="refrigerator")

