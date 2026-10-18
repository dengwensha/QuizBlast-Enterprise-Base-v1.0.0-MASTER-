"""Read-only, fail-closed content validation for the first English school pilot.

Publication is intentionally out of scope: successful validation does not write to DB.
"""
import json
from collections import Counter
from pathlib import Path

from app.schemas.qbds import QBDSQuestionDTO
from app.services.content_taxonomy import EDUCATION, classify_catalog_set
from app.services.validation_engine import validate_questions

CONTENT_FILE = Path(__file__).resolve().parents[1] / "content" / "education_english_pilot_v1.json"
EXPECTED = {
    "ilkokul-3-ingilizce-renkler-sayilar": ("primary", 3, "Renkler ve Sayılar"),
    "ortaokul-5-ingilizce-gunluk-ifadeler": ("middle", 5, "Günlük İfadeler"),
}


def load_english_pilot(path=CONTENT_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_english_pilot(data):
    if not isinstance(data, dict) or data.get("collection_version") != 2 or data.get("language") != "tr":
        raise ValueError("invalid_english_pilot_version")
    sets = data.get("sets")
    if not isinstance(sets, list) or len(sets) != 2:
        raise ValueError("expected_two_english_sets")
    if {item.get("slug") for item in sets} != set(EXPECTED):
        raise ValueError("unexpected_english_set_slugs")

    for item in sets:
        slug = item["slug"]
        expected_stage, expected_grade, expected_topic = EXPECTED[slug]
        classification = classify_catalog_set(
            item.get("collection"), stage=item.get("stage"), grade=item.get("grade"),
            subject=item.get("subject"), topic=item.get("school_topic"),
        )
        if (classification.collection != EDUCATION or
                classification.stage != expected_stage or
                classification.grade != expected_grade or
                classification.subject != "İngilizce" or
                classification.topic != expected_topic):
            raise ValueError(f"{slug}:invalid_education_metadata")
        if item.get("topic") != "İngilizce" or item.get("difficulty") != "Kolay":
            raise ValueError(f"{slug}:invalid_topic_or_difficulty")
        for field in ("title", "audience", "description"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{slug}:missing_{field}")

        questions = item.get("questions")
        if not isinstance(questions, list) or len(questions) != 10:
            raise ValueError(f"{slug}:expected_ten_questions")
        rows = []
        positions = []
        for number, question in enumerate(questions, 1):
            options = question.get("options")
            correct = question.get("correct")
            if (not isinstance(options, list) or len(options) != 4 or
                    type(correct) is not int or correct not in range(4)):
                raise ValueError(f"{slug}:invalid_options_or_answer:{number}")
            if type(question.get("time")) is not int or not 5 <= question["time"] <= 120:
                raise ValueError(f"{slug}:invalid_time:{number}")
            if not isinstance(question.get("explanation"), str) or not question["explanation"].strip():
                raise ValueError(f"{slug}:missing_explanation:{number}")
            if len({str(option).strip().casefold() for option in options}) != 4:
                raise ValueError(f"{slug}:duplicate_options:{number}")
            positions.append(correct)
            rows.append((number, QBDSQuestionDTO(
                question=question.get("question", ""),
                option_a=options[0], option_b=options[1],
                option_c=options[2], option_d=options[3],
                correct="ABCD"[correct], time=question["time"],
                difficulty=item["difficulty"],
            )))
        counts = Counter(positions)
        if set(counts) != {0, 1, 2, 3} or max(counts.values()) - min(counts.values()) > 1:
            raise ValueError(f"{slug}:unbalanced_correct_answers")
        report = validate_questions(rows)
        if report.error_count or report.warning_count:
            raise ValueError(f"{slug}:question_validation_failed:{report.to_text()}")
    return {"set_count": 2, "question_count": 20}
