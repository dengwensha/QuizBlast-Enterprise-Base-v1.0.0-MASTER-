"""CONTENT-01D.4D — offline structural validation of unpublished SVG drafts."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from app.services.content_visual_review import load_visual_review, validate_visual_review

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "backend/app/content/visual_original_drafts_v1.json"
SVG_NS = "{http://www.w3.org/2000/svg}"


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
        path = ROOT / record["source_path"]
        assert path.is_relative_to(ROOT / "frontend/src/assets/quiz")
        assert path.is_file()
        source = path.read_text(encoding="utf-8")
        doc = ET.fromstring(source)
        assert doc.tag == SVG_NS + "svg"
        assert doc.attrib.get("viewBox") == "0 0 800 500"
        assert doc.find(SVG_NS + "title") is not None
        assert doc.find(SVG_NS + "desc") is not None
        assert "<script" not in source.lower()
        assert "http://" not in source and "https://" not in source
    assert validate_visual_review(load_visual_review()) == {
        "total": 7, "approved": 0, "pending": 7
    }
    assert len(keys) == 5


if __name__ == "__main__":
    run()
    print("PASS — 5 original SVG drafts structurally valid; all 7 publication approvals pending")
