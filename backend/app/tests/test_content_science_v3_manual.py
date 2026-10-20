"""CONTENT-01D.3: science V3 positive and negative tests; V2 must not change."""
from copy import deepcopy

from app.services.content_expansion_v2 import load_expansion, validate_expansion
from app.services.content_science_v3 import load_science_v3, validate_science_v3


def expect_invalid(data):
    try:
        validate_science_v3(data)
    except ValueError:
        return
    raise AssertionError("Invalid science V3 draft accepted")


def run():
    source = validate_expansion(load_expansion())
    unchanged = deepcopy(source)
    draft = load_science_v3()
    result = validate_science_v3(draft, source_sets=source)
    assert source == unchanged, "V2 source mutated"
    base = next(item for item in source if item["slug"] == draft["base_slug"])
    assert result["questions"][:10] == base["questions"]
    assert len(result["questions"]) == 15
    assert result["publication_status"] == "draft_only"
    assert sum(q.get("visual_candidate", False) for q in result["questions"]) == 4

    broken = deepcopy(draft)
    broken["questions"][0]["correct"] = 5
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["explanation"] = ""
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["options"][1] = broken["questions"][0]["options"][0]
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["image_url"] = "https://example.invalid/unreviewed.png"
    expect_invalid(broken)
    broken = deepcopy(draft)
    broken["questions"][0]["visual_brief"] = ""
    expect_invalid(broken)


if __name__ == "__main__":
    run()
    print("PASS — science V3 15 questions; V2 unchanged; 4 image candidates")
