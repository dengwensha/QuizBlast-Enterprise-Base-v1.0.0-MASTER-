"""CONTENT-01D.4: fail-closed visual asset review for V3 quiz drafts.

This module performs no network calls or database writes. A URL's reachability,
image content and license must be verified by a separate editorial process.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

from app.services.content_general_culture_v3 import load_general_culture_v3
from app.services.content_science_v3 import load_science_v3

MANIFEST = Path(__file__).resolve().parents[1] / "content" / "visual_assets_review_v1.json"
PENDING = "pending_review"
APPROVED = "approved"
ALLOWED_LICENSES = {"CC0", "CC-BY-4.0", "CC-BY-SA-4.0", "public-domain", "original"}


def load_visual_review(path=MANIFEST):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _https_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def validate_visual_review(manifest, *, drafts=None):
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != 1 or manifest.get("status") != "draft_only":
        raise ValueError("invalid_visual_manifest")
    items = manifest.get("assets")
    if not isinstance(items, list) or len(items) != 7:
        raise ValueError("expected_seven_visual_candidates")
    if drafts is None:
        drafts = [load_general_culture_v3(), load_science_v3()]
    expected = {}
    for draft in drafts:
        for index, question in enumerate(draft["questions"], start=11):
            if question.get("visual_candidate") is True:
                expected[(draft["slug"], index)] = question["visual_brief"]
    if len(expected) != 7:
        raise ValueError("draft_visual_candidates_mismatch")
    seen = set()
    approved = 0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid_visual_item")
        key = (item.get("set_slug"), item.get("question_number"))
        if key not in expected or key in seen or not isinstance(item.get("description"), str) or not item["description"].strip():
            raise ValueError("invalid_or_duplicate_visual_mapping")
        seen.add(key)
        status = item.get("status")
        if status == PENDING:
            if any(item.get(field) is not None for field in ("image_url", "source_url", "license", "attribution")):
                raise ValueError("unreviewed_visual_contains_asset")
            if item.get("accessibility_checked") is not False or item.get("visual_qa_pass") is not False:
                raise ValueError("unreviewed_visual_marked_as_checked")
        elif status == APPROVED:
            if (not _https_url(item.get("image_url")) or not _https_url(item.get("source_url"))
                    or item.get("license") not in ALLOWED_LICENSES
                    or not isinstance(item.get("attribution"), str) or not item["attribution"].strip()
                    or item.get("accessibility_checked") is not True
                    or item.get("visual_qa_pass") is not True):
                raise ValueError("incomplete_visual_approval")
            approved += 1
        else:
            raise ValueError("invalid_visual_status")
    if seen != set(expected):
        raise ValueError("missing_visual_candidates")
    return {"total": len(items), "approved": approved, "pending": len(items)-approved}


def require_all_visuals_approved(manifest):
    result = validate_visual_review(manifest)
    if result["pending"] != 0:
        raise ValueError("visual_publication_blocked_until_review_complete")
    return result
