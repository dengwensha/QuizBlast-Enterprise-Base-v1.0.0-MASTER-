"""Private event-draft API. No room or quiz side effects."""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import update
from app.schemas.events import EventCreate, EventUpdate
from app.services.event_store import serialize_event, describe_event_game


def create_events_router(session_factory, User, EventDraft, authenticate, game_features=None):
    router = APIRouter(prefix='/events', tags=['events'])

    def serialize(db, row):
        if game_features is None:
            return serialize_event(row)
        return describe_event_game(db, row, game_features['Selection'],
                                   game_features['EventSession'], game_features['builder'].Room)['event']

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    def owned(db, event_id, owner_id):
        row = db.query(EventDraft).filter_by(id=event_id.hex, owner_id=owner_id).first()
        if row is None:
            raise HTTPException(404, detail='event_not_found')
        return row

    @router.post('', status_code=201)
    def create_event(data: EventCreate, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = EventDraft(owner_id=owner_id, **data.model_dump())
            db.add(row)
            db.commit()
            db.refresh(row)
            return serialize(db, row)

    @router.get('')
    def list_events(limit: int = Query(20, ge=1, le=100),
                    offset: int = Query(0, ge=0, le=1000000), owner_id: int = Depends(owner)):
        with session_factory() as db:
            rows = db.query(EventDraft).filter_by(owner_id=owner_id).order_by(
                EventDraft.created_at.desc(), EventDraft.id.desc()
            ).offset(offset).limit(limit + 1).all()
            return dict(items=[serialize(db, row) for row in rows[:limit]],
                        has_more=len(rows) > limit)

    @router.get('/{event_id}')
    def get_event(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            return serialize(db, owned(db, event_id, owner_id))

    @router.patch('/{event_id}')
    def update_event(event_id: UUID, data: EventUpdate, owner_id: int = Depends(owner)):
        with session_factory() as db:
            owned(db, event_id, owner_id)
            values = data.model_dump(exclude_unset=True, exclude={'revision'})
            values.update(revision=EventDraft.revision + 1, updated_at=datetime.now(timezone.utc))
            result = db.execute(update(EventDraft).where(
                EventDraft.id == event_id.hex, EventDraft.owner_id == owner_id,
                EventDraft.revision == data.revision,
            ).values(**values))
            if result.rowcount != 1:
                raise HTTPException(409, detail='event_revision_conflict')
            db.commit()
            return serialize(db, owned(db, event_id, owner_id))

    if game_features is not None:
        from app.routes.event_games import create_event_game_router
        router.include_router(create_event_game_router(owner, session_factory, EventDraft, User, **game_features))
    return router
