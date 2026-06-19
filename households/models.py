import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel, UUIDModel

DEFAULT_MEMBER_PERMISSIONS = [
    "meal.view", "meal.suggest", "recipe.view", "shopping.view",
    "shopping.check", "inventory.view", "inventory.edit",
]
MANAGER_PERMISSIONS = [
    "meal.view", "meal.edit", "meal.suggest", "recipe.view", "recipe.create",
    "recipe.edit", "shopping.view", "shopping.edit", "shopping.check",
    "inventory.view", "inventory.edit", "budget.view", "nutrition.view",
    "member.invite", "household.manage",
]


class Household(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    currency = models.CharField(max_length=3, default="DKK")
    locale = models.CharField(max_length=10, default="da")
    timezone = models.CharField(max_length=50, default="Europe/Copenhagen")
    week_starts_on = models.PositiveSmallIntegerField(default=1)
    settings = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class Membership(UUIDModel, TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    permissions = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["household", "user"], name="unique_household_user"),
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def has_permission(self, permission):
        if not self.is_active:
            return False
        if self.role == self.Role.OWNER:
            return True
        defaults = MANAGER_PERMISSIONS if self.role == self.Role.MANAGER else DEFAULT_MEMBER_PERMISSIONS
        return permission in set(defaults) | set(self.permissions)

    def clean(self):
        if self.pk and self.role != self.Role.OWNER:
            original = Membership.objects.filter(pk=self.pk, role=self.Role.OWNER).exists()
            if original and not Membership.objects.filter(
                household=self.household, role=self.Role.OWNER, is_active=True
            ).exclude(pk=self.pk).exists():
                raise ValidationError("A household must retain at least one owner.")


class HouseholdMemberProfile(UUIDModel, TimeStampedModel):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="member_profiles")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    display_name = models.CharField(max_length=100)
    age_group = models.CharField(
        max_length=20,
        choices=[("adult", "Adult"), ("child", "Child"), ("senior", "Senior"), ("unspecified", "Unspecified")],
        default="unspecified",
    )
    portion_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    daily_calorie_target = models.PositiveIntegerField(null=True, blank=True)
    meal_targets = models.JSONField(default=dict, blank=True)
    protein_target_g = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    carbohydrate_target_g = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    fat_target_g = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    dietary_preferences = models.JSONField(default=list, blank=True)
    allergies = models.JSONField(default=list, blank=True)
    foods_to_avoid = models.JSONField(default=list, blank=True)
    disliked_foods = models.JSONField(default=list, blank=True)
    favourite_foods = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["household", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_household_linked_profile",
            )
        ]


class AttendanceSchedule(UUIDModel, TimeStampedModel):
    profile = models.ForeignKey(HouseholdMemberProfile, on_delete=models.CASCADE, related_name="attendance")
    weekday = models.PositiveSmallIntegerField()
    meal_type = models.CharField(max_length=50)
    present = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "weekday", "meal_type"], name="unique_attendance_slot"),
            models.CheckConstraint(condition=models.Q(weekday__gte=1, weekday__lte=7), name="valid_weekday"),
        ]


class HouseholdInvitation(UUIDModel, TimeStampedModel):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    permissions = models.JSONField(default=list, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_invitations")
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def issue(cls, household, email, invited_by, role=Membership.Role.MEMBER, permissions=None):
        raw = secrets.token_urlsafe(32)
        invitation = cls.objects.create(
            household=household,
            email=email.strip().lower(),
            invited_by=invited_by,
            role=role,
            permissions=permissions or [],
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        return invitation, raw

    @property
    def usable(self):
        return not self.accepted_at and not self.revoked_at and self.expires_at > timezone.now()

    @classmethod
    def find(cls, raw):
        return cls.objects.filter(token_hash=hashlib.sha256(raw.encode()).hexdigest()).first()

