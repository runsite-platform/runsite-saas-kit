import re
from pathlib import PurePosixPath

from fastapi import UploadFile

from app.utils.exceptions import BusinessError

UNSAFE_NAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]+")
FALLBACK_FILE_NAME = "file"
MAX_SAFE_NAME_LENGTH = 100
MAX_DISPLAY_NAME_LENGTH = 255


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise BusinessError(
            "file_too_large", f"The file exceeds the {max_bytes} byte limit", 413, details={"max_bytes": max_bytes}
        )
    return data


def _base_name(file_name: str | None) -> str:
    return PurePosixPath((file_name or "").replace("\\", "/")).name


def safe_file_name(file_name: str | None) -> str:
    cleaned = UNSAFE_NAME_CHARACTERS.sub("_", _base_name(file_name)).strip("._")
    if not cleaned:
        return FALLBACK_FILE_NAME
    return cleaned[-MAX_SAFE_NAME_LENGTH:]


def display_file_name(file_name: str | None) -> str:
    base_name = _base_name(file_name).strip()
    return (base_name or FALLBACK_FILE_NAME)[:MAX_DISPLAY_NAME_LENGTH]
