import ssl
import threading
import time
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from accounts.models import SecurityToken, User
from notifications.backends.smtp import EmailBackend
from notifications.mail import PermanentMailDeliveryError, deliver
from offers.salling import (
    SallingAuthenticationError,
    SallingClient,
    SallingInvalidResponseError,
    SallingPermissionError,
    SallingRateLimitError,
)

STORE = {
    "id": "store-1",
    "name": "Netto Test",
    "brand": "netto",
    "address": {"street": "Testvej 1", "zip": "8000", "city": "Aarhus", "country": "DK"},
    "coordinates": [10.2, 56.1],
    "hours": [],
    "modified": "2026-06-20T10:00:00Z",
}
CLEARANCE = {
    "store": STORE,
    "clearances": [{
        "offer": {
            "currency": "DKK",
            "discount": 7,
            "ean": "offer-1",
            "endTime": "2026-06-21T20:00:00Z",
            "lastUpdate": "2026-06-20T10:00:00Z",
            "newPrice": 15,
            "originalPrice": 22,
            "percentDiscount": 31.82,
            "startTime": "2026-06-20T08:00:00Z",
            "stock": 4,
            "stockUnit": "each",
        },
        "product": {"description": "TEST PRODUCT", "ean": "5700000000000", "image": "https://example.test/a.jpg"},
    }],
}


@pytest.fixture(autouse=True)
def clear_integration_cache():
    cache.clear()
    yield
    cache.clear()


def client_for(handler, settings):
    settings.SALLING_GROUP_MAX_RETRIES = 0
    settings.SALLING_GROUP_CACHE_TTL_SECONDS = 30
    return SallingClient(token="test-token", transport=httpx.MockTransport(handler), sleep=lambda _: None)


def test_mail_has_plain_text_and_html(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "MealHouse <mealhouse@taxoz.org>"
    deliver({"to": "user@example.test", "subject": "Test", "template": "email/smtp_test.txt", "context": {}})
    assert len(mail.outbox) == 1
    assert mail.outbox[0].alternatives[0].mimetype == "text/html"


def test_permanent_smtp_error_is_sanitized(settings):
    class RejectingConnection:
        def send_messages(self, messages):
            raise __import__("smtplib").SMTPDataError(550, b"private upstream detail")

    settings.DEFAULT_FROM_EMAIL = "MealHouse <mealhouse@taxoz.org>"
    with pytest.raises(PermanentMailDeliveryError, match="status 550") as caught:
        deliver(
            {"to": "user@example.test", "subject": "Test", "template": "email/smtp_test.txt", "context": {}},
            connection=RejectingConnection(),
        )
    assert "private upstream detail" not in str(caught.value)


def test_smtp_backend_uses_connection_local_ca_file(settings, tmp_path):
    ca_file = tmp_path / "mail.pem"
    ca_file.write_text("certificate fixture")
    settings.SMTP_CA_FILE = str(ca_file)
    with patch("notifications.backends.smtp.ssl.create_default_context") as create_context:
        context = EmailBackend(host="mail.taxoz.org").ssl_context
    assert context is create_context.return_value
    create_context.assert_called_once_with(cafile=str(ca_file))


def test_smtp_backend_rejects_ca_file_for_other_host(settings, tmp_path):
    ca_file = tmp_path / "mail.pem"
    ca_file.write_text("certificate fixture")
    settings.SMTP_CA_FILE = str(ca_file)
    with pytest.raises(ssl.SSLCertVerificationError):
        _ = EmailBackend(host="smtp.example.test").ssl_context


def test_smtp_backend_without_ca_uses_default_global_trust(settings):
    settings.SMTP_CA_FILE = ""
    with patch("notifications.backends.smtp.ssl.create_default_context") as create_context:
        context = EmailBackend(host="mail.taxoz.org").ssl_context
    assert context is create_context.return_value
    create_context.assert_called_once_with()


def test_salling_food_waste_success_and_normalization(settings):
    client = client_for(lambda request: httpx.Response(200, json=[CLEARANCE]), settings)
    result = client.food_waste(zip_code="8000")
    assert result.cache_hit is False
    assert result.items[0]["offer_price"] == Decimal("15")
    assert result.items[0]["store"]["latitude"] == Decimal("56.1")
    assert result.items[0]["raw_source_timestamp"] == datetime(2026, 6, 20, 10, tzinfo=UTC)


def test_salling_empty_result_and_cache_hit(settings):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[])

    client = client_for(handler, settings)
    assert client.food_waste(zip_code="8000").items == []
    assert client.food_waste(zip_code="8000").cache_hit is True
    assert calls == 1


def test_salling_store_pagination(settings):
    def handler(request):
        page = request.url.params.get("page")
        if page == "2":
            return httpx.Response(200, json=[{**STORE, "id": "store-2", "name": "Second"}])
        return httpx.Response(
            200,
            json=[STORE],
            headers={"Link": '<https://api.sallinggroup.com/v2/stores?page=2&per_page=100>; rel="next"'},
        )

    result = client_for(handler, settings).stores(country="dk")
    assert [item["external_id"] for item in result.items] == ["store-1", "store-2"]


@pytest.mark.parametrize(
    ("status", "exception"),
    [(401, SallingAuthenticationError), (403, SallingPermissionError), (429, SallingRateLimitError)],
)
def test_salling_auth_permission_and_rate_errors(settings, status, exception):
    client = client_for(lambda request: httpx.Response(status, headers={"Retry-After": "1"}), settings)
    with pytest.raises(exception):
        client.food_waste(zip_code="8000")


def test_salling_invalid_json_and_shape(settings):
    client = client_for(lambda request: httpx.Response(200, content=b"{"), settings)
    with pytest.raises(SallingInvalidResponseError):
        client.food_waste(zip_code="8000")
    cache.clear()
    client = client_for(lambda request: httpx.Response(200, json={"unexpected": True}), settings)
    with pytest.raises(SallingInvalidResponseError):
        client.stores()


def test_salling_timeout_network_and_5xx(settings):
    for error_response in (
        httpx.ReadTimeout("timeout"),
        httpx.ConnectError("network"),
        httpx.Response(503),
    ):
        def handler(request, value=error_response):
            if isinstance(value, Exception):
                raise value
            return value

        with pytest.raises(Exception, match="temporarily unavailable|status 503"):
            client_for(handler, settings).food_waste(zip_code="8000")
        cache.clear()


def test_salling_stale_cache_graceful_degradation(settings):
    client = client_for(lambda request: httpx.Response(200, json=[CLEARANCE]), settings)
    assert client.food_waste(zip_code="8000").items
    key = client._cache_key("v1/food-waste/", {"zip": "8000"})
    cache.delete(key)
    failing = client_for(lambda request: httpx.Response(503), settings)
    result = failing.food_waste(zip_code="8000")
    assert result.degraded is True
    assert result.items


def test_salling_concurrent_identical_requests_are_coalesced(settings):
    calls = 0
    barrier = threading.Barrier(2)

    def handler(request):
        nonlocal calls
        calls += 1
        time.sleep(0.05)
        return httpx.Response(200, json=[CLEARANCE])

    client = client_for(handler, settings)
    results = []

    def run():
        barrier.wait()
        results.append(client.food_waste(zip_code="8000"))

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert calls == 1
    assert len(results) == 2


@pytest.mark.django_db
def test_admin_bootstrap_upgrades_existing_user(user):
    with (
        patch("builtins.input", side_effect=["", "y"]),
        patch("getpass.getpass", side_effect=["A much stronger admin password 74!", "A much stronger admin password 74!"]),
    ):
        call_command("create_admin", email=user.email)
    user.refresh_from_db()
    assert user.is_staff and user.is_superuser and user.is_email_verified
    assert user.check_password("A much stronger admin password 74!")


@pytest.mark.django_db
def test_admin_bootstrap_accepts_restricted_password_file(user, tmp_path):
    password_file = tmp_path / "admin-password"
    password_file.write_text("A strong file-based admin password 85!")
    password_file.chmod(0o600)
    call_command(
        "create_admin",
        email=user.email,
        password_file=str(password_file),
        yes_upgrade=True,
        non_interactive=True,
    )
    user.refresh_from_db()
    assert user.is_staff and user.is_superuser
    assert user.check_password("A strong file-based admin password 85!")


@pytest.mark.django_db
def test_admin_bootstrap_rejects_exposed_password_file(user, tmp_path):
    password_file = tmp_path / "admin-password"
    password_file.write_text("A strong file-based admin password 85!")
    password_file.chmod(0o644)
    with pytest.raises(CommandError, match="must not be accessible"):
        call_command(
            "create_admin",
            email=user.email,
            password_file=str(password_file),
            yes_upgrade=True,
            non_interactive=True,
        )


@pytest.mark.django_db
def test_password_reset_preserves_administrator_role(client, user):
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    token = SecurityToken.issue(user, SecurityToken.Purpose.PASSWORD_RESET)
    response = client.post(
        f"/account/reset/{token}/",
        {
            "new_password1": "A new strong administrator password 96!",
            "new_password2": "A new strong administrator password 96!",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.is_staff and user.is_superuser
    assert user.check_password("A new strong administrator password 96!")


@pytest.mark.django_db
def test_registration_cannot_assign_administrator(client):
    response = client.post(
        "/account/register/",
        {
            "email": "new@example.test",
            "display_name": "New",
            "locale": "da",
            "accept_terms": "on",
            "password1": "Strong registration password 93!",
            "password2": "Strong registration password 93!",
            "is_staff": "on",
            "is_superuser": "on",
        },
    )
    assert response.status_code == 200
    user = User.objects.get(email="new@example.test")
    assert not user.is_staff and not user.is_superuser


@pytest.mark.django_db
def test_offer_image_proxy_blocks_untrusted_hosts(client, user):
    client.force_login(user)
    response = client.get(reverse("offers:image_proxy"), {"url": "https://127.0.0.1/private"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_offer_image_proxy_validates_content(client, user):
    client.force_login(user)
    with patch(
        "offers.views.httpx.get",
        return_value=httpx.Response(
            200,
            content=b"\xff\xd8image",
            headers={"content-type": "image/jpeg"},
            request=httpx.Request("GET", "https://dam.dsg.dk/image.jpg"),
        ),
    ):
        response = client.get(
            reverse("offers:image_proxy"), {"url": "https://dam.dsg.dk/image.jpg"}
        )
    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"


def test_verify_salling_command_is_sanitized(capsys):
    result = type("Result", (), {"items": [], "cache_hit": False, "degraded": False})()
    with (
        patch("offers.management.commands.verify_salling.SallingClient") as client_class,
    ):
        client_class.return_value.stores.return_value = result
        client_class.return_value.food_waste.return_value = result
        call_command("verify_salling", zip_code="8000")
    output = capsys.readouterr().out
    assert "verification succeeded" in output
    assert "token" not in output.lower()
