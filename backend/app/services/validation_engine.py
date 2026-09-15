from app.schemas.qbds import QBDSQuestionDTO
from app.services.duplicate_detector import detect_duplicate_questions
from app.services.validation_result import ValidationReport, Severity
from app.services.validation_rules import (
    MIN_TIME,
    MAX_TIME,
    VALID_CORRECT,
    VALID_DIFFICULTIES,
    VALID_QUESTION_TYPES,
    VALID_LANGUAGES,
    ERROR_CODES,
)


def _is_blank(value) -> bool:
    return str(value or "").strip() == ""


def validate_question(dto: QBDSQuestionDTO, row_no: int, report: ValidationReport) -> bool:
    row_has_error = False

    if _is_blank(dto.question):
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["EMPTY_QUESTION"],
            field="Question",
            severity=Severity.ERROR,
            message="Soru metni boş olamaz.",
            expected="Dolu metin",
            actual=dto.question
        )
        row_has_error = True

    options = [
        ("OptionA", dto.option_a),
        ("OptionB", dto.option_b),
        ("OptionC", dto.option_c),
        ("OptionD", dto.option_d),
    ]

    for field, option in options:
        if _is_blank(option):
            report.add_issue(
                row_no=row_no,
                code=ERROR_CODES["EMPTY_OPTION"],
                field=field,
                severity=Severity.ERROR,
                message="Seçenek boş olamaz.",
                expected="Dolu metin",
                actual=option
            )
            row_has_error = True

    normalized_options = [
        str(option or "").strip().casefold()
        for _, option in options
        if not _is_blank(option)
    ]

    if len(normalized_options) != len(set(normalized_options)):
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["DUPLICATE_OPTION"],
            field="Options",
            severity=Severity.WARNING,
            message="Aynı seçenek birden fazla kullanılmış olabilir.",
            expected="4 farklı seçenek",
            actual=[option for _, option in options]
        )

    if dto.correct not in VALID_CORRECT:
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["INVALID_CORRECT"],
            field="Correct",
            severity=Severity.ERROR,
            message="Correct alanı A/B/C/D olmalıdır.",
            expected="A/B/C/D",
            actual=dto.correct
        )
        row_has_error = True

    if dto.time < MIN_TIME or dto.time > MAX_TIME:
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["INVALID_TIME"],
            field="Time",
            severity=Severity.ERROR,
            message=f"Süre {MIN_TIME}-{MAX_TIME} saniye arasında olmalıdır.",
            expected=f"{MIN_TIME}-{MAX_TIME}",
            actual=dto.time
        )
        row_has_error = True

    if dto.difficulty not in VALID_DIFFICULTIES:
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["INVALID_DIFFICULTY"],
            field="Difficulty",
            severity=Severity.ERROR,
            message="Geçersiz zorluk değeri.",
            expected=", ".join(sorted(VALID_DIFFICULTIES)),
            actual=dto.difficulty
        )
        row_has_error = True

    if dto.question_type not in VALID_QUESTION_TYPES:
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["INVALID_QUESTION_TYPE"],
            field="QuestionType",
            severity=Severity.ERROR,
            message="Geçersiz soru tipi.",
            expected=", ".join(sorted(VALID_QUESTION_TYPES)),
            actual=dto.question_type
        )
        row_has_error = True

    if dto.language not in VALID_LANGUAGES:
        report.add_issue(
            row_no=row_no,
            code=ERROR_CODES["UNKNOWN_LANGUAGE"],
            field="Language",
            severity=Severity.WARNING,
            message="Dil desteklenen liste dışında; import devam edebilir.",
            expected=", ".join(sorted(VALID_LANGUAGES)),
            actual=dto.language
        )

    return not row_has_error


def validate_questions(rows: list[tuple[int, QBDSQuestionDTO]]) -> ValidationReport:
    report = ValidationReport(total_rows=len(rows))

    row_validity: dict[int, bool] = {}

    for row_no, dto in rows:
        row_validity[row_no] = validate_question(dto, row_no, report)

    duplicates = detect_duplicate_questions(rows)

    for match in duplicates:
        report.add_issue(
            row_no=match.row_no,
            code=ERROR_CODES["DUPLICATE_QUESTION"],
            field="Question",
            severity=Severity.WARNING,
            message=(
                f"Aynı veya çok benzer soru daha önce {match.first_row_no}. satırda görülmüş. "
                f"Eşleşme tipi: {match.match_type}, benzerlik: {match.similarity:.2f}"
            ),
            expected="Tekil soru",
            actual=f"Duplicate of row {match.first_row_no}"
        )

    report.valid_rows = sum(1 for ok in row_validity.values() if ok)

    return report
