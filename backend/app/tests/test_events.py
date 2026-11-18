"""HTTP acceptance of event drafts against a persistent SQL database."""
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn
from fastapi import FastAPI
from jose import jwt
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from app.routes.events import create_events_router
from app.services.event_store import register_event_model
from app.services.host_authorization import require_authenticated_email


class EventAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.url = 'sqlite:///' + str(Path(cls.temp.name) / 'events.db')
        cls.engine = create_engine(cls.url, connect_args={'check_same_thread': False})
        base = declarative_base()
        class User(base):
            __tablename__ = 'users'
            id = Column(Integer, primary_key=True)
            email = Column(String, unique=True)
        cls.User = User
        cls.Event = register_event_model(base)
        cls.metadata = base.metadata
        cls.factory = sessionmaker(bind=cls.engine)
        base.metadata.create_all(cls.engine)
        base.metadata.create_all(cls.engine)  # Repeatable additive initialization.
        with cls.factory() as db:
            db.add_all([User(id=1, email='owner@test'), User(id=2, email='other@test')])
            db.commit()
        app = FastAPI()
        app.include_router(create_events_router(cls.factory, User, cls.Event,
            lambda auth: require_authenticated_email(auth, 'event-test-secret', 'HS256')))
        cls.sock = socket.socket()
        cls.sock.bind(('127.0.0.1', 0))
        cls.address = f'http://127.0.0.1:{cls.sock.getsockname()[1]}'
        cls.server = uvicorn.Server(uvicorn.Config(app, log_level='error', lifespan='off'))
        cls.thread = threading.Thread(target=lambda: cls.server.run(sockets=[cls.sock]), daemon=True)
        cls.thread.start()
        for _ in range(100):
            if cls.server.started:
                break
            time.sleep(.02)
        assert cls.server.started

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)
        cls.sock.close()
        cls.engine.dispose()
        cls.temp.cleanup()

    def request(self, method='GET', path='/events', data=None, email='owner@test', expired=False):
        headers = {}
        if email:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=-10 if expired else 3600)
            token = jwt.encode({'sub': email, 'exp': expiry}, 'event-test-secret', algorithm='HS256')
            headers['Authorization'] = 'Bearer ' + token
        body = json.dumps(data).encode() if data is not None else None
        if body:
            headers['Content-Type'] = 'application/json'
        try:
            response = urlopen(Request(self.address + path, data=body, headers=headers, method=method), timeout=5)
        except HTTPError as error:
            response = error
        return response.code, json.load(response)

    def create(self, **values):
        status, row = self.request('POST', data={'title': '  Event  ', **values})
        self.assertEqual(status, 201, row)
        return row

    def test_auth_and_ownership(self):
        self.assertEqual(self.request(email=None)[0], 401)
        self.assertEqual(self.request(expired=True)[0], 401)
        self.assertEqual(self.request(email='deleted@test')[0], 401)
        row = self.create()
        path = '/events/' + row['id']
        self.assertEqual(self.request(path=path, email='other@test'),
                         self.request(path='/events/' + uuid4().hex, email='other@test'))
        self.assertEqual(self.request('PATCH', path, {'title': 'stolen', 'revision': 1}, email='other@test')[0], 404)
        self.assertFalse(any(x['id'] == row['id'] for x in self.request(email='other@test')[1]['items']))
        self.assertEqual(self.request(path=path)[1]['title'], 'Event')

    def test_validation_and_timezone(self):
        for payload in ({'title': ' '}, {'title': 'x' * 161}, {'title': None},
                        {'title': 'ok', 'owner_id': 2}, {'title': 'ok', 'status': 'completed'},
                        {'title': 'ok', 'scheduled_at': '2026-11-04T12:00:00'}):
            self.assertEqual(self.request('POST', data=payload)[0], 422)
        row = self.create(scheduled_at='2026-11-04T12:00:00+03:00')
        self.assertEqual(row['scheduled_at'], '2026-11-04T09:00:00+00:00')
        path = '/events/' + row['id']
        status, changed = self.request('PATCH', path, {'organization': ' ACME ', 'revision': 1})
        self.assertEqual(status, 200)
        self.assertEqual(changed['scheduled_at'], row['scheduled_at'])
        self.assertEqual(changed['organization'], 'ACME')
        self.assertEqual(self.request('PATCH', path, {'title': None, 'revision': 2})[0], 422)
        status, cleared = self.request('PATCH', path, {'scheduled_at': None, 'revision': 2})
        self.assertEqual(status, 200)
        self.assertIsNone(cleared['scheduled_at'])

    def test_stale_update_and_concurrency(self):
        row = self.create()
        path = '/events/' + row['id']
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda title: self.request('PATCH', path,
                {'title': title, 'revision': 1}), ['First', 'Second']))
        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        self.assertEqual(self.request(path=path)[1]['revision'], 2)

    def test_pagination_is_owner_scoped(self):
        row = self.create()
        one = self.request(path='/events?limit=1')[1]
        two = self.request(path='/events?limit=1&offset=1')[1]
        self.assertEqual(one['items'][0]['id'], row['id'])
        self.assertNotEqual(one['items'], two['items'])
        for path in ['/events?limit=0', '/events?limit=101', '/events?offset=-1']:
            self.assertEqual(self.request(path=path)[0], 422)

    @unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires production database configuration')
    def test_production_registration_and_additive_initialization(self):
        import app.main as main
        self.assertIn('/events', main.app.openapi()['paths'])
        suffix = uuid4().hex
        with main.db_session() as db:
            quiz_count = db.query(main.Quiz).count()
            room_count = db.query(main.GameRoom).count()
            user = main.User(email=f'event-{suffix}@test', password_hash='unused')
            db.add(user)
            db.flush()
            user_id = user.id
            row = main.EventDraft(owner_id=user_id, title='Persistent event')
            db.add(row)
            db.commit()
            event_id = row.id
        try:
            main.Base.metadata.create_all(main.engine)
            main.Base.metadata.create_all(main.engine)
            with main.db_session() as db:
                self.assertEqual(db.get(main.EventDraft, event_id).owner_id, user_id)
                self.assertEqual(db.query(main.Quiz).count(), quiz_count)
                self.assertEqual(db.query(main.GameRoom).count(), room_count)
        finally:
            with main.db_session() as db:
                db.query(main.EventDraft).filter_by(id=event_id).delete()
                db.query(main.User).filter_by(id=user_id).delete()
                db.commit()

    def test_persistence_and_existing_records(self):
        row = self.create()
        fresh = create_engine(self.url)
        self.metadata.create_all(fresh)
        with sessionmaker(bind=fresh)() as db:
            self.assertEqual(db.get(self.Event, row['id']).title, 'Event')
            self.assertEqual(db.get(self.User, 1).email, 'owner@test')
        self.assertEqual(set(inspect(fresh).get_table_names()), {'users', 'event_drafts'})
        fresh.dispose()


if __name__ == '__main__':
    unittest.main()
