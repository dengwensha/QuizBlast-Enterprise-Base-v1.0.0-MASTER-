from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    row_no: int
    code: str
    field: str
    severity: Severity
    message: str
    expected: str = ""
    actual: Any = ""


@dataclass
class ValidationReport:
    total_rows: int = 0
    valid_rows: int = 0
    error_count: int = 0
    warning_count: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    def add_issue(
        self,
        row_no: int,
        code: str,
        field: str,
        severity: Severity,
        message: str,
        expected: str = "",
        actual: Any = ""
    ):
        issue = ValidationIssue(
            row_no=row_no,
            code=code,
            field=field,
            severity=severity,
            message=message,
            expected=expected,
            actual=actual
        )

        self.issues.append(issue)

        if severity == Severity.ERROR:
            self.error_count += 1
        elif severity == Severity.WARNING:
            self.warning_count += 1

    @property
    def success(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
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
                for issue in self.issues
            ]
        }

    def to_text(self) -> str:
        lines = [
            "QuizBlast Validation Report",
            f"Toplam satır: {self.total_rows}",
            f"Geçerli satır: {self.valid_rows}",
            f"Hata: {self.error_count}",
            f"Uyarı: {self.warning_count}",
            ""
        ]

        for issue in self.issues:
            lines.append(
                f"Satır {issue.row_no} | {issue.severity.value} | {issue.code} | "
                f"{issue.field}: {issue.message} | Beklenen: {issue.expected} | Gelen: {issue.actual}"
            )

        return "\n".join(lines)
