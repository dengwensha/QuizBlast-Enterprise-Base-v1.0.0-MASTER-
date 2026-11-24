"""Owner-scoped durable identity for an already committed Excel import."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint


def register_poll_import_model(base):
    class PollImportBatch(base):
        __tablename__ = 'poll_import_batches'
        __table_args__ = (
            UniqueConstraint('owner_id', 'file_sha256', name='uq_poll_import_owner_file'),
        )
        id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)
        owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
        file_sha256 = Column(String(64), nullable=False)
        poll_ids = Column(JSON, nullable=False)
        created_at = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    return PollImportBatch
