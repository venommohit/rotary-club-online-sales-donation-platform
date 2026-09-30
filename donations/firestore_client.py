# donations/firestore_client.py
#
# Single place that talks to Firebase. Everything else in the app goes
# through donations/firestore_data.py, not this file directly.

import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from django.conf import settings


@lru_cache(maxsize=1)
def get_db():
    """
    Returns a cached Firestore client, initialising the Firebase Admin
    SDK on first use. Cached with lru_cache so we only connect once per
    process, not on every request.
    """
    if not firebase_admin._apps:
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if not cred_path or not os.path.exists(cred_path):
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_PATH is not set or the file doesn't "
                "exist. Download a service account key from the Firebase "
                "console (Project settings -> Service accounts -> "
                "Generate new private key) and point FIREBASE_CREDENTIALS_PATH "
                "at it — see README.md for the full walkthrough."
            )
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})

    return firestore.client()
