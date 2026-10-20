"""CONTENT-01D.2: immutable V3 General Culture draft validation.

No database operations or automatic publishing. Visual candidates are planning
metadata, not image assets; a valid image URL is not implied.
"""
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from app.schemas.qbds import QBDSQuestionDTO
from app.services.content_expansion_v2 import load_expansion, validate_expansion
from app.services.validation_engine import validate_questions

DRAFT_PATH = Path(__file__).resolve().parents[1] / "content" / "general_culture_v3_additions.json"
EXPECTED_SLUG = "genel-kultur-genisletilmis-v3"


def load_general_culture_v3(path=DRAFT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_general_culture_v3(data, *, source_sets=None):
    if (not isinstance(data, dict) or data.get("collection_version") != 3
            or data.get("language") != "tr"
            or data.get("publication_status") != "draft_only"
            or data.get("base_slug") != "genel-kultur-genisletilmis-v2"
            or data.get("slug") != EXPECTED_SLUG):
        raise ValueError("invalid_general_culture_v3_metadata")
    additions = data.get("questions")
    if not isinstance(additions, list) or len(additions) != 5:
        raise ValueError("expected_five_additions")
    v2 = validate_expansion(load_expansion()) if source_sets is None else source_sets
    base = next((s for s in v2 if s["slug"] == data["base_slug"]), None)
    if base is None or len(base["questions"]) != 10:
        raise ValueError("invalid_v2_source")
    questions = deepcopy(base["questions"]) + deepcopy(additions)
    rows = []
    for index, q in enumerate(questions, 1):
        choices = q.get("options")
        answer = q.get("correct")
        if (not isinstance(q.get("question"), str) or not q["question"].strip()
                or not isinstance(choices, list) or len(choices) != 4
                or any(not isinstance(x, str) or not x.strip() for x in choices)
                or len({x.strip().casefold() for x in choices}) != 4
                or type(answer) is not int or answer not in range(4)
                or type(q.get("time")) is not int or not 5 <= q["time"] <= 120
                or not isinstance(q.get("explanation"), str)
                or not q["explanation"].strip()):
            raise ValueError(f"invalid_v3_question:{index}")
        rows.append((index, QBDSQuestionDTO(
            question=q["question"], option_a=choices[0], option_b=choices[1],
            option_c=choices[2], option_d=choices[3], correct="ABCD"[answer],
            time=q["time"], difficulty=q.get("difficulty", base["difficulty"]),
        )))
    positions = Counter(q["correct"] for q in questions)
    if set(positions) != set(range(4)) or max(positions.values()) - min(positions.values()) > 1:
        raise ValueError("unbalanced_v3_answer_positions")
    if Counter(q.get("difficulty") for q in additions) != {"Orta": 3, "Zor": 2}:
        raise ValueError("invalid_new_question_difficulty_mix")
    for q in additions:
        if type(q.get("visual_candidate")) is not bool:
            raise ValueError("missing_visual_candidate_flag")
        if q["visual_candidate"] and (not isinstance(q.get("visual_brief"), str)
                                      or not q["visual_brief"].strip()):
            raise ValueError("missing_visual_brief")
        if q.get("image_url"):
            raise ValueError("visual_assets_must_be_reviewed_before_use")
    if sum(q["visual_candidate"] for q in additions) != 3:
        raise ValueError("expected_three_visual_candidates")
    report = validate_questions(rows)
    if report.error_count or report.warning_count:
        raise ValueError(f"general_culture_v3_validation_failed:{report.to_text()}")
    return {"slug": EXPECTED_SLUG, "questions": questions, "publication_status": "draft_only"}
