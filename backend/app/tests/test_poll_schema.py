"""POLL-SR01-FIX05: additive migration preserves historic poll sessions."""
import unittest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.services.poll_schema import ensure_poll_display_digest


class PollSchemaMigrationAcceptance(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        with self.engine.begin() as db:
            db.execute(text('CREATE TABLE poll_sessions (id VARCHAR(32) PRIMARY KEY, status VARCHAR(16) NOT NULL)'))
            db.execute(text("INSERT INTO poll_sessions (id, status) VALUES ('old-session', 'closed')"))

    def tearDown(self):
        self.engine.dispose()

    def test_legacy_table_preserved_and_new_display_key_unique(self):
        ensure_poll_display_digest(self.engine)
        with self.engine.begin() as db:
            session = db.execute(text(
                "SELECT id, status, display_digest FROM poll_sessions WHERE id='old-session'"
            )).one()
            self.assertEqual(tuple(session), ('old-session', 'closed', None))
            db.execute(text("INSERT INTO poll_sessions(id,status,display_digest) "
                            "VALUES('new-session','open','unique-display-key')"))
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as db:
                db.execute(text("INSERT INTO poll_sessions(id,status,display_digest) "
                                "VALUES('duplicate','open','unique-display-key')"))
        with self.engine.begin() as db:
            self.assertEqual(db.execute(text('SELECT COUNT(*) FROM poll_sessions')).scalar(), 2)

    def test_restarts_do_not_drop_rows_or_add_duplicate_indexes(self):
        ensure_poll_display_digest(self.engine)
        first = inspect(self.engine).get_indexes('poll_sessions')
        ensure_poll_display_digest(self.engine)
        second = inspect(self.engine).get_indexes('poll_sessions')
        self.assertEqual(first, second)
        with self.engine.begin() as db:
            self.assertEqual(db.execute(text(
                "SELECT status FROM poll_sessions WHERE id='old-session'"
            )).scalar(), 'closed')

    def test_existing_display_column_and_unique_index_remain_unchanged(self):
        with self.engine.begin() as db:
            db.execute(text('ALTER TABLE poll_sessions ADD COLUMN display_digest VARCHAR(64) NULL'))
            db.execute(text('CREATE UNIQUE INDEX existing_display_key ON poll_sessions(display_digest)'))
        ensure_poll_display_digest(self.engine)
        indexes = inspect(self.engine).get_indexes('poll_sessions')
        self.assertEqual(len([i for i in indexes if 'display_digest' in i['column_names']]), 1)

    def test_no_poll_session_table_is_a_noop(self):
        with self.engine.begin() as db:
            db.execute(text('DROP TABLE poll_sessions'))
        ensure_poll_display_digest(self.engine)
        self.assertNotIn('poll_sessions', inspect(self.engine).get_table_names())


if __name__ == '__main__':
    unittest.main()
