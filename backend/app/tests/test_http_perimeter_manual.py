from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.services.http_perimeter import (
    CORS_HEADERS,
    CORS_METHODS,
    SlidingWindowRateLimiter,
    parse_allowed_origins,
    read_positive_int,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 1000.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


async def empty_asgi_app(
    scope,
    receive,
    send,
) -> None:
    return None


def expect_runtime_error(action) -> None:
    try:
        action()
    except RuntimeError:
        return

    raise AssertionError("Expected RuntimeError.")


def expect_rate_limit(
    action,
    expected_retry_after: str,
) -> None:
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.detail == "auth_rate_limit_exceeded"
        assert exc.headers == {
            "Retry-After": expected_retry_after,
        }
        return

    raise AssertionError(
        "Expected HTTP 429 rate-limit rejection."
    )


def run_cors_tests() -> None:
    origins = parse_allowed_origins(
        "http://localhost:5173,"
        "https://quiz.example"
    )

    assert origins == (
        "http://localhost:5173",
        "https://quiz.example",
    )

    middleware = CORSMiddleware(
        app=empty_asgi_app,
        allow_origins=list(origins),
        allow_credentials=False,
        allow_methods=list(CORS_METHODS),
        allow_headers=list(CORS_HEADERS),
    )

    assert middleware.is_allowed_origin(
        "http://localhost:5173"
    )
    assert middleware.is_allowed_origin(
        "https://quiz.example"
    )

    assert not middleware.is_allowed_origin(
        "http://attacker.example:5173"
    )
    assert not middleware.is_allowed_origin(
        "https://sub.quiz.example"
    )
    assert not middleware.is_allowed_origin(
        "http://quiz.example"
    )
    assert not middleware.is_allowed_origin(
        "https://quiz.example:5173"
    )

    invalid_origin_sets = (
        "",
        "*",
        "http://.*:5173",
        "localhost:5173",
        "http://localhost:5173/",
        "http://user@localhost:5173",
        "http://localhost:5173?source=unsafe",
    )

    for invalid_value in invalid_origin_sets:
        expect_runtime_error(
            lambda value=invalid_value: (
                parse_allowed_origins(value)
            )
        )


def run_configuration_tests() -> None:
    assert read_positive_int(
        "5",
        "TEST_LIMIT",
    ) == 5

    for invalid_value in (
        "",
        "0",
        "-1",
        "not-a-number",
    ):
        expect_runtime_error(
            lambda value=invalid_value: (
                read_positive_int(
                    value,
                    "TEST_LIMIT",
                )
            )
        )


def run_rate_limit_tests() -> None:
    clock = FakeClock()

    limiter = SlidingWindowRateLimiter(
        window_seconds=60,
        clock=clock,
    )

    login_key = "192.0.2.10:/auth/login"

    limiter.enforce(
        login_key,
        max_requests=2,
    )
    limiter.enforce(
        login_key,
        max_requests=2,
    )

    expect_rate_limit(
        lambda: limiter.enforce(
            login_key,
            max_requests=2,
        ),
        expected_retry_after="60",
    )

    limiter.enforce(
        "192.0.2.11:/auth/login",
        max_requests=2,
    )

    limiter.enforce(
        "192.0.2.10:/auth/register",
        max_requests=2,
    )

    clock.advance(60)

    limiter.enforce(
        login_key,
        max_requests=2,
    )


def main() -> None:
    run_cors_tests()
    run_configuration_tests()
    run_rate_limit_tests()

    print(
        "PASS - HTTP perimeter origin and "
        "rate-limit negative tests completed."
    )


if __name__ == "__main__":
    main()
