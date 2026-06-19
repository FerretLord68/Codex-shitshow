from datetime import date

import pytest
from django.urls import reverse

from households.models import HouseholdInvitation, HouseholdMemberProfile, Membership
from planning.models import MealPlan, PlannedMeal
from planning.services import generate_plan
from recipes.models import Recipe


@pytest.mark.django_db
def test_owner_can_create_household(client, user):
    client.force_login(user)
    response = client.post(reverse("households:create"), {
        "name": "Home", "currency": "DKK", "locale": "da", "timezone": "Europe/Copenhagen",
    })
    assert response.status_code == 302
    assert Membership.objects.filter(user=user, role="owner").exists()


@pytest.mark.django_db
def test_member_cannot_manage_household(client, user, other_user, household):
    Membership.objects.create(household=household, user=other_user, role="member")
    client.force_login(other_user)
    response = client.get(reverse("households:edit", args=[household.id]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_generator_preserves_locked_meal(user, household, meal_type):
    HouseholdMemberProfile.objects.create(household=household, user=user, display_name="Owner")
    old = Recipe.objects.create(household=household, owner=user, name="Locked", servings=2)
    Recipe.objects.create(household=household, owner=user, name="Candidate", servings=2)
    plan = MealPlan.objects.create(
        household=household, name="Day", start_date=date.today(),
        end_date=date.today(), created_by=user,
    )
    meal = PlannedMeal.objects.create(
        household=household, meal_plan=plan, recipe=old, date=date.today(),
        meal_type=meal_type, servings=2, created_by=user, locked=True,
    )
    generate_plan(plan, user, only_empty=False)
    meal.refresh_from_db()
    assert meal.recipe == old


@pytest.mark.django_db
def test_password_reset_page_does_not_enumerate(client):
    response1 = client.post(reverse("accounts:password_reset_request"), {"email": "unknown@example.test"})
    response2 = client.post(reverse("accounts:password_reset_request"), {"email": "also-unknown@example.test"})
    assert response1.status_code == response2.status_code == 200
    assert response1.content == response2.content


@pytest.mark.django_db
def test_health_is_non_sensitive(client):
    response = client.get(reverse("operations:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_final_owner_cannot_delete_account(client, user, household):
    client.force_login(user)
    response = client.post(reverse("accounts:delete"))
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
def test_signed_out_invitee_sees_authentication_choices(client, user, household):
    _, raw = HouseholdInvitation.issue(household, "invitee@example.test", user)
    response = client.get(reverse("households:accept_invitation", args=[raw]))
    assert response.status_code == 200
    assert reverse("accounts:login") in response.content.decode()


@pytest.mark.django_db
def test_recipe_owner_can_add_ingredient(client, user, household, ingredient, units):
    recipe = Recipe.objects.create(household=household, owner=user, name="Soup", servings=2)
    client.force_login(user)
    response = client.post(
        reverse("recipes:ingredient_create", args=[recipe.id]),
        {
            "ingredient": ingredient.id,
            "quantity": "500",
            "unit": units[0].id,
            "preparation": "chopped",
            "position": "1",
        },
    )
    assert response.status_code == 302
    assert recipe.recipe_ingredients.filter(ingredient=ingredient, quantity=500).exists()
