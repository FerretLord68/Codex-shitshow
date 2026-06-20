from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse

from accounts.models import SecurityToken
from households.models import HouseholdInvitation
from recipes.models import Recipe


@pytest.mark.django_db
def test_password_uses_argon2(user):
    assert user.password.startswith("argon2$")
    assert user.check_password("Strong test password 47!")


@pytest.mark.django_db
def test_security_token_is_hashed_and_single_use(user):
    raw = SecurityToken.issue(user, SecurityToken.Purpose.EMAIL_VERIFY)
    record = SecurityToken.objects.get(user=user)
    assert raw not in record.token_hash
    assert SecurityToken.consume(raw, SecurityToken.Purpose.EMAIL_VERIFY)
    assert SecurityToken.consume(raw, SecurityToken.Purpose.EMAIL_VERIFY) is None


@pytest.mark.django_db
def test_invitation_wrong_account_is_rejected(client, user, other_user, household):
    invitation, raw = HouseholdInvitation.issue(household, other_user.email, user)
    client.force_login(user)
    response = client.get(reverse("households:accept_invitation", args=[raw]))
    assert response.status_code == 403
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


@pytest.mark.django_db
def test_cross_household_recipe_is_denied(client, user, other_user, other_household):
    recipe = Recipe.objects.create(household=other_household, owner=other_user, name="Private", servings=2)
    client.force_login(user)
    response = client.get(reverse("recipes:detail", args=[recipe.id]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_secure_cookie_settings():
    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.SESSION_COOKIE_NAME.startswith("__Host-")


@pytest.mark.django_db
def test_spoofed_proxy_headers_are_ignored(client, settings):
    settings.TRUSTED_PROXY_CIDRS = ["10.0.0.1/32"]
    response = client.get(
        reverse("operations:health"),
        REMOTE_ADDR="203.0.113.8",
        HTTP_X_FORWARDED_PROTO="https",
        HTTP_X_FORWARDED_FOR="1.2.3.4",
    )
    request = response.wsgi_request
    assert request.client_ip == "203.0.113.8"
    assert request.is_secure() is False
    assert "HTTP_X_FORWARDED_FOR" not in request.META


@pytest.mark.django_db
def test_trusted_proxy_headers_are_honored(client, settings):
    settings.TRUSTED_PROXY_CIDRS = ["10.0.0.1/32"]
    response = client.get(
        reverse("operations:health"),
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_FORWARDED_PROTO="https",
        HTTP_X_FORWARDED_FOR="198.51.100.4",
    )
    request = response.wsgi_request
    assert request.client_ip == "198.51.100.4"
    assert request.is_secure() is True


@pytest.mark.django_db
def test_password_reset_email_uses_canonical_https_url(client, user):
    with patch("accounts.views.queue_email") as queued:
        response = client.post(
            reverse("accounts:password_reset_request"),
            {"email": user.email},
        )
    assert response.status_code == 200
    assert queued.call_args.args[3]["url"].startswith(
        "https://codex-shitshow.fejlgoblin.ovh/account/reset/"
    )


@pytest.mark.django_db
def test_invitation_email_uses_canonical_https_url(client, user, household):
    client.force_login(user)
    with patch("households.views.queue_email") as queued:
        response = client.post(
            reverse("households:invite", args=[household.id]),
            {"email": "invitee@example.test", "role": "member"},
        )
    assert response.status_code == 302
    assert queued.call_args.args[3]["url"].startswith(
        "https://codex-shitshow.fejlgoblin.ovh/households/invitations/"
    )


@pytest.mark.django_db
def test_suspended_user_loses_existing_session(client, user):
    client.force_login(user)
    user.is_suspended = True
    user.save(update_fields=["is_suspended"])
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
