from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImportIssue:
    row_no: int
    level: str
    field: str
    message: str
    expected: str = ""
    actual: Any = ""


@dataclass
class ImportReport:
    total_rows: int = 0
    success_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    issues: list[ImportIssue] = field(default_factory=list)

    def add_error(self, row_no: int, field: str, message: str, expected: str = "", actual: Any = ""):
        self.error_count += 1
        self.issues.append(
            ImportIssue(
                row_no=row_no,
                level="ERROR",
                field=field,
                message=message,
                expected=expected,
                actual=actual
            )
        )

    def add_warning(self, row_no: int, field: str, message: str, expected: str = "", actual: Any = ""):
        self.warning_count += 1
        self.issues.append(
            ImportIssue(
                row_no=row_no,
                level="WARNING",
                field=field,
                message=message,
                expected=expected,
                actual=actual
            )
        )

    def to_text(self) -> str:
        lines = [
            "QuizBlast Import Report",
            f"Toplam satır: {self.total_rows}",
            f"Başarılı: {self.success_count}",
            f"Hatalı: {self.error_count}",
            f"Uyarı: {self.warning_count}",
            ""
        ]

        for issue in self.issues:
            lines.append(
                f"Satır {issue.row_no} | {issue.level} | {issue.field}: "
                f"{issue.message} | Beklenen: {issue.expected} | Gelen: {issue.actual}"
            )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "row_no": issue.row_no,
                    "level": issue.level,
                    "field": issue.field,
                    "message": issue.message,
                    "expected": issue.expected,
                    "actual": issue.actual
                }
                for issue in self.issues
            ]
        }
