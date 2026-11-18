"""Catalog classification contract for future education and event collections.

Pure validation only: this module does not migrate the database or republish sets.
Existing published sets with no new metadata remain in the general collection.
"""
from dataclasses import dataclass

EDUCATION = "education"
GENERAL_EVENT = "general_event"
COLLECTIONS = frozenset({EDUCATION, GENERAL_EVENT})
SCHOOL_STAGES = {"primary": range(1, 5), "middle": range(5, 9)}


@dataclass(frozen=True)
class CatalogClassification:
    collection: str
    stage: str | None = None
    grade: int | None = None
    subject: str | None = None
    topic: str | None = None


def classify_catalog_set(
    collection: str | None = None,
    *,
    stage: str | None = None,
    grade: int | None = None,
    subject: str | None = None,
    topic: str | None = None,
) -> CatalogClassification:
    """Validate a two-collection classification without inferring school grades."""
    selected = GENERAL_EVENT if collection is None else collection
    if selected not in COLLECTIONS:
        raise ValueError("invalid_catalog_collection")
    fields = (stage, grade, subject, topic)
    if selected == GENERAL_EVENT:
        if any(value is not None for value in fields):
            raise ValueError("general_collection_cannot_have_school_metadata")
        return CatalogClassification(collection=selected)
    if stage not in SCHOOL_STAGES:
        raise ValueError("invalid_school_stage")
    if type(grade) is not int or grade not in SCHOOL_STAGES[stage]:
        raise ValueError("grade_outside_school_stage")
    for field_name, value in (("subject", subject), ("topic", topic)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"invalid_school_{field_name}")
    return CatalogClassification(
        collection=selected, stage=stage, grade=grade,
        subject=subject.strip(), topic=topic.strip(),
    )
