import unittest

from app.services.room_connections import remove_connection


class RoomConnectionsTests(unittest.TestCase):
    def test_cleanup_removes_only_the_ended_socket(self):
        old_socket = object()
        new_socket = object()
        players = [
            {'name': 'Ada', 'socket': old_socket},
            {'name': 'Ada', 'socket': new_socket},
        ]
        self.assertEqual(
            remove_connection(players, old_socket),
            [{'name': 'Ada', 'socket': new_socket}],
        )


if __name__ == '__main__':
    unittest.main()
