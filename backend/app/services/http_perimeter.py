"""HTTP perimeter controls for the current single-worker deployment.

The rate limiter is process-local. A multi-worker or horizontally scaled
deployment must replace it with a shared rate-limit store.
"""

from collections import deque
from math import ceil
from threading import Lock
from time import monotonic
from typing import Callable
from urllib.parse import urlsplit

from fastapi import HTTPException


CORS_METHODS = ("GET", "POST", "PUT", "DELETE")
CORS_HEADERS = ("Authorization", "Content-Type")


def parse_allowed_origins(raw_value: str) -> tuple[str, ...]:
    origins: list[str] = []
    seen: set[str] = set()

    for raw_origin in raw_value.split(","):
        origin = raw_origin.strip()

        if not origin:
            continue

        if "*" in origin:
            raise RuntimeError(
                "CORS_ORIGINS must contain exact origins; "
                "wildcards are not allowed."
            )

        if any(character.isspace() for character in origin):
            raise RuntimeError(
                f"CORS_ORIGINS contains a malformed origin: "
                f"{origin!r}."
            )

        try:
            parsed = urlsplit(origin)
            parsed.port
        except ValueError as exc:
            raise RuntimeError(
                f"CORS_ORIGINS contains a malformed origin: "
                f"{origin!r}."
            ) from exc

        canonical_origin = f"{parsed.scheme}://{parsed.netloc}"

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or origin != canonical_origin
        ):
            raise RuntimeError(
                f"CORS_ORIGINS contains a malformed origin: "
                f"{origin!r}."
            )

        if origin not in seen:
            seen.add(origin)
            origins.append(origin)

    if not origins:
        raise RuntimeError(
            "CORS_ORIGINS must contain at least one exact origin."
        )

    return tuple(origins)


def read_positive_int(
    raw_value: str,
    setting_name: str,
) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{setting_name} must be a positive integer."
        ) from exc

    if value <= 0:
        raise RuntimeError(
            f"{setting_name} must be a positive integer."
        )

    return value


class SlidingWindowRateLimiter:
    def __init__(
        self,
        window_seconds: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")

        self._window_seconds = window_seconds
        self._clock = clock or monotonic
        self._requests: dict[str, deque[float]] = {}
        self._lock = Lock()
        self._check_count = 0

    def enforce(
        self,
        key: str,
        max_requests: int,
    ) -> None:
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError(
                "Rate-limit key must not be empty."
            )

        if max_requests <= 0:
            raise ValueError(
                "max_requests must be positive."
            )

        now = float(self._clock())
        window_start = now - self._window_seconds

        with self._lock:
            self._check_count += 1

            if self._check_count % 256 == 0:
                self._prune_expired(now)

            timestamps = self._requests.setdefault(
                normalized_key,
                deque(),
            )

            while (
                timestamps
                and timestamps[0] <= window_start
            ):
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                retry_after = max(
                    1,
                    ceil(
                        timestamps[0]
                        + self._window_seconds
                        - now
                    ),
                )

                raise HTTPException(
                    status_code=429,
                    detail="auth_rate_limit_exceeded",
                    headers={
                        "Retry-After": str(retry_after),
                    },
                )

            timestamps.append(now)

    def _prune_expired(self, now: float) -> None:
        window_start = now - self._window_seconds

        for key in list(self._requests):
            timestamps = self._requests[key]

            while (
                timestamps
                and timestamps[0] <= window_start
            ):
                timestamps.popleft()

            if not timestamps:
                del self._requests[key]
