"""
Serwis przechowywania plików — S3/MinIO.
Ulepszenie: presigned URLs + automatyczne wykrywanie content-type.
"""

import os
import uuid
from pathlib import Path

import boto3
import structlog
from botocore.config import Config

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class StorageService:
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION,
            "config": Config(signature_version="s3v4"),
        }
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        self.s3 = boto3.client("s3", **kwargs)

    def upload_file(self, local_path: str, key: str, content_type: str | None = None) -> str:
        """Uploaduje plik do S3 i zwraca publiczny URL dostępny dla przeglądarki."""
        ct = content_type or self._guess_content_type(local_path)

        logger.info("Upload do S3", key=key, content_type=ct)

        self.s3.upload_file(
            local_path,
            self.bucket,
            key,
            ExtraArgs={"ContentType": ct},
        )

        return self._public_url(key)

    def upload_bytes(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        """Uploaduje bajty do S3 i zwraca publiczny URL."""
        import io

        self.s3.upload_fileobj(io.BytesIO(data), self.bucket, key, ExtraArgs={"ContentType": content_type})

        return self._public_url(key)

    def _public_url(self, key: str) -> str:
        """Zwraca URL dostępny dla przeglądarki/klienta zewnętrznego.

        Priorytety:
        1. S3_PUBLIC_BASE_URL (jawnie ustawiony publiczny base, np. http://localhost:9000)
        2. AWS S3 presigned — gdy brak endpoint (produkcyjne S3)
        3. Fallback: S3_ENDPOINT_URL (uwaga: w dev może być niedostępny z przeglądarki)
        """
        if settings.S3_PUBLIC_BASE_URL:
            base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
            return f"{base}/{self.bucket}/{key}"
        if not settings.S3_ENDPOINT_URL:
            return f"https://{self.bucket}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
        # Ostateczny fallback — adres wewnętrzny (MinIO); może nie działać z przeglądarki
        logger.warning(
            "S3_PUBLIC_BASE_URL nie ustawione; URL może być niedostępny z przeglądarki",
            key=key,
        )
        return f"{settings.S3_ENDPOINT_URL}/{self.bucket}/{key}"

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generuje presigned URL do odczytu."""
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, key: str):
        """Usuwa plik z S3."""
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    @staticmethod
    def generate_key(prefix: str, extension: str) -> str:
        """Generuje unikalny klucz: prefix/uuid.ext"""
        return f"{prefix}/{uuid.uuid4().hex}.{extension}"

    @staticmethod
    def _guess_content_type(path: str) -> str:
        ext = Path(path).suffix.lower()
        mapping = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".srt": "text/plain",
        }
        return mapping.get(ext, "application/octet-stream")
