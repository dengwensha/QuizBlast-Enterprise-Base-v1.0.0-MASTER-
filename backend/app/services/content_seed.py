"""Strict, fail-closed validation and one-shot publication for curated catalog sets."""
import json
from pathlib import Path

from app.schemas.qbds import QBDSQuestionDTO
from app.services.validation_engine import validate_questions
from app.services.validation_rules import VALID_DIFFICULTIES

CONTENT_FILE = Path(__file__).resolve().parents[1] / "content" / "initial_sets_v1.json"
REQUIRED_TITLES = {
    "QuizBlast'ı Tanı", "Genel Kültür", "Bilim ve Teknoloji", "Takım Isınma",
}


def load_initial_sets(path=CONTENT_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_initial_sets(data):
    if data.get("collection_version") != 1 or data.get("language") != "tr":
        raise ValueError("invalid_collection_version_or_language")
    sets = data.get("sets")
    if not isinstance(sets, list) or len(sets) != 4:
        raise ValueError("expected_four_sets")
    if {s.get("title") for s in sets} != REQUIRED_TITLES:
        raise ValueError("unexpected_set_titles")
    slugs = [s.get("slug") for s in sets]
    if any(not isinstance(s, str) or not s for s in slugs) or len(set(slugs)) != len(slugs):
        raise ValueError("invalid_or_duplicate_slug")

    for item in sets:
        for field in ("topic", "audience", "description"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{item['slug']}:missing_{field}")
        if item.get("difficulty") not in VALID_DIFFICULTIES:
            raise ValueError(f"{item['slug']}:invalid_difficulty")
        questions = item.get("questions")
        if not isinstance(questions, list) or len(questions) != 6:
            raise ValueError(f"{item['slug']}:expected_six_questions")
        dto_rows = []
        for index, question in enumerate(questions, 1):
            opts = question.get("options")
            correct = question.get("correct")
            if (not isinstance(opts, list) or len(opts) != 4 or
                    type(correct) is not int or correct not in range(4)):
                raise ValueError(f"{item['slug']}:invalid_options_or_correct:{index}")
            if type(question.get("time")) is not int:
                raise ValueError(f"{item['slug']}:invalid_time:{index}")
            if not isinstance(question.get("explanation", ""), str):
                raise ValueError(f"{item['slug']}:invalid_explanation:{index}")
            dto_rows.append((index, QBDSQuestionDTO(
                question=question.get("question", ""),
                option_a=opts[0], option_b=opts[1],
                option_c=opts[2], option_d=opts[3],
                correct="ABCD"[correct], time=question["time"],
                difficulty=item["difficulty"],
            )))
        answer_positions = {question["correct"] for question in questions}
        if len(answer_positions) != 4:
            raise ValueError(f"{item['slug']}:unbalanced_answer_positions")
        report = validate_questions(dto_rows)
        # For centrally published content, warning-level duplicates block publication too.
        if report.error_count or report.warning_count:
            raise ValueError(f"{item['slug']}:validation_failed:{report.to_text()}")
    return {"set_count": len(sets), "question_count": sum(len(s["questions"]) for s in sets)}


def publish_initial_sets(db, data, Quiz, Question, PublishedQuizSet):
    """Stage all four sets in the caller's single transaction; caller commits."""
    summary = validate_initial_sets(data)
    slugs = [s["slug"] for s in data["sets"]]
    # Never overwrite existing content, even if a set is still a draft.
    if db.query(PublishedQuizSet.id).filter(PublishedQuizSet.slug.in_(slugs)).first():
        raise ValueError("set_slug_already_exists")
    for item in data["sets"]:
        quiz = Quiz(title=item["title"], owner_email=None)
        db.add(quiz)
        db.flush()
        for question in item["questions"]:
            db.add(Question(
                quiz_id=quiz.id, question=question["question"],
                image_url=question.get("image_url"),
                explanation=question.get("explanation") or None,
                option1=question["options"][0],
                option2=question["options"][1],
                option3=question["options"][2],
                option4=question["options"][3],
                correct=question["correct"], time=question["time"],
            ))
        db.add(PublishedQuizSet(
            quiz_id=quiz.id, slug=item["slug"], description=item["description"],
            topic=item["topic"], audience=item["audience"],
            difficulty=item["difficulty"], version=1, is_published=True,
        ))
    db.flush()
    return summary
