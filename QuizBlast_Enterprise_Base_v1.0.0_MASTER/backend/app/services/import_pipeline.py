from dataclasses import dataclass, field
from typing import Any

from app.schemas.qbds import QBDSQuestionDTO
from app.services.qbds_mapper import map_excel_row_to_qbds
from app.services.import_preview_engine import (
    build_import_preview_payload,
    get_importable_legacy_payloads
)


@dataclass
class PipelineRowError:
    row_no: int
    stage: str
    message: str
    raw_row: dict[str, Any]


@dataclass
class ImportPipelineResult:
    mapped_rows: list[tuple[int, QBDSQuestionDTO]] = field(default_factory=list)
    mapping_errors: list[PipelineRowError] = field(default_factory=list)
    preview_payload: dict[str, Any] | None = None
    importable_payloads: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_mapping_errors(self) -> bool:
        return len(self.mapping_errors) > 0

    @property
    def can_continue_to_import(self) -> bool:
        if self.has_mapping_errors:
            return False

        if not self.preview_payload:
            return False

        return self.preview_payload.get("summary", {}).get("error_count", 0) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapped_rows": len(self.mapped_rows),
            "mapping_errors": [
                {
                    "row_no": error.row_no,
                    "stage": error.stage,
                    "message": error.message,
                    "raw_row": error.raw_row
                }
                for error in self.mapping_errors
            ],
            "preview_payload": self.preview_payload,
            "importable_payloads": self.importable_payloads,
            "can_continue_to_import": self.can_continue_to_import
        }


def run_qbds_import_pipeline(raw_rows: list[dict[str, Any]], first_data_row_no: int = 2) -> ImportPipelineResult:
    '''
    Orchestrates the QBDS import flow.

    Important:
    This service does NOT write to database.
    It only maps, validates, reports and prepares importable payloads.

    Steps:
    1. Raw rows -> QBDS DTOs
    2. DTOs -> Validation/Preview payload
    3. Importable rows -> current legacy QuestionCreate payloads
    '''

    result = ImportPipelineResult()

    for index, raw_row in enumerate(raw_rows):
        row_no = first_data_row_no + index

        try:
            dto = map_excel_row_to_qbds(raw_row, row_no=row_no)
            result.mapped_rows.append((row_no, dto))

        except Exception as exc:
            result.mapping_errors.append(
                PipelineRowError(
                    row_no=row_no,
                    stage="QBDS_MAPPER",
                    message=str(exc),
                    raw_row=raw_row
                )
            )

    if result.mapped_rows:
        result.preview_payload = build_import_preview_payload(result.mapped_rows)
        result.importable_payloads = get_importable_legacy_payloads(result.mapped_rows)
    else:
        result.preview_payload = {
            "summary": {
                "total_rows": len(raw_rows),
                "preview_rows": 0,
                "importable_rows": 0,
                "blocked_rows": len(raw_rows),
                "error_count": len(result.mapping_errors),
                "warning_count": 0,
                "can_import": False
            },
            "preview_rows": [],
            "issues": [],
            "message": "Hiç geçerli satır map edilemedi."
        }

    return result


def build_pipeline_user_message(result: ImportPipelineResult) -> str:
    lines = [
        "QBDS Import Pipeline tamamlandı.",
        f"Map edilen satır: {len(result.mapped_rows)}",
        f"Mapping hatası: {len(result.mapping_errors)}"
    ]

    if result.preview_payload:
        summary = result.preview_payload.get("summary", {})
        lines.extend([
            f"Önizleme satırı: {summary.get('preview_rows', 0)}",
            f"Import edilebilir: {summary.get('importable_rows', 0)}",
            f"Bloklanan: {summary.get('blocked_rows', 0)}",
            f"Validation hatası: {summary.get('error_count', 0)}",
            f"Validation uyarısı: {summary.get('warning_count', 0)}"
        ])

    if result.mapping_errors:
        lines.append("")
        lines.append("Mapping Hataları:")

        for error in result.mapping_errors:
            lines.append(f"Satır {error.row_no} | {error.stage}: {error.message}")

    return "\n".join(lines)
