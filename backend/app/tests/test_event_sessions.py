"""EVENT-02 HTTP + SQL acceptance against the configured production app."""
import asyncio
import json
import socket
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn
from websockets.asyncio.client import connect
import app.main as main
from app.services.extend_event_report import main as extend_report


class EventSessionsAcceptance(unittest.TestCase):
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
        self.email = f'event-session-{suffix}@test'
        self.other = f'other-session-{suffix}@test'
        self.tokens = {email: main.create_access_token({'sub': email}) for email in (self.email, self.other)}
        self.quiz_ids = []
        with main.db_session() as db:
            db.add_all([main.User(email=self.email, password_hash='unused'),
                        main.User(email=self.other, password_hash='unused')])
            for kind in ('owned', 'foreign', 'published', 'unpublished', 'empty'):
                quiz = main.Quiz(title=f'{kind}-{suffix}', owner_email=(
                    self.email if kind in ('owned', 'empty') else self.other if kind == 'foreign' else None))
                db.add(quiz)
                db.flush()
                if kind in ('published', 'unpublished'):
                    db.add(main.PublishedQuizSet(quiz_id=quiz.id, slug=f'{kind}-{suffix}',
                        topic='Test', audience='General', difficulty='Easy', is_published=kind == 'published'))
                if kind != 'empty':
                    db.add(main.Question(quiz_id=quiz.id, question='One?', option1='A', option2='B',
                        option3='C', option4='D', correct=0, time=60))
                self.quiz_ids.append(quiz.id)
            db.commit()

    def tearDown(self):
        with main.db_session() as db:
            ids = [e.id for e in db.query(main.EventDraft).join(main.User).filter(main.User.email == self.email)]
            links = db.query(main.EventGameSession).filter(main.EventGameSession.event_id.in_(ids)).all()
            pins = [link.pin for link in links]
            db.query(main.EventReport).filter(main.EventReport.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventGameSession).filter(main.EventGameSession.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventQuizSelection).filter(main.EventQuizSelection.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventDraft).filter(main.EventDraft.id.in_(ids)).delete(synchronize_session=False)
            # Also remove a staged room if an atomicity check exposed a bug.
            for room in db.query(main.GameRoom).filter(main.GameRoom.host_email == self.email):
                pins.append(room.pin)
                db.delete(room)
            db.query(main.PublishedQuizSet).filter(main.PublishedQuizSet.quiz_id.in_(self.quiz_ids)).delete(synchronize_session=False)
            for quiz in db.query(main.Quiz).filter(main.Quiz.id.in_(self.quiz_ids)):
                db.delete(quiz)
            db.query(main.User).filter(main.User.email.in_([self.email, self.other])).delete(synchronize_session=False)
            db.commit()
        for pin in pins:
            for mapping in (main.rooms, main.scores, main.current_question_index, main.answered_players,
                            main.room_quiz_map, main.room_host_map, main.answer_stats_map,
                            main.waiting_next_question, main.question_start_time, main.game_phase,
                            main.remaining_seconds, main.question_deadline, main.room_instance_map):
                mapping.pop(pin, None)

    def request(self, method='GET', path='/events', data=None, email=None, anonymous=False):
        headers = {} if anonymous else {'Authorization': 'Bearer ' + self.tokens[email or self.email]}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(self.address + path, data=json.dumps(data).encode() if data is not None else None,
                      method=method, headers=headers)
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        raw = response.read()
        return response.code, json.loads(raw) if raw.startswith(b'{') or raw.startswith(b'[') else raw.decode()

    def event(self, quiz_index=0):
        status, row = self.request('POST', data={'title': 'Event game'})
        self.assertEqual(status, 201)
        path = '/events/' + row['id']
        status, state = self.request('PUT', path + '/quiz', {'quiz_id': self.quiz_ids[quiz_index], 'revision': row['revision']})
        self.assertEqual(status, 200, state)
        return path, state

    def test_eligible_quizzes_and_foreign_event(self):
        path, state = self.event()
        status, game = self.request(path=path + '/game')
        self.assertEqual(status, 200)
        choices = {q['id'] for q in game['quizzes']}
        self.assertTrue({self.quiz_ids[0], self.quiz_ids[2]}.issubset(choices))
        self.assertTrue({self.quiz_ids[1], self.quiz_ids[3]}.isdisjoint(choices))
        for index, expected in ((1, 404), (3, 404), (4, 409)):
            self.assertEqual(self.request('PUT', path + '/quiz',
                {'quiz_id': self.quiz_ids[index], 'revision': state['event']['revision']})[0], expected)
        for method, suffix, data in [('GET', '/game', None), ('PUT', '/quiz', {'quiz_id': self.quiz_ids[0], 'revision': 2}),
                                     ('POST', '/session', {'revision': 2})]:
            self.assertEqual(self.request(method, path + suffix, data, email=self.other)[0], 404)
            self.assertEqual(self.request(method, path + suffix, data, anonymous=True)[0], 401)

    def test_concurrent_idempotent_session_and_quiz_freeze(self):
        path, state = self.event()
        revision = state['event']['revision']
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.request('POST', path + '/session', {'revision': revision}), range(2)))
        self.assertEqual([status for status, _ in results], [200, 200])
        self.assertEqual(results[0][1]['session'], results[1][1]['session'])
        session = results[0][1]['session']
        self.assertEqual(session['phase'], 'lobby')
        self.assertEqual(main.game_phase[session['pin']], 'lobby')
        self.assertNotIn(session['pin'], main.game_tasks)
        self.assertEqual(self.request('PUT', path + '/quiz', {'quiz_id': self.quiz_ids[2], 'revision': 3})[0], 409)
        self.assertEqual(self.request('POST', '/start-game/' + session['pin'], {})[1], {'error': 'no_players'})
        with main.db_session() as db:
            self.assertEqual(db.query(main.GameRoom).filter_by(host_email=self.email).count(), 1)
            self.assertEqual(db.query(main.EventGameSession).filter_by(event_id=path.split('/')[-1]).count(), 1)
            q = db.query(main.Question).filter_by(quiz_id=self.quiz_ids[0]).first()
            question_id = q.id
        self.assertEqual(self.request('PUT', '/questions/' + str(question_id),
            {'question': 'changed', 'options': ['A', 'B', 'C', 'D'], 'correct': 0, 'time': 10})[0], 409)

    def test_rollback_stale_and_retry_after_response_failure(self):
        path, state = self.event()
        revision = state['event']['revision']
        self.assertEqual(self.request('POST', path + '/session', {'revision': revision - 1})[0], 409)
        stage = main.room_builder.stage
        def fail_after_stage(*args):
            stage(*args)
            raise RuntimeError('injected transaction failure')
        with patch.object(main.room_builder, 'stage', side_effect=fail_after_stage):
            self.assertEqual(self.request('POST', path + '/session', {'revision': revision})[0], 500)
        with main.db_session() as db:
            self.assertEqual(db.query(main.GameRoom).filter_by(host_email=self.email).count(), 0)
        with patch.object(main, 'initialize_lobby_room', side_effect=RuntimeError('response failure after commit')):
            self.assertEqual(self.request('POST', path + '/session', {'revision': revision})[0], 500)
        status, state = self.request('POST', path + '/session', {'revision': revision})
        self.assertEqual(status, 200)
        self.assertEqual(main.game_phase[state['session']['pin']], 'lobby')

    def test_published_session_closed_and_purged_identity(self):
        path, state = self.event(2)
        _, state = self.request('POST', path + '/session', {'revision': state['event']['revision']})
        original = state['session']
        self.assertEqual(self.request('POST', '/close-room/' + original['pin'], {})[0], 200)
        with main.db_session() as db:
            room = db.get(main.GameRoom, original['pin'])
            db.delete(room)
            db.commit()
        _, state = self.request('POST', path + '/session', {'revision': 1})
        self.assertEqual(state['session']['instance_id'], original['instance_id'])
        self.assertFalse(state['session']['can_open'])
        with main.db_session() as db:
            self.assertEqual(db.query(main.GameRoom).filter_by(host_email=self.email).count(), 0)

    def test_session_requires_selection_and_survives_pin_reuse(self):
        _, row = self.request('POST', data={'title': 'No quiz yet'})
        path = '/events/' + row['id']
        self.assertEqual(self.request('POST', path + '/session', {'revision': 1})[1]['detail'], 'event_quiz_required')
        _, state = self.request('PUT', path + '/quiz', {'quiz_id': self.quiz_ids[0], 'revision': 1})
        _, state = self.request('POST', path + '/session', {'revision': state['event']['revision']})
        original = state['session']
        self.request('POST', '/close-room/' + original['pin'], {})
        with main.db_session() as db:
            db.delete(db.get(main.GameRoom, original['pin']))
            db.commit()
        with patch.object(main, 'generate_pin', return_value=original['pin']):
            main.create_room(self.quiz_ids[0], authorization='Bearer ' + self.tokens[self.email])
        _, state = self.request('POST', path + '/session', {'revision': 1})
        self.assertEqual(state['session']['instance_id'], original['instance_id'])
        self.assertFalse(state['session']['can_open'])
        self.assertNotEqual(main.room_instance_map[original['pin']], original['instance_id'])

    def test_startup_restores_same_event_room(self):
        path, state = self.event()
        _, state = self.request('POST', path + '/session', {'revision': state['event']['revision']})
        original = state['session']
        main.room_instance_map.pop(original['pin'])
        main.rooms.pop(original['pin'])
        asyncio.run(main.restore_active_rooms())
        _, restored = self.request(path=path + '/game')
        self.assertEqual(restored['session'], original)
        self.assertEqual(main.room_instance_map[original['pin']], original['instance_id'])
        _, repeated = self.request('POST', path + '/session', {'revision': 1})
        self.assertEqual(repeated['session'], original)

    def test_host_player_display_and_completed_restart_guard(self):
        path, state = self.event()
        _, state = self.request('POST', path + '/session', {'revision': state['event']['revision']})
        session = state['session']
        pin, identity = session['pin'], session['instance_id']
        self.assertEqual(self.request('POST', '/start-game/' + pin, {}, email=self.other)[0], 403)
        self.assertEqual(self.request(path=path + '/report')[0], 404)
        async def flow():
            ws = self.address.replace('http:', 'ws:') + f'/ws/{pin}/'
            async with connect(ws + f'HOST?instance={identity}', subprotocols=['quizblast-host', self.tokens[self.email]]) as host:
                await host.recv()
                async with connect(ws + f'Ada?instance={identity}') as player, connect(ws + f'DISPLAY?instance={identity}') as display:
                    await player.recv()
                    await display.recv()
                    self.assertEqual(self.request('POST', '/start-game/' + pin, {})[0], 200)
                    self.assertEqual(self.request('POST', '/end-game/' + pin, {})[0], 200)
                    self.assertEqual(self.request('POST', '/start-game/' + pin, {})[1]['detail'], 'event_session_completed')
        asyncio.run(flow())
        _, result = self.request(path=path + '/game')
        self.assertEqual(result['session']['phase'], 'completed')
        status, report = self.request(path=path + '/report')
        self.assertEqual(status, 200)
        self.assertEqual(report['ranking'], [{'name': 'Ada', 'score': 0}])
        self.assertEqual(datetime.fromisoformat(report['expires_at']) -
                         datetime.fromisoformat(report['completed_at']), timedelta(days=15))
        self.assertEqual(self.request(path=path + '/report', email=self.other)[0], 404)
        self.assertEqual(self.request(path=path + '/report', anonymous=True)[0], 401)
        self.assertEqual(self.request('POST', '/close-room/' + pin, {})[0], 200)
        with main.db_session() as db:
            db.delete(db.get(main.GameRoom, pin))
            db.commit()
        self.assertEqual(self.request(path=path + '/report'), (200, report))
        extended = datetime.fromisoformat(report['expires_at']) + timedelta(days=15)
        with patch('sys.argv', ['extend_event_report', state['event']['id'], extended.isoformat()]):
            extend_report()
        status, updated = self.request(path=path + '/report')
        self.assertEqual(status, 200)
        self.assertEqual(datetime.fromisoformat(updated['expires_at']), extended)
        self.assertEqual(updated['ranking'], report['ranking'])
        with main.db_session() as db:
            db.get(main.EventReport, state['event']['id']).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.request(path=path + '/report')[0], 410)
        main.purge_closed_room_batches()
        self.assertEqual(self.request(path=path + '/report')[0], 404)


if __name__ == '__main__':
    unittest.main()
