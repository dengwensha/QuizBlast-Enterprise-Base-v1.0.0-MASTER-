from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import jwt

from app.services.host_authorization import (
    require_authenticated_email,
    require_room_host,
)


TEST_SIGNING_KEY = (
    "quizblast-sr02-test-signing-key-"
    "not-for-production-use-0123456789"
)
TEST_ALGORITHM = "HS256"


def expect_http_error(
    expected_status: int,
    expected_detail: str,
    action,
) -> None:
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == expected_status, (
            f"Expected HTTP {expected_status}, "
            f"received HTTP {exc.status_code}."
        )
        assert exc.detail == expected_detail, (
            f"Expected detail {expected_detail!r}, "
            f"received {exc.detail!r}."
        )
        return

    raise AssertionError(
        f"Expected HTTP {expected_status} "
        f"with detail {expected_detail!r}."
    )


def create_token(
    subject: str | None,
    expires_at: datetime,
) -> str:
    payload = {"exp": expires_at}

    if subject is not None:
        payload["sub"] = subject

    return jwt.encode(
        payload,
        TEST_SIGNING_KEY,
        algorithm=TEST_ALGORITHM,
    )


def run_authentication_tests() -> None:
    valid_token = create_token(
        "host@example.com",
        datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    expired_token = create_token(
        "host@example.com",
        datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    token_without_subject = create_token(
        None,
        datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    expect_http_error(
        401,
        "invalid_authentication_credentials",
        lambda: require_authenticated_email(
            None,
            TEST_SIGNING_KEY,
            TEST_ALGORITHM,
        ),
    )

    expect_http_error(
        401,
        "invalid_authentication_credentials",
        lambda: require_authenticated_email(
            "",
            TEST_SIGNING_KEY,
            TEST_ALGORITHM,
        ),
    )

    expect_http_error(
        401,
        "invalid_authentication_credentials",
        lambda: require_authenticated_email(
            "Basic credentials",
            TEST_SIGNING_KEY,
            TEST_ALGORITHM,
        ),
    )

    expect_http_error(
        401,
        "invalid_authentication_credentials",
        lambda: require_authenticated_email(
            "Bearer invalid-token",
            TEST_SIGNING_KEY,
            TEST_ALGORITHM,
        ),
    )

    expect_http_error(
        401,
        "invalid_authentication_credentials",
        lambda: require_authenticated_email(
            f"Bearer {expired_token}",
            TEST_SIGNING_KEY,
            TEST_ALGORITHM,
        ),
    )

    expect_http_error(
        401,
        "invalid_authentication_credentials",
        lambda: require_authenticated_email(
            f"Bearer {token_without_subject}",
            TEST_SIGNING_KEY,
            TEST_ALGORITHM,
        ),
    )

    authenticated_email = require_authenticated_email(
        f"Bearer {valid_token}",
        TEST_SIGNING_KEY,
        TEST_ALGORITHM,
    )

    assert authenticated_email == "host@example.com"


def run_room_authorization_tests() -> None:
    rooms = {
        "123456": [],
        "654321": [],
    }
    room_host_map = {
        "123456": "host@example.com",
    }

    require_room_host(
        "123456",
        "host@example.com",
        rooms,
        room_host_map,
    )

    expect_http_error(
        403,
        "host_forbidden",
        lambda: require_room_host(
            "123456",
            "attacker@example.com",
            rooms,
            room_host_map,
        ),
    )

    expect_http_error(
        404,
        "room_not_found",
        lambda: require_room_host(
            "999999",
            "host@example.com",
            rooms,
            room_host_map,
        ),
    )

    expect_http_error(
        403,
        "host_forbidden",
        lambda: require_room_host(
            "654321",
            "host@example.com",
            rooms,
            room_host_map,
        ),
    )


def main() -> None:
    run_authentication_tests()
    run_room_authorization_tests()

    print(
        "PASS — host authentication and room authorization "
        "negative tests completed."
    )


if __name__ == "__main__":
    main()