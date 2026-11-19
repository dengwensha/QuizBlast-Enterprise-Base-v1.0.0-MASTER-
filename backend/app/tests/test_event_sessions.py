"""EVENT-02 HTTP + SQL acceptance against the configured production app."""
import asyncio
from io import BytesIO
from PIL import Image
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
            step_links = db.query(main.EventStepSession).filter(main.EventStepSession.event_id.in_(ids)).all()
            pins = [link.pin for link in [*links, *step_links]]
            db.query(main.EventStepReport).filter(main.EventStepReport.instance_id.in_(
                [link.instance_id for link in step_links])).delete(synchronize_session=False)
            db.query(main.EventStepSession).filter(main.EventStepSession.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventRetention).filter(main.EventRetention.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventDeck).filter(main.EventDeck.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventRun).filter(main.EventRun.event_id.in_(ids)).delete(synchronize_session=False)
            db.query(main.EventAgenda).filter(main.EventAgenda.event_id.in_(ids)).delete(synchronize_session=False)
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

    def test_delete_unstarted_event_and_protect_started_events(self):
        path, state = self.event()
        self.assertTrue(self.request(path=path)[1]['can_delete'])
        revision = state['event']['revision']
        self.assertEqual(self.request('DELETE', f'{path}?revision={revision}', email=self.other)[0], 404)
        self.assertEqual(self.request('DELETE', f'{path}?revision={revision}', anonymous=True)[0], 401)
        status, agenda = self.request('PUT', path + '/agenda', {
            'revision': revision, 'steps': [{'kind': 'break', 'title': 'Coffee'}]})
        self.assertEqual(status, 200)
        self.assertEqual(self.request('DELETE', f'{path}?revision={revision}')[0], 409)
        with main.db_session() as db:
            db.add(main.EventDeck(event_id=state['event']['id'], name='slides.pdf', page_count=1, pages=['']))
            db.commit()
        self.assertEqual(self.request('DELETE', f"{path}?revision={agenda['revision']}")[0], 204)
        self.assertEqual(self.request(path=path)[0], 404)
        with main.db_session() as db:
            event_id = state['event']['id']
            self.assertIsNone(db.get(main.EventAgenda, event_id))
            self.assertIsNone(db.get(main.EventQuizSelection, event_id))
            self.assertFalse(db.query(main.EventDeck).filter_by(event_id=event_id).count())
            self.assertIsNotNone(db.get(main.Quiz, self.quiz_ids[0]))

        for mode in ('live', 'session'):
            path, state = self.event()
            revision = state['event']['revision']
            if mode == 'live':
                _, agenda = self.request('PUT', path + '/agenda', {
                    'revision': revision, 'steps': [{'kind': 'break', 'title': 'Coffee'}]})
                self.assertEqual(self.request('POST', path + '/live')[0], 200)
                revision = agenda['revision']
            else:
                self.assertEqual(self.request('POST', path + '/session', {'revision': revision})[0], 200)
            self.assertFalse(self.request(path=path)[1]['can_delete'])
            self.assertEqual(self.request('DELETE', f'{path}?revision={revision}'),
                             (409, {'detail': 'event_delete_started'}))

    def test_pdf_deck_preview_and_live_page_isolation(self):
        path, _ = self.event()
        pdf = BytesIO()
        Image.new('RGB', (48, 36), 'white').save(
            pdf, 'PDF', save_all=True, append_images=[Image.new('RGB', (48, 36), 'blue')])
        body = (b'--deck\r\nContent-Disposition: form-data; name="file"; filename="opening.pdf"\r\n'
                b'Content-Type: application/pdf\r\n\r\n' + pdf.getvalue() + b'\r\n--deck--\r\n')
        upload = Request(self.address + path + '/decks', data=body,
                         headers={'Authorization': 'Bearer ' + self.tokens[self.email],
                                  'Content-Type': 'multipart/form-data; boundary=deck'})
        with urlopen(upload, timeout=10) as response:
            self.assertEqual(response.status, 201)
            deck = json.load(response)
        self.assertEqual(deck['page_count'], 2)
        _, agenda = self.request(path=path + '/agenda')
        data = {'revision': agenda['revision'], 'steps': [
            {'kind': 'presentation', 'title': 'Opening', 'deck_id': deck['id']}]}
        other_path, _ = self.event()
        self.assertEqual(self.request('PUT', other_path + '/agenda', data)[0], 422)
        self.assertEqual(self.request('PUT', path + '/agenda', data)[0], 200)
        _, reopened = self.request(path=path + '/agenda')
        self.assertEqual(reopened['deck_names'], {deck['id']: 'opening.pdf'})
        self.assertEqual(self.request(path=other_path + '/agenda')[1]['deck_names'], {})
        preview_path = path + '/decks/' + deck['id'] + '/0'
        self.assertEqual(self.request(path=preview_path, email=self.other)[0], 404)
        def png(suffix, token):
            request = Request(self.address + suffix, headers={'Authorization': 'Bearer ' + token})
            try:
                response = urlopen(request, timeout=10)
            except HTTPError as exc:
                return exc.code, b''
            with response:
                self.assertEqual(response.headers.get_content_type(), 'image/png')
                return response.status, response.read()
        self.assertEqual(png(preview_path, self.tokens[self.email])[0], 200)
        _, run = self.request('POST', path + '/live')
        key = run['display_key']
        page_path = '/events/display/program/page/'
        self.assertEqual(png(page_path + '1', key)[0], 404)
        _, current = self.request('PUT', path + '/live', {'action': 'open', 'revision': 1})
        self.assertEqual(current['live']['page_count'], 2)
        first = png(page_path + '2', key)
        self.assertEqual(first[0], 200)
        _, next_page = self.request('PUT', path + '/live', {'action': 'next_page', 'revision': 2})
        self.assertEqual(next_page['live']['page'], 1)
        self.assertEqual(png(page_path + '2', key)[0], 404)
        second = png(page_path + '3', key)
        self.assertEqual(second[0], 200)
        self.assertNotEqual(first[1], second[1])
        self.assertEqual(self.request('PUT', path + '/live',
                                      {'action': 'next_page', 'revision': 3})[0], 409)

    def test_live_agenda_display_and_transitions(self):
        path, _ = self.event()
        self.assertEqual(self.request('POST', path + '/live')[0], 409)
        _, agenda = self.request(path=path + '/agenda')
        steps = [{'kind': 'presentation', 'title': 'Opening'},
                 {'kind': 'break', 'title': 'Pause'},
                 {'kind': 'quiz', 'title': 'Quiz'}]
        self.assertEqual(self.request('PUT', path + '/agenda',
                                      {'revision': agenda['revision'], 'steps': steps})[0], 200)
        status, run = self.request('POST', path + '/live')
        self.assertEqual(status, 200)
        self.assertEqual(self.request('POST', path + '/live'), (200, run))
        self.assertEqual(self.request(path=path + '/live', email=self.other)[0], 404)
        self.assertEqual(self.request(path='/events/display/program/state')[0], 404)
        request = Request(self.address + '/events/display/program/state',
                          headers={'Authorization': 'Bearer ' + run['display_key']})
        def display():
            with urlopen(request, timeout=10) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                return json.load(response)
        self.assertEqual(display(), run['live'])
        command = lambda action, revision: self.request('PUT', path + '/live',
                                                        {'action': action, 'revision': revision})
        self.assertEqual(command('open', 1)[0], 200)
        self.assertEqual(display()['view'], 'step')
        self.assertEqual(command('complete', 1)[0], 409)
        self.assertEqual(command('complete', 2)[0], 200)
        self.assertEqual((display()['view'], display()['cursor']), ('agenda', 1))
        self.assertEqual(command('open', 3)[0], 200)
        self.assertEqual(command('complete', 4)[0], 200)
        self.assertEqual(command('open', 5)[0], 200)
        self.assertEqual(command('complete', 6)[1]['detail'], 'event_quiz_not_completed')
        self.assertIsNone(display()['quiz_display'])
        _, game = self.request(path=path + '/game')
        status, created = self.request('POST', path + '/session',
                                       {'revision': game['event']['revision']})
        self.assertEqual(status, 200)
        room = created['session']
        self.assertEqual(display()['quiz_display'], {key: room[key] for key in ('pin', 'instance_id')})
        self.assertEqual(self.request('POST', '/close-room/' + room['pin']),
                         (409, {'detail': 'event_quiz_not_completed'}))
        self.assertEqual(main.game_phase[room['pin']], 'lobby')
        main.game_phase[room['pin']] = 'completed'
        main.save_game(room['pin'])
        self.assertEqual(self.request('POST', '/close-room/' + room['pin'])[0], 200)
        self.assertIsNone(display()['quiz_display'])

    def test_presentation_retention_follows_program_completion(self):
        path, _ = self.event()
        agenda = path + '/agenda'
        state = lambda: self.request(path=agenda)[1]
        self.assertIsNone(state()['retention'])
        steps = [{'kind': 'break', 'title': title} for title in ('A', 'B')]
        def save(**fields):
            return self.request('PUT', agenda, dict(revision=state()['revision'], steps=steps, **fields))[0]
        self.assertEqual(save(retention='delete_after_7_days'), 200)
        self.assertEqual(save(), 200)  # Older clients omit the preference.
        self.assertEqual(state()['retention'], 'delete_after_7_days')
        self.assertEqual(self.request('POST', path + '/live')[0], 200)
        for rev, action in enumerate(('open', 'complete', 'open', 'complete'), 1):
            self.assertIsNone(state()['program_completed_at'])
            self.assertEqual(self.request('PUT', path + '/live', dict(action=action, revision=rev))[0], 200)
        finished = state()['program_completed_at']
        self.assertIsNotNone(finished)
        self.assertEqual(save(retention='keep'), 200)
        self.assertEqual((state()['retention'], state()['program_completed_at']), ('keep', finished))

    def test_agenda_order_ownership_and_revision(self):
        path, _ = self.event()
        path += '/agenda'
        status, initial = self.request(path=path)
        self.assertEqual(status, 200)
        self.assertEqual(initial['steps'], [])
        kinds = ['presentation'] * 3 + ['break'] + ['presentation'] * 2 + ['quiz', 'presentation']
        steps = [{'kind': kind, 'title': f'Adım {index}'} for index, kind in enumerate(kinds)]
        data = {'revision': initial['revision'], 'steps': steps}
        self.assertEqual(self.request('PUT', path, data, email=self.other)[0], 404)
        self.assertEqual(self.request(path=path, email=self.other)[0], 404)
        status, saved = self.request('PUT', path, data)
        self.assertEqual(status, 200)
        quiz_step = saved['steps'][-2]
        self.assertEqual({k: v for k, v in quiz_step.items() if k != 'step_id'}, steps[-2])
        self.assertEqual(saved['steps'][:-2] + saved['steps'][-1:], steps[:-2] + steps[-1:])
        self.assertEqual(self.request(path=path), (200, saved))
        reordered = [dict(quiz_step, title='Quiz renamed'), *saved['steps'][:-2], saved['steps'][-1]]
        status, resaved = self.request('PUT', path, {'revision': saved['revision'], 'steps': reordered})
        self.assertEqual((status, resaved['steps'][0]), (200, reordered[0]))
        foreign_path, foreign = self.event()
        self.assertEqual(self.request('PUT', foreign_path + '/agenda', {
            'revision': foreign['event']['revision'], 'steps': [quiz_step],
        }), (422, {'detail': 'event_quiz_step_invalid'}))
        self.assertEqual(self.request('PUT', path, data)[0], 409)

    def test_multiple_quiz_selections_follow_steps_and_stay_in_draft(self):
        path, state = self.event()
        revision = state['event']['revision']
        endpoint = path + '/agenda'
        first = {'kind': 'quiz', 'title': 'Quiz A', 'quiz_id': self.quiz_ids[0]}
        second = {'kind': 'quiz', 'title': 'Quiz B', 'quiz_id': self.quiz_ids[2]}
        pause = {'kind': 'break', 'title': 'Pause'}
        for invalid, code in [
            (dict(second, quiz_id=self.quiz_ids[1]), 404),
            (dict(second, quiz_id=self.quiz_ids[4]), 409),
            (dict(pause, quiz_id=self.quiz_ids[0]), 422),
        ]:
            self.assertEqual(self.request('PUT', endpoint, {
                'revision': revision, 'steps': [first, invalid],
            })[0], code)
        status, agenda = self.request('PUT', endpoint, {
            'revision': revision, 'steps': [first, pause, second],
        })
        self.assertEqual(status, 200, agenda)
        first, pause, second = agenda['steps']
        self.assertNotEqual(first['step_id'], second['step_id'])
        self.assertEqual(self.request('PUT', endpoint, {
            'revision': agenda['revision'], 'steps': [first, first],
        }), (422, {'detail': 'event_quiz_step_invalid'}))
        status, reordered = self.request('PUT', endpoint, {
            'revision': agenda['revision'], 'steps': [second, pause, first],
        })
        self.assertEqual(status, 200, reordered)
        self.assertEqual(self.request(path=endpoint)[1]['steps'], [second, pause, first])
        self.assertEqual(self.request('POST', path + '/session', {'revision': reordered['revision']}),
                         (409, {'detail': 'event_step_sessions_unavailable'}))
        second.pop('quiz_id')
        status, incomplete = self.request('PUT', endpoint, {
            'revision': reordered['revision'], 'steps': [second, pause, first],
        })
        self.assertEqual(status, 200)
        self.assertEqual(self.request('POST', path + '/live'),
                         (409, {'detail': 'event_step_quiz_required'}))
        self.assertEqual(self.request(path=path + '/live'), (200, 'null'))
        self.assertIsNone(self.request(path=path + '/game')[1]['session'])

    def test_delete_quiz_respects_agenda_and_remaining_run_steps(self):
        path, state = self.event(2)  # Legacy selection is a different, published quiz.
        quiz_id = self.quiz_ids[0]
        delete = lambda: self.request('DELETE', f'/quizzes/{quiz_id}')
        step = {'kind': 'quiz', 'title': 'A', 'quiz_id': quiz_id}
        status, agenda = self.request('PUT', path + '/agenda', {
            'steps': [step], 'revision': state['event']['revision']})
        self.assertEqual(status, 200)
        blocked = (409, {'detail': 'quiz_used_in_event'})
        self.assertEqual(delete(), blocked)
        self.assertEqual(self.request('POST', path + '/live')[0], 200)
        self.assertEqual(delete(), blocked)
        # A run has its own snapshot; exercise it independently of the editable agenda.
        event_id = state['event']['id']
        with main.db_session() as db:
            db.get(main.EventAgenda, event_id).steps = []
            db.commit()
        self.assertEqual(delete(), blocked)
        with main.db_session() as db:
            db.get(main.EventRun, event_id).cursor = 1
            db.commit()
        self.assertEqual(delete(), (200, {'status': 'quiz_deleted'}))

    def test_live_multi_quiz_display_follows_active_step_and_requires_its_result(self):
        path, state = self.event()
        status, agenda = self.request('PUT', path + '/agenda', {
            'revision': state['event']['revision'],
            'steps': [{'kind': 'presentation', 'title': 'Opening'},
                      {'kind': 'quiz', 'title': 'A', 'quiz_id': self.quiz_ids[0]},
                      {'kind': 'break', 'title': 'Pause'},
                      {'kind': 'quiz', 'title': 'B', 'quiz_id': self.quiz_ids[2]}],
        })
        self.assertEqual(status, 200)
        first, second = [f"{path}/steps/{agenda['steps'][i]['step_id']}" for i in (1, 3)]
        status, live = self.request('POST', path + '/live')
        self.assertEqual(status, 200, live)
        self.assertEqual(self.request(path=path)[1]['status'], 'running')
        self.assertEqual(next(row for row in self.request()[1]['items']
                              if row['id'] == path.split('/')[-1])['status'], 'running')
        revision = live['live']['revision']
        event_revision = agenda['revision']

        def advance(action, expected=200):
            nonlocal revision
            status, result = self.request('PUT', path + '/live', {'action': action, 'revision': revision})
            self.assertEqual(status, expected, result)
            if status == 200:
                revision = result['live']['revision']
            return result

        def display():
            request = Request(self.address + '/events/display/program/state',
                              headers={'Authorization': 'Bearer ' + live['display_key']})
            with urlopen(request, timeout=10) as response:
                return json.load(response)

        def create(endpoint, expected):
            nonlocal event_revision
            status, result = self.request('POST', endpoint + '/session', {'revision': event_revision})
            self.assertEqual(status, expected, result)
            if status == 200:
                event_revision += 1
            return result

        advance('open')
        self.assertEqual(display()['cursor'], 0)
        self.assertEqual(create(first, 409)['detail'], 'event_quiz_step_inactive')
        advance('complete')
        advance('open')
        self.assertIsNone(display()['quiz_display'])
        self.assertEqual(create(second, 409)['detail'], 'event_quiz_step_inactive')
        a_session = None
        for endpoint, cursor, player in [(first, 1, 'Ada'), (second, 3, 'Bora')]:
            self.assertEqual(advance('complete', 409)['detail'], 'event_quiz_not_completed')
            session = create(endpoint, 200)
            async def verify_program_display():
                url = self.address.replace('http:', 'ws:') + f"/ws/{session['pin']}/DISPLAY?instance={session['instance_id']}"
                async with connect(url, subprotocols=['quizblast-program', live['display_key']]) as screen:
                    self.assertEqual(screen.subprotocol, 'quizblast-program')
                    self.assertEqual(json.loads(await asyncio.wait_for(screen.recv(), 3))['type'], 'players')
                    # Refresh of the official projection can overlap its original connection.
                    async with connect(url, subprotocols=['quizblast-program', live['display_key']]) as refreshed:
                        self.assertEqual(json.loads(await asyncio.wait_for(refreshed.recv(), 3))['type'], 'players')
                        await asyncio.wait_for(screen.wait_closed(), 3)
                        self.assertEqual(screen.close_code, 4001)
            asyncio.run(verify_program_display())
            state = display()
            self.assertEqual(state['cursor'], cursor)
            self.assertEqual(state['quiz_display'], {key: session[key] for key in ('pin', 'instance_id')})
            self.assertNotIn('quiz_id', state['steps'][cursor])
            if a_session:
                self.assertNotEqual(session['pin'], a_session['pin'])
            self.assertEqual(self.request('POST', '/close-room/' + session['pin']),
                             (409, {'detail': 'event_quiz_not_completed'}))
            self.assertEqual(main.game_phase[session['pin']], 'lobby')
            main.game_phase[session['pin']] = 'completed'
            main.scores[session['pin']] = {player: 10}
            main.save_game(session['pin'])
            self.assertEqual(self.request(path=endpoint + '/report')[1]['ranking'],
                             [{'name': player, 'score': 10}])
            self.assertEqual(self.request('POST', '/close-room/' + session['pin'])[0], 200)
            advance('complete')
            self.assertIsNone(display()['quiz_display'])
            if cursor == 1:
                a_session = session
                advance('open')
                self.assertEqual(display()['steps'][2]['kind'], 'break')
                advance('complete')
                advance('open')
        self.assertEqual((display()['view'], display()['cursor']), ('agenda', 4))
        self.assertEqual(self.request(path=path)[1]['status'], 'completed')
        self.assertEqual(next(row for row in self.request()[1]['items']
                              if row['id'] == path.split('/')[-1])['status'], 'completed')

    def test_step_sessions_are_independent_and_report_by_room_instance(self):
        path, state = self.event()
        status, agenda = self.request('PUT', path + '/agenda', {
            'revision': state['event']['revision'],
            'steps': [{'kind': 'quiz', 'title': 'A', 'quiz_id': self.quiz_ids[0]},
                      {'kind': 'quiz', 'title': 'B', 'quiz_id': self.quiz_ids[2]}],
        })
        self.assertEqual(status, 200)
        first, second = [f"{path}/steps/{step['step_id']}" for step in agenda['steps']]
        revision = agenda['revision']
        create = lambda step, rev: self.request('POST', step + '/session', {'revision': rev})
        self.assertEqual(self.request('POST', first + '/session', {'revision': revision}, email=self.other)[0], 404)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: create(first, revision), range(2)))
        self.assertEqual(results[0], results[1])
        status, a = results[0]
        self.assertEqual(status, 200, a)
        self.assertEqual(a['quiz_id'], self.quiz_ids[0])
        self.assertEqual(create(second, revision)[0], 409)
        status, b = create(second, revision + 1)
        self.assertEqual(status, 200, b)
        self.assertEqual(b['quiz_id'], self.quiz_ids[2])
        self.assertNotEqual(a['pin'], b['pin'])
        self.assertNotEqual(a['instance_id'], b['instance_id'])
        self.assertEqual(self.request(path=path)[1]['can_delete'], False)
        self.assertEqual(self.request('DELETE', f'{path}?revision={revision + 2}')[0], 409)
        self.assertEqual(self.request('PUT', path + '/agenda', {
            'revision': revision + 2, 'steps': agenda['steps'][1:],
        }), (409, {'detail': 'event_session_locked'}))
        for step, session, name in [(first, a, 'Ada'), (second, b, 'Bora')]:
            self.assertEqual(self.request(path=step + '/report')[0], 404)
            main.game_phase[session['pin']] = 'completed'
            main.scores[session['pin']] = {name: 10}
            main.save_game(session['pin'])
            self.assertEqual(self.request(path=step + '/report', email=self.other)[0], 404)
            status, report = self.request(path=step + '/report')
            self.assertEqual(status, 200, report)
            self.assertEqual(report['ranking'], [{'name': name, 'score': 10}])
            self.assertEqual(datetime.fromisoformat(report['expires_at']) -
                             datetime.fromisoformat(report['completed_at']), timedelta(days=15))
            self.assertEqual(self.request('POST', '/start-game/' + session['pin'])[1]['detail'],
                             'event_session_completed')
        self.assertEqual(self.request(path=path + '/report')[0], 404)

        # Operator extension targets exactly one event/step's durable report.
        original_a = self.request(path=first + '/report')[1]
        original_b = self.request(path=second + '/report')[1]
        extended = datetime.fromisoformat(original_a['expires_at']) + timedelta(days=15)
        command = ['extend_event_report', state['event']['id'], extended.isoformat(),
                   '--step-id', agenda['steps'][0]['step_id']]
        with patch('sys.argv', command):
            extend_report()
        updated = self.request(path=first + '/report')[1]
        self.assertEqual(datetime.fromisoformat(updated['expires_at']), extended)
        self.assertEqual(updated['ranking'], original_a['ranking'])
        self.assertEqual(updated['completed_at'], original_a['completed_at'])
        self.assertEqual(self.request(path=second + '/report')[1], original_b)

        def reject(argv):
            with patch('sys.argv', argv), self.assertRaises(SystemExit) as failure:
                extend_report()
            self.assertEqual(failure.exception.code, 2)

        reject(command)  # Equal expiry does not extend the report.
        reject([*command[:2], original_a['expires_at'], *command[3:]])
        reject([*command[:2], '2027-01-01T12:00:00', *command[3:]])
        reject([*command[:4], str(uuid4())])
        _, other_state = self.event()
        reject([command[0], other_state['event']['id'], *command[2:]])
        self.assertEqual(self.request(path=first + '/report')[1], updated)
        self.assertEqual(self.request(path=second + '/report')[1], original_b)
        with main.db_session() as db:
            db.get(main.EventStepReport, a['instance_id']).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        reject([*command[:2], (extended + timedelta(days=1)).isoformat(), *command[3:]])
        self.assertEqual(self.request(path=first + '/report')[0], 410)
        self.assertEqual(self.request(path=second + '/report')[1], original_b)

    def test_legacy_quiz_step_identity_matches_agenda_and_new_live_snapshot(self):
        path, state = self.event()
        with main.db_session() as db:
            db.add(main.EventAgenda(event_id=state['event']['id'],
                                    steps=[{'kind': 'quiz', 'title': 'Legacy quiz'}]))
            db.commit()
        _, first = self.request(path=path + '/agenda')
        self.assertEqual(self.request(path=path + '/agenda'), (200, first))
        self.assertTrue(first['steps'][0]['step_id'])
        status, run = self.request('POST', path + '/live')
        self.assertEqual(status, 200)
        self.assertEqual(run['live']['steps'], first['steps'])
        status, saved = self.request('PUT', path + '/agenda', {
            'revision': first['revision'], 'steps': first['steps'],
        })
        self.assertEqual(status, 200)
        self.assertEqual(saved['steps'], first['steps'])

    def test_copy_event_keeps_eligible_quiz_but_creates_independent_lobby(self):
        path, state = self.event()
        _, source = self.request('POST', path + '/session', {'revision': state['event']['revision']})
        self.assertEqual(self.request('POST', path + '/copy', email=self.other)[0], 404)
        self.assertEqual(self.request('POST', path + '/copy', anonymous=True)[0], 401)
        status, clone = self.request('POST', path + '/copy')
        self.assertEqual(status, 201)
        self.assertEqual(clone['event']['title'], 'Event game (Kopya)')
        self.assertEqual(clone['quiz_id'], self.quiz_ids[0])
        self.assertIsNone(clone['session'])
        clone_path = '/events/' + clone['event']['id']
        self.assertNotEqual(clone_path, path)
        status, new_game = self.request('POST', clone_path + '/session', {'revision': clone['event']['revision']})
        self.assertEqual(status, 200)
        self.assertNotEqual(new_game['session']['pin'], source['session']['pin'])
        self.assertEqual(self.request(path=path + '/game')[1]['session'], source['session'])

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
        main.game_phase[original['pin']] = 'completed'
        main.save_game(original['pin'])
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
        main.game_phase[original['pin']] = 'completed'
        main.save_game(original['pin'])
        self.assertEqual(self.request('POST', '/close-room/' + original['pin'], {})[0], 200)
        with main.db_session() as db:
            db.delete(db.get(main.GameRoom, original['pin']))
            db.commit()
        with patch.object(main, 'generate_pin', return_value=original['pin']):
            main.create_room(self.quiz_ids[0], authorization='Bearer ' + self.tokens[self.email])
        _, state = self.request('POST', path + '/session', {'revision': 1})
        self.assertEqual(state['session']['instance_id'], original['instance_id'])
        self.assertFalse(state['session']['can_open'])
        self.assertNotEqual(main.room_instance_map[original['pin']], original['instance_id'])
        self.assertEqual(self.request('POST', '/close-room/' + original['pin'])[0], 200)

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
