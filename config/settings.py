import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None, *, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Required environment variable {name} is missing")
    return value


def env_bool(name, default=False):
    return str(env(name, str(default))).lower() in {"1", "true", "yes", "on"}


def env_int(name, default, *, minimum=None):
    try:
        value = int(env(name, default))
    except (TypeError, ValueError) as error:
        raise ImproperlyConfigured(f"{name} must be an integer") from error
    if minimum is not None and value < minimum:
        raise ImproperlyConfigured(f"{name} must be at least {minimum}")
    return value


ENVIRONMENT = env("ENVIRONMENT", "development")
DEBUG = env_bool("DEBUG", False)
if ENVIRONMENT == "production" and DEBUG:
    raise ImproperlyConfigured("DEBUG must be false in production")

SECRET_KEY = env("SECRET_KEY", "unsafe-development-key", required=ENVIRONMENT == "production")
APP_URL = env("APP_URL", "http://localhost:8000").rstrip("/")
ALLOWED_HOSTS = [x.strip() for x in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [APP_URL] if APP_URL.startswith(("http://", "https://")) else []
TRUSTED_PROXY_CIDRS = [x.strip() for x in env("TRUSTED_PROXY_CIDRS", "").split(",") if x.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "common",
    "accounts",
    "audit",
    "households",
    "catalog",
    "recipes",
    "planning",
    "inventory",
    "shopping",
    "offers",
    "budgets",
    "notifications",
    "operations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.RequestIDMiddleware",
    "common.middleware.TrustedProxyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.ActiveSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.SecurityHeadersMiddleware",
    "audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "common.context_processors.application",
        ],
    },
}]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "mealhouse"),
        "USER": env("POSTGRES_USER", "mealhouse"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 5},
        "TEST": {"NAME": env("POSTGRES_TEST_DB", "mealhouse_test")},
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "landing"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "da"
LANGUAGES = [("da", "Dansk"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Copenhagen"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = Path(env("MEDIA_ROOT", BASE_DIR / "media"))
MEDIA_URL = "/media/"
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

SESSION_COOKIE_NAME = "__Host-mealhouse_session"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_NAME = "__Host-mealhouse_csrf"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_PATH = "/"
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SILENCED_SYSTEM_CHECKS = [
    "security.W005",  # Parent-domain subdomains are not controlled by this service.
    "security.W008",  # HTTPS redirect is enforced by the external proxy.
    "security.W021",  # HSTS preload is a parent-domain operational decision.
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
EMAIL_FILE_PATH = Path(env("EMAIL_FILE_PATH", "/var/lib/mealhouse/email-spool"))
SMTP_HOST = env("SMTP_HOST", "")
SMTP_PORT = env_int("SMTP_PORT", 587, minimum=1)
SMTP_SECURE = env_bool("SMTP_SECURE", False)
SMTP_USERNAME = env("SMTP_USERNAME", "")
SMTP_PASSWORD = env("SMTP_PASSWORD", "")
SMTP_FROM_ADDRESS = env("SMTP_FROM_ADDRESS", "")
SMTP_FROM_NAME = env("SMTP_FROM_NAME", "MealHouse")
SMTP_CONNECTION_TIMEOUT_MS = env_int("SMTP_CONNECTION_TIMEOUT_MS", 10000, minimum=1000)
SMTP_SEND_TIMEOUT_MS = env_int("SMTP_SEND_TIMEOUT_MS", 15000, minimum=1000)
EMAIL_HOST = SMTP_HOST
EMAIL_PORT = SMTP_PORT
EMAIL_HOST_USER = SMTP_USERNAME
EMAIL_HOST_PASSWORD = SMTP_PASSWORD
EMAIL_USE_SSL = SMTP_SECURE
EMAIL_USE_TLS = not SMTP_SECURE
EMAIL_TIMEOUT = max(SMTP_CONNECTION_TIMEOUT_MS, SMTP_SEND_TIMEOUT_MS) / 1000
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    f"{SMTP_FROM_NAME} <{SMTP_FROM_ADDRESS}>" if SMTP_FROM_ADDRESS else "MealHouse <no-reply@localhost>",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
if ENVIRONMENT == "production" and EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    for required_name, required_value in (
        ("SMTP_HOST", SMTP_HOST),
        ("SMTP_USERNAME", SMTP_USERNAME),
        ("SMTP_PASSWORD", SMTP_PASSWORD),
        ("SMTP_FROM_ADDRESS", SMTP_FROM_ADDRESS),
    ):
        if not required_value:
            raise ImproperlyConfigured(f"Required environment variable {required_name} is missing")
    if not SMTP_FROM_ADDRESS.lower().endswith("@taxoz.org"):
        raise ImproperlyConfigured("SMTP_FROM_ADDRESS must use the authorized taxoz.org domain")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "common.logging.JsonFormatter",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {"django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}

OFFER_SOURCE_URL = env("OFFER_SOURCE_URL", "")
SALLING_GROUP_API_TOKEN = env("SALLING_GROUP_API_TOKEN", "")
SALLING_GROUP_API_BASE_URL = env("SALLING_GROUP_API_BASE_URL", "https://api.sallinggroup.com").rstrip("/")
SALLING_GROUP_REQUEST_TIMEOUT_MS = env_int("SALLING_GROUP_REQUEST_TIMEOUT_MS", 10000, minimum=1000)
SALLING_GROUP_CACHE_TTL_SECONDS = env_int("SALLING_GROUP_CACHE_TTL_SECONDS", 300, minimum=1)
SALLING_GROUP_MAX_RETRIES = env_int("SALLING_GROUP_MAX_RETRIES", 2, minimum=0)
SALLING_GROUP_IMAGE_HOSTS = {
    value.strip().lower()
    for value in env("SALLING_GROUP_IMAGE_HOSTS", "dam.dsg.dk").split(",")
    if value.strip()
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mealhouse-runtime-cache",
    }
}
MAX_IMAGE_BYTES = env_int("MAX_IMAGE_BYTES", 5 * 1024 * 1024, minimum=1024)
SECURITY_TOKEN_TTL_SECONDS = env_int("SECURITY_TOKEN_TTL_SECONDS", 3600, minimum=300)
INVITATION_TTL_SECONDS = env_int("INVITATION_TTL_SECONDS", 604800, minimum=3600)
