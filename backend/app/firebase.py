from functools import lru_cache

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.storage import Bucket

from .config import get_settings


@lru_cache
def _app() -> firebase_admin.App:
    settings = get_settings()
    if settings.google_application_credentials:
        cred = credentials.Certificate(settings.google_application_credentials)
    else:
        cred = credentials.ApplicationDefault()
    return firebase_admin.initialize_app(
        cred,
        {
            "projectId": settings.firebase_project_id or None,
            "storageBucket": settings.firebase_storage_bucket or None,
        },
    )


def db() -> FirestoreClient:
    _app()
    return firestore.client()


def bucket() -> Bucket:
    return storage.bucket(app=_app())


def verify_id_token(token: str) -> dict[str, object]:
    _app()
    return fb_auth.verify_id_token(token)
