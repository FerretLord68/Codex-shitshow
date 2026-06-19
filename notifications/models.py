from django.conf import settings
from django.db import models

from common.models import TimeStampedModel, UUIDModel


class Notification(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    household = models.ForeignKey("households.Household", on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at", "-created_at"])]


class NotificationPreference(UUIDModel, TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    in_app = models.JSONField(default=dict, blank=True)
    email = models.JSONField(default=dict, blank=True)
    quiet_hours = models.JSONField(default=dict, blank=True)

