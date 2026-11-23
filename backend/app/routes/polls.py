"""Owner-only standalone poll definitions; no event, quiz or voting endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from app.schemas.polls import PollCreate
from app.services.poll_store import serialize_poll


def create_polls_router(session_factory, User, PollDefinition, authenticate):
    router = APIRouter(prefix='/polls', tags=['polls'])

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    @router.post('', status_code=201)
    def create_poll(data: PollCreate, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = PollDefinition(owner_id=owner_id, question=data.question,
                                 options=data.options)
            db.add(row)
            db.commit()
            db.refresh(row)
            return serialize_poll(row)

    @router.get('')
    def list_polls(limit: int = Query(20, ge=1, le=100),
                   offset: int = Query(0, ge=0, le=1000000),
                   owner_id: int = Depends(owner)):
        with session_factory() as db:
            rows = db.query(PollDefinition).filter_by(owner_id=owner_id).order_by(
                PollDefinition.created_at.desc(), PollDefinition.id.desc()
            ).offset(offset).limit(limit + 1).all()
            return dict(items=[serialize_poll(row) for row in rows[:limit]],
                        has_more=len(rows) > limit)

    @router.get('/{poll_id}')
    def get_poll(poll_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = db.query(PollDefinition).filter_by(
                id=poll_id.hex, owner_id=owner_id).first()
            if not row:
                raise HTTPException(404, detail='poll_not_found')
            return serialize_poll(row)

    return router
