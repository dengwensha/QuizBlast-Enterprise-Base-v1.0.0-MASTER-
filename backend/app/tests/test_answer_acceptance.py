import unittest

from app.services.answer_acceptance import answer_is_open, valid_answer


class AnswerAcceptanceTests(unittest.TestCase):
    def test_only_four_integer_options_are_accepted(self):
        for index in range(4):
            self.assertEqual(valid_answer(index), index)
        for value in (None, -1, 4, '0', 'invalid', True, False, 1.0, [], {}):
            self.assertIsNone(valid_answer(value))

    def test_question_deadline_and_closed_phase(self):
        self.assertTrue(answer_is_open(100, 15, 115))
        self.assertFalse(answer_is_open(100, 15, 115.01))
        self.assertFalse(answer_is_open(None, 15, 110))
        self.assertFalse(answer_is_open(100, 15, 99))


if __name__ == '__main__':
    unittest.main()
