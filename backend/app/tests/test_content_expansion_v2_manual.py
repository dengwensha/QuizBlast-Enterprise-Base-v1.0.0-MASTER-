"""CONTENT-01C: V2 expansion is validated, but never published by this test."""
from copy import deepcopy

from app.services.content_seed import load_initial_sets
from app.services.content_expansion_v2 import load_expansion, validate_expansion


def expect_invalid(data):
    try:
        validate_expansion(data)
    except ValueError:
        return
    raise AssertionError("Invalid expansion accepted")


def run():
    base = load_initial_sets()
    original = deepcopy(base)
    draft = load_expansion()
    full_sets = validate_expansion(draft, base=base)
    assert len(full_sets) == 2
    assert [len(item["questions"]) for item in full_sets] == [10, 10]
    assert base == original, "Expansion must not mutate V1 source"
    for expanded in full_sets:
        source = next(s for s in base["sets"] if expanded["title"].startswith(s["title"]))
        assert expanded["questions"][:6] == source["questions"]
        assert all(q["explanation"].strip() for q in expanded["questions"])

    invalid = deepcopy(draft)
    invalid["sets"][0]["questions"][0]["correct"] = 7
    expect_invalid(invalid)
    invalid = deepcopy(draft)
    invalid["sets"][0]["questions"][0]["explanation"] = ""
    expect_invalid(invalid)
    invalid = deepcopy(draft)
    invalid["sets"][1]["questions"][0]["options"][1] = invalid["sets"][1]["questions"][0]["options"][0]
    expect_invalid(invalid)
    invalid = deepcopy(draft)
    invalid["sets"][1]["slug"] = "bilim-teknoloji-baslangic"
    expect_invalid(invalid)


if __name__ == "__main__":
    run()
    print("PASS — V2 drafts: 2 sets / 20 questions; V1 unchanged")
