"""
Storage abstraction layer for Verifact radiographs and heatmaps.
Supports Local Disk (default), Supabase Storage, and AWS S3 via environment variables.
"""

import os
import io
import uuid
from pathlib import Path
from typing import Optional

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
LOCAL_STORAGE_DIR = Path(os.getenv("LOCAL_STORAGE_DIR", "uploads")).resolve()
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class BaseStorageService:
    def save_bytes(self, data: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        raise NotImplementedError

    def get_bytes(self, file_id_or_url: str) -> Optional[bytes]:
        raise NotImplementedError


class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: Path = LOCAL_STORAGE_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, data: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        ext = Path(filename).suffix or ".jpg"
        unique_name = f"{uuid.uuid4().hex}_{Path(filename).stem}{ext}"
        target_path = self.base_dir / unique_name
        with open(target_path, "wb") as f:
            f.write(data)
        # Return web accessible path
        return f"/uploads/{unique_name}"

    def get_bytes(self, file_id_or_url: str) -> Optional[bytes]:
        filename = Path(file_id_or_url).name
        target_path = self.base_dir / filename
        if target_path.exists():
            with open(target_path, "rb") as f:
                return f.read()
        return None


class SupabaseStorageService(BaseStorageService):
    def __init__(self):
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required for Supabase storage.")
        self.client = create_client(url, key)
        self.bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "verifact-artifacts")

    def save_bytes(self, data: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        self.client.storage.from_(self.bucket).upload(
            path=unique_name,
            file=data,
            file_options={"content-type": content_type}
        )
        return self.client.storage.from_(self.bucket).get_public_url(unique_name)

    def get_bytes(self, file_id_or_url: str) -> Optional[bytes]:
        filename = Path(file_id_or_url).name
        res = self.client.storage.from_(self.bucket).download(filename)
        return res


def get_storage_service() -> BaseStorageService:
    if STORAGE_BACKEND == "supabase" and os.getenv("SUPABASE_URL"):
        try:
            return SupabaseStorageService()
        except Exception as e:
            print(f"[Storage] Supabase init failed ({e}), falling back to local storage.")
    return LocalStorageService()
