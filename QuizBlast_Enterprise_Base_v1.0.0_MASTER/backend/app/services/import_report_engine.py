from dataclasses import dataclass
from typing import Any
from app.services.validation_result import ValidationReport, Severity


@dataclass
class ImportSummary:
    total_rows: int
    valid_rows: int
    error_count: int
    warning_count: int
    can_import: bool


def build_import_summary(report: ValidationReport) -> ImportSummary:
    return ImportSummary(
        total_rows=report.total_rows,
        valid_rows=report.valid_rows,
        error_count=report.error_count,
        warning_count=report.warning_count,
        can_import=report.error_count == 0
    )


def build_user_message(report: ValidationReport) -> str:
    summary = build_import_summary(report)

    lines = [
        "Excel doğrulama tamamlandı.",
        f"Toplam satır: {summary.total_rows}",
        f"Geçerli satır: {summary.valid_rows}",
        f"Hata: {summary.error_count}",
        f"Uyarı: {summary.warning_count}",
        ""
    ]

    if summary.can_import:
        lines.append("Sonuç: Import yapılabilir.")
    else:
        lines.append("Sonuç: Hatalar düzeltilmeden import yapılamaz.")

    if report.issues:
        lines.append("")
        lines.append("Detaylar:")

    for issue in report.issues:
        lines.append(
            f"Satır {issue.row_no} | {issue.severity.value} | {issue.code} | "
            f"{issue.field}: {issue.message}"
        )

    return "\n".join(lines)


def build_frontend_payload(report: ValidationReport) -> dict[str, Any]:
    summary = build_import_summary(report)

    return {
        "summary": {
            "total_rows": summary.total_rows,
            "valid_rows": summary.valid_rows,
            "error_count": summary.error_count,
            "warning_count": summary.warning_count,
            "can_import": summary.can_import
        },
        "issues": [
            {
                "row_no": issue.row_no,
                "code": issue.code,
                "field": issue.field,
                "severity": issue.severity.value,
                "message": issue.message,
                "expected": issue.expected,
                "actual": issue.actual
            }
            for issue in report.issues
        ],
        "message": build_user_message(report)
    }


def build_table_rows(report: ValidationReport) -> list[dict[str, Any]]:
    rows = []

    for issue in report.issues:
        rows.append({
            "RowNo": issue.row_no,
            "Severity": issue.severity.value,
            "Code": issue.code,
            "Field": issue.field,
            "Message": issue.message,
            "Expected": issue.expected,
            "Actual": issue.actual
        })

    return rows


def group_issues_by_row(report: ValidationReport) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}

    for issue in report.issues:
        grouped.setdefault(issue.row_no, []).append({
            "code": issue.code,
            "field": issue.field,
            "severity": issue.severity.value,
            "message": issue.message,
            "expected": issue.expected,
            "actual": issue.actual
        })

    return grouped
