"""
Google Cloud Storage uploader with local filesystem fallback.

If GCS credentials are absent (no GOOGLE_CLOUD_BUCKET env var), files are
saved to backend/static/ and served via FastAPI's StaticFiles mount at /static.
"""

import os
import shutil
import uuid
from pathlib import Path

# Resolve static dir relative to this file's location
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

_GCS_AVAILABLE = False
_storage_client = None
_bucket_name = None


def _init_gcs() -> bool:
    """Lazily initialise GCS client. Returns True if GCS is usable."""
    global _GCS_AVAILABLE, _storage_client, _bucket_name
    if _GCS_AVAILABLE:
        return True
    bucket = os.environ.get("GOOGLE_CLOUD_BUCKET", "")
    if not bucket:
        return False
    try:
        from google.cloud import storage  # type: ignore
        _storage_client = storage.Client()
        _bucket_name = bucket
        _GCS_AVAILABLE = True
        return True
    except Exception:
        return False


def upload_file(local_path: str, gcs_path: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a file to GCS and return its public URL.
    Falls back to serving from /static if GCS is unavailable.

    Args:
        local_path: Absolute path to the local file.
        gcs_path: Destination path within the GCS bucket (e.g. "audio/session123.wav").
        content_type: MIME type of the file.

    Returns:
        Public URL string.
    """
    if _init_gcs():
        try:
            bucket = _storage_client.bucket(_bucket_name)
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path, content_type=content_type)
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"[gcs_uploader] GCS upload failed, falling back to local: {e}")

    # Fallback: copy to static dir
    filename = f"{uuid.uuid4()}_{Path(local_path).name}"
    dest = STATIC_DIR / filename
    shutil.copy2(local_path, dest)
    # Return relative URL — FastAPI serves /static from this folder
    base_url = os.environ.get("BACKEND_URL", "http://localhost:8080")
    return f"{base_url}/static/{filename}"


def get_signed_url(gcs_path: str, expiry_minutes: int = 60) -> str:
    """
    Generate a signed URL for a private GCS object.
    Falls back to the public URL if GCS is unavailable.
    """
    if _init_gcs():
        try:
            import datetime
            bucket = _storage_client.bucket(_bucket_name)
            blob = bucket.blob(gcs_path)
            url = blob.generate_signed_url(
                expiration=datetime.timedelta(minutes=expiry_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            print(f"[gcs_uploader] Signed URL generation failed: {e}")
    # Return a placeholder — caller should handle gracefully
    return f"http://localhost:8080/static/{Path(gcs_path).name}"
