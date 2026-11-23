"""POLL-01C-01: trusted, scoped vote counts and owner-only results."""
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


class PollResultsAcceptance(unittest.TestCase):
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
        self.email = f'poll-results-{suffix}@test'
        self.foreign = f'poll-results-foreign-{suffix}@test'
        self.tokens = {email: main.create_access_token({'sub': email})
                       for email in (self.email, self.foreign)}
        with main.db_session() as db:
            db.add_all([main.User(email=email, password_hash='unused')
                        for email in self.tokens])
            db.commit()

    def tearDown(self):
        with main.db_session() as db:
            owner_ids = [u.id for u in db.query(main.User).filter(
                main.User.email.in_([self.email, self.foreign]))]
            poll_ids = [p.id for p in db.query(main.PollDefinition).filter(
                main.PollDefinition.owner_id.in_(owner_ids))]
            session_ids = [s.id for s in db.query(main.PollSession).filter(
                main.PollSession.poll_id.in_(poll_ids))]
            db.query(main.PollVote).filter(main.PollVote.session_id.in_(
                session_ids)).delete(synchronize_session=False)
            db.query(main.PollParticipant).filter(main.PollParticipant.session_id.in_(
                session_ids)).delete(synchronize_session=False)
            db.query(main.PollSession).filter(main.PollSession.id.in_(
                session_ids)).delete(synchronize_session=False)
            db.query(main.PollDefinition).filter(main.PollDefinition.id.in_(
                poll_ids)).delete(synchronize_session=False)
            db.query(main.User).filter(main.User.id.in_(
                owner_ids)).delete(synchronize_session=False)
            db.commit()

    def req(self, method, path, data=None, token=None):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if data is not None:
            headers['Content-Type'] = 'application/json'
        request = Request(self.address + path, method=method, headers=headers,
                          data=json.dumps(data).encode() if data is not None else None)
        try:
            response = urlopen(request, timeout=12)
        except HTTPError as exc:
            response = exc
        raw = response.read()
        return response.code, json.loads(raw) if raw else None

    def new_session(self):
        status, poll = self.req('POST', '/polls',
                                {'question': 'Production technology?',
                                 'options': ['CAD', 'CAM', 'AI']},
                                self.tokens[self.email])
        self.assertEqual(status, 201)
        status, session = self.req('POST', '/polls/' + poll['id'] + '/sessions',
                                   token=self.tokens[self.email])
        self.assertEqual(status, 201)
        return session

    def join(self, session):
        status, participant = self.req(
            'POST', '/poll-invites/' + session['invite'] + '/join',
            {'join_key': token_urlsafe(32)})
        self.assertEqual(status, 200)
        return participant['participant_token']

    def results(self, session, token=None):
        return self.req('GET', '/poll-sessions/' + session['session_id'] + '/results',
                        token=token or self.tokens[self.email])

    def test_display_capability_is_read_only_and_survives_close(self):
        session = self.new_session()
        display_key = session['display_key']
        results_url = '/poll-sessions/' + session['session_id'] + '/display-results'
        status, initial = self.req('GET', results_url, token=display_key)
        self.assertEqual(status, 200)
        self.assertEqual(initial['total_votes'], 0)
        self.assertEqual([row['votes'] for row in initial['options']], [0, 0, 0])
        self.assertEqual(self.req('GET', results_url)[0], 401)
        self.assertEqual(self.req('GET', results_url, token=token_urlsafe(32))[0], 404)
        self.assertEqual(self.req('GET', results_url,
                                  token=self.tokens[self.email])[0], 401)
        voter = self.join(session)
        self.assertEqual(self.req('GET', results_url, token=voter)[0], 401)
        self.assertEqual(self.req('POST', '/poll-sessions/' + session['session_id'] + '/close',
                                  token=display_key)[0], 401)
        self.assertEqual(self.req('POST', '/poll-sessions/' + session['session_id'] + '/votes',
                                  {'option_index': 0}, display_key)[0], 401)
        self.assertEqual(self.req('POST', '/poll-sessions/' + session['session_id'] + '/votes',
                                  {'option_index': 1}, voter)[0], 200)
        status, active = self.req('GET', results_url, token=display_key)
        self.assertEqual(status, 200)
        self.assertEqual(active['total_votes'], 1)
        self.assertEqual(active['options'][1]['votes'], 1)
        self.assertNotIn('participant_id', str(active))
        self.assertNotIn('token_digest', str(active))
        self.assertEqual(self.req('POST', '/poll-sessions/' + session['session_id'] + '/close',
                                  token=self.tokens[self.email])[0], 200)
        status, closed = self.req('GET', results_url, token=display_key)
        self.assertEqual(status, 200)
        self.assertEqual(closed['status'], 'closed')
        self.assertEqual(closed['options'], active['options'])

    def test_empty_ballot_no_division_by_zero(self):
        session = self.new_session()
        status, result = self.results(session)
        self.assertEqual(status, 200)
        self.assertEqual(result['total_votes'], 0)
        self.assertEqual(result['registered_participants'], 0)
        self.assertEqual(result['response_rate_percent'], 0)
        self.assertEqual([item['votes'] for item in result['options']], [0, 0, 0])
        self.assertEqual([item['percent'] for item in result['options']], [0, 0, 0])
        self.assertEqual(result['definition_revision'], 1)
        self.assertNotIn('invite', result)

    def test_only_accepted_votes_count_and_response_denominator(self):
        session = self.new_session()
        first, second, abstains = (self.join(session) for _ in range(3))
        url = '/poll-sessions/' + session['session_id'] + '/votes'
        self.assertEqual(self.req('POST', url, {'option_index': 0}, first)[0], 200)
        self.assertEqual(self.req('POST', url, {'option_index': 0}, first)[0], 200)
        self.assertEqual(self.req('POST', url, {'option_index': 2}, first)[0], 409)
        self.assertEqual(self.req('POST', url, {'option_index': 2}, second)[0], 200)
        self.assertEqual(self.req('POST', url, {'option_index': 1}, abstains + 'bad')[0], 401)
        status, result = self.results(session)
        self.assertEqual(status, 200)
        self.assertEqual(result['total_votes'], 2)
        self.assertEqual(result['registered_participants'], 3)
        self.assertEqual(result['response_rate_percent'], 66.67)
        self.assertEqual([row['votes'] for row in result['options']], [1, 0, 1])
        self.assertEqual([row['percent'] for row in result['options']], [50, 0, 50])
        self.assertNotIn('participant_id', str(result))
        self.assertNotIn('token_digest', str(result))

    def test_owner_scope_anonymous_and_participant_fail_closed(self):
        session = self.new_session()
        token = self.join(session)
        path = '/poll-sessions/' + session['session_id'] + '/results'
        self.assertEqual(self.req('GET', path)[0], 401)
        self.assertEqual(self.req('GET', path, token=token)[0], 401)
        self.assertEqual(self.req('GET', path, token=self.tokens[self.foreign])[0], 404)
        self.assertEqual(self.req('GET', '/poll-sessions/' + uuid4().hex + '/results',
                                  token=self.tokens[self.email])[0], 404)

    def test_parallel_votes_stable_aggregate_and_closed_snapshot(self):
        session = self.new_session()
        tokens = [self.join(session) for _ in range(8)]
        url = '/poll-sessions/' + session['session_id']
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(
                lambda pair: self.req('POST', url + '/votes',
                                      {'option_index': pair[0] % 3}, pair[1]),
                enumerate(tokens)))
        self.assertTrue(all(code == 200 for code, _ in results), results)
        status, before = self.results(session)
        self.assertEqual(status, 200)
        self.assertEqual(before['total_votes'], 8)
        self.assertEqual(sum(row['votes'] for row in before['options']), 8)
        self.assertEqual(before['registered_participants'], 8)
        self.assertEqual(before['response_rate_percent'], 100)
        self.assertEqual(self.req('POST', url + '/close',
                                  token=self.tokens[self.email])[0], 200)
        # An accepted same-choice retry returns the original receipt even after close.
        replay_status, replay = self.req('POST', url + '/votes',
                                         {'option_index': 0}, tokens[0])
        self.assertEqual(replay_status, 200)
        self.assertEqual(replay, results[0][1])
        # Changing the already accepted ballot remains forbidden.
        self.assertEqual(self.req('POST', url + '/votes',
                                  {'option_index': 1}, tokens[0])[0], 409)
        status, after = self.results(session)
        self.assertEqual(status, 200)
        self.assertEqual(after['status'], 'closed')
        self.assertEqual(after['options'], before['options'])
        self.assertEqual(after['total_votes'], before['total_votes'])


if __name__ == '__main__':
    unittest.main()
