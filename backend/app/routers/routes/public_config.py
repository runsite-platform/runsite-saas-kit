from fastapi import APIRouter

from app.schemas.public_config import PublicConfigResponse, PublicFeatures
from app.utils.dependencies import AppSettings

router = APIRouter()


@router.get("/public", response_model=PublicConfigResponse)
async def get_public_config(settings: AppSettings) -> PublicConfigResponse:
    """Return public frontend configuration."""
    return PublicConfigResponse(
        brand_name=settings.BRAND_NAME,
        features=PublicFeatures(
            google_login=settings.google_login_enabled,
            billing=settings.billing_enabled,
            file_uploads=settings.storage_enabled,
            email=settings.email_enabled,
        ),
    )
