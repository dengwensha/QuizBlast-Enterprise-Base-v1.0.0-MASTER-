"""Standalone Poll Studio storage; no Event Studio or GameRoom dependency."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint


def register_poll_models(base):
    class PollDefinition(base):
        __tablename__ = 'poll_definitions'
        id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)
        owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
        question = Column(String(500), nullable=False)
        options = Column(JSON, nullable=False)
        revision = Column(Integer, nullable=False, default=1)
        created_at = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))

    class PollSession(base):
        __tablename__ = 'poll_sessions'
        id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)
        poll_id = Column(String(32), ForeignKey('poll_definitions.id'), nullable=False, index=True)
        definition_revision = Column(Integer, nullable=False)
        invite_digest = Column(String(64), nullable=False, unique=True)
        status = Column(String(16), nullable=False, default='draft')
        created_at = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    class PollParticipant(base):
        __tablename__ = 'poll_participants'
        __table_args__ = (UniqueConstraint('session_id', 'join_key_digest',
                                           name='uq_poll_participant_join'),)
        id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)
        session_id = Column(String(32), ForeignKey('poll_sessions.id'),
                            nullable=False, index=True)
        join_key_digest = Column(String(64), nullable=False)
        token_digest = Column(String(64), nullable=False)
        joined_at = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    return PollDefinition, PollSession, PollParticipant


def serialize_poll(row):
    date = row.created_at
    if date is not None and date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return dict(id=row.id, question=row.question, options=row.options,
                revision=row.revision, created_at=date)
