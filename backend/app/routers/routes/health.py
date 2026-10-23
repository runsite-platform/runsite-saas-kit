from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config.logger import logger
from app.utils.dependencies import DbSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(session: DbSession) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as error:
        logger.warning("Health check failed: %s", error)
        return JSONResponse(status_code=503, content={"status": "error"})
    return JSONResponse(content={"status": "ok"})
