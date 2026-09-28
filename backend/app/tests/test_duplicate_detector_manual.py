import json
from pathlib import Path

from app.services.qbds_mapper import map_excel_row_to_qbds
from app.services.duplicate_detector import (
    detect_duplicate_questions,
    detect_exact_duplicates,
    detect_near_duplicates,
    normalize_question_text,
    jaccard_similarity,
)

BASE = Path(__file__).parent / "golden" / "duplicate_detector_cases.json"

rows_raw = json.loads(BASE.read_text(encoding="utf-8"))

rows = [
    (item["row_no"], map_excel_row_to_qbds(item["data"], row_no=item["row_no"]))
    for item in rows_raw
]

exact = detect_exact_duplicates(rows)
near = detect_near_duplicates(rows, threshold=0.50)
all_matches = detect_duplicate_questions(rows, include_near_duplicates=True, near_threshold=0.50)

print("Exact duplicates:")
for match in exact:
    print(match)

print("\nNear duplicates:")
for match in near:
    print(match)

print("\nAll matches:")
for match in all_matches:
    print(match)

assert normalize_question_text(" II. Dünya Savaşı hangi yıl başladı? ") == normalize_question_text("ii. dünya savaşı hangi yıl başladı")
assert len(exact) >= 1
assert any(match.row_no == 3 and match.first_row_no == 2 for match in exact)
assert jaccard_similarity("A B C", "A B") > 0.5
assert len(all_matches) >= len(exact)

print("Duplicate Detector manual test passed.")
