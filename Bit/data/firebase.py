import os
import firebase_admin
from firebase_admin import credentials, firestore, storage

from django.conf import settings


_service_account = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", getattr(settings, "FIREBASE_SERVICE_ACCOUNT_FILE", None))
_bucket_name = getattr(settings, "FIREBASE_STORAGE_BUCKET", None)

if not firebase_admin._apps:
    if _service_account:
        cred = credentials.Certificate(_service_account)
        firebase_admin.initialize_app(cred, {
            'storageBucket': _bucket_name
        } if _bucket_name else None)
    else:
        firebase_admin.initialize_app()

db = firestore.client()
bucket = storage.bucket() if _bucket_name else None
