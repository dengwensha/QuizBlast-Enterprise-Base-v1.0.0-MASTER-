"""Non-database acceptance checks for optional question image descriptions."""
import unittest
from types import SimpleNamespace

from app.services.content_catalog import serialize_preview_question


def make_question(**overrides):
    fields = dict(
        question="What color is the apple?", image_url=None,
        option1="Red", option2="Blue", option3="Black", option4="White", time=20,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


class OptionalImageAltTests(unittest.TestCase):
    def test_text_only_legacy_question_remains_valid(self):
        preview = serialize_preview_question(make_question())
        self.assertIsNone(preview["image_url"])
        self.assertIsNone(preview["image_alt_text"])
        self.assertEqual(len(preview["options"]), 4)

    def test_image_description_is_public_but_answer_is_not(self):
        question = make_question(
            image_url="https://example.org/apple.png",
            image_alt_text="A red apple on a white background",
            correct=0, explanation="Red is the correct answer.",
        )
        preview = serialize_preview_question(question)
        self.assertEqual(preview["image_alt_text"], "A red apple on a white background")
        self.assertNotIn("correct", preview)
        self.assertNotIn("explanation", preview)


if __name__ == "__main__":
    unittest.main()
