"""QB-CATALOG-02B pilot content acceptance tests; no publication side effects."""
import copy
import unittest

from app.services.content_english_pilot import load_english_pilot, validate_english_pilot


class EnglishPilotValidationTests(unittest.TestCase):
    def test_pilot_has_two_sets_and_twenty_questions(self):
        self.assertEqual(
            validate_english_pilot(load_english_pilot()),
            {"set_count": 2, "question_count": 20},
        )

    def test_primary_and_middle_classification_are_distinct(self):
        first, second = load_english_pilot()["sets"]
        self.assertEqual((first["stage"], first["grade"]), ("primary", 3))
        self.assertEqual((second["stage"], second["grade"]), ("middle", 5))
        self.assertEqual(first["subject"], second["subject"])

    def test_wrong_answer_index_is_rejected(self):
        data = copy.deepcopy(load_english_pilot())
        data["sets"][0]["questions"][0]["correct"] = 4
        with self.assertRaisesRegex(ValueError, "invalid_options_or_answer"):
            validate_english_pilot(data)

    def test_missing_explanation_is_rejected(self):
        data = copy.deepcopy(load_english_pilot())
        data["sets"][0]["questions"][0]["explanation"] = ""
        with self.assertRaisesRegex(ValueError, "missing_explanation"):
            validate_english_pilot(data)

    def test_invalid_school_grade_is_rejected(self):
        data = copy.deepcopy(load_english_pilot())
        data["sets"][1]["grade"] = 3
        with self.assertRaisesRegex(ValueError, "grade_outside_school_stage"):
            validate_english_pilot(data)

    def test_duplicate_options_are_rejected(self):
        data = copy.deepcopy(load_english_pilot())
        data["sets"][0]["questions"][0]["options"][2] = "Red"
        with self.assertRaisesRegex(ValueError, "duplicate_options"):
            validate_english_pilot(data)


if __name__ == "__main__":
    unittest.main()
