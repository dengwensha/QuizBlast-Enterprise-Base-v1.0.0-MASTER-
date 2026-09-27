"""A quiz in a recoverable room cannot be deleted through the API handler."""

from uuid import uuid4

from fastapi import HTTPException

import app.main as main_app


def run():
    owner = f"room-deletion-{uuid4().hex}@example.com"
    token = main_app.create_access_token({'sub': owner})
    quiz_ids = []
    pin = None

    try:
        with main_app.db_session() as db:
            for title in ('Unassigned quiz', 'Room quiz'):
                quiz = main_app.Quiz(title=title, owner_email=owner)
                quiz.questions.append(main_app.Question(
                    question='Still available?', option1='Yes', option2='No',
                    option3='Maybe', option4='Later', correct=0, time=15,
                ))
                db.add(quiz)
                db.commit()
                quiz_ids.append(quiz.id)

        unassigned, linked = quiz_ids
        assert main_app.delete_quiz(unassigned, authorization=f'Bearer {token}') == {
            'status': 'quiz_deleted'
        }
        pin = main_app.create_room(linked, authorization=f'Bearer {token}')['room_pin']

        for phase in ('lobby', 'question', 'result', 'completed'):
            with main_app.db_session() as db:
                room = db.get(main_app.GameRoom, pin)
                room.phase = phase
                db.commit()
            try:
                main_app.delete_quiz(linked, authorization=f'Bearer {token}')
            except HTTPException as error:
                assert error.status_code == 409
                assert error.detail == 'quiz_has_game_rooms'
            else:
                raise AssertionError(f'Deletion succeeded in {phase} phase')

            with main_app.db_session() as db:
                assert db.get(main_app.Quiz, linked) is not None
                assert db.query(main_app.Question).filter_by(quiz_id=linked).count() == 1
                assert db.get(main_app.GameRoom, pin) is not None
    finally:
        with main_app.db_session() as db:
            if pin is not None:
                room = db.get(main_app.GameRoom, pin)
                if room is not None:
                    db.delete(room)
            for quiz_id in quiz_ids:
                quiz = db.get(main_app.Quiz, quiz_id)
                if quiz is not None:
                    db.delete(quiz)
            db.commit()
        if pin is not None:
            for state in (main_app.rooms, main_app.scores, main_app.current_question_index,
                          main_app.answered_players, main_app.room_quiz_map,
                          main_app.room_host_map, main_app.answer_stats_map,
                          main_app.waiting_next_question, main_app.question_start_time,
                          main_app.game_phase, main_app.remaining_seconds,
                          main_app.question_deadline):
                state.pop(pin, None)


if __name__ == '__main__':
    run()
    print('PASS — linked quizzes are protected; unassigned quiz deletion works.')
