"""Persisted room state for the staged game recovery implementation.

No WebSocket objects or asyncio tasks belong in this model. Callers must write
each accepted game transition in the same transaction as its player changes.
"""

import hashlib
import hmac
import secrets
import time

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class RecoveryBase(DeclarativeBase):
    pass


class GameRoom(RecoveryBase):
    __tablename__ = 'game_rooms'

    pin: Mapped[str] = mapped_column(String(6), primary_key=True)
    quiz_id: Mapped[int] = mapped_column(Integer, nullable=False)
    host_email: Mapped[str] = mapped_column(String, nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False, default='lobby')
    question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_epoch: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_stats: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: [0, 0, 0, 0])
    players: Mapped[list['GamePlayer']] = relationship(
        back_populates='room', cascade='all, delete-orphan'
    )


class GamePlayer(RecoveryBase):
    __tablename__ = 'game_players'

    room_pin: Mapped[str] = mapped_column(ForeignKey('game_rooms.pin'), primary_key=True)
    name: Mapped[str] = mapped_column(String, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answered_question_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room: Mapped[GameRoom] = relationship(back_populates='players')


def new_player_token():
    token = secrets.token_urlsafe(32)
    return token, token_digest(token)


def token_digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def player_token_matches(player, token):
    return hmac.compare_digest(player.token_hash, token_digest(token))


def pause_question(room, now=None):
    """Freeze server-authoritative time when the host is absent."""
    if room.phase != 'question' or room.deadline_epoch is None:
        return
    now = time.time() if now is None else now
    room.remaining_seconds = max(0.0, room.deadline_epoch - now)
    room.deadline_epoch = None


def checkpoint_question(room, now=None):
    """Persist a running clock sample; restart resumes from the last sample."""
    if room.phase != 'question' or room.deadline_epoch is None:
        return
    now = time.time() if now is None else now
    room.remaining_seconds = max(0.0, room.deadline_epoch - now)


def resume_question(room, now=None):
    """Resume only an already paused question after host authentication."""
    if room.phase != 'question' or room.deadline_epoch is not None:
        return
    if room.remaining_seconds is None:
        raise ValueError('question_remaining_time_missing')
    now = time.time() if now is None else now
    room.deadline_epoch = now + room.remaining_seconds


def freeze_after_restart(room):
    """Use the last persisted clock sample; downtime does not consume time."""
    if room.phase == 'question':
        room.deadline_epoch = None


def persist_game_state(session, pin, *, phase, index, scores, answered, stats,
                       remaining=None, deadline=None):
    """Commit a transition and its player effects atomically."""
    room = session.get(GameRoom, pin)
    if room is None:
        raise ValueError('room_not_persisted')
    room.phase = phase
    room.question_index = index
    room.answer_stats = list(stats)
    room.remaining_seconds = remaining
    room.deadline_epoch = deadline
    for player in room.players:
        player.score = scores.get(player.name, player.score)
        player.answered_question_index = index if player.name in answered else None
    session.commit()


def room_state(room):
    """Detach recovery data before closing the database session."""
    return {
        'pin': room.pin,
        'quiz_id': room.quiz_id,
        'host_email': room.host_email,
        'phase': room.phase,
        'index': room.question_index,
        'remaining': room.remaining_seconds,
        'scores': {player.name: player.score for player in room.players},
        'answered': {player.name for player in room.players
                     if player.answered_question_index == room.question_index},
        'stats': list(room.answer_stats),
    }
