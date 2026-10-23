from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from app.config.db import DatabaseManager
from app.config.logger import configure_logging, logger
from app.config.settings import Settings, get_settings
from app.routers.api import api_router
from app.services.superadmin_service import promote_superadmin_on_startup
from app.utils.exceptions import BusinessError, business_error_handler
from app.utils.spa import mount_spa


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(debug=app_settings.DEBUG)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        DatabaseManager.setup(app_settings.DATABASE_URL, echo=False)
        if app_settings.SUPERADMIN_EMAIL and DatabaseManager.session_maker is not None:
            await promote_superadmin_on_startup(DatabaseManager.session_maker, app_settings.SUPERADMIN_EMAIL)
        logger.info("Application started")
        try:
            yield
        finally:
            await DatabaseManager.stop()

    app = FastAPI(
        title=app_settings.BRAND_NAME,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_exception_handler(BusinessError, business_error_handler)
    app.include_router(api_router)
    add_pagination(app)
    mount_spa(app, app_settings.FRONTEND_DIST_DIR)
    return app


app = create_app()
