"""POLL-SR02-FIX03: only an authenticated network hop may supply Poll client IP."""
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.poll_client_ip import poll_client_address


class PollClientIpTrustAcceptance(unittest.TestCase):
    @staticmethod
    def request(peer, header=None):
        return SimpleNamespace(
            client=SimpleNamespace(host=peer),
            headers=({'x-real-ip': header} if header is not None else {}),
        )

    @staticmethod
    def frontend_addresses(*_args, **_kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('172.22.0.12', 0)),
        ]

    def test_only_verified_frontend_peer_supplies_client_ip(self):
        with patch('app.services.poll_client_ip.socket.getaddrinfo',
                   side_effect=self.frontend_addresses):
            self.assertEqual(poll_client_address(self.request(
                '172.22.0.12', '192.0.2.41')), '192.0.2.41')
            self.assertEqual(poll_client_address(self.request(
                '172.22.0.12', '198.51.100.64')), '198.51.100.64')
            # Direct access to the backend port must not spoof quota identity.
            self.assertEqual(poll_client_address(self.request(
                '172.22.0.1', '203.0.113.7')), '172.22.0.1')

    def test_malformed_or_missing_forwarded_address_fails_closed(self):
        with patch('app.services.poll_client_ip.socket.getaddrinfo',
                   side_effect=self.frontend_addresses):
            for invalid in ('192.0.2.1, 192.0.2.2', 'attacker', '', '1.2.3.4\\n7.8.9.0'):
                with self.subTest(value=invalid):
                    self.assertEqual(poll_client_address(self.request(
                        '172.22.0.12', invalid)), '172.22.0.12')
            self.assertEqual(poll_client_address(self.request('172.22.0.12')),
                             '172.22.0.12')

    def test_unknown_proxy_dns_never_trusts_unverified_header(self):
        with patch('app.services.poll_client_ip.socket.getaddrinfo',
                   side_effect=socket.gaierror('no frontend')):
            self.assertEqual(poll_client_address(self.request(
                '172.22.0.12', '192.0.2.41')), '172.22.0.12')

    def test_ipv6_is_accepted_when_supplied_by_verified_frontend(self):
        with patch('app.services.poll_client_ip.socket.getaddrinfo',
                   side_effect=self.frontend_addresses):
            self.assertEqual(poll_client_address(self.request(
                '172.22.0.12', '2001:db8::31')), '2001:db8::31')


if __name__ == '__main__':
    unittest.main()
