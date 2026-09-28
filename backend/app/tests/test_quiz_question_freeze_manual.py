"""Question writes cannot change a quiz referenced by a recoverable room."""

import asyncio
from uuid import uuid4

from fastapi import HTTPException

import app.main as main_app
from app.tests.test_import_commit_trust_boundary_manual import build_workbook, create_upload


def expect_frozen(action):
    try:
        action()
    except HTTPException as error:
        assert error.status_code == 409, error
        assert error.detail == 'quiz_has_game_rooms', error
    else:
        raise AssertionError('Question mutation was accepted for a room quiz')


def run():
    owner = f'question-freeze-{uuid4().hex}@example.com'
    token = main_app.create_access_token({'sub': owner})
    authorization = f'Bearer {token}'
    payload = main_app.QuestionCreate(
        question='Original?', options=['A', 'B', 'C', 'D'], correct=0, time=15,
    )
    changed = main_app.QuestionCreate(
        question='Changed?', options=['D', 'C', 'B', 'A'], correct=1, time=20,
    )
    workbook = build_workbook([['Imported?', 'A', 'B', 'C', 'D', 'A', 15]])
    quiz_ids = []
    pin = None

    def import_questions(quiz_id):
        return asyncio.run(main_app.commit_quiz_import(
            quiz_id, create_upload(workbook), authorization=authorization,
        ))

    try:
        for title in ('Editable', 'Room linked'):
            with main_app.db_session() as db:
                quiz = main_app.Quiz(title=title, owner_email=owner)
                db.add(quiz)
                db.commit()
                quiz_ids.append(quiz.id)

        editable, linked = quiz_ids
        assert main_app.add_question(editable, payload, authorization=authorization)['status'] == 'question_added'
        with main_app.db_session() as db:
            editable_question = db.query(main_app.Question).filter_by(quiz_id=editable).one()
            editable_question_id = editable_question.id
        assert main_app.update_question(editable_question_id, changed, authorization=authorization)['status'] == 'question_updated'
        assert main_app.delete_question(editable_question_id, authorization=authorization)['status'] == 'question_deleted'
        assert import_questions(editable)['imported'] == 1

        assert main_app.add_question(linked, payload, authorization=authorization)['status'] == 'question_added'
        with main_app.db_session() as db:
            question_id = db.query(main_app.Question).filter_by(quiz_id=linked).one().id
        pin = main_app.create_room(linked, authorization=authorization)['room_pin']

        for phase in ('lobby', 'question', 'result', 'completed'):
            with main_app.db_session() as db:
                db.get(main_app.GameRoom, pin).phase = phase
                db.commit()
            expect_frozen(lambda: main_app.add_question(linked, changed, authorization=authorization))
            expect_frozen(lambda: main_app.update_question(question_id, changed, authorization=authorization))
            expect_frozen(lambda: main_app.delete_question(question_id, authorization=authorization))
            expect_frozen(lambda: import_questions(linked))
            with main_app.db_session() as db:
                questions = db.query(main_app.Question).filter_by(quiz_id=linked).all()
                assert len(questions) == 1 and questions[0].question == 'Original?'
                assert db.query(main_app.ImportHistory).filter_by(quiz_id=linked).count() == 0
    finally:
        with main_app.db_session() as db:
            if pin:
                room = db.get(main_app.GameRoom, pin)
                if room: db.delete(room)
            for quiz_id in quiz_ids:
                quiz = db.get(main_app.Quiz, quiz_id)
                if quiz: db.delete(quiz)
            db.query(main_app.ImportHistory).filter_by(owner_email=owner).delete(synchronize_session=False)
            db.commit()
        if pin:
            for state in (main_app.rooms, main_app.scores, main_app.current_question_index,
                          main_app.answered_players, main_app.room_quiz_map,
                          main_app.room_host_map, main_app.answer_stats_map,
                          main_app.waiting_next_question, main_app.question_start_time,
                          main_app.game_phase, main_app.remaining_seconds,
                          main_app.question_deadline):
                state.pop(pin, None)


if __name__ == '__main__':
    run()
    print('PASS — room questions frozen; unlinked quiz edits and import work.')
