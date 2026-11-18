"""Opt-in, fail-closed, idempotent first-collection publisher.

No default startup writes. Only QB_PUBLISH_INITIAL_CONTENT=publish-v1 enables it.
"""
import os

from app.services.content_seed import (
    load_initial_sets, validate_initial_sets, publish_initial_sets,
)


def publish_if_requested(db, Quiz, Question, PublishedQuizSet, *, flag=None):
    flag = os.environ.get("QB_PUBLISH_INITIAL_CONTENT", "") if flag is None else flag
    if flag != "publish-v1":
        return "disabled"

    data = load_initial_sets()
    expected = validate_initial_sets(data)
    slugs = [item["slug"] for item in data["sets"]]
    # Check all catalog rows, including unpublished drafts; never overwrite.
    existing = db.query(PublishedQuizSet).filter(
        PublishedQuizSet.slug.in_(slugs)
    ).all()
    if existing:
        if len(existing) != len(slugs):
            raise RuntimeError("partial_initial_catalog_requires_manual_review")
        for record in existing:
            quiz = db.get(Quiz, record.quiz_id)
            if (not record.is_published or quiz is None or
                    quiz.owner_email is not None or
                    len(quiz.questions) != 6 or record.version != 1):
                raise RuntimeError("initial_catalog_differs_requires_manual_review")
        return "already_published"

    summary = publish_initial_sets(
        db, data, Quiz, Question, PublishedQuizSet
    )
    if summary != expected:
        raise RuntimeError("unexpected_initial_catalog_summary")
    # Caller owns the transaction and must commit.
    return "published"
