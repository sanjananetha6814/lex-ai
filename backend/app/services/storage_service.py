import os
import uuid
import abc
from typing import Tuple
from fastapi import HTTPException, status
from app.config import settings

class BaseStorageService(abc.ABC):
    @abc.abstractmethod
    def save_file(self, content: bytes, original_filename: str) -> Tuple[str, str]:
        pass

    @abc.abstractmethod
    def read_file(self, storage_path: str) -> bytes:
        pass

    @abc.abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        pass

class LocalStorageService(BaseStorageService):
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    def _sanitize_extension(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not allowed. Supported types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        return ext

    def save_file(self, content: bytes, original_filename: str) -> Tuple[str, str]:
        ext = self._sanitize_extension(original_filename)
        # Generate safe unique filename
        safe_name = f"{uuid.uuid4().hex}{ext}"
        storage_path = os.path.join(self.upload_dir, safe_name)

        with open(storage_path, "wb") as f:
            f.write(content)

        return storage_path, safe_name

    def read_file(self, storage_path: str) -> bytes:
        if not os.path.exists(storage_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored file was not found on disk."
            )
        with open(storage_path, "rb") as f:
            return f.read()

    def delete_file(self, storage_path: str) -> bool:
        if os.path.exists(storage_path):
            os.remove(storage_path)
            return True
        return False

class S3StorageService(BaseStorageService):
    """
    Prepared architecture for Object Storage (AWS S3 / GCS / Cloudflare R2).
    """
    def __init__(self, bucket_name: str = "lexai-documents"):
        self.bucket_name = bucket_name
        self.is_connected = False

    def save_file(self, content: bytes, original_filename: str) -> Tuple[str, str]:
        raise NotImplementedError("S3 object storage is not configured. Using local storage adapter.")

    def read_file(self, storage_path: str) -> bytes:
        raise NotImplementedError("S3 object storage is not configured. Using local storage adapter.")

    def delete_file(self, storage_path: str) -> bool:
        raise NotImplementedError("S3 object storage is not configured. Using local storage adapter.")

default_storage_service = LocalStorageService()
