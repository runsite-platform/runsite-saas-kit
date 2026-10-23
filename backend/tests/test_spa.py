from pathlib import Path

import httpx
import pytest

from app.config.settings import Settings
from tests.conftest import make_settings

INDEX_HTML = "<!doctype html><html><body><div id='root'></div></body></html>"


@pytest.fixture
def frontend_dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX_HTML)
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "favicon.svg").write_text("<svg></svg>")
    return tmp_path


@pytest.fixture
def settings(frontend_dist: Path) -> Settings:
    return make_settings(FRONTEND_DIST_DIR=frontend_dist)


async def test_root_serves_index_html(client: httpx.AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.text == INDEX_HTML
    assert response.headers["content-type"].startswith("text/html")


async def test_client_side_route_serves_index_html(client: httpx.AsyncClient) -> None:
    response = await client.get("/app/acme/projects")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


async def test_assets_are_served_as_static_files(client: httpx.AsyncClient) -> None:
    response = await client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log('app')"


async def test_missing_asset_returns_404_not_index(client: httpx.AsyncClient) -> None:
    response = await client.get("/assets/missing.js")
    assert response.status_code == 404
    assert response.text != INDEX_HTML


async def test_root_level_public_file_is_served(client: httpx.AsyncClient) -> None:
    response = await client.get("/favicon.svg")
    assert response.status_code == 200
    assert response.text == "<svg></svg>"


async def test_path_traversal_falls_back_to_index(client: httpx.AsyncClient) -> None:
    response = await client.get("/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
async def test_unknown_api_path_returns_json_404(client: httpx.AsyncClient, method: str) -> None:
    response = await client.request(method, "/api/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Endpoint not found"}}


async def test_api_routes_still_win_over_spa(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.json() == {"status": "ok"}


class TestWithoutFrontendBuild:
    @pytest.fixture
    def settings(self, tmp_path: Path) -> Settings:
        return make_settings(FRONTEND_DIST_DIR=tmp_path / "missing-dist")

    async def test_spa_path_returns_json_404(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/dashboard")
        assert response.status_code == 404
        assert response.json() == {"error": {"code": "not_found", "message": "Frontend build not found"}}


async def test_null_byte_path_falls_back_to_index(client: httpx.AsyncClient) -> None:
    response = await client.get("/x%00y")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


async def test_bare_api_path_returns_json_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
