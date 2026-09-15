import json
from pathlib import Path

from app.services.qbds_mapper import map_excel_row_to_qbds
from app.services.import_preview_engine import (
    build_import_preview_payload,
    get_importable_legacy_payloads
)


BASE = Path(__file__).parent / "golden" / "import_preview_cases.json"

rows_raw = json.loads(BASE.read_text(encoding="utf-8"))

rows = [
    (item["row_no"], map_excel_row_to_qbds(item["data"], row_no=item["row_no"]))
    for item in rows_raw
]

payload = build_import_preview_payload(rows)
legacy_payloads = get_importable_legacy_payloads(rows)

print(payload)

assert payload["summary"]["preview_rows"] == 3
assert payload["summary"]["blocked_rows"] >= 1
assert payload["summary"]["importable_rows"] >= 1

statuses = {
    row["row_no"]: row["status"]
    for row in payload["preview_rows"]
}

assert statuses[2] == "OK"
assert statuses[3] == "ERROR"
assert statuses[4] == "WARNING"

assert len(legacy_payloads) == payload["summary"]["importable_rows"]

print("Import Preview Engine manual test passed.")
