"""End-to-end game flow against a running backend on localhost:8000."""

import asyncio
import json
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from websockets.asyncio.client import connect


BASE_URL = 'http://localhost:8000'
WS_URL = 'ws://localhost:8000'


def post(path, payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = Request(
        BASE_URL + path,
        data=json.dumps(payload or {}).encode(),
        headers=headers,
        method='POST',
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


async def receive_until(socket, event_type):
    observed = []
    while True:
        event = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
        observed.append(event)
        if event.get('type') == event_type:
            return event, observed


async def run_game_flow():
    email = f'game-flow-{uuid.uuid4().hex}@example.com'
    status, registration = await asyncio.to_thread(
        post, '/auth/register', {'email': email, 'password': 'integration-password'}
    )
    assert status == 200 and registration['status'] == 'registered'
    status, login = await asyncio.to_thread(
        post, '/auth/login', {'email': email, 'password': 'integration-password'}
    )
    assert status == 200 and login['access_token']
    token = login['access_token']

    status, quiz = await asyncio.to_thread(post, '/quizzes', {'title': 'Game flow'}, token)
    assert status == 200 and quiz['id']
    quiz_id = quiz['id']
    status, added = await asyncio.to_thread(
        post,
        f'/quizzes/{quiz_id}/questions',
        {'question': 'Two plus two?', 'options': ['4', '3', '2', '1'], 'correct': 0, 'time': 1},
        token,
    )
    assert status == 200 and added['status'] == 'question_added'
    status, room = await asyncio.to_thread(post, f'/create-room/{quiz_id}', None, token)
    assert status == 200 and room['room_pin']
    pin = room['room_pin']

    async with connect(f'{WS_URL}/ws/{pin}/HOST') as host:
        async with connect(f'{WS_URL}/ws/{pin}/Ada') as player:
            async with connect(f'{WS_URL}/ws/{pin}/DISPLAY') as display:
                status, started = await asyncio.to_thread(post, f'/start-game/{pin}', None, token)
                assert status == 200 and started['status'] == 'started'

                for socket in (host, player, display):
                    question, events = await receive_until(socket, 'question')
                    assert question['question'] == 'Two plus two?'
                    assert any(
                        event.get('type') == 'players'
                        and set(event['players']) == {'HOST', 'Ada', 'DISPLAY'}
                        for event in events
                    )

                status, rejected = await asyncio.to_thread(
                    post, f'/next-question/{pin}', None, token
                )
                assert status == 409 and rejected['detail'] == 'question_result_not_ready'

                await player.send(json.dumps({'type': 'answer', 'answer': 0}))
                for socket in (host, player, display):
                    result, events = await receive_until(socket, 'question_result')
                    assert result['correct'] == 0 and result['stats'] == [1, 0, 0, 0]
                    assert any(
                        event.get('type') == 'answer_count' and event['count'] == 1
                        for event in events
                    )

                status, advanced = await asyncio.to_thread(
                    post, f'/next-question/{pin}', None, token
                )
                assert status == 200 and advanced['status'] == 'game_over'
                for socket in (host, player, display):
                    await receive_until(socket, 'game_over')

                status, rejected = await asyncio.to_thread(
                    post, f'/next-question/{pin}', None, token
                )
                assert status == 409 and rejected['detail'] == 'question_result_not_ready'


if __name__ == '__main__':
    asyncio.run(run_game_flow())
    print('Host/player/display game flow passed.')
