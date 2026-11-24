"""Resolve Poll join client identity only through the known local NGINX proxy.

Never trust forwarded headers merely because a caller supplies them.
The Docker backend runs uvicorn with --no-proxy-headers so request.client
is the actual TCP peer. Render requires a separate environment verification.
"""
from ipaddress import ip_address
import socket


def poll_client_address(request):
    peer = request.client.host if request.client else 'unknown'
    # Docker DNS resolves only a running frontend service on this Compose network.
    # This check is not a generic trust of private ranges or client-supplied XFF.
    try:
        addresses = {record[4][0] for record in socket.getaddrinfo(
            'frontend', None, type=socket.SOCK_STREAM)}
    except (socket.gaierror, OSError):
        return peer
    if peer not in addresses:
        return peer

    # NGINX MUST overwrite this header with $remote_addr (never append).
    raw = request.headers.get('x-real-ip', '')
    try:
        return str(ip_address(raw))
    except ValueError:
        return peer
