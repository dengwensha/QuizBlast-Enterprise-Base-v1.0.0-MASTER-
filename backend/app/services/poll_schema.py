"""Additive migration for a PollSession Display capability on existing databases.

No data removal, backfill or capability issuance for historic sessions.
"""
from sqlalchemy import inspect, text


def ensure_poll_display_digest(engine):
    inspector = inspect(engine)
    if 'poll_sessions' not in inspector.get_table_names():
        return
    columns = {column['name'] for column in inspector.get_columns('poll_sessions')}
    unique_sets = [
        tuple(constraint['column_names'])
        for constraint in inspector.get_unique_constraints('poll_sessions')
    ] + [
        tuple(index['column_names'])
        for index in inspector.get_indexes('poll_sessions')
        if index.get('unique')
    ]
    with engine.begin() as connection:
        if 'display_digest' not in columns:
            connection.execute(text(
                'ALTER TABLE poll_sessions ADD COLUMN display_digest VARCHAR(64) NULL'
            ))
        # Existing pre-Display tables lack the ORM-managed unique constraint.
        # New tables already have one; avoid a redundant additional index.
        if ('display_digest',) not in unique_sets:
            connection.execute(text(
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_poll_sessions_display_digest '
                'ON poll_sessions (display_digest)'
            ))
