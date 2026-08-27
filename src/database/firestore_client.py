"""Cliente Firestore de la plataforma."""

import firebase_admin
from firebase_admin import credentials, firestore

from src.utils.config import GCP_PROJECT


def init_firebase() -> firestore.Client:
    """Initialize Firebase app and return Firestore client."""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {"projectId": GCP_PROJECT})
    return firestore.client()


db: firestore.Client = init_firebase()