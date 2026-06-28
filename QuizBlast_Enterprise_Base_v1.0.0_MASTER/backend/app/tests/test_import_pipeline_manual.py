import json
from pathlib import Path

from app.services.import_pipeline import (
    run_qbds_import_pipeline,
    build_pipeline_user_message
)

BASE = Path(__file__).parent / "golden" / "import_pipeline_cases.json"

raw_rows = json.loads(BASE.read_text(encoding="utf-8"))

result = run_qbds_import_pipeline(raw_rows, first_data_row_no=2)

print(build_pipeline_user_message(result))
print(result.to_dict())

assert len(result.mapped_rows) == 3
assert len(result.mapping_errors) == 1
assert result.preview_payload is not None

summary = result.preview_payload["summary"]

assert summary["preview_rows"] == 3
assert summary["importable_rows"] >= 1
assert summary["blocked_rows"] >= 1
assert len(result.importable_payloads) == summary["importable_rows"]

print("Import Pipeline Orchestrator manual test passed.")
