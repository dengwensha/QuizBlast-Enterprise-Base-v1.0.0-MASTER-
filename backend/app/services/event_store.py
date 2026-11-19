"""Event drafts use the existing metadata and immutable user primary key."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String


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
    session = describe_session(db, link, Room)
    status = session['phase'] if session else 'ready' if selected else 'draft'
    return dict(event=serialize_event(row, status), quiz_id=selected.quiz_id if selected else None,
                session=session)

def register_event_report_model(base):
    class EventReport(base):
        __tablename__ = 'event_reports'
        event_id = Column(String(32), ForeignKey('event_game_sessions.event_id'), primary_key=True)
        event_title = Column(String(160), nullable=False)
        quiz_title = Column(String, nullable=False)
        completed_at = Column(DateTime(timezone=True), nullable=False)
        expires_at = Column(DateTime(timezone=True), nullable=False)
        ranking = Column(JSON, nullable=False)
    return EventReport


def report_utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def register_event_retention_model(base):
    class EventRetention(base):
        __tablename__ = 'event_presentation_retention'
        event_id = Column(String(32), ForeignKey('event_drafts.id'), primary_key=True)
        preference = Column(String(24), nullable=True)
        program_completed_at = Column(DateTime(timezone=True), nullable=True)
    return EventRetention


def register_event_agenda_model(base):
    class EventAgenda(base):
        __tablename__ = 'event_agendas'
        event_id = Column(String(32), ForeignKey('event_drafts.id'), primary_key=True)
        steps = Column(JSON, nullable=False)
    return EventAgenda


def register_event_run_model(base):
    class EventRun(base):
        __tablename__ = 'event_runs'
        event_id = Column(String(32), ForeignKey('event_drafts.id'), primary_key=True)
        display_key = Column(String(64), nullable=False, unique=True)
        title = Column(String(160), nullable=False)
        steps = Column(JSON, nullable=False)
        cursor = Column(Integer, nullable=False, default=0)
        view = Column(String(16), nullable=False, default='agenda')
        revision = Column(Integer, nullable=False, default=1)
    return EventRun


def register_event_deck_model(base):
    class EventDeck(base):
        __tablename__ = 'event_decks'
        id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)
        event_id = Column(String(32), ForeignKey('event_drafts.id'), nullable=False, index=True)
        name = Column(String(160), nullable=False)
        page_count = Column(Integer, nullable=False)
        pages = Column(JSON, nullable=False)
    return EventDeck

def describe_session(db, link, Room):
    if link is None:
        return None
    room = db.get(Room, link.pin)
    valid = bool(room and room.identity and room.identity.instance_id == link.instance_id)
    phase = room.phase if valid else 'closed'
    return dict(pin=link.pin, instance_id=link.instance_id, quiz_id=link.quiz_id,
                phase=phase, can_open=valid and phase != 'closed')


def register_event_step_game_models(base):
    class EventStepSession(base):
        __tablename__ = 'event_step_sessions'
        event_id = Column(String(32), ForeignKey('event_drafts.id'), primary_key=True)
        step_id = Column(String(36), primary_key=True)
        pin = Column(String(6), nullable=False)
        instance_id = Column(String(32), nullable=False, unique=True)
        quiz_id = Column(Integer, nullable=False)

    class EventStepReport(base):
        __tablename__ = 'event_step_reports'
        instance_id = Column(String(32), ForeignKey('event_step_sessions.instance_id'), primary_key=True)
        event_title = Column(String(160), nullable=False)
        quiz_title = Column(String, nullable=False)
        completed_at = Column(DateTime(timezone=True), nullable=False)
        expires_at = Column(DateTime(timezone=True), nullable=False)
        ranking = Column(JSON, nullable=False)

    return EventStepSession, EventStepReport
