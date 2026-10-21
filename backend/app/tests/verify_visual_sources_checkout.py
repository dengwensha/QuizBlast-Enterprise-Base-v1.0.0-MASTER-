"""CONTENT-01D.4D: validate SVG source files from a complete GitHub checkout.

The backend Docker image has no frontend tree; this check runs on the CI host.
"""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "backend/app/content/visual_original_drafts_v1.json"
SVG_NS = "{http://www.w3.org/2000/svg}"


def run():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["status"] == "draft_only"
    assert len(registry["assets"]) == 5
    for record in registry["assets"]:
        relative = Path(record["source_path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert relative.parts[:4] == ("frontend", "src", "assets", "quiz")
        path = ROOT / relative
        assert path.is_file(), f"SVG missing: {relative}"
        source = path.read_text(encoding="utf-8")
        doc = ET.fromstring(source)
        assert doc.tag == SVG_NS + "svg"
        assert doc.attrib.get("viewBox") == "0 0 800 500"
        for element in doc.iter():
            name = element.tag.rsplit("}", 1)[-1].lower()
            assert name not in {"script", "foreignobject", "image", "animate", "set"}
            for key, value in element.attrib.items():
                assert not key.lower().startswith("on")
                if key.rsplit("}", 1)[-1] == "href":
                    assert value.startswith("#"), "External SVG references prohibited"
        title = doc.find(SVG_NS + "title")
        desc = doc.find(SVG_NS + "desc")
        assert title is not None and title.text and title.text.strip()
        assert desc is not None and desc.text and desc.text.strip()

    planet_path = ROOT / "frontend/src/assets/quiz/planet-orbits.svg"
    root = ET.parse(planet_path).getroot()
    circles = [
        element for element in root.findall(SVG_NS + "circle")
        if element.get("data-planet")
    ]
    assert len(circles) == 8, "Expected eight planet circles"
    assert len({circle.get("data-planet") for circle in circles}) == 8
    reference = next(circle for circle in circles if circle.get("data-planet") == "Jupiter")
    ref_radius = float(reference.get("r"))
    ref_diameter = float(reference.get("data-diameter-km"))
    assert ref_radius > 0 and ref_diameter > 0
    for circle in circles:
        radius = float(circle.get("r"))
        diameter = float(circle.get("data-diameter-km"))
        assert abs(radius / ref_radius - diameter / ref_diameter) < 0.001, (
            "Displayed planet radius must match actual diameter ratio"
        )
    assert "isimler gizli" in planet_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    run()
    print("PASS — five original SVG files validated from the full checkout")
