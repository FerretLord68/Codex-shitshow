from django.conf import settings
from django.db import models

from common.models import TimeStampedModel, UUIDModel


class AuditEvent(UUIDModel, TimeStampedModel):
    event = models.CharField(max_length=100, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    household = models.ForeignKey("households.Household", on_delete=models.SET_NULL, null=True, blank=True)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["household", "-created_at"])]

    def save(self, *args, **kwargs):
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit events are append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit events are append-only")


class SupportAccess(UUIDModel, TimeStampedModel):
    administrator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    household = models.ForeignKey("households.Household", on_delete=models.PROTECT)
    reason = models.TextField()
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

