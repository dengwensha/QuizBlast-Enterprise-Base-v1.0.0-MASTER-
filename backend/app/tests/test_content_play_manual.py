"""QB-CONTENT-01D: published-only direct play with host isolation."""
from uuid import uuid4

from fastapi import HTTPException

import app.main as app


def expect_error(action, status):
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == status, exc
    else:
        raise AssertionError(f"Expected HTTP {status}")


def run():
    tag = uuid4().hex
    owner = f"host-{tag}@example.com"
    outsider = f"other-{tag}@example.com"
    auth = f"Bearer {app.create_access_token({'sub': owner})}"
    other_auth = f"Bearer {app.create_access_token({'sub': outsider})}"
    quiz_ids = {}
    pins = []
    try:
        with app.db_session() as db:
            for kind in ("published", "draft", "private", "owned"):
                quiz = app.Quiz(
                    title=f"{kind}-{tag}",
                    owner_email=(outsider if kind == "private" else
                                 owner if kind == "owned" else None),
                )
                quiz.questions.append(app.Question(
                    question="Original?", option1="A", option2="B",
                    option3="C", option4="D", correct=1, time=15,
                ))
                db.add(quiz)
                db.flush()
                quiz_ids[kind] = quiz.id
                if kind != "owned":
                    db.add(app.PublishedQuizSet(
                        quiz_id=quiz.id, slug=f"{kind}-{tag}",
                        topic="Genel", audience="Genel",
                        difficulty="Kolay", is_published=(kind != "draft"),
                    ))
            db.commit()

        published = quiz_ids["published"]
        count_before = None
        with app.db_session() as db:
            count_before = db.query(app.Quiz).count()

        expect_error(lambda: app.create_room(published, authorization=None), 401)
        expect_error(lambda: app.create_room(quiz_ids["draft"], authorization=auth), 404)
        expect_error(lambda: app.create_room(quiz_ids["private"], authorization=auth), 404)
        expect_error(lambda: app.create_room(quiz_ids["owned"], authorization=other_auth), 404)

        for quiz_id in (published, quiz_ids["owned"]):
            result = app.create_room(quiz_id, authorization=auth)
            pin = result["room_pin"]
            pins.append(pin)
            assert result["quiz_id"] == quiz_id
            assert app.room_host_map[pin] == owner
            assert app.get_room_questions(pin)[0]["question"] == "Original?"
            app.require_room_host(pin, owner, app.rooms, app.room_host_map)
            expect_error(
                lambda: app.require_room_host(pin, outsider, app.rooms, app.room_host_map),
                403,
            )
            with app.db_session() as db:
                assert db.get(app.GameRoom, pin).host_email == owner

        with app.db_session() as db:
            assert db.query(app.Quiz).count() == count_before
            original = db.get(app.Quiz, published)
            assert original.owner_email is None
            assert len(original.questions) == 1
            assert original.questions[0].correct == 1

        # A published source cannot be edited by a host without ownership.
        new_question = app.QuestionCreate(
            question="Modified?", options=["1", "2", "3", "4"], correct=0,
        )
        assert app.add_question(published, new_question, authorization=auth)["error"] == "quiz_not_found"
    finally:
        with app.db_session() as db:
            for pin in pins:
                room = db.get(app.GameRoom, pin)
                if room is not None:
                    db.delete(room)
            db.flush()
            for quiz_id in quiz_ids.values():
                db.query(app.PublishedQuizSet).filter_by(quiz_id=quiz_id).delete()
                quiz = db.get(app.Quiz, quiz_id)
                if quiz is not None:
                    db.delete(quiz)
            db.commit()
        for pin in pins:
            for state in (
                app.rooms, app.room_instance_map, app.scores,
                app.current_question_index, app.answered_players,
                app.room_quiz_map, app.room_host_map, app.answer_stats_map,
                app.waiting_next_question, app.question_start_time, app.game_phase,
                app.remaining_seconds, app.question_deadline,
            ):
                state.pop(pin, None)


if __name__ == "__main__":
    run()
    print("PASS — direct published play, host authorization, no source mutation")
