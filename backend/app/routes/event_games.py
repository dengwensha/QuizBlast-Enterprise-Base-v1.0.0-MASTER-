"""One event -> one authorized quiz -> one durable room identity."""
from base64 import b64decode
from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5
from hashlib import sha256
from secrets import compare_digest, token_urlsafe
from time import time
from fastapi import APIRouter, Depends, Header, HTTPException, Response, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import defer
from app.schemas.events import SlideCommand, EventRunCommand, EventAgendaUpdate, EventQuizSelect, EventSessionCreate
from app.services.event_pptx import pptx_to_pdf
from app.services.event_pdf import MAX_PDF_BYTES, render_pdf
from pypdfium2 import PdfiumError
from app.services.event_store import describe_event_game, describe_session, report_utc


def create_event_game_router(owner, session_factory, EventDraft, User,
                             Selection, EventSession, builder, initialize, Report, Retention, Agenda, Run, Deck, StepSession, StepReport):
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

    def identified_steps(event_id, steps):
        # Legacy agendas have at most one quiz. Give that quiz the same
        # event-scoped identity on every read until its next save.
        return [
            {**step, 'step_id': str(uuid5(UUID(event_id), 'legacy-quiz-step'))}
            if step['kind'] == 'quiz' and not step.get('step_id') else step
            for step in steps
        ]

    def requires_step_sessions(steps):
        quizzes = [step for step in steps if step['kind'] == 'quiz']
        return len(quizzes) > 1 or any(step.get('quiz_id') is not None for step in quizzes)

    def retention_row(db, event_id):
        record = db.get(Retention, event_id)
        if record is None:
            record = Retention(event_id=event_id)
            db.add(record)
        return record

    def agenda_state(db, row):
        agenda = db.get(Agenda, row.id)
        steps = identified_steps(row.id, agenda.steps) if agenda else []
        ids = {UUID(step['deck_id']).hex for step in steps if step.get('deck_id')}
        names = dict(db.query(Deck.id, Deck.name).filter(
            Deck.event_id == row.id, Deck.id.in_(ids)).all()) if ids else {}
        record = db.get(Retention, row.id)
        return dict(title=row.title, revision=row.revision,
                    retention=record.preference if record else None,
                    program_completed_at=report_utc(record.program_completed_at)
                    if record and record.program_completed_at else None,
                    steps=steps, deck_names=names)

    @router.delete('/{event_id}', status_code=204)
    def delete_event(event_id: UUID, revision: int, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            if (db.get(Run, row.id) is not None or db.get(EventSession, row.id) is not None or
                    db.query(StepSession.event_id).filter_by(event_id=row.id).first() is not None):
                raise HTTPException(409, detail='event_delete_started')
            if row.revision != revision:
                raise HTTPException(409, detail='event_revision_conflict')
            for model in (Retention, Deck, Agenda, Selection):
                db.query(model).filter_by(event_id=row.id).delete(synchronize_session=False)
            db.delete(row)
            db.commit()
        return Response(status_code=204)

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
            run = db.get(Run, row.id)
            if run and run.cursor < len(run.steps) and requires_step_sessions(run.steps):
                raise HTTPException(409, detail='event_program_running')
            prior_steps = identified_steps(row.id, agenda.steps) if agenda else []
            known_ids = {UUID(step['step_id']) for step in prior_steps if step.get('step_id')}
            if agenda is None:
                agenda = Agenda(event_id=row.id)
                db.add(agenda)
            steps = []
            seen_ids = set()
            quiz_ids = set()
            for step in data.steps:
                if step.step_id is not None:
                    if step.kind != 'quiz' or step.step_id not in known_ids or step.step_id in seen_ids:
                        raise HTTPException(422, detail='event_quiz_step_invalid')
                    seen_ids.add(step.step_id)
                if step.quiz_id is not None:
                    if step.kind != 'quiz':
                        raise HTTPException(422, detail='event_quiz_step_invalid')
                    quiz_ids.add(step.quiz_id)
                if step.slide_seconds is not None and (step.kind != 'presentation' or not step.deck_id):
                    raise HTTPException(422, detail='event_slide_interval_invalid')
                if step.deck_id:
                    deck = db.get(Deck, step.deck_id.hex)
                    if step.kind != 'presentation' or not deck or deck.event_id != row.id:
                        raise HTTPException(422, detail='event_deck_invalid')
                payload = step.model_dump(mode='json', exclude_none=True)
                if step.kind == 'quiz':
                    payload['step_id'] = str(step.step_id or uuid4())
                steps.append(payload)
            selections = {s['step_id']: s.get('quiz_id') for s in steps if 'step_id' in s}
            if any(selections.get(link.step_id) != link.quiz_id
                   for link in db.query(StepSession).filter_by(event_id=row.id)):
                raise HTTPException(409, detail='event_session_locked')
            if quiz_ids:
                email = db.get(User, owner_id).email
                for quiz_id in sorted(quiz_ids):
                    builder.lock_quiz(db, quiz_id, email, require_questions=True)
            if 'retention' in data.model_fields_set:
                retention_row(db, row.id).preference = data.retention
            # Track agenda membership, not live/editor activity. No cleanup here.
            previous = {UUID(s['deck_id']).hex for s in prior_steps if s.get('deck_id')}
            current = {UUID(s['deck_id']).hex for s in steps if s.get('deck_id')}
            for ids, since in ((previous - current, datetime.now(timezone.utc)), (current - previous, None)):
                if ids:
                    db.execute(update(Deck).where(Deck.event_id == row.id, Deck.id.in_(ids))
                               .values(agenda_unlinked_since=since))
            agenda.steps = steps
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
        is_pptx = (file.filename or '').lower().endswith('.pptx')
        try:
            data = file.file.read(MAX_PDF_BYTES + 1)
            pages = render_pdf(pptx_to_pdf(data) if is_pptx else data)
        except OSError:
            raise HTTPException(503, detail='event_converter_unavailable') from None
        except (ValueError, PdfiumError):
            raise HTTPException(422, detail='event_pptx_invalid' if is_pptx else 'event_pdf_invalid') from None
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            if db.query(Deck.id).filter_by(event_id=row.id).count() >= 12:
                raise HTTPException(409, detail='event_deck_limit')
            deck = Deck(event_id=row.id, name=(file.filename or 'Sunum.pdf')[:160], page_count=len(pages), pages=pages,
                        agenda_unlinked_since=datetime.now(timezone.utc))
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
        deck = query.first()
        step = run.steps[run.cursor]
        if deck and 'opened_at' in step:
            elapsed = max(0, time() - step['opened_at'])
            return deck, min(deck.page_count - 1, int(elapsed // step['slide_seconds']))
        return deck, int(run.view.split(':')[1])

    def live_quiz_link(db, run):
        step = run.steps[run.cursor]
        if step.get('quiz_id'):
            return db.get(StepSession, (run.event_id, step['step_id']))
        return db.get(EventSession, run.event_id)

    def live_state(run, db, public=False):
        deck, page = active_deck(db, run)
        quiz_display = None
        if run.view == 'step' and run.steps[run.cursor]['kind'] == 'quiz':
            link = live_quiz_link(db, run)
            room = db.get(builder.Room, link.pin) if link else None
            if room and room.identity and room.identity.instance_id == link.instance_id and room.phase != 'closed':
                quiz_display = dict(pin=link.pin, instance_id=link.instance_id)
        hidden = {'deck_id', 'quiz_id'} if public else {'deck_id'}
        remote_enabled = (not public and run.view.startswith('step:') and
                          bool(run.steps[run.cursor].get('remote_digest')))
        return dict(remote_enabled=remote_enabled, quiz_display=quiz_display, title=run.title,
                    steps=[{k: v for k, v in step.items() if k not in hidden and k not in {'opened_at', 'remote_digest'}} for step in run.steps],
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
                steps = identified_steps(row.id, agenda.steps)
                if requires_step_sessions(steps):
                    if db.get(EventSession, row.id):
                        raise HTTPException(409, detail='event_session_locked')
                    quiz_ids = {step.get('quiz_id') for step in steps if step['kind'] == 'quiz'}
                    if None in quiz_ids:
                        raise HTTPException(409, detail='event_step_quiz_required')
                    email = db.get(User, owner_id).email
                    for quiz_id in sorted(quiz_ids):
                        builder.lock_quiz(db, quiz_id, email, require_questions=True)
                run = Run(event_id=row.id, title=row.title, steps=steps,
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
                step = run.steps[run.cursor]
                if step.get('slide_seconds') and step.get('deck_id'):
                    # Replace the JSON list so SQLAlchemy persists the clock across restarts.
                    run.steps = [dict(item, opened_at=time()) if i == run.cursor else item
                                 for i, item in enumerate(run.steps)]
                run.view = 'step:0' if run.steps[run.cursor].get('deck_id') else 'step'
            elif data.action in {'previous_page', 'next_page'} and run.view.startswith('step:'):
                deck, page = active_deck(db, run)
                if run.steps[run.cursor].get('slide_seconds'):
                    raise HTTPException(409, detail='event_slide_automatic')
                page += 1 if data.action == 'next_page' else -1
                if not deck or not 0 <= page < deck.page_count:
                    raise HTTPException(409, detail='event_run_transition_invalid')
                run.view = f'step:{page}'
            elif data.action == 'complete' and run.view.startswith('step'):
                if run.steps[run.cursor]['kind'] == 'quiz':
                    link = live_quiz_link(db, run)
                    session = describe_session(db, link, builder.Room)
                    if run.steps[run.cursor].get('quiz_id'):
                        report = db.get(StepReport, link.instance_id) if link else None
                    else:
                        report = db.get(Report, row.id)
                    if not report and (not session or session['phase'] != 'completed'):
                        raise HTTPException(409, detail='event_quiz_not_completed')
                run.cursor += 1
                if run.cursor == len(run.steps):
                    retention_row(db, row.id).program_completed_at = datetime.now(timezone.utc)
                run.view = 'agenda'
            else:
                raise HTTPException(409, detail='event_run_transition_invalid')
            run.revision += 1
            result = dict(live=live_state(run, db), display_key=run.display_key)
            db.commit()
            return result

    def manual_slide(run):
        return (run and run.view.startswith('step:') and run.cursor < len(run.steps)
                and run.steps[run.cursor]['kind'] == 'presentation'
                and not run.steps[run.cursor].get('slide_seconds'))

    @router.post('/{event_id}/slide-remote')
    def enable_remote(event_id: UUID, data: EventSessionCreate, response: Response, owner_id: int = Depends(owner)):
        response.headers["Cache-Control"] = "no-store"
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            run = db.get(Run, row.id)
            if not manual_slide(run) or run.revision != data.revision:
                raise HTTPException(409, detail='event_run_transition_invalid')
            key = token_urlsafe(32)
            digest = sha256(key.encode()).hexdigest()
            run.steps = [dict(item, remote_digest=digest) if i == run.cursor else item
                         for i, item in enumerate(run.steps)]
            run.revision += 1
            result = dict(key=key, live=live_state(run, db), display_key=run.display_key)
            db.commit()
            return result

    def remote_state(event_id, authorization, data=None):
        key = authorization.removeprefix('Bearer ')
        missing = HTTPException(404, detail='slide_remote_inactive')
        if key == authorization or len(key) != 43:
            raise missing
        digest = sha256(key.encode()).hexdigest()
        with session_factory() as db:
            def authorized(run):
                return manual_slide(run) and compare_digest(
                    run.steps[run.cursor].get('remote_digest', ''), digest)
            run = db.get(Run, event_id.hex)
            if not authorized(run):
                raise missing
            if data is not None:
                row = db.get(EventDraft, event_id.hex)
                event(db, event_id, row.owner_id, lock=True)
                db.refresh(run)
                if not authorized(run):
                    raise missing
            deck, page = active_deck(db, run)
            if not deck:
                raise missing
            if data is not None:
                page += 1 if data.action == 'next_page' else -1
                if data.revision != run.revision or not 0 <= page < deck.page_count:
                    raise HTTPException(409, detail='event_revision_conflict')
                run.view = f'step:{page}'
                run.revision += 1
            result = dict(page=page, page_count=deck.page_count, revision=run.revision)
            if data is not None:
                db.commit()
            return result

    @router.get('/{event_id}/slide-remote/state')
    def read_remote(event_id: UUID, response: Response, authorization: str = Header(default='')):
        response.headers['Cache-Control'] = 'no-store'
        return remote_state(event_id, authorization)

    @router.put('/{event_id}/slide-remote/page')
    def move_remote(event_id: UUID, data: SlideCommand, authorization: str = Header(default='')):
        return remote_state(event_id, authorization, data)

    @router.get('/display/program/state')
    def get_display_live(response: Response, authorization: str = Header(default='')):
        key = authorization.removeprefix('Bearer ')
        with session_factory() as db:
            run = db.query(Run).filter_by(display_key=key).first() if key != authorization and len(key) == 43 else None
            if not run:
                raise HTTPException(404, detail='event_run_not_found')
            response.headers['Cache-Control'] = 'no-store'
            return live_state(run, db, public=True)

    @router.get('/display/program/page/{revision}')
    def display_page(revision: int, requested_page: int | None = None, authorization: str = Header(default='')):
        key = authorization.removeprefix('Bearer ')
        with session_factory() as db:
            run = db.query(Run).filter_by(display_key=key).first() if key != authorization and len(key) == 43 else None
            if run and run.revision == revision:
                deck, page = active_deck(db, run, include_pages=True)
                if deck and (requested_page is None or requested_page == page):
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
            agenda = db.get(Agenda, row.id)
            run = db.get(Run, row.id)
            result['step_quizzes_planned'] = bool(requires_step_sessions(
                run.steps if run else agenda.steps if agenda else []))
            result['quizzes'] = [dict(id=q.id, title=q.title,
                question_count=db.query(builder.Question.id).filter_by(quiz_id=q.id).count())
                for q in builder.eligible(db, email).order_by(builder.Quiz.id).all()]
            return result

    @router.get('/{event_id}/report')
    def get_report(event_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            return report_state(db.get(Report, row.id))

    def report_state(report):
        if report is None:
            raise HTTPException(404, detail='event_report_unavailable')
        expires = report_utc(report.expires_at)
        if datetime.now(timezone.utc) >= expires:
            raise HTTPException(410, detail='event_report_expired')
        return dict(event_title=report.event_title, quiz_title=report.quiz_title,
                    completed_at=report_utc(report.completed_at), expires_at=expires,
                    ranking=report.ranking)

    def step_session_state(db, link):
        return describe_session(db, link, builder.Room)

    @router.get('/{event_id}/steps/{step_id}/session')
    def get_step_session(event_id: UUID, step_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            return step_session_state(db, db.get(StepSession, (row.id, str(step_id))))

    @router.post('/{event_id}/steps/{step_id}/session')
    def create_step_session(event_id: UUID, step_id: UUID, data: EventSessionCreate,
                            owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id, lock=True)
            key = (row.id, str(step_id))
            email = db.get(User, owner_id).email
            run = db.get(Run, row.id)
            if run:
                if (run.view != 'step' or run.cursor >= len(run.steps) or
                        run.steps[run.cursor].get('step_id') != key[1] or
                        not run.steps[run.cursor].get('quiz_id')):
                    raise HTTPException(409, detail='event_quiz_step_inactive')
                steps = [run.steps[run.cursor]]
            else:
                agenda = db.get(Agenda, row.id)
                steps = agenda.steps if agenda else []
            link = db.get(StepSession, key)
            if link is None:
                if row.revision != data.revision:
                    raise HTTPException(409, detail='event_revision_conflict')
                if db.get(EventSession, row.id):
                    raise HTTPException(409, detail='event_session_locked')
                step = next((s for s in steps
                             if s.get('step_id') == key[1] and s['kind'] == 'quiz'), None)
                if step is None:
                    raise HTTPException(404, detail='event_quiz_step_invalid')
                if not step.get('quiz_id'):
                    raise HTTPException(409, detail='event_quiz_required')
                builder.lock_quiz(db, step['quiz_id'], email, require_questions=True)
                room = builder.stage(db, step['quiz_id'], email)
                link = StepSession(event_id=row.id, step_id=key[1], quiz_id=room.quiz_id,
                                   pin=room.pin, instance_id=room.identity.instance_id)
                db.add(link)
                row.revision += 1
                row.updated_at = datetime.now(timezone.utc)
            session = step_session_state(db, link)
            db.commit()
            if session['can_open'] and session['phase'] == 'lobby':
                initialize(session['pin'], session['quiz_id'], email, session['instance_id'])
            return session

    @router.get('/{event_id}/steps/{step_id}/report')
    def get_step_report(event_id: UUID, step_id: UUID, owner_id: int = Depends(owner)):
        with session_factory() as db:
            row = event(db, event_id, owner_id)
            link = db.get(StepSession, (row.id, str(step_id)))
            return report_state(db.get(StepReport, link.instance_id) if link else None)

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
            agenda = db.get(Agenda, row.id)
            run = db.get(Run, row.id)
            if requires_step_sessions(run.steps if run else agenda.steps if agenda else []):
                raise HTTPException(409, detail='event_step_sessions_unavailable')
            if db.query(StepSession.event_id).filter_by(event_id=row.id).first() is not None:
                raise HTTPException(409, detail='event_session_locked')
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
