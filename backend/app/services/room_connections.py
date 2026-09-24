def remove_connection(players, websocket):
    """Remove only the connection that ended, preserving a newer session."""
    return [player for player in players if player['socket'] is not websocket]
