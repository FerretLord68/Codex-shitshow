from .models import AuditEvent

SENSITIVE_METADATA_KEYS = {"password", "token", "secret", "session", "authorization", "dietary_data"}


def audit_event(event, *, actor=None, household=None, target=None, request=None, metadata=None):
    safe_metadata = {
        key: value
        for key, value in (metadata or {}).items()
        if key.lower() not in SENSITIVE_METADATA_KEYS
    }
    return AuditEvent.objects.create(
        event=event,
        actor=actor if getattr(actor, "pk", None) else None,
        household=household,
        target_type=target._meta.label if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        request_id=getattr(request, "request_id", ""),
        ip_address=getattr(request, "client_ip", None),
        metadata=safe_metadata,
    )

