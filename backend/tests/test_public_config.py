import httpx
import pytest

from app.config.settings import Settings
from tests.conftest import make_settings


async def test_public_config_with_defaults(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/config/public")
    assert response.status_code == 200
    assert response.json() == {
        "brand_name": "Acme",
        "features": {"google_login": False, "billing": False, "file_uploads": False, "email": False},
    }


class TestPublicConfigWithIntegrations:
    @pytest.fixture
    def settings(self) -> Settings:
        return make_settings(
            BRAND_NAME="Rocket",
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            BILLING_PROVIDER="creem",
            EMAIL_API_KEY="email-key",
            S3_ACCESS_KEY_ID="access",
            S3_SECRET_ACCESS_KEY="secret",
            S3_ENDPOINT_URL="https://s3.runsite.app",
            S3_BUCKET="bucket",
        )

    async def test_reports_enabled_features(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/config/public")
        assert response.json() == {
            "brand_name": "Rocket",
            "features": {"google_login": True, "billing": True, "file_uploads": True, "email": True},
        }
