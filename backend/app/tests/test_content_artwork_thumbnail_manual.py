"""CONTENT-01D.11 — verify compact artwork candidate is non-publishing."""
import json
from pathlib import Path
from urllib.parse import urlparse

from app.services.content_visual_review import load_visual_review, validate_visual_review

FILE = Path(__file__).resolve().parents[1] / "content/artwork_thumbnail_candidate_v1.json"


def run():
    record = json.loads(FILE.read_text(encoding="utf-8"))
    assert record["record_version"] == 1
    assert record["status"] == "draft_only"
    assert record["release_status"] == "pending_review"
    assert record["set_slug"] == "genel-kultur-genisletilmis-v3"
    assert record["question_number"] == 12
    assert record["candidate_dimensions"] == {"width": 500, "height": 592}
    image_url = urlparse(record["candidate_image_url"])
    assert image_url.scheme == "https"
    assert image_url.hostname == "upload.wikimedia.org"
    assert image_url.path.endswith("/500px-1665_Girl_with_a_Pearl_Earring.jpg")
    page = urlparse(record["source_page"])
    assert page.scheme == "https" and page.hostname == "commons.wikimedia.org"
    assert record["license_mark"] == "PDM 1.0"
    assert record["alt_text_draft"].strip()
    assert record["credit_draft"].strip()
    assert record["source_metadata_reviewed"] is True
    assert record["asset_download_verified"] is False
    assert record["browser_loading_verified"] is False
    assert record["visual_qa_pass"] is False
    assert validate_visual_review(load_visual_review()) == {
        "total": 7, "approved": 0, "pending": 7
    }


if __name__ == "__main__":
    run()
    print("PASS — artwork thumbnail candidate metadata validated; release blocked")
