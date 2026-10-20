"""CONTENT-01D.4: visual inventory and publication-blocking regression."""
from copy import deepcopy

from app.services.content_visual_review import (
    load_visual_review, validate_visual_review, require_all_visuals_approved,
)


def rejects(fn, value):
    try:
        fn(value)
    except ValueError:
        return
    raise AssertionError("Invalid visual review state accepted")


def run():
    data = load_visual_review()
    assert validate_visual_review(data) == {"total": 7, "approved": 0, "pending": 7}
    rejects(require_all_visuals_approved, data)

    invalid = deepcopy(data)
    invalid["assets"][0]["status"] = "approved"
    rejects(validate_visual_review, invalid)

    invalid = deepcopy(data)
    invalid["assets"][0]["image_url"] = "http://example.org/unsafe.png"
    rejects(validate_visual_review, invalid)

    invalid = deepcopy(data)
    invalid["assets"][0]["question_number"] = 99
    rejects(validate_visual_review, invalid)

    invalid = deepcopy(data)
    invalid["assets"][1]["question_number"] = invalid["assets"][0]["question_number"]
    invalid["assets"][1]["set_slug"] = invalid["assets"][0]["set_slug"]
    rejects(validate_visual_review, invalid)

    invalid = deepcopy(data)
    invalid["assets"].pop()
    rejects(validate_visual_review, invalid)


if __name__ == "__main__":
    run()
    print("PASS — seven visual candidates inventoried; unapproved publication blocked")
