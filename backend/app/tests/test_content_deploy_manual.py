"""QB-CONTENT-DEPLOY-01 opt-in publishing regression."""
import app.main as app
from app.services.content_deploy import publish_if_requested
from app.services.content_seed import load_initial_sets


def run():
    data = load_initial_sets()
    slugs = [item["slug"] for item in data["sets"]]
    with app.db_session() as db:
        before = db.query(app.PublishedQuizSet).count()
        assert publish_if_requested(db, app.Quiz, app.Question,
                                    app.PublishedQuizSet, flag="") == "disabled"
        assert publish_if_requested(db, app.Quiz, app.Question,
                                    app.PublishedQuizSet, flag="unexpected") == "disabled"
        assert db.query(app.PublishedQuizSet).count() == before
        assert not db.query(app.PublishedQuizSet).filter(
            app.PublishedQuizSet.slug.in_(slugs)
        ).first()

        assert publish_if_requested(db, app.Quiz, app.Question,
                                    app.PublishedQuizSet, flag="publish-v1") == "published"
        assert publish_if_requested(db, app.Quiz, app.Question,
                                    app.PublishedQuizSet, flag="publish-v1") == "already_published"
        rows = db.query(app.PublishedQuizSet).filter(
            app.PublishedQuizSet.slug.in_(slugs)
        ).all()
        assert len(rows) == 4
        assert sum(len(db.get(app.Quiz, row.quiz_id).questions) for row in rows) == 24

        rows[0].is_published = False
        db.flush()
        try:
            publish_if_requested(db, app.Quiz, app.Question,
                                 app.PublishedQuizSet, flag="publish-v1")
        except RuntimeError as exc:
            assert str(exc) == "initial_catalog_differs_requires_manual_review"
        else:
            raise AssertionError("inconsistent existing set accepted")
        db.rollback()

    with app.db_session() as db:
        assert db.query(app.PublishedQuizSet).count() == before
        assert not db.query(app.PublishedQuizSet).filter(
            app.PublishedQuizSet.slug.in_(slugs)
        ).first()


if __name__ == "__main__":
    run()
    print("PASS — opt-in publication, idempotence, fail-closed and rollback")
