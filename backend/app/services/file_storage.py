import asyncio
import logging
from functools import lru_cache
from typing import Any, Protocol
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config.settings import Settings
from app.utils.exceptions import BusinessError

logger = logging.getLogger(__name__)

MAX_PRESIGNED_SECONDS = 900
ACCESS_DENIED_CODE = "AccessDenied"


class ObjectStorage(Protocol):
    """Protocol for object storage backends."""

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Upload data under the given key."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete the object under the given key."""
        ...  # False when the key may not delete (AccessDenied); logs a warning

    def presigned_get_url(
        self, key: str, expires_seconds: int = MAX_PRESIGNED_SECONDS, download_name: str | None = None
    ) -> str:
        """Return a temporary download URL for the key."""
        ...


def attachment_disposition(file_name: str) -> str:
    """Return a Content-Disposition attachment header for the file name."""
    ascii_fallback = file_name.encode("ascii", "ignore").decode().replace('"', "").replace("\\", "") or "download"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(file_name, safe='')}"


def build_s3_client(*, access_key_id: str, secret_access_key: str, endpoint_url: str, region: str) -> Any:
    """Create a boto3 S3 client for an S3-compatible endpoint."""
    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=config,
    )


class S3ObjectStorage:
    """Object storage backed by an S3-compatible bucket."""

    def __init__(self, *, bucket: str, client: Any, delete_client: Any | None) -> None:
        self.bucket = bucket
        self.client = client
        self.delete_client = delete_client

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Upload data to the bucket under the given key."""
        await asyncio.to_thread(
            self.client.put_object, Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )

    async def delete(self, key: str) -> bool:
        """Delete the object, returning False when access is denied."""
        client = self.delete_client if self.delete_client is not None else self.client
        try:
            await asyncio.to_thread(client.delete_object, Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != ACCESS_DENIED_CODE:
                raise
            logger.warning(
                "Object %s was left in the bucket: the storage key cannot delete objects (AccessDenied). "
                "Set S3_DELETE_ACCESS_KEY_ID and S3_DELETE_SECRET_ACCESS_KEY to a delete-capable key",
                key,
            )
            return False
        return True

    def presigned_get_url(
        self, key: str, expires_seconds: int = MAX_PRESIGNED_SECONDS, download_name: str | None = None
    ) -> str:
        """Return a presigned GET URL capped at the maximum lifetime."""
        params: dict[str, str] = {"Bucket": self.bucket, "Key": key}
        if download_name is not None:
            params["ResponseContentDisposition"] = attachment_disposition(download_name)
        return self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=min(expires_seconds, MAX_PRESIGNED_SECONDS),
        )


@lru_cache(maxsize=4)
def _cached_object_storage(
    bucket: str,
    endpoint_url: str,
    region: str,
    access_key_id: str,
    secret_access_key: str,
    delete_access_key_id: str,
    delete_secret_access_key: str,
) -> S3ObjectStorage:
    client = build_s3_client(
        access_key_id=access_key_id, secret_access_key=secret_access_key, endpoint_url=endpoint_url, region=region
    )
    delete_client = None
    if delete_access_key_id and delete_secret_access_key:
        delete_client = build_s3_client(
            access_key_id=delete_access_key_id,
            secret_access_key=delete_secret_access_key,
            endpoint_url=endpoint_url,
            region=region,
        )
    return S3ObjectStorage(bucket=bucket, client=client, delete_client=delete_client)


def build_object_storage(settings: Settings) -> S3ObjectStorage | None:
    """Return the configured S3 storage, or None when disabled."""
    if not settings.storage_enabled:
        return None
    delete_enabled = settings.storage_delete_enabled
    return _cached_object_storage(
        settings.S3_BUCKET,
        settings.S3_ENDPOINT_URL,
        settings.S3_REGION,
        settings.S3_ACCESS_KEY_ID,
        settings.S3_SECRET_ACCESS_KEY,
        settings.S3_DELETE_ACCESS_KEY_ID if delete_enabled else "",
        settings.S3_DELETE_SECRET_ACCESS_KEY if delete_enabled else "",
    )


def require_storage(storage: ObjectStorage | None) -> ObjectStorage:
    """Return the storage or raise if it is not configured."""
    if storage is None:
        raise BusinessError("storage_disabled", "File storage is not configured", 400)
    return storage


def presigned_url_or_none(storage: ObjectStorage | None, key: str | None) -> str | None:
    """Return a presigned URL for the key, or None if unavailable."""
    if storage is None or not key:
        return None
    return storage.presigned_get_url(key)


async def delete_object_best_effort(storage: ObjectStorage, key: str) -> bool:
    """Delete the object, logging and returning False on failure."""
    try:
        return await storage.delete(key)
    except Exception:
        logger.exception("Object %s was left in the bucket: deleting it failed", key)
        return False
