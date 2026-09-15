import re
import unicodedata
from dataclasses import dataclass
from app.schemas.qbds import QBDSQuestionDTO


@dataclass
class DuplicateMatch:
    row_no: int
    first_row_no: int
    question: str
    first_question: str
    similarity: float
    match_type: str


def normalize_question_text(text: str) -> str:
    '''
    Normalizes question text for exact duplicate detection.
    - trim
    - casefold
    - unicode normalization
    - remove punctuation
    - collapse spaces
    '''
    value = str(text or "").strip().casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^\w\sığüşöçİĞÜŞÖÇ]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def tokenize(text: str) -> set[str]:
    normalized = normalize_question_text(text)
    return {
        token
        for token in normalized.split(" ")
        if token
    }


def jaccard_similarity(a: str, b: str) -> float:
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)

    if not tokens_a and not tokens_b:
        return 1.0

    if not tokens_a or not tokens_b:
        return 0.0

    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def detect_exact_duplicates(rows: list[tuple[int, QBDSQuestionDTO]]) -> list[DuplicateMatch]:
    seen: dict[str, tuple[int, str]] = {}
    duplicates: list[DuplicateMatch] = []

    for row_no, dto in rows:
        key = normalize_question_text(dto.question)

        if not key:
            continue

        if key in seen:
            first_row_no, first_question = seen[key]
            duplicates.append(
                DuplicateMatch(
                    row_no=row_no,
                    first_row_no=first_row_no,
                    question=dto.question,
                    first_question=first_question,
                    similarity=1.0,
                    match_type="EXACT"
                )
            )
        else:
            seen[key] = (row_no, dto.question)

    return duplicates


def detect_near_duplicates(
    rows: list[tuple[int, QBDSQuestionDTO]],
    threshold: float = 0.85
) -> list[DuplicateMatch]:
    '''
    Simple near-duplicate detector using Jaccard similarity.
    Pilot-safe version: suitable for small/medium imports.
    '''
    matches: list[DuplicateMatch] = []

    for i, (row_no, dto) in enumerate(rows):
        current_question = dto.question

        if not normalize_question_text(current_question):
            continue

        for first_row_no, previous_dto in rows[:i]:
            previous_question = previous_dto.question

            if not normalize_question_text(previous_question):
                continue

            similarity = jaccard_similarity(current_question, previous_question)

            if similarity >= threshold and similarity < 1.0:
                matches.append(
                    DuplicateMatch(
                        row_no=row_no,
                        first_row_no=first_row_no,
                        question=current_question,
                        first_question=previous_question,
                        similarity=similarity,
                        match_type="NEAR"
                    )
                )
                break

    return matches


def detect_duplicate_questions(
    rows: list[tuple[int, QBDSQuestionDTO]],
    include_near_duplicates: bool = True,
    near_threshold: float = 0.85
) -> list[DuplicateMatch]:
    exact = detect_exact_duplicates(rows)

    if not include_near_duplicates:
        return exact

    exact_pairs = {
        (match.row_no, match.first_row_no)
        for match in exact
    }

    near = [
        match
        for match in detect_near_duplicates(rows, threshold=near_threshold)
        if (match.row_no, match.first_row_no) not in exact_pairs
    ]

    return exact + near


def duplicate_matches_to_legacy_map(matches: list[DuplicateMatch]) -> dict[int, int]:
    '''
    Backward-compatible helper for older validation code.
    duplicate_row_no -> first_seen_row_no
    '''
    return {
        match.row_no: match.first_row_no
        for match in matches
    }
