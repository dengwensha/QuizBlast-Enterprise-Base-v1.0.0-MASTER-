import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services.preview_event_retention import QUERY, candidates


class PreviewTests(unittest.TestCase):
    def test_only_due_opted_in_completed_program_decks_are_reported(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.executescript("""
          CREATE TABLE event_presentation_retention(event_id, preference, program_completed_at);
          CREATE TABLE event_runs(event_id, cursor, steps);
          CREATE TABLE event_decks(event_id, id, name);
        """)
        now = datetime.now(timezone.utc)
        due = now - timedelta(days=7)
        for event, pref, end, cursor in [
            ('due', 'delete_after_7_days', due, 1),
            ('early', 'delete_after_7_days', due + timedelta(seconds=1), 1),
            ('keep', 'keep', due, 1), ('unset', None, due, 1),
            ('active', 'delete_after_7_days', due, 0),
            ('legacy', 'delete_after_7_days', None, 1),
        ]:
            deck = uuid4()
            db.execute('INSERT INTO event_presentation_retention VALUES(?,?,?)',
                       (event, pref, end.isoformat() if end else None))
            db.execute('INSERT INTO event_runs VALUES(?,?,?)', (event, cursor, json.dumps([
                dict(kind='presentation', deck_id=str(deck))])))
            db.executemany('INSERT INTO event_decks VALUES(?,?,?)', [
                (event, deck.hex, 'shown.pdf'), (event, uuid4().hex, 'unused.pdf')])
        db.execute('PRAGMA query_only=ON')
        result = list(candidates(db.execute(QUERY), now))
        self.assertEqual([(r['event_id'], r['name'], r['eligible_since']) for r in result],
                         [('due', 'shown.pdf', now.isoformat())])
