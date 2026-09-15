from typing import Any
from app.schemas.qbds import QBDSQuestionDTO


CORRECT_MAP = {
    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
    "0": "A",
    "1": "B",
    "2": "C",
    "3": "D"
}


def _normalize_key(key: str) -> str:
    return str(key or "").strip().lower().replace(" ", "").replace("_", "")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get(row: dict, *names: str, default: str = "") -> str:
    normalized = {
        _normalize_key(k): v
        for k, v in row.items()
    }

    for name in names:
        key = _normalize_key(name)
        if key in normalized:
            return _normalize_text(normalized[key])

    return default


def normalize_correct(value: Any) -> str | None:
    raw = _normalize_text(value).upper()

    if raw in CORRECT_MAP:
        return CORRECT_MAP[raw]

    return None


def split_tags(value: Any) -> list[str]:
    raw = _normalize_text(value)

    if not raw:
        return []

    return [
        tag.strip()
        for tag in raw.split(",")
        if tag.strip()
    ]


def map_excel_row_to_qbds(row: dict, row_no: int | None = None) -> QBDSQuestionDTO:
    '''
    Maps both QBDS v1 and legacy Excel rows into QBDSQuestionDTO.

    Supported new QBDS columns:
    QuizName, Category, Language, Audience, Question, Image,
    OptionA, OptionB, OptionC, OptionD, Correct, Time,
    Difficulty, QuestionType, Tags, Notes

    Supported legacy columns:
    question, image_url, a, b, c, d, correct, time
    '''

    correct = normalize_correct(
        _get(row, "Correct", "correct", "Doğru", "Dogru")
    )

    if correct is None:
        raise ValueError(
            f"Satır {row_no or '?'}: Correct alanı A/B/C/D veya 0/1/2/3 olmalı."
        )

    time_raw = _get(row, "Time", "time", "Süre", "Sure", default="15")

    try:
        time_value = int(float(time_raw))
    except Exception:
        raise ValueError(
            f"Satır {row_no or '?'}: Time/Süre sayısal olmalı."
        )

    dto = QBDSQuestionDTO(
        quiz_name=_get(row, "QuizName", "Quiz Name", "Quiz", default=""),
        category=_get(row, "Category", "Kategori", default=""),
        language=_get(row, "Language", "Dil", default="tr") or "tr",
        audience=_get(row, "Audience", "Hedef Kitle", default="Serbest") or "Serbest",

        question=_get(row, "Question", "question", "Soru"),
        image=_get(row, "Image", "image_url", "Görsel", "Gorsel", default=""),

        option_a=_get(row, "OptionA", "A", "a", "Seçenek A", "Secenek A"),
        option_b=_get(row, "OptionB", "B", "b", "Seçenek B", "Secenek B"),
        option_c=_get(row, "OptionC", "C", "c", "Seçenek C", "Secenek C"),
        option_d=_get(row, "OptionD", "D", "d", "Seçenek D", "Secenek D"),

        correct=correct,
        time=time_value,
        difficulty=_get(row, "Difficulty", "Zorluk", default="Orta") or "Orta",
        question_type=_get(row, "QuestionType", "Soru Tipi", default="Çoktan Seçmeli") or "Çoktan Seçmeli",
        tags=split_tags(_get(row, "Tags", "Etiketler", default="")),
        notes=_get(row, "Notes", "Notlar", default="")
    )

    return dto


def map_ai_output_to_qbds(data: dict) -> QBDSQuestionDTO:
    '''
    Standardizes AI-generated question objects into QBDSQuestionDTO.
    '''

    options = data.get("options") or []

    if len(options) != 4:
        raise ValueError("AI çıktısında 4 seçenek olmalı.")

    correct = normalize_correct(data.get("correct"))

    if correct is None:
        raise ValueError("AI çıktısında correct A/B/C/D veya 0/1/2/3 olmalı.")

    return QBDSQuestionDTO(
        quiz_name=data.get("quiz_name"),
        category=data.get("category"),
        language=data.get("language", "tr"),
        audience=data.get("audience", "Serbest"),
        question=data.get("question", ""),
        image=data.get("image") or data.get("image_url") or "",
        option_a=options[0],
        option_b=options[1],
        option_c=options[2],
        option_d=options[3],
        correct=correct,
        time=int(data.get("time", 15)),
        difficulty=data.get("difficulty", "Orta"),
        question_type=data.get("question_type", "Çoktan Seçmeli"),
        tags=data.get("tags") or [],
        notes=data.get("notes", "")
    )


def map_manual_input_to_qbds(data: dict) -> QBDSQuestionDTO:
    '''
    Standardizes Admin manual input into QBDSQuestionDTO.
    '''

    return map_ai_output_to_qbds(data)


def qbds_to_legacy_payload(dto: QBDSQuestionDTO) -> dict:
    '''
    Converts QBDS DTO to current backend QuestionCreate payload.
    '''

    return dto.to_legacy_question_create()
