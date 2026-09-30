"""
Django settings for the Padstow Rotary donation & sales platform.

Data now lives in Firebase Firestore instead of a SQL database (see
donations/firestore_client.py and donations/firestore_data.py), and
Django's own admin/auth apps have been dropped along with it — the
committee dashboard is the app's own views, not /admin/.

With no ORM models anywhere in the project, this file deliberately has
NO `DATABASES` setting at all. Django is fine running without one
(it falls back to an empty {} internally) as long as nothing tries to
use the ORM — which nothing here does. That also means there is no
`manage.py migrate` step for this project any more.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# TODO: replace with a real secret and load it from an environment
# variable before this ever goes near a real server.
SECRET_KEY = "django-insecure-change-me-before-deploying-xyz123"

# TODO: set DEBUG = False and configure ALLOWED_HOSTS before deploying.
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "donations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],  # not needed — donations/templates/ is picked up via APP_DIRS
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# No DATABASES setting — see module docstring. Django defaults to {}.

# Sessions are stored in a signed cookie on the client rather than a
# database table, since there is no SQL database to store them in any
# more. The cookie is signed (not encrypted) using SECRET_KEY, so don't
# put anything in the session the user shouldn't be able to read —
# only IDs/flags (pending_transaction, last_reference, staff_user),
# never secrets.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# donations/static/donations/... is auto-discovered via APP_DIRS finder,
# no STATICFILES_DIRS needed for this single-app project.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Firebase
# ---------------------------------------------------------------------------
# Path to the service account JSON key downloaded from the Firebase
# console (see README.md, section "Firebase setup"). Reads from an
# environment variable so the key file itself never gets committed.
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "FIREBASE_CREDENTIALS_PATH",
    str(BASE_DIR / "firebase-service-account.json"),
)
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
