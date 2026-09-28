from hmac import compare_digest

from fastapi import HTTPException, status
from jose import JWTError, jwt


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid_authentication_credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_authenticated_email(
    authorization: str | None,
    secret_key: str,
    algorithm: str,
) -> str:
    if not authorization:
        raise _authentication_error()

    parts = authorization.strip().split()

    if len(parts) != 2:
        raise _authentication_error()

    scheme, token = parts

    if scheme.casefold() != "bearer" or not token:
        raise _authentication_error()

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
        )
    except JWTError as exc:
        raise _authentication_error() from exc

    email = payload.get("sub")

    if not isinstance(email, str) or not email.strip():
        raise _authentication_error()

    return email.strip()


def require_room_host(
    room_pin: str,
    email: str,
    rooms: dict,
    room_host_map: dict[str, str],
) -> None:
    if room_pin not in rooms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="room_not_found",
        )

    room_host = room_host_map.get(room_pin)

    if (
        not isinstance(room_host, str)
        or not compare_digest(room_host, email)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="host_forbidden",
        )