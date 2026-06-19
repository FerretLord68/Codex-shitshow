
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from audit.services import audit_event
from notifications.services import queue_email

from .forms import (
    LoginForm,
    PasswordResetConfirmForm,
    PasswordUpdateForm,
    ProfileForm,
    RegistrationForm,
    ResetRequestForm,
)
from .models import SecurityToken, User, UserSession


def _public_url(path):
    return f"{settings.APP_URL}{path}"


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        raw = SecurityToken.issue(user, SecurityToken.Purpose.EMAIL_VERIFY)
        queue_email(
            user.email,
            _("Verify your MealHouse account"),
            "email/verify.txt",
            {"user": user, "url": _public_url(f"/account/verify/{raw}/")},
            dedupe_key=f"verify:{user.id}:{raw[:8]}",
        )
        audit_event("account.registered", actor=user, request=request)
        return render(request, "accounts/check_email.html")
    return render(request, "accounts/register.html", {"form": form})


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def login_view(request):
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        user.clear_login_failures()
        login(request, user)
        request.session.cycle_key()
        audit_event("auth.login_success", actor=user, request=request)
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect("dashboard")
    if request.method == "POST":
        audit_event("auth.login_failure", request=request, metadata={"email_hash": "redacted"})
        messages.error(request, _("Login failed. Check your details or try again later."))
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
@require_POST
def logout_view(request):
    audit_event("auth.logout", actor=request.user, request=request)
    if request.session.session_key:
        UserSession.objects.filter(
            session_key_hash=UserSession.hash_key(request.session.session_key)
        ).update(revoked_at=timezone.now())
    logout(request)
    return redirect("landing")


def verify_email(request, token):
    with transaction.atomic():
        security_token = SecurityToken.consume(token, SecurityToken.Purpose.EMAIL_VERIFY)
        if not security_token:
            raise Http404
        security_token.user.is_email_verified = True
        security_token.user.save(update_fields=["is_email_verified"])
    audit_event("account.email_verified", actor=security_token.user, request=request)
    messages.success(request, _("Your e-mail address is verified."))
    return redirect("accounts:login")


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def password_reset_request(request):
    form = ResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(email=form.cleaned_data["email"].lower(), is_active=True).first()
        if user:
            raw = SecurityToken.issue(user, SecurityToken.Purpose.PASSWORD_RESET)
            queue_email(
                user.email,
                _("Reset your MealHouse password"),
                "email/password_reset.txt",
                {"user": user, "url": _public_url(f"/account/reset/{raw}/")},
                dedupe_key=f"reset:{user.id}:{raw[:8]}",
            )
        return render(request, "accounts/check_email.html")
    return render(request, "accounts/password_reset_request.html", {"form": form})


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def password_reset_confirm(request, token):
    digest = __import__("hashlib").sha256(token.encode()).hexdigest()
    security_token = SecurityToken.objects.filter(
        token_hash=digest,
        purpose=SecurityToken.Purpose.PASSWORD_RESET,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).select_related("user").first()
    if not security_token:
        raise Http404
    form = PasswordResetConfirmForm(security_token.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            consumed = SecurityToken.consume(token, SecurityToken.Purpose.PASSWORD_RESET)
            if not consumed:
                raise Http404
            user = form.save()
            user.last_password_change_at = timezone.now()
            user.save(update_fields=["last_password_change_at"])
            UserSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
        audit_event("account.password_reset", actor=user, request=request)
        return redirect("accounts:login")
    return render(request, "accounts/password_reset_confirm.html", {"form": form})


@login_required
def settings_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Settings saved."))
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"form": form})


@login_required
def password_change(request):
    form = PasswordUpdateForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.last_password_change_at = timezone.now()
        user.save(update_fields=["last_password_change_at"])
        update_session_auth_hash(request, user)
        current_hash = UserSession.hash_key(request.session.session_key)
        UserSession.objects.filter(user=user).exclude(session_key_hash=current_hash).update(revoked_at=timezone.now())
        request.session.cycle_key()
        audit_event("account.password_changed", actor=user, request=request)
        return redirect("accounts:sessions")
    return render(request, "accounts/password_change.html", {"form": form})


@login_required
def sessions(request):
    return render(request, "accounts/sessions.html", {"sessions": request.user.active_sessions.order_by("-last_seen_at")})


@login_required
@require_POST
def revoke_session(request, session_id):
    session = get_object_or_404(UserSession, id=session_id, user=request.user)
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
    audit_event("account.session_revoked", actor=request.user, request=request)
    return redirect("accounts:sessions")


@login_required
def export_data(request):
    data = {
        "account": {
            "id": str(request.user.id),
            "email": request.user.email,
            "display_name": request.user.display_name,
            "locale": request.user.locale,
        },
        "households": list(request.user.memberships.values("household_id", "role", "created_at")),
    }
    audit_event("account.data_exported", actor=request.user, request=request)
    response = JsonResponse(data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'attachment; filename="mealhouse-export.json"'
    return response


@login_required
@require_POST
def delete_account(request):
    from households.models import Membership

    owned_households = Membership.objects.filter(
        user=request.user, role=Membership.Role.OWNER, is_active=True
    ).values_list("household_id", flat=True)
    final_owner = any(
        Membership.objects.filter(
            household_id=household_id, role=Membership.Role.OWNER, is_active=True
        ).count() == 1
        for household_id in owned_households
    )
    if final_owner:
        messages.error(request, _("Transfer ownership or delete the household first."))
        return redirect("accounts:settings")
    with transaction.atomic():
        user = request.user
        audit_event("account.deleted", actor=user, request=request)
        UserSession.objects.filter(user=user).update(revoked_at=timezone.now())
        user.email = f"deleted-{user.id}@invalid.local"
        user.username = user.email
        user.display_name = _("Deleted user")
        user.is_active = False
        user.set_unusable_password()
        user.save()
        logout(request)
    return redirect("landing")
