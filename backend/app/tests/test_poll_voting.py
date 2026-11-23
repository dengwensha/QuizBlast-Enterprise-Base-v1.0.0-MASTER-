"""POLL-01B-02: immutable vote, authorization, retries and close serialization."""
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


class PollVoteAcceptance(unittest.TestCase):
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
        self.email = f'poll-vote-{suffix}@test'
        self.foreign = f'poll-vote-foreign-{suffix}@test'
        self.tokens = {email: main.create_access_token({'sub': email})
                       for email in (self.email, self.foreign)}
        with main.db_session() as db:
            db.add_all([main.User(email=email, password_hash='unused')
                        for email in self.tokens])
            db.commit()

    def tearDown(self):
        with main.db_session() as db:
            owners = [u.id for u in db.query(main.User).filter(
                main.User.email.in_([self.email, self.foreign]))]
            poll_ids = [p.id for p in db.query(main.PollDefinition).filter(
                main.PollDefinition.owner_id.in_(owners))]
            session_ids = [s.id for s in db.query(main.PollSession).filter(
                main.PollSession.poll_id.in_(poll_ids))]
            db.query(main.PollVote).filter(
                main.PollVote.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(main.PollParticipant).filter(
                main.PollParticipant.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(main.PollSession).filter(
                main.PollSession.id.in_(session_ids)).delete(synchronize_session=False)
            db.query(main.PollDefinition).filter(
                main.PollDefinition.id.in_(poll_ids)).delete(synchronize_session=False)
            db.query(main.User).filter(main.User.id.in_(owners)).delete(synchronize_session=False)
            db.commit()

    def request(self, method, path, data=None, credential=None):
        headers = {}
        if credential:
            headers['Authorization'] = 'Bearer ' + credential
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(self.address + path, headers=headers, method=method,
                      data=json.dumps(data).encode() if data is not None else None)
        try:
            response = urlopen(req, timeout=12)
        except HTTPError as exc:
            response = exc
        content = response.read()
        return response.code, json.loads(content) if content else None

    def start(self):
        status, poll = self.request('POST', '/polls',
                                    {'question': 'Pick?', 'options': ['A', 'B', 'C']},
                                    self.tokens[self.email])
        self.assertEqual(status, 201)
        status, session = self.request('POST', '/polls/' + poll['id'] + '/sessions',
                                       credential=self.tokens[self.email])
        self.assertEqual(status, 201)
        return session

    def join(self, session):
        status, record = self.request('POST', '/poll-invites/' + session['invite'] + '/join',
                                      {'join_key': token_urlsafe(32)})
        self.assertEqual(status, 200)
        return record

    def test_immutable_idempotent_vote_and_resume(self):
        session = self.start()
        participant = self.join(session)
        path = '/poll-sessions/' + session['session_id']
        token = participant['participant_token']
        first = self.request('POST', path + '/votes', {'option_index': 1}, token)
        repeat = self.request('POST', path + '/votes', {'option_index': 1}, token)
        self.assertEqual(first[0], 200, first)
        self.assertEqual(repeat, first)
        status, state = self.request('GET', path + '/me', credential=token)
        self.assertEqual(status, 200)
        self.assertEqual(state['participant_id'], participant['participant_id'])
        self.assertEqual(state['vote'], first[1])
        self.assertEqual(self.request('POST', path + '/votes',
                                      {'option_index': 2}, token)[0], 409)
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollVote).filter_by(
                session_id=session['session_id']).count(), 1)

    def test_concurrent_conflicting_votes_have_one_durable_winner(self):
        session = self.start()
        token = self.join(session)['participant_token']
        path = '/poll-sessions/' + session['session_id'] + '/votes'
        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(
                lambda option: self.request('POST', path, {'option_index': option}, token),
                [0, 1, 2, 0]))
        accepted = [result for code, result in outcomes if code == 200]
        self.assertGreaterEqual(len(accepted), 1)
        self.assertTrue(all(code in (200, 409) for code, _ in outcomes), outcomes)
        self.assertEqual(len({r['vote_id'] for r in accepted}), 1)
        with main.db_session() as db:
            rows = db.query(main.PollVote).filter_by(session_id=session['session_id']).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].option_index, accepted[0]['option_index'])

    def test_cross_session_invalid_token_and_invalid_choice(self):
        first = self.start()
        second = self.start()
        token = self.join(first)['participant_token']
        one = '/poll-sessions/' + first['session_id']
        two = '/poll-sessions/' + second['session_id']
        self.assertEqual(self.request('POST', two + '/votes', {'option_index': 0}, token)[0], 401)
        self.assertEqual(self.request('POST', one + '/votes', {'option_index': 0})[0], 401)
        self.assertEqual(self.request('POST', one + '/votes',
                                      {'option_index': 10}, token)[0], 422)
        self.assertEqual(self.request('POST', one + '/votes',
                                      {'option_index': -1}, token)[0], 422)
        self.assertEqual(self.request('POST', one + '/votes',
                                      {'option_index': 0, 'owner_id': 2}, token)[0], 422)
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollVote).count(), 0)

    def test_close_rejects_late_votes_and_restores_prior_receipt(self):
        session = self.start()
        a = self.join(session)['participant_token']
        b = self.join(session)['participant_token']
        path = '/poll-sessions/' + session['session_id']
        accepted = self.request('POST', path + '/votes', {'option_index': 0}, a)
        self.assertEqual(accepted[0], 200)
        self.assertEqual(self.request('POST', path + '/close',
                                      credential=self.tokens[self.foreign])[0], 404)
        self.assertEqual(self.request('POST', path + '/close',
                                      credential=self.tokens[self.email])[0], 200)
        self.assertEqual(self.request('POST', path + '/votes', {'option_index': 1}, b)[0], 409)
        self.assertEqual(self.request('POST', path + '/votes', {'option_index': 0}, a),
                         accepted)
        self.assertEqual(self.request('GET', path + '/me', credential=a)[1]['vote'],
                         accepted[1])
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollVote).filter_by(
                session_id=session['session_id']).count(), 1)

    def test_vote_close_race_is_consistent(self):
        session = self.start()
        token = self.join(session)['participant_token']
        path = '/poll-sessions/' + session['session_id']
        with ThreadPoolExecutor(max_workers=2) as pool:
            vote_future = pool.submit(self.request, 'POST', path + '/votes',
                                      {'option_index': 2}, token)
            close_future = pool.submit(self.request, 'POST', path + '/close',
                                       None, self.tokens[self.email])
            vote_result, close_result = vote_future.result(), close_future.result()
        self.assertIn(vote_result[0], (200, 409))
        self.assertEqual(close_result[0], 200)
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollVote).filter_by(
                session_id=session['session_id']).count(),
                1 if vote_result[0] == 200 else 0)


if __name__ == '__main__':
    unittest.main()
