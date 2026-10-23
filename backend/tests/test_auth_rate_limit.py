import httpx
from fastapi import FastAPI

from app.utils.rate_limit import SlidingWindowRateLimiter, get_rate_limiter
from tests.auth_helpers import login_user


class FakeClock:
    def __init__(self) -> None:
        self.now = 500.0

    def __call__(self) -> float:
        return self.now


async def test_login_is_limited_per_ip(client: httpx.AsyncClient) -> None:
    for attempt in range(10):
        response = await login_user(client, email=f"user{attempt}@example.com", password="whatever1")
        assert response.status_code == 401
    blocked = await login_user(client, email="another@example.com", password="whatever1")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"


async def test_register_is_limited_per_ip(client: httpx.AsyncClient) -> None:
    for attempt in range(10):
        response = await client.post(
            "/api/auth/register", json={"email": f"new{attempt}@example.com", "password": "password123"}
        )
        assert response.status_code == 201
    blocked = await client.post("/api/auth/register", json={"email": "late@example.com", "password": "password123"})
    assert blocked.status_code == 429


async def test_forgot_password_is_limited_per_email_across_ips(app: FastAPI, client: httpx.AsyncClient) -> None:
    for _ in range(10):
        response = await client.post("/api/auth/forgot-password", json={"email": "ann@example.com"})
        assert response.status_code == 200

    other_transport = httpx.ASGITransport(app=app, client=("203.0.113.9", 4000))
    async with httpx.AsyncClient(transport=other_transport, base_url="http://testserver") as other_client:
        same_email = await other_client.post("/api/auth/forgot-password", json={"email": "ANN@example.com"})
        other_email = await other_client.post("/api/auth/forgot-password", json={"email": "bob@example.com"})

    assert same_email.status_code == 429
    assert other_email.status_code == 200


async def test_resend_verification_is_limited(client: httpx.AsyncClient) -> None:
    for _ in range(10):
        response = await client.post("/api/auth/resend-verification", json={"email": "ann@example.com"})
        assert response.status_code == 200
    blocked = await client.post("/api/auth/resend-verification", json={"email": "ann@example.com"})
    assert blocked.status_code == 429


async def test_limit_resets_after_window(app: FastAPI, client: httpx.AsyncClient) -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    assert (await client.post("/api/auth/forgot-password", json={"email": "ann@example.com"})).status_code == 200
    assert (await client.post("/api/auth/forgot-password", json={"email": "ann@example.com"})).status_code == 429
    clock.now += 61
    assert (await client.post("/api/auth/forgot-password", json={"email": "ann@example.com"})).status_code == 200


async def test_spoofed_forwarded_for_does_not_bypass_ip_limit(client: httpx.AsyncClient) -> None:
    for attempt in range(10):
        response = await client.post(
            "/api/auth/login",
            json={"email": f"spray{attempt}@example.com", "password": "whatever1"},
            headers={"X-Forwarded-For": f"10.0.0.{attempt}, 198.51.100.7"},
        )
        assert response.status_code == 401
    blocked = await client.post(
        "/api/auth/login",
        json={"email": "spray-last@example.com", "password": "whatever1"},
        headers={"X-Forwarded-For": "10.0.0.250, 198.51.100.7"},
    )
    assert blocked.status_code == 429
