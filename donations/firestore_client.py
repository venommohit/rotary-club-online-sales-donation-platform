# donations/firestore_client.py
#
# Single place that talks to Firebase. Everything else in the app goes
# through donations/firestore_data.py, not this file directly.

import json
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from django.conf import settings


def _load_credentials():
    """
    Hosted servers (Render etc.) shouldn't have a key *file* checked into the repo,
    so the whole service-account JSON can be supplied in FIREBASE_CREDENTIALS_JSON.
    Locally, fall back to the key file next to manage.py.
    """
    raw = settings.FIREBASE_CREDENTIALS_JSON
    if raw:
        return credentials.Certificate(json.loads(raw))

    path = settings.FIREBASE_CREDENTIALS_PATH
    if path and os.path.exists(path):
        return credentials.Certificate(path)

    raise RuntimeError(
        "No Firebase credentials found. Set FIREBASE_CREDENTIALS_JSON (the full "
        "service-account JSON) on a server, or put firebase-service-account.json "
        "next to manage.py locally — see README.md."
    )


@lru_cache(maxsize=1)
def get_db():
    """Cached Firestore client; the Admin SDK is initialised once per process."""
    if not firebase_admin._apps:
        options = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None
        firebase_admin.initialize_app(_load_credentials(), options)
    return firestore.client()
