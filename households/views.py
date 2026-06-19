from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from audit.services import audit_event
from common.decorators import household_permission
from notifications.services import queue_email

from .forms import HouseholdForm, InvitationForm, MemberProfileForm
from .models import HouseholdInvitation, HouseholdMemberProfile, Membership


@login_required
def household_list(request):
    return render(request, "households/list.html", {"memberships": request.user.memberships.filter(is_active=True)})


@login_required
def create(request):
    form = HouseholdForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            household = form.save()
            Membership.objects.create(household=household, user=request.user, role=Membership.Role.OWNER)
            HouseholdMemberProfile.objects.create(
                household=household,
                user=request.user,
                display_name=request.user.display_name or request.user.email,
            )
            audit_event("household.created", actor=request.user, household=household, request=request)
        return redirect("households:detail", household_id=household.id)
    return render(request, "households/form.html", {"form": form})


@login_required
@household_permission("meal.view")
def detail(request, household_id):
    return render(request, "households/detail.html", {
        "household": request.household,
        "membership": request.membership,
        "members": request.household.memberships.filter(is_active=True).select_related("user"),
        "profiles": request.household.member_profiles.all(),
    })


@login_required
@household_permission("household.manage")
def edit(request, household_id):
    form = HouseholdForm(request.POST or None, instance=request.household)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit_event("household.updated", actor=request.user, household=request.household, request=request)
        return redirect("households:detail", household_id=household_id)
    return render(request, "households/form.html", {"form": form, "household": request.household})


@login_required
@household_permission("member.invite")
def invite(request, household_id):
    form = InvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        invitation, raw = HouseholdInvitation.issue(
            request.household,
            form.cleaned_data["email"],
            request.user,
            form.cleaned_data["role"],
        )
        url = f"{settings.APP_URL}/households/invitations/{raw}/"
        queue_email(
            invitation.email,
            _("Invitation to MealHouse"),
            "email/invitation.txt",
            {"household": request.household, "url": url},
            dedupe_key=f"invite:{invitation.id}",
        )
        audit_event("household.invitation_created", actor=request.user, household=request.household, target=invitation, request=request)
        messages.success(request, _("Invitation sent."))
        return redirect("households:detail", household_id=household_id)
    return render(request, "households/invite.html", {"form": form, "household": request.household})


@login_required
def accept_invitation(request, token):
    invitation = HouseholdInvitation.find(token)
    if not invitation or not invitation.usable:
        return render(request, "households/invitation_invalid.html", status=410)
    if request.user.email.lower() != invitation.email.lower():
        return render(request, "households/invitation_wrong_account.html", {"email": invitation.email}, status=403)
    if request.method == "POST":
        with transaction.atomic():
            invitation = HouseholdInvitation.objects.select_for_update().get(pk=invitation.pk)
            if not invitation.usable:
                return render(request, "households/invitation_invalid.html", status=410)
            Membership.objects.update_or_create(
                household=invitation.household,
                user=request.user,
                defaults={"role": invitation.role, "permissions": invitation.permissions, "is_active": True},
            )
            HouseholdMemberProfile.objects.get_or_create(
                household=invitation.household,
                user=request.user,
                defaults={"display_name": request.user.display_name or request.user.email},
            )
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["accepted_at"])
            audit_event("household.invitation_accepted", actor=request.user, household=invitation.household, target=invitation, request=request)
        return redirect("households:detail", household_id=invitation.household_id)
    return render(request, "households/invitation_accept.html", {"invitation": invitation})


@login_required
@household_permission("member.invite")
@require_POST
def revoke_invitation(request, household_id, invitation_id):
    invitation = get_object_or_404(HouseholdInvitation, pk=invitation_id, household=request.household)
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["revoked_at"])
    audit_event("household.invitation_revoked", actor=request.user, household=request.household, target=invitation, request=request)
    return redirect("households:detail", household_id=household_id)


@login_required
@household_permission("household.manage")
def profile_create(request, household_id):
    form = MemberProfileForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.household = request.household
        profile.save()
        return redirect("households:detail", household_id=household_id)
    return render(request, "households/profile_form.html", {"form": form, "household": request.household})


@login_required
@household_permission("household.manage")
@require_POST
def transfer_ownership(request, household_id, membership_id):
    if request.membership.role != Membership.Role.OWNER:
        raise PermissionDenied
    target = get_object_or_404(Membership, pk=membership_id, household=request.household, is_active=True)
    with transaction.atomic():
        target.role = Membership.Role.OWNER
        target.save(update_fields=["role"])
        if request.POST.get("retain_owner") != "yes":
            request.membership.role = Membership.Role.MANAGER
            request.membership.save(update_fields=["role"])
        audit_event("household.ownership_transferred", actor=request.user, household=request.household, target=target, request=request)
    return redirect("households:detail", household_id=household_id)

