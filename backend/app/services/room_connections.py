def remove_connection(players, websocket):
    """Remove only the connection that ended, preserving a newer session."""
    return [player for player in players if player['socket'] is not websocket]


def remove_failed_connections(players, failed_sockets):
    """Filter the current room state, including joins made during a broadcast."""
    return [
        player for player in players
        if all(player['socket'] is not failed for failed in failed_sockets)
    ]


async def send_to_room(rooms, room_pin, payload):
    failed = []
    for player in tuple(rooms.get(room_pin, [])):
        try:
            await player['socket'].send_json(payload)
        except Exception:
            failed.append(player['socket'])
    if failed:
        rooms[room_pin] = remove_failed_connections(rooms.get(room_pin, []), failed)
