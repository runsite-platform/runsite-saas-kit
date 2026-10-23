import uuid

import pytest

from app.utils.exceptions import BusinessError
from app.utils.security import (
    create_access_token,
    decode_access_token,
    generate_token,
    hash_password,
    hash_token,
    normalize_email,
    verify_password,
)

SECRET = "unit-test-secret-" + "y" * 40


def test_hash_and_verify_password() -> None:
    password_hash = hash_password("correct horse")
    assert password_hash != "correct horse"
    assert verify_password("correct horse", password_hash)
    assert not verify_password("wrong horse", password_hash)


def test_verify_password_with_long_password_does_not_raise() -> None:
    long_password = "ж" * 100
    password_hash = hash_password(long_password)
    assert verify_password(long_password, password_hash)


def test_verify_password_with_malformed_hash_returns_false() -> None:
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_generate_token_is_random_and_hash_is_sha256_hex() -> None:
    first_token = generate_token()
    second_token = generate_token()
    assert first_token != second_token
    assert len(first_token) >= 40
    token_hash = hash_token(first_token)
    assert len(token_hash) == 64
    assert token_hash == hash_token(first_token)


def test_normalize_email() -> None:
    assert normalize_email("  Ann@Example.COM ") == "ann@example.com"


def test_access_token_round_trip() -> None:
    user_id = uuid.uuid4()
    impersonator_id = uuid.uuid4()
    token = create_access_token(user_id, secret=SECRET, impersonated_by=impersonator_id)
    claims = decode_access_token(token, secret=SECRET)
    assert claims.user_id == user_id
    assert claims.impersonated_by == impersonator_id


def test_access_token_without_impersonation() -> None:
    user_id = uuid.uuid4()
    claims = decode_access_token(create_access_token(user_id, secret=SECRET), secret=SECRET)
    assert claims.impersonated_by is None


@pytest.mark.parametrize(
    "token_factory",
    [
        lambda: create_access_token(uuid.uuid4(), secret=SECRET, expires_minutes=-1),
        lambda: create_access_token(uuid.uuid4(), secret="another-secret-" + "z" * 40),
        lambda: "not-a-jwt",
    ],
    ids=["expired", "wrong-secret", "garbage"],
)
def test_invalid_access_tokens_raise_not_authenticated(token_factory) -> None:
    with pytest.raises(BusinessError) as error_info:
        decode_access_token(token_factory(), secret=SECRET)
    assert error_info.value.code == "not_authenticated"
    assert error_info.value.status_code == 401


def test_token_of_another_type_is_rejected() -> None:
    from jose import jwt

    foreign_token = jwt.encode({"sub": str(uuid.uuid4()), "type": "oauth_state"}, SECRET, algorithm="HS256")
    with pytest.raises(BusinessError):
        decode_access_token(foreign_token, secret=SECRET)
