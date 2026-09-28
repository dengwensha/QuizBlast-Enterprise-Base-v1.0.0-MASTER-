import asyncio
import unittest

from app.services.room_connections import remove_connection, send_to_room


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

    def test_broadcast_cleanup_preserves_join_during_send(self):
        rooms = {'123456': []}

        class NewSocket:
            async def send_json(self, payload):
                self.payload = payload

        new_socket = NewSocket()

        class FailingSocket:
            async def send_json(self, payload):
                rooms['123456'].append({'name': 'Ada', 'socket': new_socket})
                await asyncio.sleep(0)
                raise RuntimeError('socket closed')

        rooms['123456'].append({'name': 'HOST', 'socket': FailingSocket()})
        asyncio.run(send_to_room(rooms, '123456', {'type': 'players'}))
        self.assertEqual(
            rooms['123456'],
            [{'name': 'Ada', 'socket': new_socket}],
        )


if __name__ == '__main__':
    unittest.main()
