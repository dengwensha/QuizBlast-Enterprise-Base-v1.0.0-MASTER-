"""CONTENT-01C: read-only assembly and validation of versioned expansion drafts.

Existing V1 sets and persisted published rows are never changed.
"""
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from app.schemas.qbds import QBDSQuestionDTO
from app.services.content_seed import load_initial_sets
from app.services.validation_engine import validate_questions

CONTENT_FILE = Path(__file__).resolve().parents[1] / "content" / "expanded_sets_v2.json"
EXPECTED = {
    "genel-kultur-baslangic": "genel-kultur-genisletilmis-v2",
    "bilim-teknoloji-baslangic": "bilim-teknoloji-genisletilmis-v2",
}


def load_expansion(path=CONTENT_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_expansion(data, *, base=None):
    if (not isinstance(data, dict) or data.get("collection_version") != 2
            or data.get("base_collection_version") != 1 or data.get("language") != "tr"):
        raise ValueError("invalid_expansion_version")
    entries = data.get("sets")
    if not isinstance(entries, list) or len(entries) != 2:
        raise ValueError("expected_two_expansions")
    if {entry.get("base_slug") for entry in entries} != set(EXPECTED):
        raise ValueError("unexpected_base_slugs")

    source = load_initial_sets() if base is None else base
    base_sets = {item["slug"]: item for item in source["sets"]}
    combined = []
    for item in entries:
        old = base_sets[item["base_slug"]]
        if item.get("slug") != EXPECTED[item["base_slug"]]:
            raise ValueError("unexpected_versioned_slug")
        additions = item.get("questions")
        if not isinstance(additions, list) or len(additions) != 4:
            raise ValueError("expected_four_new_questions")
        questions = deepcopy(old["questions"]) + deepcopy(additions)
        rows = []
        for number, question in enumerate(questions, 1):
            choices = question.get("options")
            answer = question.get("correct")
            if (not isinstance(question.get("question"), str) or not question["question"].strip()
                    or not isinstance(choices, list) or len(choices) != 4
                    or any(not isinstance(opt, str) or not opt.strip() for opt in choices)
                    or len({opt.strip().casefold() for opt in choices}) != 4
                    or type(answer) is not int or answer not in range(4)
                    or type(question.get("time")) is not int or not 5 <= question["time"] <= 120
                    or not isinstance(question.get("explanation"), str)
                    or not question["explanation"].strip()):
                raise ValueError(f"invalid_expansion_question:{number}")
            rows.append((number, QBDSQuestionDTO(
                question=question["question"], option_a=choices[0], option_b=choices[1],
                option_c=choices[2], option_d=choices[3],
                correct="ABCD"[answer], time=question["time"], difficulty=old["difficulty"],
            )))
        positions = Counter(q["correct"] for q in questions)
        if set(positions) != {0, 1, 2, 3} or max(positions.values()) - min(positions.values()) > 1:
            raise ValueError("unbalanced_expansion_answers")
        report = validate_questions(rows)
        if report.error_count or report.warning_count:
            raise ValueError(f"expansion_validation_failed:{report.to_text()}")
        combined.append({
            "slug": item["slug"], "title": old["title"] + " — Genişletilmiş",
            "topic": old["topic"], "audience": old["audience"],
            "difficulty": old["difficulty"], "description": old["description"],
            "questions": questions,
        })
    return combined
