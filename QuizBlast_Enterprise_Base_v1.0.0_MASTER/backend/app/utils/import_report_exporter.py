import csv
import json
from pathlib import Path
from app.services.validation_result import ValidationReport
from app.services.import_report_engine import build_frontend_payload, build_table_rows


def export_report_json(report: ValidationReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.write_text(
        json.dumps(build_frontend_payload(report), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return path


def export_report_csv(report: ValidationReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    rows = build_table_rows(report)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["RowNo", "Severity", "Code", "Field", "Message", "Expected", "Actual"]
        )
        writer.writeheader()
        writer.writerows(rows)

    return path
