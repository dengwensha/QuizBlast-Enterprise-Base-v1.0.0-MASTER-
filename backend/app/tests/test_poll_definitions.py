"""POLL-01A HTTP/SQL acceptance for the standalone poll definition boundary."""
import json
import socket
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn
import app.main as main


class PollDefinitionsAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sock = socket.socket()
        cls.sock.bind(('127.0.0.1', 0))
        cls.address = f'http://127.0.0.1:{cls.sock.getsockname()[1]}'
        cls.server = uvicorn.Server(uvicorn.Config(main.app, log_level='critical', lifespan='off'))
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

    def setUp(self):
        suffix = uuid4().hex
        self.owner_email = f'poll-owner-{suffix}@test'
        self.foreign_email = f'poll-foreign-{suffix}@test'
        self.tokens = {
            email: main.create_access_token({'sub': email})
            for email in (self.owner_email, self.foreign_email)
        }
        with main.db_session() as db:
            db.add_all([main.User(email=email, password_hash='unused')
                        for email in self.tokens])
            db.commit()

    def tearDown(self):
        with main.db_session() as db:
            ids = [u.id for u in db.query(main.User).filter(
                main.User.email.in_([self.owner_email, self.foreign_email]))]
            polls = [p.id for p in db.query(main.PollDefinition.id).filter(
                main.PollDefinition.owner_id.in_(ids))]
            db.query(main.PollSession).filter(main.PollSession.poll_id.in_(polls)).delete(
                synchronize_session=False)
            db.query(main.PollDefinition).filter(main.PollDefinition.id.in_(polls)).delete(
                synchronize_session=False)
            db.query(main.User).filter(main.User.id.in_(ids)).delete(
                synchronize_session=False)
            db.commit()

    def request(self, method='GET', path='/polls', data=None, email=None, anonymous=False):
        headers = {} if anonymous else {
            'Authorization': 'Bearer ' + self.tokens[email or self.owner_email]
        }
        if data is not None:
            headers['Content-Type'] = 'application/json'
        request = Request(
            self.address + path,
            method=method, headers=headers,
            data=json.dumps(data).encode() if data is not None else None,
        )
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as exc:
            response = exc
        raw = response.read()
        return response.code, json.loads(raw) if raw else None

    def test_create_read_and_list_without_event_or_quiz(self):
        status, poll = self.request('POST', data={
            'question': '  Which topic next? ',
            'options': [' Robotics ', 'Energy', 'Culture'],
        })
        self.assertEqual(status, 201)
        self.assertEqual(poll['question'], 'Which topic next?')
        self.assertEqual(poll['options'], ['Robotics', 'Energy', 'Culture'])
        self.assertEqual(poll['revision'], 1)
        self.assertEqual(self.request(path='/polls/' + poll['id'])[1], poll)
        listing = self.request()[1]
        self.assertEqual([p['id'] for p in listing['items']], [poll['id']])
        self.assertFalse(listing['has_more'])
        with main.db_session() as db:
            row = db.get(main.PollDefinition, poll['id'])
            self.assertIsNotNone(row)
            self.assertEqual(row.options, poll['options'])
            self.assertEqual(db.query(main.PollSession).filter_by(poll_id=poll['id']).count(), 0)

    def test_owner_isolation_and_anonymous_rejection(self):
        status, poll = self.request('POST', data={
            'question': 'Favorite subject?', 'options': ['A', 'B'],
        })
        self.assertEqual(status, 201)
        self.assertEqual(self.request(path='/polls/' + poll['id'], email=self.foreign_email)[0], 404)
        self.assertEqual(self.request(email=self.foreign_email)[1]['items'], [])
        self.assertEqual(self.request('POST', data={
            'question': 'Another?', 'options': ['A', 'B'],
        }, anonymous=True)[0], 401)
        self.assertEqual(self.request(anonymous=True)[0], 401)
        self.assertEqual(self.request(path='/polls/' + poll['id'], anonymous=True)[0], 401)

    def test_option_constraints_and_no_partial_writes(self):
        cases = [
            {'question': 'Any?', 'options': ['Only one']},
            {'question': 'Any?', 'options': list('ABCDEFG')},
            {'question': 'Any?', 'options': ['A', ' a ']},
            {'question': 'Any?', 'options': ['A', '   ']},
            {'question': 'Any?', 'options': ['A', 'B' * 161]},
            {'question': ' ', 'options': ['A', 'B']},
            {'question': 'Any?', 'options': ['A', 'B'], 'owner_id': 123},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(self.request('POST', data=case)[0], 422)
        self.assertEqual(self.request()[1]['items'], [])

    def test_six_options_and_stable_read_after_separate_database_session(self):
        options = ['One', 'Two', 'Three', 'Four', 'Five', 'Six']
        status, poll = self.request('POST', data={
            'question': 'Pick one', 'options': options,
        })
        self.assertEqual(status, 201)
        with main.db_session() as db:
            self.assertEqual(db.get(main.PollDefinition, poll['id']).options, options)
        self.assertEqual(self.request(path='/polls/' + poll['id'])[1]['options'], options)

    def test_unknown_id_and_pagination(self):
        self.assertEqual(self.request(path='/polls/' + uuid4().hex)[0], 404)
        for number in range(3):
            self.assertEqual(self.request('POST', data={
                'question': f'Question {number}', 'options': ['Yes', 'No'],
            })[0], 201)
        status, page = self.request(path='/polls?limit=2&offset=0')
        self.assertEqual(status, 200)
        self.assertEqual(len(page['items']), 2)
        self.assertTrue(page['has_more'])
        self.assertEqual(len(self.request(path='/polls?limit=2&offset=2')[1]['items']), 1)


if __name__ == '__main__':
    unittest.main()
