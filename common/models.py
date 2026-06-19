import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class VersionedModel(models.Model):
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class HouseholdOwnedModel(models.Model):
    household = models.ForeignKey("households.Household", on_delete=models.CASCADE)

    class Meta:
        abstract = True

