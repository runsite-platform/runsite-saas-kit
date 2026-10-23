import pytest

from app.config.settings import REQUIRED_SETTINGS, Settings, SettingsError, load_settings
from tests.conftest import make_settings


@pytest.mark.parametrize(
    ("raw_url", "expected_url"),
    [
        ("postgres://user:secret@db:5432/app", "postgresql+asyncpg://user:secret@db:5432/app"),
        ("postgresql://user:secret@db:5432/app", "postgresql+asyncpg://user:secret@db:5432/app"),
        ("postgresql+asyncpg://user:secret@db:5432/app", "postgresql+asyncpg://user:secret@db:5432/app"),
    ],
)
def test_database_url_uses_asyncpg_driver(raw_url: str, expected_url: str) -> None:
    assert make_settings(DATABASE_URL=raw_url).DATABASE_URL == expected_url


def test_app_url_trailing_slash_is_removed() -> None:
    assert make_settings(APP_URL="https://demo.runsite.app/").APP_URL == "https://demo.runsite.app"


def test_feature_flags_are_off_by_default() -> None:
    settings = make_settings()
    assert settings.email_enabled is False
    assert settings.storage_enabled is False
    assert settings.storage_delete_enabled is False
    assert settings.google_login_enabled is False
    assert settings.billing_enabled is False
    assert settings.is_secure_cookie is False


def test_feature_flags_follow_configured_values() -> None:
    settings = make_settings(
        APP_URL="https://demo.runsite.app",
        EMAIL_API_KEY="email-key",
        S3_ACCESS_KEY_ID="access",
        S3_SECRET_ACCESS_KEY="secret",
        S3_ENDPOINT_URL="https://s3.runsite.app",
        S3_BUCKET="bucket",
        S3_DELETE_ACCESS_KEY_ID="delete-access",
        S3_DELETE_SECRET_ACCESS_KEY="delete-secret",
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="client-secret",
        BILLING_PROVIDER="stripe",
    )
    assert settings.email_enabled is True
    assert settings.storage_enabled is True
    assert settings.storage_delete_enabled is True
    assert settings.google_login_enabled is True
    assert settings.billing_enabled is True
    assert settings.is_secure_cookie is True


def test_unknown_billing_provider_keeps_billing_disabled() -> None:
    assert make_settings(BILLING_PROVIDER="paypal").billing_enabled is False


@pytest.fixture
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for variable_name in REQUIRED_SETTINGS:
        monkeypatch.delenv(variable_name, raising=False)
    return monkeypatch


def test_load_settings_names_every_missing_variable(isolated_environment: pytest.MonkeyPatch) -> None:
    with pytest.raises(SettingsError) as error_info:
        load_settings()
    assert str(error_info.value) == "Missing required environment variables: APP_URL, DATABASE_URL, JWT_SECRET"


def test_load_settings_names_only_missing_variables(isolated_environment: pytest.MonkeyPatch) -> None:
    isolated_environment.setenv("DATABASE_URL", "postgres://user:secret@db:5432/app")
    isolated_environment.setenv("APP_URL", "https://demo.runsite.app")
    with pytest.raises(SettingsError) as error_info:
        load_settings()
    assert str(error_info.value) == "Missing required environment variables: JWT_SECRET"


def test_load_settings_reads_environment(isolated_environment: pytest.MonkeyPatch) -> None:
    isolated_environment.setenv("DATABASE_URL", "postgres://user:secret@db:5432/app")
    isolated_environment.setenv("APP_URL", "https://demo.runsite.app/")
    isolated_environment.setenv("JWT_SECRET", "secret-value")
    loaded_settings = load_settings()
    assert loaded_settings.DATABASE_URL == "postgresql+asyncpg://user:secret@db:5432/app"
    assert loaded_settings.APP_URL == "https://demo.runsite.app"
