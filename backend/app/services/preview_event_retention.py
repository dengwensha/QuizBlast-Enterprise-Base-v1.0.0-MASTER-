"""Read-only preview of retained presentations from completed event programs."""
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

# One snapshot; never fetch page images or initialize application tables.
QUERY = """
SELECT d.event_id, d.id, d.name, p.program_completed_at, r.cursor, r.steps
FROM event_presentation_retention p
JOIN event_runs r ON r.event_id = p.event_id
JOIN event_decks d ON d.event_id = p.event_id
WHERE p.preference = 'delete_after_7_days' AND p.program_completed_at IS NOT NULL
ORDER BY d.event_id, d.id
"""


def candidates(rows, now):
    for event_id, deck_id, name, completed, cursor, steps in rows:
        if isinstance(completed, str):
            completed = datetime.fromisoformat(completed)
        if completed.tzinfo is None:  # SQLite stores UTC without the offset.
            completed = completed.replace(tzinfo=timezone.utc)
        due = completed + timedelta(days=7)
        if now < due:
            continue
        if isinstance(steps, str):
            steps = json.loads(steps)
        if not steps or cursor != len(steps):
            continue
        if any(s.get('kind') == 'presentation' and s.get('deck_id')
               and UUID(s['deck_id']).hex == deck_id for s in steps):
            yield dict(event_id=event_id, deck_id=deck_id, name=name,
                       eligible_since=due.astimezone(timezone.utc).isoformat())


def main():
    from sqlalchemy import create_engine
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        if conn.dialect.name == 'postgresql':
            conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        print(json.dumps(dict(mode='preview', candidates=list(candidates(
            conn.exec_driver_sql(QUERY), datetime.now(timezone.utc)))), ensure_ascii=False))


if __name__ == '__main__':
    main()
