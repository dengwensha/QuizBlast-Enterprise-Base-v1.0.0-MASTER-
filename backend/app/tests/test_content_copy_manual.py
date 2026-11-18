"""Content-01C: independent copy, access denial and atomic rollback."""
from unittest.mock import patch
from uuid import uuid4
from fastapi import HTTPException
import app.main as app


def run():
    suffix = uuid4().hex
    user = f"copy-{suffix}@example.com"
    authorization = f"Bearer {app.create_access_token({'sub': user})}"
    ids = []
    copied_ids = []
    try:
        with app.db_session() as db:
            for kind in ("published", "draft", "private", "empty"):
                original = app.Quiz(
                    title=f"{kind}-{suffix}",
                    owner_email=f"other-{suffix}@example.com" if kind == "private" else None,
                )
                db.add(original)
                db.flush()
                catalog = app.PublishedQuizSet(
                    quiz_id=original.id,
                    slug=f"{kind}-{suffix}",
                    topic="Bilim",
                    audience="Genel",
                    difficulty="Kolay",
                    version=1,
                    is_published=(kind != "draft"),
                )
                db.add(catalog)
                db.flush()
                if kind != "empty":
                    db.add(app.Question(
                        quiz_id=original.id,
                        question="What is the answer?",
                        image_url="https://example.com/image.png",
                        explanation="Optional explanation",
                        option1="First", option2="Second",
                        option3="Third", option4="Fourth",
                        correct=2, time=25,
                    ))
                ids.append((catalog.id, original.id))
            db.commit()

        published, draft, private, empty = [entry[0] for entry in ids]
        result = app.copy_content_set(published, authorization=authorization)
        copied_ids.append(result["id"])
        assert result["question_count"] == 1
        with app.db_session() as db:
            source = db.query(app.Question).filter_by(quiz_id=ids[0][1]).one()
            replica = db.query(app.Question).filter_by(quiz_id=result["id"]).one()
            owned = db.get(app.Quiz, result["id"])
            assert owned.owner_email == user
            assert replica.id != source.id and replica.quiz_id != source.quiz_id
            for field in ("question", "image_url", "explanation",
                          "option1", "option2", "option3", "option4", "correct", "time"):
                assert getattr(replica, field) == getattr(source, field)
        changed = app.QuestionCreate(question="Edited", options=["W", "X", "Y", "Z"], correct=0)
        assert app.update_question(replica.id, changed, authorization=authorization)["status"] == "question_updated"
        with app.db_session() as db:
            assert db.get(app.Question, source.id).question == "What is the answer?"

        for forbidden, expected in ((draft, 404), (private, 404), (empty, 409)):
            try:
                app.copy_content_set(forbidden, authorization=authorization)
            except HTTPException as exc:
                assert exc.status_code == expected
            else:
                raise AssertionError("Invalid set copied")

        with app.db_session() as db:
            before = db.query(app.Quiz).filter_by(owner_email=user).count()
        with patch("app.services.content_copy.clone_question", side_effect=RuntimeError("forced failure")):
            try:
                app.copy_content_set(published, authorization=authorization)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Expected rollback failure")
        with app.db_session() as db:
            assert db.query(app.Quiz).filter_by(owner_email=user).count() == before
    finally:
        with app.db_session() as db:
            for _, original_id in ids:
                db.query(app.PublishedQuizSet).filter_by(quiz_id=original_id).delete()
            for quiz_id in copied_ids + [original_id for _, original_id in ids]:
                quiz = db.get(app.Quiz, quiz_id)
                if quiz is not None:
                    db.delete(quiz)
            db.commit()


if __name__ == "__main__":
    run()
    print("PASS — independent copy, access boundaries, atomic rollback")
