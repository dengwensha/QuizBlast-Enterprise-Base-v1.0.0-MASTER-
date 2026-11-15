"""One event -> one authorized quiz -> one durable room identity."""
from base64 import b64decode
from datetime import datetime, timezone
from uuid import UUID
from secrets import token_urlsafe
from fastapi import APIRouter, Depends, Header, HTTPException, Response, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import defer
from app.schemas.events import EventRunCommand, EventAgendaUpdate, EventQuizSelect, EventSessionCreate
from app.services.event_pdf import MAX_PDF_BYTES, render_pdf
from pypdfium2 import PdfiumError
from app.services.event_store import describe_event_game, report_utc


def create_event_game_router(owner, session_factory, EventDraft, User,
                             Selection, EventSession, builder, initialize, Report, Agenda, Run, Deck):
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
            for step in data.steps:
                if step.deck_id:
                    deck = db.get(Deck, step.deck_id.hex)
                    if step.kind != 'presentation' or not deck or deck.event_id != row.id:
                        raise HTTPException(422, detail='event_deck_invalid')
            agenda.steps = [step.model_dump(mode='json', exclude_none=True) for step in data.steps]
            row.revision += 1
            row.updated_at = datetime.now(timezone.utc)
            db.flush()
            result = agenda_state(db, row)
            db.commit()
            return result

    @router.post('/{event_id}/decks', status_code=201)
    def upload_deck(event_id: UUID, file: UploadFile, owner_id: int = Depends(owner)):
        with session_factory() as db:
            event(db, event_id, owner_id)
        try:
            pages = render_pdf(file.file.read(MAX_PDF_BYTES + 1))
        except (ValueError, PdfiumError):
            raise HTTPException(422, detail='event_pdf_invalid') from None
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            if db.query(Deck.id).filter_by(event_id=row.id).count() >= 12:
                raise HTTPException(409, detail='event_deck_limit')
            deck = Deck(event_id=row.id, name=(file.filename or 'Sunum.pdf')[:160], page_count=len(pages), pages=pages)
            db.add(deck)
            db.flush()
            result = dict(id=deck.id, name=deck.name, page_count=len(pages))
            db.commit()
            return result

    @router.get('/{event_id}/decks/{deck_id}/{page}')
    def preview_deck(event_id: UUID, deck_id: UUID, page: int, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            deck = db.get(Deck, deck_id.hex)
            if not deck or deck.event_id != row.id or not 0 <= page < len(deck.pages):
                raise HTTPException(404, detail='event_deck_not_found')
            return Response(b64decode(deck.pages[page]), media_type='image/png',
                            headers={'Cache-Control': 'no-store', 'X-Page-Count': str(len(deck.pages))})

    def active_deck(db, run, include_pages=False):
        if not run.view.startswith('step:'):
            return None, 0
        deck_id = run.steps[run.cursor]['deck_id']
        query = db.query(Deck).filter_by(id=UUID(deck_id).hex)
        if not include_pages:
            query = query.options(defer(Deck.pages))
        return query.first(), int(run.view.split(':')[1])

    def live_state(run, db):
        deck, page = active_deck(db, run)
        return dict(title=run.title, steps=[{k: v for k, v in step.items() if k != 'deck_id'} for step in run.steps],
                    cursor=run.cursor, view='step' if run.view.startswith('step') else run.view,
                    revision=run.revision, page=page, page_count=deck.page_count if deck else 0)

    @router.get('/{event_id}/live')
    def get_live(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            run = db.get(Run, row.id)
            return dict(live=live_state(run, db), display_key=run.display_key) if run else None

    @router.post('/{event_id}/live')
    def start_live(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            run = db.get(Run, row.id)
            if run is None:
                agenda = db.get(Agenda, row.id)
                if not agenda or not agenda.steps:
                    raise HTTPException(409, detail='event_agenda_required')
                run = Run(event_id=row.id, title=row.title, steps=agenda.steps,
                          display_key=token_urlsafe(32))
                db.add(run)
                db.flush()
            result = dict(live=live_state(run, db), display_key=run.display_key)
            db.commit()
            return result

    @router.put('/{event_id}/live')
    def advance_live(event_id: UUID, data: EventRunCommand, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            run = db.get(Run, row.id)
            if not run:
                raise HTTPException(404, detail='event_run_not_found')
            if run.revision != data.revision:
                raise HTTPException(409, detail='event_revision_conflict')
            if data.action == 'open' and run.view == 'agenda' and run.cursor < len(run.steps):
                run.view = 'step:0' if run.steps[run.cursor].get('deck_id') else 'step'
            elif data.action in {'previous_page', 'next_page'} and run.view.startswith('step:'):
                deck, page = active_deck(db, run)
                page += 1 if data.action == 'next_page' else -1
                if not deck or not 0 <= page < deck.page_count:
                    raise HTTPException(409, detail='event_run_transition_invalid')
                run.view = f'step:{page}'
            elif data.action == 'complete' and run.view.startswith('step'):
                if run.steps[run.cursor]['kind'] == 'quiz':
                    session = state(db, row)['session']
                    report = db.get(Report, row.id)
                    if not report and (not session or session['phase'] != 'completed'):
                        raise HTTPException(409, detail='event_quiz_not_completed')
                run.cursor += 1
                run.view = 'agenda'
            else:
                raise HTTPException(409, detail='event_run_transition_invalid')
            run.revision += 1
            result = dict(live=live_state(run, db), display_key=run.display_key)
            db.commit()
            return result

    @router.get('/display/program/state')
    def get_display_live(response: Response, authorization: str = Header(default='')):
        key = authorization.removeprefix('Bearer ')
        with session_factory() as db:
            run = db.query(Run).filter_by(display_key=key).first() if key != authorization and len(key) == 43 else None
            if not run:
                raise HTTPException(404, detail='event_run_not_found')
            response.headers['Cache-Control'] = 'no-store'
            return live_state(run, db)

    @router.get('/display/program/page/{revision}')
    def display_page(revision: int, authorization: str = Header(default='')):
        key = authorization.removeprefix('Bearer ')
        with session_factory() as db:
            run = db.query(Run).filter_by(display_key=key).first() if key != authorization and len(key) == 43 else None
            if run and run.revision == revision:
                deck, page = active_deck(db, run, include_pages=True)
                if deck:
                    return Response(b64decode(deck.pages[page]), media_type='image/png',
                                    headers={'Cache-Control': 'no-store'})
            raise HTTPException(404, detail='event_deck_not_found')

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
