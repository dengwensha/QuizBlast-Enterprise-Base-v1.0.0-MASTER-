"""QB-CONTENT-01F: strict content validation and safe publication rollback."""
from copy import deepcopy

import app.main as app
from app.services.content_seed import (
    load_initial_sets, validate_initial_sets, publish_initial_sets,
)


def expect_rejected(content):
    try:
        validate_initial_sets(content)
    except ValueError:
        return
    raise AssertionError("Invalid content accepted")


def run():
    data = load_initial_sets()
    assert validate_initial_sets(data) == {"set_count": 4, "question_count": 24}
    assert [len(s["questions"]) for s in data["sets"]] == [6] * 4

    invalid = deepcopy(data)
    for item in invalid["sets"][0]["questions"]:
        item["correct"] = 0
    expect_rejected(invalid)

    invalid = deepcopy(data)
    invalid["sets"][0]["questions"][0]["correct"] = 9
    expect_rejected(invalid)
    invalid = deepcopy(data)
    invalid["sets"][0]["questions"][0]["options"][1] = invalid["sets"][0]["questions"][0]["options"][0]
    expect_rejected(invalid)
    invalid = deepcopy(data)
    invalid["sets"][0]["questions"][0]["time"] = 0
    expect_rejected(invalid)
    invalid = deepcopy(data)
    invalid["sets"][0]["questions"][1]["question"] = invalid["sets"][0]["questions"][0]["question"]
    expect_rejected(invalid)

    # One transaction rolls back all four sets, without altering existing catalog.
    with app.db_session() as db:
        prior = db.query(app.PublishedQuizSet).count()
        summary = publish_initial_sets(db, data, app.Quiz, app.Question, app.PublishedQuizSet)
        assert summary["question_count"] == 24
        staged = db.query(app.PublishedQuizSet).filter(
            app.PublishedQuizSet.slug.in_([s["slug"] for s in data["sets"]])
        ).all()
        assert len(staged) == 4
        assert all(row.is_published for row in staged)
        for record in staged:
            quiz = db.get(app.Quiz, record.quiz_id)
            assert quiz.owner_email is None
            assert len(quiz.questions) == 6
        try:
            publish_initial_sets(db, data, app.Quiz, app.Question, app.PublishedQuizSet)
        except ValueError as exc:
            assert str(exc) == "set_slug_already_exists"
        else:
            raise AssertionError("Existing content overwritten")
        db.rollback()

    with app.db_session() as db:
        assert db.query(app.PublishedQuizSet).count() == prior
        for item in data["sets"]:
            assert db.query(app.PublishedQuizSet).filter_by(slug=item["slug"]).first() is None


if __name__ == "__main__":
    run()
    print("PASS — four sets validated; publication staging and rollback safe")
