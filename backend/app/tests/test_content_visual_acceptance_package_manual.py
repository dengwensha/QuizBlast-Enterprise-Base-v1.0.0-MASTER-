"""CONTENT-01D.12: non-publishing seven-asset acceptance inventory.

This checks reference consistency only. It never approves a visual or fetches media.
"""
import json
from pathlib import Path

from app.services.content_visual_review import load_visual_review, validate_visual_review

CONTENT = Path(__file__).resolve().parents[1] / "content"


def build_acceptance_inventory():
    manifest = load_visual_review()
    summary = validate_visual_review(manifest)
    originals = json.loads((CONTENT / "visual_original_drafts_v1.json").read_text(encoding="utf-8"))
    artwork = json.loads((CONTENT / "artwork_thumbnail_candidate_v1.json").read_text(encoding="utf-8"))
    assert originals["status"] == "draft_only" and len(originals["assets"]) == 6
    original_map = {}
    for asset in originals["assets"]:
        key = (asset["set_slug"], asset["question_number"])
        if key in original_map or asset["approval"] != "pending_review" or asset["image_url"] is not None:
            raise ValueError("invalid_original_asset")
        original_map[key] = asset["source_path"]
    art_key = (artwork["set_slug"], artwork["question_number"])
    if art_key in original_map or artwork["release_status"] != "pending_review":
        raise ValueError("invalid_artwork_candidate")
    if artwork["asset_download_verified"] or artwork["browser_loading_verified"] or artwork["visual_qa_pass"]:
        raise ValueError("unverified_artwork_marked_ready")
    if len(original_map) != 6 or summary != {"total": 7, "approved": 0, "pending": 7}:
        raise ValueError("unexpected_visual_approval_state")

    entries = []
    for visual in manifest["assets"]:
        key = (visual["set_slug"], visual["question_number"])
        if key in original_map:
            source_kind = "original_svg"
            candidate = original_map[key]
        elif key == art_key:
            source_kind = "external_artwork_thumbnail"
            candidate = artwork["candidate_image_url"]
        else:
            raise ValueError("missing_visual_candidate_source")
        entries.append({
            "set_slug": key[0],
            "question_number": key[1],
            "description": visual["description"],
            "source_kind": source_kind,
            "draft_source": candidate,
            "approval": visual["status"],
            "physical_test": "deferred",
        })
    if { (item["set_slug"], item["question_number"]) for item in entries } != set(original_map) | {art_key}:
        raise ValueError("inconsistent_visual_source_mapping")
    return entries


def run():
    entries = build_acceptance_inventory()
    assert len(entries) == 7
    assert sum(x["source_kind"] == "original_svg" for x in entries) == 6
    assert sum(x["source_kind"] == "external_artwork_thumbnail" for x in entries) == 1
    assert all(x["approval"] == "pending_review" and x["physical_test"] == "deferred" for x in entries)


if __name__ == "__main__":
    run()
    print("PASS — 7/7 source mappings ready for deferred acceptance; 0 approved")
