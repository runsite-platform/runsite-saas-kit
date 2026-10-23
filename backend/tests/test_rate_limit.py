import pytest
from starlette.requests import Request

from app.utils.exceptions import BusinessError
from app.utils.rate_limit import SlidingWindowRateLimiter, resolve_client_ip


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_limit_then_blocks() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60, clock=clock)
    results = [limiter.hit("login:ip:1.1.1.1") for _ in range(11)]
    assert results == [True] * 10 + [False]


def test_window_slides() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, clock=clock)
    assert limiter.hit("key")
    clock.now += 30
    assert limiter.hit("key")
    assert not limiter.hit("key")
    clock.now += 31
    assert limiter.hit("key")
    assert not limiter.hit("key")


def test_keys_are_independent() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    assert limiter.hit("first")
    assert limiter.hit("second")
    assert not limiter.hit("first")


def test_tracked_keys_stay_bounded() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=5, window_seconds=60, max_tracked_keys=50, clock=clock)
    for key_number in range(500):
        limiter.hit(f"key-{key_number}")
    assert limiter.tracked_keys <= 50


def test_stale_keys_are_pruned_first() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, max_tracked_keys=3, clock=clock)
    limiter.hit("old-1")
    limiter.hit("old-2")
    limiter.hit("blocked")
    clock.now += 120
    limiter.hit("fresh")
    assert limiter.tracked_keys == 1


def test_check_raises_rate_limited_per_ip_and_per_email() -> None:
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, clock=FakeClock())
    limiter.check("login", client_ip="1.1.1.1", email="Ann@Example.com")
    limiter.check("login", client_ip="2.2.2.2", email="ann@example.com")
    with pytest.raises(BusinessError) as error_info:
        limiter.check("login", client_ip="3.3.3.3", email="ANN@example.com")
    assert error_info.value.code == "rate_limited"
    assert error_info.value.status_code == 429


def test_actions_are_limited_separately() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    limiter.check("login", client_ip="1.1.1.1")
    limiter.check("register", client_ip="1.1.1.1")
    with pytest.raises(BusinessError):
        limiter.check("login", client_ip="1.1.1.1")


def test_reset_clears_state() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    limiter.hit("key")
    limiter.reset()
    assert limiter.tracked_keys == 0
    assert limiter.hit("key")


def make_request(forwarded_for: str | None, peer: str = "192.0.2.1") -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_resolve_client_ip_takes_the_hop_appended_by_the_proxy() -> None:
    assert resolve_client_ip(make_request("6.6.6.6, 203.0.113.5"), trusted_proxy_hops=1) == "203.0.113.5"
    assert resolve_client_ip(make_request("6.6.6.6, 203.0.113.5, 10.1.1.1"), trusted_proxy_hops=2) == "203.0.113.5"


def test_resolve_client_ip_with_short_chain_uses_leftmost_entry() -> None:
    assert resolve_client_ip(make_request("203.0.113.5"), trusted_proxy_hops=3) == "203.0.113.5"


def test_resolve_client_ip_falls_back_to_peer() -> None:
    assert resolve_client_ip(make_request(None), trusted_proxy_hops=1) == "192.0.2.1"
    assert resolve_client_ip(make_request("6.6.6.6"), trusted_proxy_hops=0) == "192.0.2.1"
