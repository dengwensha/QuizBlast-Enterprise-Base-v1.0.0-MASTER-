def valid_answer(value):
    """Return a valid option index without coercing untrusted WebSocket input."""
    if type(value) is int and 0 <= value <= 3:
        return value
    return None


def answer_is_open(started_at, duration, now):
    return started_at is not None and 0 <= now - started_at <= duration
