import re

import pytest

from app.utils.slugs import (
    FALLBACK_SLUG,
    NUMBERED_SUFFIX_LIMIT,
    RANDOM_SUFFIX_ATTEMPTS,
    SLUG_BASE_MAX_LENGTH,
    SLUG_PATTERN,
    SlugGenerationError,
    generate_unique_slug,
    slugify,
)


class BoundedSlugLookup:
    """Finite fake for `slug_exists`: fails the test instead of looping forever if the code loses its bound."""

    def __init__(self, taken_slugs: set[str], *, always_taken: bool = False, max_calls: int = 100) -> None:
        self.taken_slugs = taken_slugs
        self.always_taken = always_taken
        self.max_calls = max_calls
        self.checked_slugs: list[str] = []

    async def __call__(self, slug: str) -> bool:
        self.checked_slugs.append(slug)
        if len(self.checked_slugs) > self.max_calls:
            raise AssertionError("slug lookup called more often than any bounded strategy allows")
        return self.always_taken or slug in self.taken_slugs


@pytest.mark.parametrize(
    ("name", "expected_slug"),
    [
        ("Acme Inc", "acme-inc"),
        ("  Hello,   World!! ", "hello-world"),
        ("Jane's workspace", "janes-workspace"),
        ("Jane’s workspace", "janes-workspace"),
        ("Café Déjà Vu", "cafe-deja-vu"),
        ("Привіт", FALLBACK_SLUG),
        ("---", FALLBACK_SLUG),
        ("", FALLBACK_SLUG),
    ],
)
def test_slugify(name: str, expected_slug: str) -> None:
    assert slugify(name) == expected_slug


def test_slugify_truncates_long_names_without_trailing_dash() -> None:
    slug = slugify("word " * 40)
    assert len(slug) <= SLUG_BASE_MAX_LENGTH
    assert not slug.endswith("-")
    assert re.fullmatch(SLUG_PATTERN, slug)


async def test_generate_unique_slug_returns_base_when_free() -> None:
    lookup = BoundedSlugLookup(set())
    assert await generate_unique_slug("Acme", lookup) == "acme"
    assert lookup.checked_slugs == ["acme"]


async def test_generate_unique_slug_appends_next_free_number() -> None:
    lookup = BoundedSlugLookup({"acme", "acme-2"})
    assert await generate_unique_slug("Acme", lookup) == "acme-3"


async def test_generate_unique_slug_uses_random_suffix_when_numbers_are_exhausted() -> None:
    taken_slugs = {"acme"} | {f"acme-{number}" for number in range(2, NUMBERED_SUFFIX_LIMIT + 1)}
    lookup = BoundedSlugLookup(taken_slugs)
    slug = await generate_unique_slug("Acme", lookup)
    assert re.fullmatch(r"acme-[0-9a-f]{6}", slug)


async def test_generate_unique_slug_gives_up_after_bounded_attempts() -> None:
    lookup = BoundedSlugLookup(set(), always_taken=True)
    with pytest.raises(SlugGenerationError):
        await generate_unique_slug("Acme", lookup)
    assert len(lookup.checked_slugs) == NUMBERED_SUFFIX_LIMIT + RANDOM_SUFFIX_ATTEMPTS
