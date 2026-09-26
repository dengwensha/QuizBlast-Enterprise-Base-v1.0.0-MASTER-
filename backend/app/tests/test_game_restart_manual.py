"""Real HTTP/WebSocket restart test, run inside the backend container."""

import asyncio
import json
import secrets
import signal
import subprocess
import sys
import uuid
from urllib.error import URLError
from urllib.request import Request, urlopen

from websockets.asyncio.client import connect


BASE = 'http://127.0.0.1:8002'
WS = 'ws://127.0.0.1:8002'


def post(path, data=None, token=None):
    request = Request(BASE + path, data=json.dumps(data or {}).encode(), method='POST',
                      headers={'Content-Type': 'application/json',
                               **({'Authorization': f'Bearer {token}'} if token else {})})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def start_backend():
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                '--host', '127.0.0.1', '--port', '8002'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return process


async def ready(process):
    for _ in range(60):
        if process.poll() is not None:
            raise AssertionError('backend_exited_before_ready: ' +
                                 process.stderr.read().decode()[-1200:])
        try:
            with await asyncio.to_thread(urlopen, BASE + '/', timeout=1):
                return
        except (URLError, OSError):
            await asyncio.sleep(0.1)
    raise AssertionError('backend_not_ready')


async def event_of(socket, kind):
    for _ in range(15):
        event = json.loads(await asyncio.wait_for(socket.recv(), timeout=20))
        if event.get('type') == kind:
            return event
    raise AssertionError(f'{kind}_not_received')


async def run():
    process = start_backend()
    sockets = []
    try:
        await ready(process)
        email = f'restart-{uuid.uuid4().hex}@example.com'
        await asyncio.to_thread(post, '/auth/register',
                                {'email': email, 'password': 'integration-password'})
        login = await asyncio.to_thread(post, '/auth/login',
                                        {'email': email, 'password': 'integration-password'})
        token = login['access_token']
        quiz = await asyncio.to_thread(post, '/quizzes', {'title': 'Restart'}, token)
        await asyncio.to_thread(post, f"/quizzes/{quiz['id']}/questions",
                                {'question': 'Continue?', 'options': ['Yes', 'No', 'A', 'B'],
                                 'correct': 0, 'time': 12}, token)
        room = await asyncio.to_thread(post, f"/create-room/{quiz['id']}", None, token)
        pin = room['room_pin']
        host = await connect(f'{WS}/ws/{pin}/HOST', subprotocols=['quizblast-host', token])
        ada = await connect(f'{WS}/ws/{pin}/Ada')
        bora_token = secrets.token_hex(32)
        bora = await connect(f'{WS}/ws/{pin}/Bora',
                             subprotocols=['quizblast-player', bora_token])
        sockets.extend([host, ada, bora])
        ada_token = (await event_of(ada, 'player_session'))['token']
        await asyncio.to_thread(post, f'/start-game/{pin}', None, token)
        for socket in sockets:
            await event_of(socket, 'question')
        await ada.send(json.dumps({'type': 'answer', 'answer': 0}))
        board = await event_of(ada, 'leaderboard')
        score = dict(board['scores'])['Ada']
        assert score > 0

        await host.close()
        paused = await event_of(ada, 'game_paused')
        assert 7 < paused['remaining'] <= 12
        await asyncio.sleep(1)
        host = await connect(f'{WS}/ws/{pin}/HOST',
                             subprotocols=['quizblast-host', token])
        sockets.append(host)
        resumed = await event_of(ada, 'question')
        assert abs(resumed['time'] - paused['remaining']) < 1

        process.kill()
        await asyncio.to_thread(process.wait, 5)
        process = start_backend()
        await ready(process)
        unauthorized = await connect(f'{WS}/ws/{pin}/Ada')
        sockets.append(unauthorized)
        denied = await event_of(unauthorized, 'join_error')
        assert denied['reason'] == 'player_unauthorized'
        ada2 = await connect(f'{WS}/ws/{pin}/Ada',
                             subprotocols=['quizblast-player', ada_token])
        bora2 = await connect(f'{WS}/ws/{pin}/Bora',
                              subprotocols=['quizblast-player', bora_token])
        sockets.extend([ada2, bora2])
        for socket, answered in [(ada2, True), (bora2, False)]:
            state = await event_of(socket, 'question')
            assert 7 < state['time'] <= 12 and state['paused'] is True
            assert state['answered'] is answered
            board = await event_of(socket, 'leaderboard')
            assert dict(board['scores'])['Ada'] == score
        await asyncio.sleep(2)
        host2 = await connect(f'{WS}/ws/{pin}/HOST',
                              subprotocols=['quizblast-host', token])
        sockets.append(host2)
        for socket in (ada2, bora2, host2):
            state = await event_of(socket, 'question')
            assert 7 < state['time'] <= 12 and state['paused'] is False, state
        await bora2.send(json.dumps({'type': 'answer', 'answer': 0}))
        for socket in (ada2, bora2, host2):
            result = await event_of(socket, 'question_result')
            assert result['stats'] == [2, 0, 0, 0], result

        process.kill()
        await asyncio.to_thread(process.wait, 5)
        process = start_backend()
        await ready(process)
        host3 = await connect(f'{WS}/ws/{pin}/HOST',
                              subprotocols=['quizblast-host', token])
        ada3 = await connect(f'{WS}/ws/{pin}/Ada',
                             subprotocols=['quizblast-player', ada_token])
        sockets.extend([host3, ada3])
        for socket in (host3, ada3):
            restored = await event_of(socket, 'question_result')
            assert restored['stats'] == [2, 0, 0, 0]
        finish = await asyncio.to_thread(post, f'/next-question/{pin}', None, token)
        assert finish['status'] == 'game_over'
    finally:
        for socket in sockets:
            try:
                await socket.close()
            except Exception:
                pass
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            await asyncio.to_thread(process.wait, 5)


if __name__ == '__main__':
    asyncio.run(run())
    print('Restarted game preserved identity, score, answers and paused time.')
