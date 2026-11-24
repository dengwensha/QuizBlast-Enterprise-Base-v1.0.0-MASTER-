"""Independent Poll Studio Excel preview and atomic, server-revalidated commit."""
from io import BytesIO
from hashlib import sha256
from math import isfinite
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.schemas.polls import PollCreate

MAX_BYTES = 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_MEMBER_BYTES = 10 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_ROWS = 100
EXPECTED_COLUMNS = ('Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                    'Seçenek4', 'Seçenek5', 'Seçenek6')


def create_poll_excel_router(session_factory, User, PollDefinition, PollImportBatch, authenticate):
    router = APIRouter(prefix='/polls/import', tags=['polls'])

    def owner(authorization: str | None = Header(default=None)):
        email = authenticate(authorization)
        with session_factory() as db:
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                raise HTTPException(401, detail='invalid_authentication_credentials')
            return user.id

    def validate_upload(file: UploadFile):
        filename = file.filename or ''
        if not filename.lower().endswith('.xlsx'):
            raise HTTPException(422, detail='poll_import_xlsx_required')
        # Read one byte beyond the boundary; never trust Content-Length.
        content = file.file.read(MAX_BYTES + 1)
        if not content or len(content) > MAX_BYTES:
            raise HTTPException(413, detail='poll_import_file_too_large')
        workbook = None
        try:
            # Inspect the ZIP central directory BEFORE openpyxl parses XML. The
            # compressed upload limit alone does not constrain sharedStrings.
            with ZipFile(BytesIO(content)) as archive:
                members = archive.infolist()
                total_uncompressed = 0
                for member in members:
                    if member.is_dir():
                        continue
                    total_uncompressed += member.file_size
                    if (total_uncompressed > MAX_UNCOMPRESSED_BYTES
                            or member.file_size > MAX_MEMBER_BYTES
                            or member.file_size > MAX_COMPRESSION_RATIO * max(1, member.compress_size)):
                        raise HTTPException(422, detail='poll_import_xlsx_resource_limit')
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
                # Questions must remain text; Excel may store rating/year options
                # as numbers. Accept only finite int/float option values, not
                # booleans, dates, formulas, or any other Excel cell type.
                question = filled[0]
                def option_text(cell):
                    if cell is None:
                        return ''
                    if isinstance(cell, str):
                        if cell.startswith('='):
                            raise ValueError('formula')
                        return cell.strip()
                    if isinstance(cell, bool):
                        raise ValueError('boolean')
                    if isinstance(cell, int):
                        return str(cell)
                    if isinstance(cell, float) and isfinite(cell):
                        return str(int(cell)) if cell.is_integer() else str(cell)
                    raise ValueError('unsupported cell')
                try:
                    if not isinstance(question, str) or question.startswith('='):
                        raise ValueError('invalid question')
                    options = [text for cell in filled[1:]
                               if (text := option_text(cell))]
                except ValueError:
                    errors.append(dict(row=excel_row, code='poll_import_cell_invalid'))
                    continue
                try:
                    poll = PollCreate.model_validate(
                        dict(question=question, options=options))
                except ValidationError:
                    errors.append(dict(row=excel_row, code='poll_import_poll_invalid'))
                    continue
                items.append(dict(row=excel_row, question=poll.question,
                                  options=poll.options))
            # Read-only worksheets can lack <dimension>; max_row can be None
            # or contain unreliable producer metadata. Count actual iterated rows.
            if overflow:
                raise HTTPException(422, detail='poll_import_row_limit')
            return dict(valid=not errors, count=len(items), error_count=len(errors),
                        items=items, errors=errors, can_commit=bool(items) and not errors,
                        _file_digest=sha256(content).hexdigest())
        except (BadZipFile, InvalidFileException, ValueError, OSError, EOFError):
            raise HTTPException(422, detail='poll_import_xlsx_invalid')
        finally:
            if workbook is not None:
                workbook.close()

    @router.post('/preview')
    def preview(file: UploadFile = File(...), owner_id: int = Depends(owner)):
        # Preview is always read-only, including when some rows are invalid.
        parsed = validate_upload(file)
        parsed.pop('_file_digest', None)
        return parsed

    @router.post('/commit', status_code=201)
    def commit(file: UploadFile = File(...), owner_id: int = Depends(owner)):
        # Never trust preview JSON supplied by a browser: parse and validate the
        # uploaded bytes again before any insert, then commit exactly once.
        parsed = validate_upload(file)
        if not parsed['can_commit']:
            raise HTTPException(422, detail=dict(
                code='poll_import_validation_failed',
                count=parsed['count'],
                errors=parsed['errors']))
        digest = parsed['_file_digest']
        with session_factory() as db:
            existing = db.query(PollImportBatch).filter_by(
                owner_id=owner_id, file_sha256=digest).first()
            if existing is not None:
                return dict(imported_count=len(existing.poll_ids),
                            poll_ids=existing.poll_ids, already_imported=True)
            records = [PollDefinition(owner_id=owner_id, question=item['question'],
                                      options=item['options'])
                       for item in parsed['items']]
            try:
                db.add_all(records)
                db.flush()
                ids = [record.id for record in records]
                db.add(PollImportBatch(owner_id=owner_id, file_sha256=digest,
                                       poll_ids=ids))
                db.commit()
            except IntegrityError:
                # Concurrent identical commits: unique(owner_id,file_sha256)
                # permits only one batch. Roll back all losing poll rows.
                db.rollback()
                prior = db.query(PollImportBatch).filter_by(
                    owner_id=owner_id, file_sha256=digest).first()
                if prior is None:
                    raise
                return dict(imported_count=len(prior.poll_ids),
                            poll_ids=prior.poll_ids, already_imported=True)
            except Exception:
                db.rollback()
                raise
            return dict(imported_count=len(ids), poll_ids=ids, already_imported=False)

    return router
