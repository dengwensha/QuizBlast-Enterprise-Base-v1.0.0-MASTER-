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


def serialize_event(row):
    def utc(value):
        # SQLite returns naive values; all writes normalize to UTC first.
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return dict(id=row.id, title=row.title, organization=row.organization,
                scheduled_at=utc(row.scheduled_at), revision=row.revision,
                status='draft', created_at=utc(row.created_at), updated_at=utc(row.updated_at))
