"""Additive migration for a PollSession Display capability on existing databases.

No data removal, backfill or capability issuance for historic sessions.
"""
from sqlalchemy import inspect, text


def ensure_poll_display_digest(engine):
    inspector = inspect(engine)
    if 'poll_sessions' not in inspector.get_table_names():
        return
    columns = {column['name'] for column in inspector.get_columns('poll_sessions')}
    with engine.begin() as connection:
        if 'display_digest' not in columns:
            connection.execute(text(
                'ALTER TABLE poll_sessions ADD COLUMN display_digest VARCHAR(64) NULL'
            ))
        # Existing pre-Display schemas need the new uniqueness guarantee, too.
        # The index is safe to apply again after a restart.
        connection.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_poll_sessions_display_digest '
            'ON poll_sessions (display_digest)'
        ))
