import logging
from typing import Any

import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from app.services.file_storage import (
    S3ObjectStorage,
    attachment_disposition,
    build_object_storage,
    build_s3_client,
    delete_object_best_effort,
    presigned_url_or_none,
    require_storage,
)
from app.utils.dependencies import get_object_storage
from app.utils.exceptions import BusinessError
from tests.conftest import make_settings
from tests.fakes import InMemoryObjectStorage

BUCKET = "saaskit"
ENDPOINT = "http://storage.test"


def make_client() -> Any:
    return build_s3_client(
        access_key_id="test-key", secret_access_key="test-secret", endpoint_url=ENDPOINT, region="auto"
    )


def test_client_uses_runsite_settings() -> None:
    client = make_client()

    assert client.meta.config.signature_version == "s3v4"
    assert client.meta.config.s3 == {"addressing_style": "path"}
    assert client.meta.config.request_checksum_calculation == "when_required"
    assert client.meta.config.response_checksum_validation == "when_required"


async def test_put_uploads_with_content_type() -> None:
    client = make_client()
    storage = S3ObjectStorage(bucket=BUCKET, client=client, delete_client=None)

    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            {},
            {"Bucket": BUCKET, "Key": "orgs/1/files/a.txt", "Body": b"hello", "ContentType": "text/plain"},
        )
        await storage.put("orgs/1/files/a.txt", b"hello", "text/plain")
        stubber.assert_no_pending_responses()


async def test_delete_uses_main_client_without_delete_key() -> None:
    client = make_client()
    storage = S3ObjectStorage(bucket=BUCKET, client=client, delete_client=None)

    with Stubber(client) as stubber:
        stubber.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": "users/1/avatar"})
        assert await storage.delete("users/1/avatar") is True
        stubber.assert_no_pending_responses()


async def test_delete_uses_dedicated_delete_client_when_configured() -> None:
    client = make_client()
    delete_client = make_client()
    storage = S3ObjectStorage(bucket=BUCKET, client=client, delete_client=delete_client)

    with Stubber(client) as main_stubber, Stubber(delete_client) as delete_stubber:
        delete_stubber.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": "users/1/avatar"})
        assert await storage.delete("users/1/avatar") is True
        delete_stubber.assert_no_pending_responses()
        main_stubber.assert_no_pending_responses()


async def test_delete_access_denied_logs_and_returns_false(caplog: pytest.LogCaptureFixture) -> None:
    client = make_client()
    storage = S3ObjectStorage(bucket=BUCKET, client=client, delete_client=None)

    with Stubber(client) as stubber, caplog.at_level(logging.WARNING):
        stubber.add_client_error("delete_object", service_error_code="AccessDenied", http_status_code=403)
        deleted = await storage.delete("users/1/avatar")

    assert deleted is False
    assert "left in the bucket" in caplog.text
    assert "S3_DELETE_ACCESS_KEY_ID" in caplog.text


async def test_delete_other_errors_propagate() -> None:
    client = make_client()
    storage = S3ObjectStorage(bucket=BUCKET, client=client, delete_client=None)

    with Stubber(client) as stubber:
        stubber.add_client_error("delete_object", service_error_code="InternalError", http_status_code=500)
        with pytest.raises(ClientError):
            await storage.delete("users/1/avatar")


def test_presigned_url_is_path_style_and_capped_at_900_seconds() -> None:
    storage = S3ObjectStorage(bucket=BUCKET, client=make_client(), delete_client=None)

    url = storage.presigned_get_url("orgs/1/files/a.txt", expires_seconds=3600)

    assert url.startswith(f"{ENDPOINT}/{BUCKET}/orgs/1/files/a.txt?")
    assert "X-Amz-Expires=900" in url


def test_presigned_url_with_download_name_forces_attachment() -> None:
    storage = S3ObjectStorage(bucket=BUCKET, client=make_client(), delete_client=None)

    url = storage.presigned_get_url("orgs/1/files/page.html", download_name="page.html")

    assert "response-content-disposition=attachment" in url


def test_presigned_url_without_download_name_stays_inline() -> None:
    storage = S3ObjectStorage(bucket=BUCKET, client=make_client(), delete_client=None)

    url = storage.presigned_get_url("users/1/avatar")

    assert "response-content-disposition" not in url


def test_attachment_disposition_encodes_unicode_and_strips_quotes() -> None:
    disposition = attachment_disposition('звіт "final".pdf')

    assert disposition.startswith('attachment; filename=" final.pdf";')
    assert "filename*=UTF-8''%D0%B7%D0%B2%D1%96%D1%82%20%22final%22.pdf" in disposition


def test_build_object_storage_follows_settings() -> None:
    storage_settings = {
        "S3_ACCESS_KEY_ID": "key",
        "S3_SECRET_ACCESS_KEY": "secret",
        "S3_ENDPOINT_URL": ENDPOINT,
        "S3_BUCKET": BUCKET,
    }

    delete_settings = {"S3_DELETE_ACCESS_KEY_ID": "delete-key", "S3_DELETE_SECRET_ACCESS_KEY": "x"}

    assert build_object_storage(make_settings()) is None
    without_delete = build_object_storage(make_settings(**storage_settings))
    with_delete = build_object_storage(make_settings(**storage_settings, **delete_settings))

    assert isinstance(without_delete, S3ObjectStorage)
    assert without_delete.delete_client is None
    assert isinstance(with_delete, S3ObjectStorage)
    assert with_delete.delete_client is not None
    assert build_object_storage(make_settings(**storage_settings)) is without_delete


def test_require_storage_and_presigned_helper() -> None:
    storage = S3ObjectStorage(bucket=BUCKET, client=make_client(), delete_client=None)

    with pytest.raises(BusinessError) as error_info:
        require_storage(None)

    assert error_info.value.code == "storage_disabled"
    assert error_info.value.status_code == 400
    assert require_storage(storage) is storage
    assert presigned_url_or_none(None, "users/1/avatar") is None
    assert presigned_url_or_none(storage, None) is None
    assert presigned_url_or_none(storage, "users/1/avatar") is not None


class UnreachableStorage:
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        raise ConnectionError("storage unreachable")

    async def delete(self, key: str) -> bool:
        raise ConnectionError("storage unreachable")

    def presigned_get_url(self, key: str, expires_seconds: int = 900, download_name: str | None = None) -> str:
        return f"https://storage.test/{key}"


async def test_delete_object_best_effort_logs_and_swallows_errors(caplog: pytest.LogCaptureFixture) -> None:
    client = make_client()
    storage = S3ObjectStorage(bucket=BUCKET, client=client, delete_client=None)

    with Stubber(client) as stubber, caplog.at_level(logging.WARNING):
        stubber.add_client_error("delete_object", service_error_code="InternalError", http_status_code=500)
        assert await delete_object_best_effort(storage, "users/1/avatar") is False
        assert await delete_object_best_effort(UnreachableStorage(), "users/2/avatar") is False

    assert "users/1/avatar was left in the bucket" in caplog.text
    assert "users/2/avatar was left in the bucket" in caplog.text


def test_get_object_storage_is_none_without_bucket() -> None:
    assert get_object_storage(make_settings()) is None


async def test_in_memory_storage_records_puts_and_deletes() -> None:
    storage = InMemoryObjectStorage()
    await storage.put("users/1/avatar", b"png", "image/png")

    assert storage.objects == {"users/1/avatar": b"png"}
    assert storage.content_types == {"users/1/avatar": "image/png"}
    assert storage.presigned_get_url("users/1/avatar") == "https://storage.test/users/1/avatar"
    assert await storage.delete("users/1/avatar") is True
    assert storage.objects == {}
    assert storage.deleted == ["users/1/avatar"]


async def test_in_memory_storage_without_delete_permission_keeps_objects() -> None:
    storage = InMemoryObjectStorage(can_delete=False)
    await storage.put("users/1/avatar", b"png", "image/png")

    assert await storage.delete("users/1/avatar") is False
    assert "users/1/avatar" in storage.objects
    assert storage.deleted == []


async def test_in_memory_storage_can_simulate_outage() -> None:
    storage = InMemoryObjectStorage()
    storage.fail_deletes = True

    with pytest.raises(ConnectionError):
        await storage.delete("users/1/avatar")
