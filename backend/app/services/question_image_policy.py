"""Fail-closed validation of newly saved remote question images.

Existing stored images are not rewritten by this validator. Remote image
servers can still observe a visitor IP; use only appropriately trusted hosts.
"""
import ipaddress
from urllib.parse import urlsplit

MAX_IMAGE_URL_LENGTH = 2048
MAX_IMAGE_ALT_LENGTH = 240


def validate_question_image(image_url, image_alt_text):
    url = (image_url or "").strip()
    alt = (image_alt_text or "").strip()
    if len(alt) > MAX_IMAGE_ALT_LENGTH:
        raise ValueError("image_alt_text_too_long")
    if not url:
        if alt:
            raise ValueError("image_alt_text_requires_image")
        return None, None
    if len(url) > MAX_IMAGE_URL_LENGTH or any(ord(ch) < 32 or ord(ch) == 127 for ch in url):
        raise ValueError("invalid_image_url")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid_image_url") from exc
    if (parsed.scheme != "https" or not hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.fragment or port not in (None, 443) or
            any(ch.isspace() for ch in url)):
        raise ValueError("image_url_https_required")
    # Private, loopback and link-local literal IP targets are not allowed.
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        if (hostname.lower() == "localhost" or
                hostname.lower().endswith(".localhost") or
                hostname.lower().endswith(".local") or
                "." not in hostname):
            raise ValueError("image_url_host_not_allowed")
    else:
        if not ip.is_global:
            raise ValueError("image_url_host_not_allowed")
    return url, alt or None
