"""Independent Poll Studio Excel preview and atomic, server-revalidated commit."""
from io import BytesIO
from zipfile import BadZipFile

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import ValidationError

from app.schemas.polls import PollCreate

MAX_BYTES = 1024 * 1024
MAX_ROWS = 100
EXPECTED_COLUMNS = ('Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                    'Seçenek4', 'Seçenek5', 'Seçenek6')


def create_poll_excel_router(session_factory, User, PollDefinition, authenticate):
    router = APIRouter(prefix='/polls/import', tags=['polls'])

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    async def validate_upload(file: UploadFile):
        filename = file.filename or ''
        if not filename.lower().endswith('.xlsx'):
            raise HTTPException(422, detail='poll_import_xlsx_required')
        # Read one byte beyond the boundary; never trust Content-Length.
        content = await file.read(MAX_BYTES + 1)
        if not content or len(content) > MAX_BYTES:
            raise HTTPException(413, detail='poll_import_file_too_large')
        workbook = None
        try:
            # Formula expressions are untrusted: data_only=False permits rejection.
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=False,
                                     keep_links=False)
            sheet = workbook.active
            values = sheet.iter_rows(min_row=1, max_row=MAX_ROWS + 2, values_only=True)
            header = next(values, None)
            if header is None:
                raise HTTPException(422, detail='poll_import_header_invalid')
            provided = tuple(str(value).strip() if value is not None else ''
                             for value in header)
            # Exact columns keep Excel ordering and option position unambiguous.
            if provided[:7] != EXPECTED_COLUMNS or any(provided[7:]):
                raise HTTPException(422, detail='poll_import_header_invalid')

            items, errors = [], []
            overflow = False
            for excel_row, cells in enumerate(values, start=2):
                filled = list(cells[:7])
                if not any(cell is not None and str(cell).strip() for cell in filled):
                    continue
                if excel_row > MAX_ROWS + 1:
                    overflow = True
                    break
                if any(not isinstance(cell, str) or cell.startswith('=')
                       for cell in filled if cell is not None and str(cell).strip()):
                    errors.append(dict(row=excel_row, code='poll_import_cell_invalid'))
                    continue
                question = filled[0] or ''
                options = [value for value in filled[1:] if value is not None and value.strip()]
                try:
                    poll = PollCreate.model_validate(
                        dict(question=question, options=options))
                except ValidationError:
                    errors.append(dict(row=excel_row, code='poll_import_poll_invalid'))
                    continue
                items.append(dict(row=excel_row, question=poll.question,
                                  options=poll.options))
            if overflow or sheet.max_row > MAX_ROWS + 1:
                raise HTTPException(422, detail='poll_import_row_limit')
            return dict(valid=not errors, count=len(items), error_count=len(errors),
                        items=items, errors=errors, can_commit=bool(items) and not errors)
        except (BadZipFile, InvalidFileException, ValueError, OSError, EOFError):
            raise HTTPException(422, detail='poll_import_xlsx_invalid')
        finally:
            if workbook is not None:
                workbook.close()

    @router.post('/preview')
    async def preview(file: UploadFile = File(...), owner_id: int = Depends(owner)):
        # Preview is always read-only, including when some rows are invalid.
        return await validate_upload(file)

    @router.post('/commit', status_code=201)
    async def commit(file: UploadFile = File(...), owner_id: int = Depends(owner)):
        # Never trust preview JSON supplied by a browser: parse and validate the
        # uploaded bytes again before any insert, then commit exactly once.
        parsed = await validate_upload(file)
        if not parsed['can_commit']:
            raise HTTPException(422, detail=dict(
                code='poll_import_validation_failed',
                count=parsed['count'],
                errors=parsed['errors']))
        with session_factory() as db:
            records = [PollDefinition(owner_id=owner_id, question=item['question'],
                                      options=item['options'])
                       for item in parsed['items']]
            try:
                db.add_all(records)
                db.commit()
                for record in records:
                    db.refresh(record)
            except Exception:
                db.rollback()
                raise
            return dict(imported_count=len(records), poll_ids=[record.id for record in records])

    return router
