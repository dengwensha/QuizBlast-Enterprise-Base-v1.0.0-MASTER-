from dataclasses import dataclass
from typing import Any

from app.schemas.qbds import QBDSQuestionDTO
from app.services.validation_engine import validate_questions
from app.services.import_report_engine import build_frontend_payload, group_issues_by_row


@dataclass
class PreviewRow:
    row_no: int
    status: str
    can_import: bool
    question: str
    options: list[str]
    correct: str
    time: int
    difficulty: str
    question_type: str
    category: str | None = None
    language: str | None = None
    audience: str | None = None
    tags: list[str] | None = None
    issues: list[dict[str, Any]] | None = None


def build_preview_rows(rows: list[tuple[int, QBDSQuestionDTO]], grouped_issues: dict[int, list[dict[str, Any]]]) -> list[PreviewRow]:
    preview_rows: list[PreviewRow] = []

    for row_no, dto in rows:
        issues = grouped_issues.get(row_no, [])
        has_error = any(issue.get("severity") == "ERROR" for issue in issues)
        has_warning = any(issue.get("severity") == "WARNING" for issue in issues)

        if has_error:
            status = "ERROR"
        elif has_warning:
            status = "WARNING"
        else:
            status = "OK"

        preview_rows.append(
            PreviewRow(
                row_no=row_no,
                status=status,
                can_import=not has_error,
                question=dto.question,
                options=[
                    dto.option_a,
                    dto.option_b,
                    dto.option_c,
                    dto.option_d
                ],
                correct=dto.correct,
                time=dto.time,
                difficulty=dto.difficulty,
                question_type=dto.question_type,
                category=dto.category,
                language=dto.language,
                audience=dto.audience,
                tags=dto.tags,
                issues=issues
            )
        )

    return preview_rows


def preview_row_to_dict(row: PreviewRow) -> dict[str, Any]:
    return {
        "row_no": row.row_no,
        "status": row.status,
        "can_import": row.can_import,
        "question": row.question,
        "options": row.options,
        "correct": row.correct,
        "time": row.time,
        "difficulty": row.difficulty,
        "question_type": row.question_type,
        "category": row.category,
        "language": row.language,
        "audience": row.audience,
        "tags": row.tags or [],
        "issues": row.issues or []
    }


def build_import_preview_payload(rows: list[tuple[int, QBDSQuestionDTO]]) -> dict[str, Any]:
    '''
    Main preview builder.

    Input:
      list[(row_no, QBDSQuestionDTO)]

    Output:
      payload suitable for future frontend preview UI.
    '''
    validation_report = validate_questions(rows)
    report_payload = build_frontend_payload(validation_report)
    grouped_issues = group_issues_by_row(validation_report)

    preview_rows = build_preview_rows(rows, grouped_issues)

    importable_rows = [
        row
        for row in preview_rows
        if row.can_import
    ]

    blocked_rows = [
        row
        for row in preview_rows
        if not row.can_import
    ]

    return {
        "summary": {
            **report_payload["summary"],
            "preview_rows": len(preview_rows),
            "importable_rows": len(importable_rows),
            "blocked_rows": len(blocked_rows)
        },
        "preview_rows": [
            preview_row_to_dict(row)
            for row in preview_rows
        ],
        "issues": report_payload["issues"],
        "message": report_payload["message"]
    }


def get_importable_legacy_payloads(rows: list[tuple[int, QBDSQuestionDTO]]) -> list[dict[str, Any]]:
    '''
    Returns only rows that can be safely imported, converted to current QuestionCreate payload.
    This will be used in the future integration sprint.
    '''
    payload = build_import_preview_payload(rows)
    importable_row_numbers = {
        row["row_no"]
        for row in payload["preview_rows"]
        if row["can_import"]
    }

    result = []

    for row_no, dto in rows:
        if row_no in importable_row_numbers:
            result.append(dto.to_legacy_question_create())

    return result
