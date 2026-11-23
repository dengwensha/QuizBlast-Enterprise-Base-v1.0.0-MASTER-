"""Standalone Poll Studio session invitations and idempotent anonymous registration.

No quiz room, Event Studio session, vote or Display dependencies.
"""
from base64 import urlsafe_b64encode
from hashlib import sha256
from hmac import new as hmac_new, compare_digest
from secrets import token_urlsafe
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError


def create_poll_join_router(session_factory, User, PollDefinition, PollSession,
                            PollParticipant, authenticate, secret_key):
    router = APIRouter(tags=['polls'])

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    class JoinRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')
        # Client must generate once using a cryptographically secure RNG and persist
        # before the first POST; the server derives a scoped credential from it.
        join_key: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')

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
            session = PollSession(poll_id=definition.id,
                                  definition_revision=definition.revision,
                                  invite_digest=sha256(invite.encode()).hexdigest(),
                                  status='open')
            db.add(session)
            db.commit()
            db.refresh(session)
            return dict(session_id=session.id, invite=invite,
                        status=session.status, definition_revision=session.definition_revision)

    @router.get('/poll-invites/{invite}')
    def public_poll(invite: str):
        with session_factory() as db:
            session, definition = get_invited_session(db, invite)
            return dict(session_id=session.id, question=definition.question,
                        options=definition.options, status=session.status)

    @router.post('/poll-invites/{invite}/join')
    def join(invite: str, data: JoinRequest):
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

    return router
