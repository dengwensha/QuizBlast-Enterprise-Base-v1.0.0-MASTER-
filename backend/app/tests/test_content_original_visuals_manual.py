"""CONTENT-01D.4D: backend-container metadata and publication isolation check.

SVG files are in the frontend tree and verified separately from the CI checkout.
"""
import json
from pathlib import Path, PurePosixPath

from app.services.content_visual_review import load_visual_review, validate_visual_review

REGISTRY = Path(__file__).resolve().parents[1] / "content/visual_original_drafts_v1.json"


def run():
    register = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert register["version"] == 1 and register["status"] == "draft_only"
    entries = register["assets"]
    assert len(entries) == 5
    keys = set()
    for record in entries:
        key = (record["set_slug"], record["question_number"])
        assert key not in keys
        keys.add(key)
        assert record["approval"] == "pending_review"
        assert record["image_url"] is None
        source_path = PurePosixPath(record["source_path"])
        assert not source_path.is_absolute()
        assert ".." not in source_path.parts
        assert source_path.parts[:4] == ("frontend", "src", "assets", "quiz")
        assert source_path.suffix == ".svg"
    assert validate_visual_review(load_visual_review()) == {
        "total": 7, "approved": 0, "pending": 7
    }


if __name__ == "__main__":
    run()
    print("PASS — five original SVG metadata entries; all 7 publication approvals pending")
