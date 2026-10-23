import httpx
from fastapi import FastAPI

from app.utils.exceptions import BusinessError, business_error_handler, not_found


def build_error_app() -> FastAPI:
    error_app = FastAPI()
    error_app.add_exception_handler(BusinessError, business_error_handler)

    @error_app.get("/limit")
    async def raise_limit_error() -> None:
        raise BusinessError(
            "plan_limit_reached",
            "Plan limit reached",
            status_code=402,
            details={"limit": "projects", "plan_id": "free"},
        )

    @error_app.get("/missing")
    async def raise_not_found() -> None:
        raise not_found("Project")

    return error_app


async def request_error_app(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=build_error_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as error_client:
        return await error_client.get(path)


def test_business_error_defaults_to_400() -> None:
    error = BusinessError("email_taken", "Email is already registered")
    assert error.status_code == 400
    assert error.details is None
    assert str(error) == "Email is already registered"


async def test_handler_includes_details_when_present() -> None:
    response = await request_error_app("/limit")
    assert response.status_code == 402
    assert response.json() == {
        "error": {
            "code": "plan_limit_reached",
            "message": "Plan limit reached",
            "details": {"limit": "projects", "plan_id": "free"},
        }
    }


async def test_not_found_helper_omits_details() -> None:
    response = await request_error_app("/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Project not found"}}
