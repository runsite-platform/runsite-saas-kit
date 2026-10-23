import time
from collections import deque
from collections.abc import Callable
from itertools import islice
from typing import Annotated

from fastapi import Depends, Request

from app.config.settings import Settings, get_settings
from app.utils.exceptions import BusinessError
from app.utils.security import normalize_email

Clock = Callable[[], float]


class SlidingWindowRateLimiter:
    """In-memory sliding window limiter. Single-instance only: state lives in this process."""

    def __init__(
        self,
        *,
        limit: int = 10,
        window_seconds: float = 60.0,
        max_tracked_keys: int = 10_000,
        clock: Clock = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_tracked_keys = max_tracked_keys
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}

    @property
    def tracked_keys(self) -> int:
        return len(self._hits)

    def hit(self, key: str) -> bool:
        now = self.clock()
        window_start = now - self.window_seconds
        timestamps = self._hits.get(key)
        if timestamps is None:
            self._make_room(window_start)
            timestamps = deque()
            self._hits[key] = timestamps
        while timestamps and timestamps[0] <= window_start:
            timestamps.popleft()
        if len(timestamps) >= self.limit:
            return False
        timestamps.append(now)
        return True

    def check(self, action: str, *, client_ip: str, email: str | None = None) -> None:
        keys = [f"{action}:ip:{client_ip}"]
        if email:
            keys.append(f"{action}:email:{normalize_email(email)}")
        results = [self.hit(key) for key in keys]
        if not all(results):
            raise BusinessError("rate_limited", "Too many requests, try again in a minute", status_code=429)

    def reset(self) -> None:
        self._hits.clear()

    def _make_room(self, window_start: float) -> None:
        if len(self._hits) < self.max_tracked_keys:
            return
        stale_keys = [key for key, timestamps in self._hits.items() if not timestamps or timestamps[-1] <= window_start]
        for key in stale_keys:
            del self._hits[key]
        overflow = len(self._hits) - self.max_tracked_keys + 1
        if overflow > 0:
            for key in list(islice(self._hits, overflow)):
                del self._hits[key]


auth_rate_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return auth_rate_limiter


RateLimiterDep = Annotated[SlidingWindowRateLimiter, Depends(get_rate_limiter)]


def resolve_client_ip(request: Request, trusted_proxy_hops: int) -> str:
    """Take the address appended by our own proxies: the leftmost X-Forwarded-For entries are client-controlled."""
    forwarded_hosts = [host.strip() for host in request.headers.get("x-forwarded-for", "").split(",") if host.strip()]
    if trusted_proxy_hops > 0 and forwarded_hosts:
        return forwarded_hosts[-min(trusted_proxy_hops, len(forwarded_hosts))]
    return request.client.host if request.client else "unknown"


def get_client_ip(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> str:
    return resolve_client_ip(request, settings.TRUSTED_PROXY_HOPS)


ClientIp = Annotated[str, Depends(get_client_ip)]
