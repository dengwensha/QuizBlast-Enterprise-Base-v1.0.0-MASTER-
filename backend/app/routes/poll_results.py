"""Owner-scoped aggregate of accepted votes; no participant credentials or raw ballots."""
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

    @router.get('/poll-sessions/{session_id}/results')
    def results(session_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            # An owner must be authorized before aggregate counts are disclosed.
            # PostgreSQL FOR SHARE blocks concurrent vote/close row updates during
            # the count, yielding a consistent accepted-ballot snapshot.
            session = db.query(PollSession).filter_by(
                id=session_id.hex).with_for_update(read=True).first()
            if session is None:
                raise HTTPException(404, detail='poll_session_not_found')
            definition = db.query(PollDefinition).filter_by(
                id=session.poll_id, owner_id=owner_id).first()
            if definition is None:
                raise HTTPException(404, detail='poll_session_not_found')

            option_counts = dict(
                db.query(PollVote.option_index, func.count(PollVote.id))
                .filter(PollVote.session_id == session.id)
                .group_by(PollVote.option_index).all()
            )
            registered = db.query(func.count(PollParticipant.id)).filter(
                PollParticipant.session_id == session.id).scalar() or 0
            total = sum(option_counts.values())
            # Never use external attendee counts as the denominator.
            options = [
                dict(index=index, label=label, votes=option_counts.get(index, 0),
                     percent=round(option_counts.get(index, 0) * 100 / total, 2)
                     if total else 0.0)
                for index, label in enumerate(definition.options)
            ]
            return dict(session_id=session.id, status=session.status,
                        definition_revision=session.definition_revision,
                        question=definition.question, total_votes=total,
                        registered_participants=registered,
                        response_rate_percent=round(total * 100 / registered, 2)
                        if registered else 0.0,
                        options=options)

    return router
