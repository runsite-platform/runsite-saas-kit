from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_SETTINGS = ("DATABASE_URL", "JWT_SECRET", "APP_URL")


class SettingsError(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    APP_URL: str
    DEBUG: bool = False
    BRAND_NAME: str = "Acme"
    FRONTEND_DIST_DIR: Path = PROJECT_ROOT / "frontend" / "dist"
    TRUSTED_PROXY_HOPS: int = 1

    EMAIL_API_KEY: str = ""
    EMAIL_API_URL: str = "https://api.runsite.app/emails"
    EMAIL_FROM: str = "Acme <noreply@example.com>"
    REQUIRE_EMAIL_VERIFICATION: bool = False

    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "auto"
    S3_DELETE_ACCESS_KEY_ID: str = ""
    S3_DELETE_SECRET_ACCESS_KEY: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    BILLING_PROVIDER: str = ""  # "", "stripe", "lemonsqueezy", "creem"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PRO_MONTHLY: str = ""
    STRIPE_PRICE_PRO_YEARLY: str = ""
    LEMONSQUEEZY_API_KEY: str = ""
    LEMONSQUEEZY_STORE_ID: str = ""
    LEMONSQUEEZY_WEBHOOK_SECRET: str = ""
    LEMONSQUEEZY_VARIANT_PRO_MONTHLY: str = ""
    LEMONSQUEEZY_VARIANT_PRO_YEARLY: str = ""
    CREEM_API_KEY: str = ""
    CREEM_API_URL: str = "https://api.creem.io"
    CREEM_WEBHOOK_SECRET: str = ""
    CREEM_PRODUCT_PRO_MONTHLY: str = ""
    CREEM_PRODUCT_PRO_YEARLY: str = ""

    SUPERADMIN_EMAIL: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def use_asyncpg_driver(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @field_validator("APP_URL")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def email_enabled(self) -> bool:
        return bool(self.EMAIL_API_KEY)

    @property
    def storage_enabled(self) -> bool:
        return all((self.S3_ACCESS_KEY_ID, self.S3_SECRET_ACCESS_KEY, self.S3_ENDPOINT_URL, self.S3_BUCKET))

    @property
    def storage_delete_enabled(self) -> bool:
        return self.storage_enabled and bool(self.S3_DELETE_ACCESS_KEY_ID and self.S3_DELETE_SECRET_ACCESS_KEY)

    @property
    def google_login_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def billing_enabled(self) -> bool:
        return self.BILLING_PROVIDER in ("stripe", "lemonsqueezy", "creem")

    @property
    def is_secure_cookie(self) -> bool:
        return self.APP_URL.startswith("https://")


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        missing = sorted({str(item["loc"][0]) for item in error.errors() if item["type"] == "missing"})
        if missing:
            raise SettingsError(f"Missing required environment variables: {', '.join(missing)}") from None
        raise


@lru_cache
def get_settings() -> Settings:
    return load_settings()
