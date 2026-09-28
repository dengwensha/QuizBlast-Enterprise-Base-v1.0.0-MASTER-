import unittest

from app.services.game_progression import next_question_index


class GameProgressionTests(unittest.TestCase):
    def test_advance_requires_published_result(self):
        self.assertIsNone(next_question_index(0, 3, False))
        self.assertEqual(next_question_index(0, 3, True), 1)

    def test_final_advance_and_repeated_request(self):
        self.assertEqual(next_question_index(2, 3, True), 3)
        self.assertIsNone(next_question_index(3, 3, False))
        self.assertIsNone(next_question_index(3, 3, True))

    def test_empty_quiz_cannot_advance(self):
        self.assertIsNone(next_question_index(0, 0, True))


if __name__ == '__main__':
    unittest.main()
