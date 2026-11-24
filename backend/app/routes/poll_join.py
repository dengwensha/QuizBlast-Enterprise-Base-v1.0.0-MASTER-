"""Standalone Poll Studio session invitations and idempotent anonymous registration.

No quiz room, Event Studio session, vote or Display dependencies.
"""
from base64 import urlsafe_b64encode
from hashlib import sha256
from hmac import new as hmac_new, compare_digest
from secrets import token_urlsafe
from uuid import UUID
from datetime import timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError


class VoteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    option_index: int = Field(ge=0, strict=True)


class JoinRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    # Client generates and persists once before the first POST.
    join_key: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')


def create_poll_join_router(session_factory, User, PollDefinition, PollSession,
                            PollParticipant, PollVote, authenticate, secret_key,
                            join_limiter, max_new_joins_per_ip):
    router = APIRouter(tags=['polls'])

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    def get_invited_session(db, invite):
        if not invite or len(invite) != 43:
            raise HTTPException(404, detail='poll_invite_not_found')
        digest = sha256(invite.encode()).hexdigest()
        session = db.query(PollSession).filter_by(invite_digest=digest).first()
        if session is None or session.status != 'open':
            raise HTTPException(404, detail='poll_invite_not_found')
        definition = db.get(PollDefinition, session.poll_id)
        if definition is None:
            raise HTTPException(404, detail='poll_invite_not_found')
        return session, definition

    @router.post('/polls/{poll_id}/sessions', status_code=201)
    def create_session(poll_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            definition = db.query(PollDefinition).filter_by(
                id=poll_id.hex, owner_id=owner_id).first()
            if not definition:
                raise HTTPException(404, detail='poll_not_found')
            invite = token_urlsafe(32)
            display_key = token_urlsafe(32)
            session = PollSession(poll_id=definition.id,
                                  definition_revision=definition.revision,
                                  invite_digest=sha256(invite.encode()).hexdigest(),
                                  display_digest=sha256(display_key.encode()).hexdigest(),
                                  status='open')
            db.add(session)
            db.commit()
            db.refresh(session)
            return dict(session_id=session.id, invite=invite, display_key=display_key,
                        status=session.status, definition_revision=session.definition_revision)

    @router.get('/poll-invites/{invite}')
    def public_poll(invite: str):
        with session_factory() as db:
            session, definition = get_invited_session(db, invite)
            return dict(session_id=session.id, question=definition.question,
                        options=definition.options, status=session.status)

    @router.post('/poll-invites/{invite}/join')
    def join(invite: str, data: JoinRequest, request: Request):
        with session_factory() as db:
            session, definition = get_invited_session(db, invite)
            # Never trust a nickname as the unique participant identity.
            join_digest = sha256(data.join_key.encode()).hexdigest()
            message = (session.id + ':' + data.join_key).encode()
            participant_token = urlsafe_b64encode(
                hmac_new(secret_key.encode(), message, 'sha256').digest()
            ).decode().rstrip('=')
            token_digest = sha256(participant_token.encode()).hexdigest()
            existing = db.query(PollParticipant).filter_by(
                session_id=session.id, join_key_digest=join_digest).first()
            if existing is None:
                # Apply limits only to NEW identities. An existing browser may
                # retry the same key without minting a second identity or using
                # up another quota slot. Never trust spoofable X-Forwarded-For.
                client_ip = request.client.host if request.client else 'unknown'
                join_limiter.enforce(
                    f'poll-join:{client_ip}:{session.id}',
                    max_new_joins_per_ip,
                )
                participant = PollParticipant(
                    session_id=session.id, join_key_digest=join_digest,
                    token_digest=token_digest)
                db.add(participant)
                try:
                    db.commit()
                except IntegrityError:
                    # Another request with the same key may have committed first.
                    db.rollback()
                    existing = db.query(PollParticipant).filter_by(
                        session_id=session.id, join_key_digest=join_digest).first()
                    if existing is None:
                        raise
                else:
                    existing = participant
            if not compare_digest(existing.token_digest, token_digest):
                raise HTTPException(409, detail='poll_join_identity_conflict')
            return dict(participant_id=existing.id, session_id=session.id,
                        participant_token=participant_token)


    def participant_for_token(db, session_id, authorization):
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, detail='poll_participant_unauthorized')
        credential = authorization[7:]
        if len(credential) != 43:
            raise HTTPException(401, detail='poll_participant_unauthorized')
        digest = sha256(credential.encode()).hexdigest()
        participant = db.query(PollParticipant).filter_by(
            session_id=session_id, token_digest=digest).first()
        if participant is None:
            raise HTTPException(401, detail='poll_participant_unauthorized')
        return participant

    def vote_receipt(vote):
        accepted = vote.accepted_at
        if accepted is not None and accepted.tzinfo is None:
            accepted = accepted.replace(tzinfo=timezone.utc)
        return dict(vote_id=vote.id, session_id=vote.session_id,
                    option_index=vote.option_index, accepted_at=accepted)

    @router.get('/poll-sessions/{session_id}/me')
    def my_poll_state(session_id: UUID, authorization: str | None = Header(default=None)):
        with session_factory() as db:
            participant = participant_for_token(db, session_id.hex, authorization)
            vote = db.query(PollVote).filter_by(
                session_id=session_id.hex, participant_id=participant.id).first()
            session = db.get(PollSession, session_id.hex)
            return dict(participant_id=participant.id, session_id=session_id.hex,
                        status=session.status if session else 'unavailable',
                        vote=vote_receipt(vote) if vote else None)

    @router.post('/poll-sessions/{session_id}/votes')
    def submit_vote(session_id: UUID, data: VoteRequest,
                    authorization: str | None = Header(default=None)):
        with session_factory() as db:
            # Serializes vote-vote and vote-close transitions in PostgreSQL.
            session = db.query(PollSession).filter_by(
                id=session_id.hex).with_for_update().first()
            if session is None:
                raise HTTPException(404, detail='poll_session_not_found')
            participant = participant_for_token(db, session_id.hex, authorization)
            previous = db.query(PollVote).filter_by(
                session_id=session.id, participant_id=participant.id).first()
            if previous is not None:
                if previous.option_index != data.option_index:
                    raise HTTPException(409, detail='poll_vote_already_cast')
                return vote_receipt(previous)
            if session.status != 'open':
                raise HTTPException(409, detail='poll_session_closed')
            definition = db.get(PollDefinition, session.poll_id)
            if definition is None or not 0 <= data.option_index < len(definition.options):
                raise HTTPException(422, detail='poll_option_invalid')
            record = PollVote(session_id=session.id, participant_id=participant.id,
                              option_index=data.option_index)
            db.add(record)
            db.commit()
            db.refresh(record)
            return vote_receipt(record)

    @router.post('/poll-sessions/{session_id}/close')
    def close_session(session_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            session = db.query(PollSession).filter_by(
                id=session_id.hex).with_for_update().first()
            if session is None:
                raise HTTPException(404, detail='poll_session_not_found')
            definition = db.query(PollDefinition).filter_by(
                id=session.poll_id, owner_id=owner_id).first()
            if definition is None:
                raise HTTPException(404, detail='poll_session_not_found')
            if session.status != 'open':
                raise HTTPException(409, detail='poll_session_closed')
            session.status = 'closed'
            db.commit()
            return dict(session_id=session.id, status='closed')

    return router
