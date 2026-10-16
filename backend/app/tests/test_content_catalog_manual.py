"""QB-CONTENT-01B: catalog remains published-only and answer-safe."""
from uuid import uuid4
from fastapi import HTTPException
import app.main as app


def run():
    marker = uuid4().hex
    ids = []
    try:
        with app.db_session() as db:
            for slug, owner, published in (
                (f"qb-published-{marker}", None, True),
                (f"qb-draft-{marker}", None, False),
                (f"qb-private-{marker}", f"owner-{marker}@example.com", True),
            ):
                quiz = app.Quiz(title=slug, owner_email=owner)
                db.add(quiz)
                db.flush()
                record = app.PublishedQuizSet(
                    quiz_id=quiz.id, slug=slug, topic="Bilim",
                    audience="Genel", difficulty="Kolay",
                    description="Safe preview", is_published=published,
                    version=1,
                )
                db.add(record)
                db.flush()
                db.add(app.Question(
                    quiz_id=quiz.id, question="Secret test?",
                    option1="A", option2="B", option3="C", option4="D",
                    correct=2, explanation="Hidden reason", time=15,
                ))
                ids.append((record.id, quiz.id))
            db.commit()

        published_id, draft_id, private_id = [x[0] for x in ids]
        listed = app.list_published_content_sets()
        visible = {item["id"] for item in listed}
        assert published_id in visible
        assert draft_id not in visible
        assert private_id not in visible

        details = app.get_published_content_set(published_id)
        assert details["question_count"] == 1
        assert details["play_quiz_id"] == ids[0][1]
        assert details["estimated_duration_seconds"] == 15

        preview = app.preview_published_content_set(published_id)
        assert len(preview["questions"]) == 1
        question = preview["questions"][0]
        assert question["options"] == ["A", "B", "C", "D"]
        assert "correct" not in question and "explanation" not in question
        assert "quiz_id" not in preview

        for blocked in (draft_id, private_id):
            for action in (app.get_published_content_set,
                           app.preview_published_content_set):
                try:
                    action(blocked)
                except HTTPException as exc:
                    assert exc.status_code == 404
                else:
                    raise AssertionError("Non-public catalog set accessible")
    finally:
        with app.db_session() as db:
            for _, quiz_id in ids:
                record = db.query(app.PublishedQuizSet).filter_by(quiz_id=quiz_id).first()
                if record:
                    db.delete(record)
            db.flush()
            for _, quiz_id in ids:
                quiz = db.get(app.Quiz, quiz_id)
                if quiz:
                    db.delete(quiz)
            db.commit()


if __name__ == "__main__":
    run()
    print("PASS — published catalog only; no answers leaked")
