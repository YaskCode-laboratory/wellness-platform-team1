import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase() -> firestore.Client:
    """Initialize Firebase app and return Firestore client."""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firestore.client()

db: firestore.Client = init_firebase()
