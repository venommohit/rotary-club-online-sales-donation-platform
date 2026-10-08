"""
Settings for the Padstow Rotary donation & sales platform.

Everything environment-specific comes from environment variables (or a local
.env file in development) so no secret ever lives in the repository. See
.env.example for the full list and README.md for deployment.

No ORM / DATABASES: data lives in Firebase Firestore. Sessions are signed
cookies, so there is no migrate step.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Tiny .env reader (KEY=value lines) so local dev needs no extra package."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _env(name, default=""):
    return os.environ.get(name, default)


def _flag(name, default=False):
    return _env(name, "1" if default else "0").lower() in ("1", "true", "yes", "on")


DEBUG = _flag("DJANGO_DEBUG", False)

SECRET_KEY = _env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key"
    else:
        raise ImproperlyConfigured("Set the DJANGO_SECRET_KEY environment variable.")

# ---- Hosts / HTTPS -------------------------------------------------------
ALLOWED_HOSTS = [h.strip() for h in _env("DJANGO_ALLOWED_HOSTS").split(",") if h.strip()]
_render_host = _env("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "[::1]"]

CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in ("localhost", "127.0.0.1", "[::1]")]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # behind Render's proxy
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600  # raise once you're happy the site works over HTTPS
    SECURE_CONTENT_TYPE_NOSNIFF = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 43200  # 12 hours

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "donations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "donations.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# No DATABASES — see module docstring.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

# ---- Static files (served by WhiteNoise) -----------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Firebase ---------------------------------------------------------------
FIREBASE_CREDENTIALS_JSON = _env("FIREBASE_CREDENTIALS_JSON")  # servers: whole JSON
FIREBASE_CREDENTIALS_PATH = _env("FIREBASE_CREDENTIALS_PATH",
                                 str(BASE_DIR / "firebase-service-account.json"))  # local file
FIREBASE_PROJECT_ID = _env("FIREBASE_PROJECT_ID")

# ---- Stripe -----------------------------------------------------------------
STRIPE_SECRET_KEY = _env("STRIPE_SECRET_KEY")          # sk_test_... / sk_live_...
STRIPE_WEBHOOK_SECRET = _env("STRIPE_WEBHOOK_SECRET")  # whsec_...
SITE_URL = _env("SITE_URL") or (f"https://{_render_host}" if _render_host else "")

# ---- Email ------------------------------------------------------------------
BREVO_API_KEY = _env("BREVO_API_KEY")                  # set on the server
EMAIL_FROM_ADDRESS = _env("EMAIL_FROM_ADDRESS")        # must be a verified Brevo sender
DEFAULT_FROM_EMAIL = EMAIL_FROM_ADDRESS or _env("EMAIL_HOST_USER")
if DEBUG and not BREVO_API_KEY and not _env("EMAIL_HOST_USER"):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = _env("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(_env("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = _env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = _env("EMAIL_HOST_PASSWORD")

# ---- Staff dashboard login ----------------------------------------------------
STAFF_USERNAME = _env("STAFF_USERNAME")
STAFF_PASSWORD = _env("STAFF_PASSWORD")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
