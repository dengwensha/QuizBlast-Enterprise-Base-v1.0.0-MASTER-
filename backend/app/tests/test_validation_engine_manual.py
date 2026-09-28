import json
from pathlib import Path

from app.services.qbds_mapper import map_excel_row_to_qbds
from app.services.validation_engine import validate_questions


BASE = Path(__file__).parent / "golden" / "golden_validation_rows.json"

rows_raw = json.loads(BASE.read_text(encoding="utf-8"))

rows = []

for item in rows_raw:
    dto = map_excel_row_to_qbds(item["data"], row_no=item["row_no"])
    rows.append((item["row_no"], dto))

report = validate_questions(rows)

print(report.to_text())

codes = {issue.code for issue in report.issues}

assert "QB1001" in codes
assert "QB1002" in codes
assert "QB1004" in codes
assert "QB1005" in codes
assert "QB1007" in codes
assert "QB1008" in codes

print("Validation Engine manual test passed.")
