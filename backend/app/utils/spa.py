from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config.logger import logger
from app.utils.exceptions import not_found

API_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def resolve_public_file(dist_dir: Path, requested_path: str) -> Path | None:
    if not requested_path:
        return None
    root = dist_dir.resolve()
    try:
        candidate = (root / requested_path).resolve()
    except (ValueError, OSError):
        return None
    if candidate.is_relative_to(root) and candidate.is_file():
        return candidate
    return None


def mount_spa(app: FastAPI, dist_dir: Path) -> None:
    index_file = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"

    @app.api_route("/api", methods=API_METHODS, include_in_schema=False)
    @app.api_route("/api/{api_path:path}", methods=API_METHODS, include_in_schema=False)
    async def unknown_api_route(api_path: str = "") -> None:
        raise not_found("Endpoint")

    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if not index_file.is_file():
        logger.warning("Frontend build not found at %s; only the API is served", dist_dir)

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def serve_spa(spa_path: str) -> FileResponse:
        public_file = resolve_public_file(dist_dir, spa_path)
        if public_file is not None:
            return FileResponse(public_file)
        if not index_file.is_file():
            raise not_found("Frontend build")
        return FileResponse(index_file, headers={"Cache-Control": "no-cache"})
