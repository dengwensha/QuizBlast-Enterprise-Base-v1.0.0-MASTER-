"""Event drafts use the existing metadata and immutable user primary key."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String


def register_event_model(base):
    class EventDraft(base):
        __tablename__ = 'event_drafts'
        id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)
        owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
        title = Column(String(160), nullable=False)
        organization = Column(String(160), nullable=True)
        scheduled_at = Column(DateTime(timezone=True), nullable=True)
        revision = Column(Integer, nullable=False, default=1)
        created_at = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
        updated_at = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    return EventDraft


def serialize_event(row, status='draft'):
    def utc(value):
        # SQLite returns naive values; all writes normalize to UTC first.
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return dict(id=row.id, title=row.title, organization=row.organization,
                scheduled_at=utc(row.scheduled_at), revision=row.revision,
                status=status, created_at=utc(row.created_at), updated_at=utc(row.updated_at))


def register_event_game_models(base):
    class EventQuizSelection(base):
        __tablename__ = 'event_quiz_selections'
        event_id = Column(String(32), ForeignKey('event_drafts.id'), primary_key=True)
        quiz_id = Column(Integer, nullable=False)

    class EventGameSession(base):
        __tablename__ = 'event_game_sessions'
        event_id = Column(String(32), ForeignKey('event_drafts.id'), primary_key=True)
        # Historical identifiers intentionally survive room/identity retention purge.
        pin = Column(String(6), nullable=False)
        instance_id = Column(String(32), nullable=False, unique=True)
        quiz_id = Column(Integer, nullable=False)
        created_at = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    return EventQuizSelection, EventGameSession


def describe_event_game(db, row, Selection, EventSession, Room):
    selected = db.get(Selection, row.id)
    link = db.get(EventSession, row.id)
    session = None
    if link is not None:
        room = db.get(Room, link.pin)
        valid = room and room.identity and room.identity.instance_id == link.instance_id
        phase = room.phase if valid else 'closed'
        session = dict(pin=link.pin, instance_id=link.instance_id, quiz_id=link.quiz_id,
                       phase=phase, can_open=bool(valid and phase != 'closed'))
    status = session['phase'] if session else 'ready' if selected else 'draft'
    return dict(event=serialize_event(row, status), quiz_id=selected.quiz_id if selected else None,
                session=session)
