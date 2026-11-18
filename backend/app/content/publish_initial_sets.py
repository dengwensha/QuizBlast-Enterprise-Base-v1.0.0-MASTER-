"""One-shot curated content publisher. Defaults to validation only.

Usage:
  python -m app.content.publish_initial_sets
  python -m app.content.publish_initial_sets --publish
"""
import argparse

from app.services.content_seed import (
    load_initial_sets, validate_initial_sets, publish_initial_sets,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Write all validated sets to DB")
    args = parser.parse_args()
    data = load_initial_sets()
    summary = validate_initial_sets(data)
    if not args.publish:
        print(f"DRY RUN PASS — {summary['set_count']} sets, {summary['question_count']} questions. No database writes.")
        return

    from app.main import db_session, Quiz, Question, PublishedQuizSet
    with db_session() as db:
        summary = publish_initial_sets(db, data, Quiz, Question, PublishedQuizSet)
        db.commit()
    print(f"PUBLISHED — {summary['set_count']} sets, {summary['question_count']} questions.")


if __name__ == "__main__":
    main()
