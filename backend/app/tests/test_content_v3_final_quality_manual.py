"""CONTENT-01D.5 — read-only cross-set release-candidate quality gate.

This verifies structural/editorial completeness, not historical fact accuracy,
image rights, visual rendering or successful publication.
"""
from collections import Counter
from copy import deepcopy

from app.services.content_general_culture_v3 import (
    load_general_culture_v3, validate_general_culture_v3,
)
from app.services.content_science_v3 import load_science_v3, validate_science_v3
from app.services.content_visual_review import load_visual_review, validate_visual_review


def run():
    general_draft = load_general_culture_v3()
    science_draft = load_science_v3()
    originals = deepcopy((general_draft, science_draft))
    sets = [
        validate_general_culture_v3(general_draft),
        validate_science_v3(science_draft),
    ]
    assert (general_draft, science_draft) == originals, "Source drafts mutated"
    assert len(sets) == 2
    assert [len(item["questions"]) for item in sets] == [15, 15]
    assert len({item["slug"] for item in sets}) == 2
    all_questions = [q for item in sets for q in item["questions"]]
    assert len(all_questions) == 30
    normalized = [q["question"].strip().casefold() for q in all_questions]
    assert len(set(normalized)) == 30, "Duplicate question text between collections"

    for item in sets:
        questions = item["questions"]
        assert all(
            isinstance(q["explanation"], str) and q["explanation"].strip()
            and isinstance(q["question"], str) and q["question"].strip()
            and len(q["options"]) == 4
            and len({option.strip().casefold() for option in q["options"]}) == 4
            and type(q["correct"]) is int and q["correct"] in range(4)
            and type(q["time"]) is int and 5 <= q["time"] <= 120
            for q in questions
        )
        positions = Counter(q["correct"] for q in questions)
        assert set(positions) == {0, 1, 2, 3}
        assert max(positions.values()) - min(positions.values()) <= 1
        assert all(not q.get("image_url") for q in questions), "Unapproved image URL in draft"

    assert Counter(q["difficulty"] for q in general_draft["questions"]) == {
        "Orta": 3, "Zor": 2
    }
    assert Counter(q["difficulty"] for q in science_draft["questions"]) == {
        "Orta": 3, "Zor": 2
    }
    assert sum(q.get("visual_candidate") is True for q in general_draft["questions"]) == 3
    assert sum(q.get("visual_candidate") is True for q in science_draft["questions"]) == 4
    assert validate_visual_review(load_visual_review()) == {
        "total": 7, "approved": 0, "pending": 7
    }


if __name__ == "__main__":
    run()
    print("PASS — 2 V3 drafts / 30 questions; explanations, structure, answers and visual holds")
