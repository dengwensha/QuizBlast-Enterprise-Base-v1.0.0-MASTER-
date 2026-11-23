"""Scoped owner and read-only display aggregates from persisted accepted votes."""
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func


def create_poll_results_router(session_factory, User, PollDefinition,
                               PollSession, PollParticipant, PollVote, authenticate):
    router = APIRouter(tags=['polls'])

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    def aggregate(db, session, definition):
        counts = dict(
            db.query(PollVote.option_index, func.count(PollVote.id))
            .filter(PollVote.session_id == session.id)
            .group_by(PollVote.option_index).all()
        )
        registered = db.query(func.count(PollParticipant.id)).filter(
            PollParticipant.session_id == session.id).scalar() or 0
        total = sum(counts.values())
        options = [
            dict(index=index, label=label, votes=counts.get(index, 0),
                 percent=round(counts.get(index, 0) * 100 / total, 2) if total else 0.0)
            for index, label in enumerate(definition.options)
        ]
        return dict(session_id=session.id, status=session.status,
                    definition_revision=session.definition_revision,
                    question=definition.question, total_votes=total,
                    registered_participants=registered,
                    response_rate_percent=round(total * 100 / registered, 2)
                    if registered else 0.0, options=options)

    @router.get('/poll-sessions/{session_id}/results')
    def results(session_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            session = db.query(PollSession).filter_by(
                id=session_id.hex).with_for_update(read=True).first()
            if session is None:
                raise HTTPException(404, detail='poll_session_not_found')
            definition = db.query(PollDefinition).filter_by(
                id=session.poll_id, owner_id=owner_id).first()
            if definition is None:
                raise HTTPException(404, detail='poll_session_not_found')
            return aggregate(db, session, definition)

    @router.get('/poll-sessions/{session_id}/display-results')
    def display_results(session_id: UUID, authorization: str | None = Header(default=None)):
        # Display bearer credential is never a participant, invite or Host token.
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, detail='poll_display_unauthorized')
        key = authorization[7:]
        if len(key) != 43 or not all(char.isalnum() or char in '-_' for char in key):
            raise HTTPException(401, detail='poll_display_unauthorized')
        digest = sha256(key.encode()).hexdigest()
        with session_factory() as db:
            session = db.query(PollSession).filter_by(
                id=session_id.hex).with_for_update(read=True).first()
            if session is None or not session.display_digest or not compare_digest(
                    session.display_digest, digest):
                raise HTTPException(404, detail='poll_display_not_found')
            definition = db.get(PollDefinition, session.poll_id)
            if definition is None:
                raise HTTPException(404, detail='poll_display_not_found')
            return aggregate(db, session, definition)

    return router
