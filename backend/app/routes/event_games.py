"""One event -> one authorized quiz -> one durable room identity."""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from app.schemas.events import EventAgendaUpdate, EventQuizSelect, EventSessionCreate
from app.services.event_store import describe_event_game, report_utc


def create_event_game_router(owner, session_factory, EventDraft, User,
                             Selection, EventSession, builder, initialize, Report, Agenda):
    router = APIRouter()

    def event(db, event_id, owner_id, lock=False):
        if lock:
            # UPDATE also serializes SQLite writers; PostgreSQL locks this row.
            found = db.execute(update(EventDraft).where(
                EventDraft.id == event_id.hex, EventDraft.owner_id == owner_id
            ).values(revision=EventDraft.revision))
            if found.rowcount != 1:
                raise HTTPException(404, detail='event_not_found')
        row = db.query(EventDraft).filter_by(id=event_id.hex, owner_id=owner_id).first()
        if row is None:
            raise HTTPException(404, detail='event_not_found')
        return row

    def state(db, row):
        return describe_event_game(db, row, Selection, EventSession, builder.Room)

    def agenda_state(db, row):
        agenda = db.get(Agenda, row.id)
        return dict(title=row.title, revision=row.revision,
                    steps=agenda.steps if agenda else [])

    @router.get('/{event_id}/agenda')
    def get_agenda(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            return agenda_state(db, event(db, event_id, owner_id))

    @router.put('/{event_id}/agenda')
    def save_agenda(event_id: UUID, data: EventAgendaUpdate, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            if row.revision != data.revision:
                raise HTTPException(409, detail='event_revision_conflict')
            agenda = db.get(Agenda, row.id)
            if agenda is None:
                agenda = Agenda(event_id=row.id)
                db.add(agenda)
            agenda.steps = [step.model_dump() for step in data.steps]
            row.revision += 1
            row.updated_at = datetime.now(timezone.utc)
            db.flush()
            result = agenda_state(db, row)
            db.commit()
            return result

    @router.post('/{event_id}/copy', status_code=201)
    def copy_event(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            source = event(db, event_id, owner_id)
            suffix = ' (Kopya)'
            clone = EventDraft(owner_id=owner_id,
                               title=source.title[:160 - len(suffix)].rstrip() + suffix,
                               organization=source.organization)
            db.add(clone)
            db.flush()
            selection = db.get(Selection, source.id)
            if selection is not None:
                email = db.get(User, owner_id).email
                try:
                    builder.lock_quiz(db, selection.quiz_id, email, require_questions=True)
                except HTTPException as exc:
                    if exc.detail not in {'quiz_not_found', 'no_questions'}:
                        raise
                else:
                    db.add(Selection(event_id=clone.id, quiz_id=selection.quiz_id))
            db.commit()
            return state(db, clone)

    @router.get('/{event_id}/game')
    def get_game(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            email = db.get(User, owner_id).email
            result = state(db, row)
            result['quizzes'] = [dict(id=q.id, title=q.title,
                question_count=db.query(builder.Question.id).filter_by(quiz_id=q.id).count())
                for q in builder.eligible(db, email).order_by(builder.Quiz.id).all()]
            return result

    @router.get('/{event_id}/report')
    def get_report(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            report = db.get(Report, row.id)
            if report is None:
                raise HTTPException(404, detail='event_report_unavailable')
            expires = report_utc(report.expires_at)
            if datetime.now(timezone.utc) >= expires:
                raise HTTPException(410, detail='event_report_expired')
            return dict(event_title=report.event_title, quiz_title=report.quiz_title,
                        completed_at=report_utc(report.completed_at), expires_at=expires,
                        ranking=report.ranking)

    @router.put('/{event_id}/quiz')
    def select_quiz(event_id: UUID, data: EventQuizSelect, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            if db.get(EventSession, row.id):
                raise HTTPException(409, detail='event_session_locked')
            if row.revision != data.revision:
                raise HTTPException(409, detail='event_revision_conflict')
            email = db.get(User, owner_id).email
            builder.lock_quiz(db, data.quiz_id, email, require_questions=True)
            selected = db.get(Selection, row.id)
            if selected is None:
                db.add(Selection(event_id=row.id, quiz_id=data.quiz_id))
            else:
                selected.quiz_id = data.quiz_id
            row.revision += 1
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            return state(db, row)

    @router.post('/{event_id}/session')
    def create_session(event_id: UUID, data: EventSessionCreate, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            existing = db.get(EventSession, row.id)
            if existing:
                result = state(db, row)
                db.commit()
                if result['session']['can_open'] and result['session']['phase'] == 'lobby':
                    initialize(existing.pin, existing.quiz_id, db.get(User, owner_id).email, existing.instance_id)
                return result
            if row.revision != data.revision:
                raise HTTPException(409, detail='event_revision_conflict')
            selected = db.get(Selection, row.id)
            if selected is None:
                raise HTTPException(409, detail='event_quiz_required')
            email = db.get(User, owner_id).email
            builder.lock_quiz(db, selected.quiz_id, email, require_questions=True)
            room = builder.stage(db, selected.quiz_id, email)
            db.add(EventSession(event_id=row.id, quiz_id=selected.quiz_id,
                                pin=room.pin, instance_id=room.identity.instance_id))
            row.revision += 1
            row.updated_at = datetime.now(timezone.utc)
            # Room, selection and durable event link share this one commit.
            db.commit()
            initialize(room.pin, room.quiz_id, email, room.identity.instance_id)
            return state(db, row)

    return router
