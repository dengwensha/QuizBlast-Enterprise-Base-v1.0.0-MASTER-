"""POLL-01B-01: standalone join and duplicate-registration HTTP acceptance."""
import json
import socket
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from secrets import token_urlsafe
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn
import app.main as main


class PollRegistrationAcceptance(unittest.TestCase):
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
        self.email = f'poll-join-owner-{suffix}@test'
        self.other = f'poll-join-other-{suffix}@test'
        self.tokens = {name: main.create_access_token({'sub': name})
                       for name in (self.email, self.other)}
        with main.db_session() as db:
            db.add_all([main.User(email=name, password_hash='unused') for name in self.tokens])
            db.commit()

    def tearDown(self):
        with main.db_session() as db:
            owners = [r.id for r in db.query(main.User).filter(main.User.email.in_(
                [self.email, self.other]))]
            poll_ids = [p.id for p in db.query(main.PollDefinition).filter(
                main.PollDefinition.owner_id.in_(owners))]
            ids = [s.id for s in db.query(main.PollSession).filter(
                main.PollSession.poll_id.in_(poll_ids))]
            db.query(main.PollParticipant).filter(
                main.PollParticipant.session_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.PollSession).filter(
                main.PollSession.id.in_(ids)).delete(synchronize_session=False)
            db.query(main.PollDefinition).filter(
                main.PollDefinition.id.in_(poll_ids)).delete(synchronize_session=False)
            db.query(main.User).filter(main.User.id.in_(owners)).delete(synchronize_session=False)
            db.commit()

    def request(self, method, path, data=None, email=None, anonymous=False):
        headers = {} if anonymous else {
            'Authorization': 'Bearer ' + self.tokens[email or self.email]
        }
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(self.address + path, method=method, headers=headers,
                      data=json.dumps(data).encode() if data is not None else None)
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        raw = response.read()
        return response.code, json.loads(raw) if raw else None

    def new_session(self):
        status, poll = self.request('POST', '/polls', {
            'question': 'Which technology?', 'options': ['CAD', 'CAM', 'AI']})
        self.assertEqual(status, 201)
        status, session = self.request('POST', '/polls/' + poll['id'] + '/sessions')
        self.assertEqual(status, 201)
        return poll, session

    def test_anonymous_join_and_exact_idempotent_replay(self):
        poll, session = self.new_session()
        url = '/poll-invites/' + session['invite']
        status, preview = self.request('GET', url, anonymous=True)
        self.assertEqual(status, 200)
        self.assertEqual(preview['question'], poll['question'])
        self.assertEqual(preview['options'], poll['options'])
        self.assertNotIn('invite', preview)
        self.assertNotIn('owner_id', preview)
        join_key = token_urlsafe(32)
        first_status, first = self.request('POST', url + '/join',
                                           {'join_key': join_key}, anonymous=True)
        second_status, second = self.request('POST', url + '/join',
                                             {'join_key': join_key}, anonymous=True)
        self.assertEqual((first_status, second_status), (200, 200))
        self.assertEqual(first, second)
        self.assertEqual(len(first['participant_token']), 43)
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollParticipant).filter_by(
                session_id=session['session_id']).count(), 1)
            record = db.get(main.PollParticipant, first['participant_id'])
            self.assertNotEqual(record.token_digest, first['participant_token'])

    def test_parallel_join_same_key_one_record_and_independent_key(self):
        _, session = self.new_session()
        url = '/poll-invites/' + session['invite'] + '/join'
        join_key = token_urlsafe(32)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(
                lambda _: self.request('POST', url, {'join_key': join_key}, anonymous=True),
                range(4)))
        self.assertTrue(all(code == 200 for code, _ in results), results)
        self.assertEqual(len({value['participant_id'] for _, value in results}), 1)
        code, distinct = self.request('POST', url, {'join_key': token_urlsafe(32)}, anonymous=True)
        self.assertEqual(code, 200)
        self.assertNotEqual(distinct['participant_id'], results[0][1]['participant_id'])
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollParticipant).filter_by(
                session_id=session['session_id']).count(), 2)

    def test_new_identity_rate_limit_preserves_existing_rejoin(self):
        _, session = self.new_session()
        url = '/poll-invites/' + session['invite'] + '/join'
        first_key = token_urlsafe(32)
        accepted = []
        # Rate limit is scoped to the invitation/session and observed client IP.
        for index in range(main.POLL_JOIN_MAX_NEW_IDENTITIES):
            key = first_key if index == 0 else token_urlsafe(32)
            status, record = self.request('POST', url, {'join_key': key}, anonymous=True)
            self.assertEqual(status, 200, (index, record))
            accepted.append(record)
        # A new identity beyond the boundary is rejected before any database write.
        status, rejection = self.request(
            'POST', url, {'join_key': token_urlsafe(32)}, anonymous=True)
        self.assertEqual(status, 429, rejection)
        self.assertEqual(rejection['detail'], 'auth_rate_limit_exceeded')
        status, replay = self.request('POST', url,
                                      {'join_key': first_key}, anonymous=True)
        self.assertEqual(status, 200)
        self.assertEqual(replay, accepted[0])
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollParticipant).filter_by(
                session_id=session['session_id']).count(),
                main.POLL_JOIN_MAX_NEW_IDENTITIES)
        # IP count on one poll must not block another distinct poll session.
        _, second = self.new_session()
        status, different_poll = self.request(
            'POST', '/poll-invites/' + second['invite'] + '/join',
            {'join_key': token_urlsafe(32)}, anonymous=True)
        self.assertEqual(status, 200, different_poll)

    def test_owner_boundary_invalid_invite_and_key(self):
        poll, session = self.new_session()
        self.assertEqual(self.request('POST', '/polls/' + poll['id'] + '/sessions',
                                      email=self.other)[0], 404)
        self.assertEqual(self.request('POST', '/polls/' + poll['id'] + '/sessions',
                                      anonymous=True)[0], 401)
        url = '/poll-invites/' + session['invite']
        self.assertEqual(self.request('POST', url + '/join',
                                      {'join_key': 'short'}, anonymous=True)[0], 422)
        self.assertEqual(self.request('GET', '/poll-invites/' + token_urlsafe(32),
                                      anonymous=True)[0], 404)
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollParticipant).filter_by(
                session_id=session['session_id']).count(), 0)


if __name__ == '__main__':
    unittest.main()
