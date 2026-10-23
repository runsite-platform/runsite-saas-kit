import io

import pytest
from fastapi import UploadFile

from app.utils.exceptions import BusinessError
from app.utils.uploads import display_file_name, read_upload_limited, safe_file_name


class RecordingStream(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.requested_sizes: list[int] = []

    def read(self, size: int | None = -1) -> bytes:
        self.requested_sizes.append(-1 if size is None else size)
        return super().read(size)


async def test_read_upload_limited_returns_data_within_limit() -> None:
    upload = UploadFile(file=io.BytesIO(b"0123456789"), filename="digits.txt")

    assert await read_upload_limited(upload, 10) == b"0123456789"


async def test_read_upload_limited_rejects_one_byte_over() -> None:
    upload = UploadFile(file=io.BytesIO(b"0123456789A"), filename="digits.txt")

    with pytest.raises(BusinessError) as error_info:
        await read_upload_limited(upload, 10)

    assert error_info.value.code == "file_too_large"
    assert error_info.value.status_code == 413


async def test_read_upload_limited_never_reads_more_than_limit_plus_one() -> None:
    stream = RecordingStream(b"x" * 64)
    upload = UploadFile(file=stream, filename="big.bin")

    with pytest.raises(BusinessError):
        await read_upload_limited(upload, 10)

    assert stream.requested_sizes == [11]


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("report.pdf", "report.pdf"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\photo 1.png", "photo_1.png"),
        ("отчёт.pdf", "pdf"),
        ("", "file"),
        (None, "file"),
        ("...", "file"),
        ("a" * 150 + ".txt", "a" * 96 + ".txt"),
    ],
)
def test_safe_file_name(original: str | None, expected: str) -> None:
    assert safe_file_name(original) == expected


def test_display_file_name_keeps_unicode_and_strips_paths() -> None:
    assert display_file_name("../docs/отчёт.pdf") == "отчёт.pdf"
    assert display_file_name(None) == "file"
    assert len(display_file_name("b" * 400)) == 255
