import unittest

from app.services.game_progression import next_question_index, next_stage


class GameProgressionTests(unittest.TestCase):
    def test_advance_requires_published_result(self):
        self.assertIsNone(next_question_index(0, 3, False))
        self.assertEqual(next_question_index(0, 3, True), 1)

    def test_final_advance_and_repeated_request(self):
        self.assertEqual(next_question_index(2, 3, True), 3)
        self.assertIsNone(next_question_index(3, 3, False))
        self.assertIsNone(next_question_index(3, 3, True))

    def test_ui09_stage_sequence_is_host_gated(self):
        self.assertEqual(next_stage('question', 'time_expired'), 'result')
        self.assertEqual(next_stage('result', 'reveal_leaderboard'), 'leaderboard')
        self.assertEqual(next_stage('leaderboard', 'next_question'), 'question')
        self.assertEqual(next_stage('leaderboard', 'finish_game'), 'completed')

    def test_ui09_rejects_out_of_order_and_duplicate_transitions(self):
        self.assertIsNone(next_stage('question', 'next_question'))
        self.assertIsNone(next_stage('result', 'next_question'))
        self.assertIsNone(next_stage('leaderboard', 'reveal_leaderboard'))
        self.assertIsNone(next_stage('completed', 'next_question'))

    def test_empty_quiz_cannot_advance(self):
        self.assertIsNone(next_question_index(0, 0, True))


if __name__ == '__main__':
    unittest.main()
