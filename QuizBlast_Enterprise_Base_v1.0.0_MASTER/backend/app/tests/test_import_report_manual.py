import json
from pathlib import Path

from app.services.qbds_mapper import map_excel_row_to_qbds
from app.services.validation_engine import validate_questions
from app.services.import_report_engine import (
    build_frontend_payload,
    build_user_message,
    build_table_rows,
    group_issues_by_row
)
from app.utils.import_report_exporter import export_report_json, export_report_csv


BASE = Path(__file__).parent / "golden" / "import_report_cases.json"
OUT_DIR = Path(__file__).parent / "golden" / "out"
OUT_DIR.mkdir(exist_ok=True)

rows_raw = json.loads(BASE.read_text(encoding="utf-8"))

rows = [
    (item["row_no"], map_excel_row_to_qbds(item["data"], row_no=item["row_no"]))
    for item in rows_raw
]

report = validate_questions(rows)

payload = build_frontend_payload(report)
message = build_user_message(report)
table_rows = build_table_rows(report)
grouped = group_issues_by_row(report)

print(message)
print(payload)

assert "summary" in payload
assert "issues" in payload
assert payload["summary"]["total_rows"] == 3
assert payload["summary"]["error_count"] >= 1
assert len(table_rows) >= 1
assert 3 in grouped

json_path = export_report_json(report, OUT_DIR / "sample_import_report.json")
csv_path = export_report_csv(report, OUT_DIR / "sample_import_report.csv")

assert json_path.exists()
assert csv_path.exists()

print("Import Report Engine manual test passed.")
print("JSON:", json_path)
print("CSV:", csv_path)
