from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel, UUIDModel


class FeatureFlag(UUIDModel, TimeStampedModel):
    key = models.SlugField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    configuration = models.JSONField(default=dict, blank=True)


class ApplicationSetting(UUIDModel, TimeStampedModel):
    key = models.SlugField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    sensitive = models.BooleanField(default=False)


class BackgroundJob(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        DEAD = "dead", "Dead"

    kind = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict)
    dedupe_key = models.CharField(max_length=200, null=True, blank=True, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    run_after = models.DateTimeField(default=timezone.now, db_index=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_type = models.CharField(max_length=100, blank=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "run_after"])]


class ServiceHeartbeat(UUIDModel, TimeStampedModel):
    service = models.CharField(max_length=100, unique=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

