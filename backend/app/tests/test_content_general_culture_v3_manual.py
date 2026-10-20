"""CONTENT-01D.2: positive, negative and V2-immutability checks."""
from copy import deepcopy

from app.services.content_expansion_v2 import validate_expansion, load_expansion
from app.services.content_general_culture_v3 import (
    load_general_culture_v3, validate_general_culture_v3,
)


def expect_invalid(data):
    try:
        validate_general_culture_v3(data)
    except ValueError:
        return
    raise AssertionError("Invalid General Culture V3 draft accepted")


def run():
    source = validate_expansion(load_expansion())
    unchanged = deepcopy(source)
    draft = load_general_culture_v3()
    result = validate_general_culture_v3(draft, source_sets=source)
    assert source == unchanged, "V2 source mutated"
    v2_general = next(s for s in source if s["slug"] == draft["base_slug"])
    assert result["questions"][:10] == v2_general["questions"]
    assert len(result["questions"]) == 15
    assert result["publication_status"] == "draft_only"
    assert sum(q.get("visual_candidate", False) for q in result["questions"]) == 3

    broken = deepcopy(draft)
    broken["questions"][0]["correct"] = 8
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["explanation"] = ""
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["options"][1] = broken["questions"][0]["options"][0]
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["image_url"] = "https://example.invalid/unreviewed.jpg"
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["visual_candidate"] = False
    expect_invalid(broken)


if __name__ == "__main__":
    run()
    print("PASS — General Culture V3 15 questions; V2 unchanged; 3 visual candidates")
