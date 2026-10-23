import re
import secrets
import unicodedata
from collections.abc import Awaitable, Callable

SLUG_MAX_LENGTH = 64
SLUG_BASE_MAX_LENGTH = 48
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
FALLBACK_SLUG = "workspace"
NUMBERED_SUFFIX_LIMIT = 20
RANDOM_SUFFIX_ATTEMPTS = 5


class SlugGenerationError(RuntimeError):
    pass


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    without_apostrophes = ascii_value.lower().replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", without_apostrophes).strip("-")
    slug = slug[:SLUG_BASE_MAX_LENGTH].strip("-")
    return slug or FALLBACK_SLUG


async def generate_unique_slug(name: str, slug_exists: Callable[[str], Awaitable[bool]]) -> str:
    base_slug = slugify(name)
    numbered_candidates = [base_slug] + [f"{base_slug}-{number}" for number in range(2, NUMBERED_SUFFIX_LIMIT + 1)]
    for candidate in numbered_candidates:
        if not await slug_exists(candidate):
            return candidate
    for _attempt in range(RANDOM_SUFFIX_ATTEMPTS):
        candidate = f"{base_slug}-{secrets.token_hex(3)}"
        if not await slug_exists(candidate):
            return candidate
    raise SlugGenerationError(f"Could not find a free slug for {name!r}")
