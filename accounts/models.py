import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email).lower()
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True, is_email_verified=True)
        return self._create_user(email, password, **extra_fields)


class User(UUIDModel, AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=254, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    locale = models.CharField(max_length=10, choices=[("da", "Dansk"), ("en", "English")], default="da")
    is_email_verified = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    last_password_change_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.username = self.email
        super().save(*args, **kwargs)

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_login_failure(self):
        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            delay = min(900, 2 ** min(self.failed_login_count - 4, 10))
            self.locked_until = timezone.now() + timedelta(seconds=delay)
        self.save(update_fields=["failed_login_count", "locked_until"])

    def clear_login_failures(self):
        if self.failed_login_count or self.locked_until:
            self.failed_login_count = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_count", "locked_until"])


class UserSession(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="active_sessions")
    session_key_hash = models.CharField(max_length=64, unique=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def hash_key(key):
        return hashlib.sha256(key.encode()).hexdigest()

    @property
    def active(self):
        return not self.revoked_at and self.expires_at > timezone.now()


class SecurityToken(UUIDModel, TimeStampedModel):
    class Purpose(models.TextChoices):
        EMAIL_VERIFY = "email_verify", "Email verification"
        PASSWORD_RESET = "password_reset", "Password reset"
        EMAIL_CHANGE = "email_change", "Email change"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="security_tokens")
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["purpose", "token_hash"])]

    @classmethod
    def issue(cls, user, purpose, ttl=timedelta(hours=1)):
        raw = secrets.token_urlsafe(32)
        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
        cls.objects.create(
            user=user,
            purpose=purpose,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=timezone.now() + ttl,
        )
        return raw

    @classmethod
    def consume(cls, raw, purpose):
        digest = hashlib.sha256(raw.encode()).hexdigest()
        token = cls.objects.select_for_update().filter(
            token_hash=digest,
            purpose=purpose,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).first()
        if token:
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])
        return token


class TwoFactorSetting(UUIDModel, TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="two_factor")
    enabled = models.BooleanField(default=False)
    method = models.CharField(max_length=20, choices=[("totp", "TOTP"), ("webauthn", "WebAuthn")], default="totp")
    secret_encrypted = models.BinaryField(null=True, blank=True)
    recovery_codes_hash = models.JSONField(default=list, blank=True)

