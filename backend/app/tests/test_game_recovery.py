"""Persisted room and player state survives a new database session."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.services.game_recovery import (
    GamePlayer, GameRoom, RecoveryBase, new_player_token,
    checkpoint_question, freeze_after_restart, pause_question, player_token_matches, resume_question,
    token_digest,
)


class GameRecoveryTests(unittest.TestCase):
    def test_room_and_answer_ownership_survive_new_session(self):
        engine = create_engine('sqlite://')
        RecoveryBase.metadata.create_all(engine)
        token, digest = new_player_token()
        with Session(engine) as db:
            room = GameRoom(pin='123456', quiz_id=7, host_email='host@example.com',
                            phase='question', question_index=2, answer_stats=[1, 0, 0, 0],
                            deadline_epoch=110.0)
            room.players.append(GamePlayer(name='Ada', token_hash=digest, score=240,
                                           answered_question_index=2))
            db.add(room)
            pause_question(room, now=105.0)
            db.commit()
        with Session(engine) as db:
            room = db.get(GameRoom, '123456')
            self.assertEqual((room.phase, room.question_index, room.answer_stats),
                             ('question', 2, [1, 0, 0, 0]))
            self.assertEqual((room.remaining_seconds, room.deadline_epoch), (5.0, None))
            player = db.scalar(select(GamePlayer).where(GamePlayer.room_pin == room.pin))
            self.assertEqual((player.score, player.answered_question_index), (240, 2))
            self.assertEqual(player.token_hash, token_digest(token))
            self.assertNotEqual(player.token_hash, token)
            self.assertTrue(player_token_matches(player, token))
            self.assertFalse(player_token_matches(player, 'someone-else'))
            resume_question(room, now=500.0)
            self.assertEqual(room.deadline_epoch, 505.0)

    def test_result_phase_does_not_restart_question(self):
        room = GameRoom(pin='654321', quiz_id=3, host_email='host@example.com',
                        phase='result', question_index=0)
        pause_question(room, now=100.0)
        resume_question(room, now=200.0)
        self.assertIsNone(room.deadline_epoch)

    def test_restart_uses_last_clock_checkpoint_not_downtime(self):
        room = GameRoom(pin='654321', quiz_id=3, host_email='host@example.com',
                        phase='question', remaining_seconds=10.0,
                        deadline_epoch=110.0)
        checkpoint_question(room, now=103.0)
        freeze_after_restart(room)
        self.assertEqual(room.remaining_seconds, 7.0)
        self.assertIsNone(room.deadline_epoch)
        resume_question(room, now=1000.0)
        self.assertEqual(room.deadline_epoch, 1007.0)


if __name__ == '__main__':
    unittest.main()
