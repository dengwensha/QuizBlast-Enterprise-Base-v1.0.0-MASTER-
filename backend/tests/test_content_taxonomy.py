"""Contract checks for school and general/event catalog classifications."""
import unittest
from types import SimpleNamespace

from app.services.content_catalog import serialize_set

from app.services.content_taxonomy import (
    EDUCATION, GENERAL_EVENT, classify_catalog_set,
)


class CatalogTaxonomyTests(unittest.TestCase):
    def test_existing_sets_default_to_general_event(self):
        item = classify_catalog_set()
        self.assertEqual(item.collection, GENERAL_EVENT)
        self.assertIsNone(item.grade)

    def test_event_set_does_not_accept_school_metadata(self):
        with self.assertRaisesRegex(ValueError, "general_collection_cannot"):
            classify_catalog_set(GENERAL_EVENT, grade=4)

    def test_primary_and_middle_grades(self):
        primary = classify_catalog_set(
            EDUCATION, stage="primary", grade=3,
            subject="İngilizce", topic="Renkler ve Sayılar",
        )
        middle = classify_catalog_set(
            EDUCATION, stage="middle", grade=6,
            subject="Fen Bilimleri", topic="Güneş Sistemi",
        )
        self.assertEqual((primary.grade, middle.grade), (3, 6))

    def test_grade_cannot_cross_stage_boundary(self):
        for stage, grade in (("primary", 5), ("middle", 4), ("primary", True)):
            with self.subTest(stage=stage, grade=grade):
                with self.assertRaisesRegex(ValueError, "grade_outside_school_stage"):
                    classify_catalog_set(
                        EDUCATION, stage=stage, grade=grade,
                        subject="İngilizce", topic="Renkler",
                    )

    def test_education_requires_subject_and_topic(self):
        with self.assertRaisesRegex(ValueError, "invalid_school_subject"):
            classify_catalog_set(
                EDUCATION, stage="primary", grade=2,
                subject=" ", topic="Renkler",
            )

    def test_legacy_catalog_serialization_defaults_to_general(self):
        record = SimpleNamespace(
            id=1, slug="legacy", description="Before school metadata",
            topic="Genel Kültür", audience="Herkes", difficulty="Kolay", version=1,
        )
        quiz = SimpleNamespace(id=10, title="Legacy Quiz")
        item = serialize_set(record, quiz, [SimpleNamespace(time=20)])
        self.assertEqual(item["collection"], GENERAL_EVENT)
        self.assertIsNone(item["grade"])
        self.assertEqual(item["topic"], "Genel Kültür")

    def test_school_catalog_serialization_includes_filters(self):
        record = SimpleNamespace(
            id=2, slug="colors", description="Basic English",
            topic="İngilizce", audience="İlkokul", difficulty="Kolay", version=1,
            collection=EDUCATION, stage="primary", grade=3,
            subject="İngilizce", school_topic="Renkler ve Sayılar",
        )
        quiz = SimpleNamespace(id=11, title="Colors")
        item = serialize_set(record, quiz, [SimpleNamespace(time=20)])
        self.assertEqual(
            (item["collection"], item["stage"], item["grade"], item["subject"], item["school_topic"]),
            (EDUCATION, "primary", 3, "İngilizce", "Renkler ve Sayılar"),
        )
        self.assertEqual(item["question_count"], 1)

    def test_unknown_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_catalog_collection"):
            classify_catalog_set("unknown")


if __name__ == "__main__":
    unittest.main()
