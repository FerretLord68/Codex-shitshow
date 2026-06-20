from django.utils import timezone

from operations.services import enqueue

from .mail import deliver
from .models import Notification


def queue_email(to, subject, template, context, *, dedupe_key):
    safe_context = {}
    for key, value in context.items():
        if key == "user":
            safe_context["display_name"] = value.display_name
        elif key == "household":
            safe_context["household_name"] = value.name
        else:
            safe_context[key] = value
    return enqueue(
        "email.send",
        {"to": to, "subject": str(subject), "template": template, "context": safe_context},
        dedupe_key=dedupe_key,
    )


def deliver_email(payload):
    return deliver(payload)


def notify(user, kind, title, body="", household=None, action_url=""):
    return Notification.objects.create(
        user=user, kind=kind, title=title, body=body, household=household, action_url=action_url
    )


def create_expiration_notifications():
    from inventory.models import InventoryItem

    for item in InventoryItem.objects.expiring_soon().select_related("household"):
        for membership in item.household.memberships.filter(is_active=True).select_related("user"):
            existing = Notification.objects.filter(
                user=membership.user,
                kind="inventory.expiring",
                body__contains=str(item.id),
                created_at__date=timezone.localdate(),
            ).exists()
            if not existing:
                notify(
                    membership.user,
                    "inventory.expiring",
                    "Mad udløber snart",
                    f"{item.product_name} [{item.id}]",
                    item.household,
                    "/inventory/",
                )
