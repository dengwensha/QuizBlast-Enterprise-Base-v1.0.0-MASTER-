"""POLL-01D-01 Excel preview: owner-only, bounded, no writes."""
from io import BytesIO
import re
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED
import json
import socket
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from openpyxl import Workbook
import uvicorn
import app.main as main


class PollExcelPreviewAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sock = socket.socket()
        cls.sock.bind(('127.0.0.1', 0))
        cls.address = f'http://127.0.0.1:{cls.sock.getsockname()[1]}'
        cls.server = uvicorn.Server(uvicorn.Config(main.app, log_level='critical', lifespan='off'))
        cls.thread = threading.Thread(target=lambda: cls.server.run(sockets=[cls.sock]), daemon=True)
        cls.thread.start()
        for _ in range(100):
            if cls.server.started:
                break
            time.sleep(.02)
        assert cls.server.started

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)
        cls.sock.close()

    def setUp(self):
        self.email = f'poll-import-{uuid4().hex}@test'
        self.token = main.create_access_token({'sub': self.email})
        with main.db_session() as db:
            db.add(main.User(email=self.email, password_hash='unused'))
            db.commit()

    def tearDown(self):
        with main.db_session() as db:
            user = db.query(main.User).filter_by(email=self.email).first()
            if user:
                # Imported definitions have no sessions in this acceptance module.
                db.query(main.PollImportBatch).filter_by(owner_id=user.id).delete()
                db.query(main.PollDefinition).filter_by(owner_id=user.id).delete()
                db.delete(user)
            db.commit()

    @staticmethod
    def workbook(rows):
        book = Workbook()
        sheet = book.active
        for row in rows:
            sheet.append(row)
        stream = BytesIO()
        book.save(stream)
        book.close()
        return stream.getvalue()

    def request(self, contents, filename='polls.xlsx', token=None, endpoint='preview'):
        boundary = 'poll-preview-test-boundary'
        body = (('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' +
                 filename + '"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode()
                + contents + ('\r\n--' + boundary + '--\r\n').encode())
        headers = { 'Content-Type': 'multipart/form-data; boundary=' + boundary }
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(self.address + '/polls/import/' + endpoint, method='POST',
                      headers=headers, data=body)
        try:
            response = urlopen(req, timeout=12)
        except HTTPError as exc:
            response = exc
        raw = response.read()
        return response.code, json.loads(raw) if raw else None

    def test_valid_preview_is_read_only(self):
        rows = [
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Which process?', 'CAD', 'CAM', None, None, None, None],
            ['Favorite alloy?', 'Steel', 'Aluminium', 'Titanium', None, None, None],
        ]
        status, data = self.request(self.workbook(rows), token=self.token)
        self.assertEqual(status, 200, data)
        self.assertTrue(data['valid'])
        self.assertTrue(data['can_commit'])
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['items'][0]['options'], ['CAD', 'CAM'])
        self.assertEqual(data['items'][1]['options'], ['Steel', 'Aluminium', 'Titanium'])
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollDefinition).filter(
                main.PollDefinition.owner_id == db.query(main.User.id).filter_by(
                    email=self.email).scalar()).count(), 0)

    def test_invalid_rows_report_excel_line_without_writes(self):
        rows = [
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Good question?', 'Yes', 'No'],
            ['Duplicate?', 'Yes', ' yes '],
            ['No option?', 'Only'],
            ['Formula?', '=1+1', 'No'],
        ]
        status, data = self.request(self.workbook(rows), token=self.token)
        self.assertEqual(status, 200, data)
        self.assertFalse(data['can_commit'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['error_count'], 3)
        self.assertEqual([error['row'] for error in data['errors']], [3, 4, 5])
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollDefinition).filter_by(
                owner_id=db.query(main.User.id).filter_by(email=self.email).scalar()).count(), 0)

    def test_reject_bad_type_oversize_header_and_no_auth(self):
        valid = self.workbook([
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Pick?', 'A', 'B'],
        ])
        self.assertEqual(self.request(valid)[0], 401)
        self.assertEqual(self.request(valid, token=self.token, filename='wrong.xls')[0], 422)
        self.assertEqual(self.request(b'not xlsx', token=self.token)[0], 422)
        self.assertEqual(self.request(b'x' * (1024 * 1024 + 1), token=self.token)[0], 413)
        wrong = self.workbook([['Question', 'A', 'B'], ['Pick?', 'A', 'B']])
        self.assertEqual(self.request(wrong, token=self.token)[0], 422)

    def test_commit_is_atomic_and_preview_does_not_write(self):
        base = [['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                 'Seçenek4', 'Seçenek5', 'Seçenek6']]
        good = self.workbook(base + [
            ['Preferred method?', 'CAD', 'CAM'],
            ['Preferred material?', 'Steel', 'Aluminium', 'Titanium'],
        ])
        status, preview = self.request(good, token=self.token)
        self.assertEqual(status, 200)
        self.assertTrue(preview['can_commit'])
        with main.db_session() as db:
            owner_id = db.query(main.User.id).filter_by(email=self.email).scalar()
            self.assertEqual(db.query(main.PollDefinition).filter_by(owner_id=owner_id).count(), 0)

        # The commit endpoint rejects a modified/invalid file, even after valid preview.
        changed = self.workbook(base + [
            ['Preferred method?', 'CAD', 'CAM'],
            ['Broken?', 'A', ' a '],
        ])
        status, invalid = self.request(changed, token=self.token, endpoint='commit')
        self.assertEqual(status, 422, invalid)
        self.assertEqual(invalid['detail']['code'], 'poll_import_validation_failed')
        self.assertEqual(invalid['detail']['errors'][0]['row'], 3)
        with main.db_session() as db:
            self.assertEqual(db.query(main.PollDefinition).filter_by(owner_id=owner_id).count(), 0)

        status, committed = self.request(good, token=self.token, endpoint='commit')
        self.assertEqual(status, 201, committed)
        self.assertEqual(committed['imported_count'], 2)
        self.assertEqual(len(set(committed['poll_ids'])), 2)
        with main.db_session() as db:
            records = db.query(main.PollDefinition).filter_by(owner_id=owner_id).all()
            self.assertEqual(len(records), 2)
            self.assertEqual({row.question for row in records},
                             {'Preferred method?', 'Preferred material?'})
            self.assertEqual(db.query(main.PollSession).filter(
                main.PollSession.poll_id.in_(committed['poll_ids'])).count(), 0)

    def test_commit_rejects_empty_unauthorized_and_unsafe_upload(self):
        header = [['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                   'Seçenek4', 'Seçenek5', 'Seçenek6']]
        empty = self.workbook(header)
        valid = self.workbook(header + [['Pick?', 'Yes', 'No']])
        self.assertEqual(self.request(valid, endpoint='commit')[0], 401)
        status, empty_result = self.request(empty, token=self.token, endpoint='commit')
        self.assertEqual(status, 422, empty_result)
        self.assertEqual(empty_result['detail']['code'], 'poll_import_validation_failed')
        self.assertEqual(self.request(valid, filename='poll.xls', token=self.token,
                                      endpoint='commit')[0], 422)
        self.assertEqual(self.request(b'invalid ZIP', token=self.token,
                                      endpoint='commit')[0], 422)
        with main.db_session() as db:
            owner_id = db.query(main.User.id).filter_by(email=self.email).scalar()
            self.assertEqual(db.query(main.PollDefinition).filter_by(owner_id=owner_id).count(), 0)

    def test_compressed_excel_bomb_is_rejected_for_preview_and_commit(self):
        normal = self.workbook([
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
             'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Question?', 'A', 'B'],
        ])
        # Keep it structurally XLSX while adding an XML ZIP member whose
        # decompressed size overwhelms the small compressed upload.
        stream = BytesIO()
        with ZipFile(BytesIO(normal)) as source, ZipFile(stream, 'w', ZIP_DEFLATED) as target:
            for member in source.infolist():
                target.writestr(member, source.read(member.filename))
            target.writestr('xl/oversized-sharedStrings.xml', b'x' * (21 * 1024 * 1024))
        payload = stream.getvalue()
        self.assertLess(len(payload), 1024 * 1024)
        for endpoint in ('preview', 'commit'):
            with self.subTest(endpoint=endpoint):
                status, result = self.request(payload, token=self.token, endpoint=endpoint)
                self.assertEqual(status, 422, result)
                self.assertEqual(result['detail'], 'poll_import_xlsx_resource_limit')
        with main.db_session() as db:
            owner = db.query(main.User.id).filter_by(email=self.email).scalar()
            self.assertEqual(db.query(main.PollDefinition).filter_by(owner_id=owner).count(), 0)

    def test_slow_excel_parse_does_not_block_the_http_event_loop(self):
        normal = self.workbook([
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
             'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Question?', 'A', 'B'],
        ])
        from app.routes import poll_excel
        original = poll_excel.load_workbook
        parsing_started = threading.Event()

        def deliberately_slow_parser(*args, **kwargs):
            parsing_started.set()
            time.sleep(.6)
            return original(*args, **kwargs)

        with patch.object(poll_excel, 'load_workbook', side_effect=deliberately_slow_parser):
            with ThreadPoolExecutor(max_workers=2) as executor:
                future = executor.submit(self.request, normal, token=self.token)
                self.assertTrue(parsing_started.wait(timeout=5))
                start = time.monotonic()
                with urlopen(self.address + '/', timeout=3) as response:
                    self.assertEqual(response.status, 200)
                elapsed = time.monotonic() - start
                self.assertLess(elapsed, .45, 'Excel parser blocked event-loop HTTP response')
                status, result = future.result(timeout=6)
                self.assertEqual(status, 200, result)

    @staticmethod
    def without_dimensions(content):
        # Simulate valid XLSX exports that omit worksheet <dimension> metadata.
        out = BytesIO()
        with ZipFile(BytesIO(content)) as source, ZipFile(out, 'w') as target:
            for member in source.infolist():
                data = source.read(member.filename)
                if member.filename == 'xl/worksheets/sheet1.xml':
                    data, count = re.subn(rb'<dimension\s+ref="[^"]+"\s*/>', b'', data)
                    assert count == 1
                target.writestr(member, data)
        return out.getvalue()

    def test_missing_worksheet_dimension_preview_and_commit(self):
        valid = self.workbook([
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Which process?', 'CAD', 'CAM'],
        ])
        content = self.without_dimensions(valid)
        status, preview = self.request(content, token=self.token)
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview['count'], 1)
        self.assertTrue(preview['can_commit'])
        status, saved = self.request(content, token=self.token, endpoint='commit')
        self.assertEqual(status, 201, saved)
        self.assertEqual(saved['imported_count'], 1)

    def test_numeric_option_years_and_rating_scale_are_text(self):
        rows = [
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Hangi yıl?', 2025, 2026.0, None, None, None, None],
            ['Puanınız?', 1, 2.5, 3, 4, 5, None],
        ]
        content = self.workbook(rows)
        status, preview = self.request(content, token=self.token)
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview['count'], 2)
        self.assertEqual(preview['items'][0]['options'], ['2025', '2026'])
        self.assertEqual(preview['items'][1]['options'], ['1', '2.5', '3', '4', '5'])
        status, saved = self.request(content, token=self.token, endpoint='commit')
        self.assertEqual(status, 201, saved)
        with main.db_session() as db:
            options = [db.get(main.PollDefinition, poll_id).options
                       for poll_id in saved['poll_ids']]
            self.assertEqual(options, [['2025', '2026'], ['1', '2.5', '3', '4', '5']])

    def test_formula_and_unsupported_cell_types_still_fail_closed(self):
        content = self.workbook([
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Valid?', 'Yes', 'No'],
            ['Formula?', '=1+1', 'No'],
            ['Boolean?', True, 'No'],
        ])
        status, preview = self.request(content, token=self.token)
        self.assertEqual(status, 200, preview)
        self.assertFalse(preview['can_commit'])
        self.assertEqual([row['row'] for row in preview['errors']], [3, 4])
        status, invalid = self.request(content, token=self.token, endpoint='commit')
        self.assertEqual(status, 422, invalid)
        with main.db_session() as db:
            owner_id = db.query(main.User.id).filter_by(email=self.email).scalar()
            self.assertEqual(db.query(main.PollDefinition).filter_by(owner_id=owner_id).count(), 0)

    def test_dimensionless_workbook_over_row_limit_rejected(self):
        rows = [['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                 'Seçenek4', 'Seçenek5', 'Seçenek6']]
        rows += [[f'Question {i}?', 'Yes', 'No'] for i in range(101)]
        content = self.without_dimensions(self.workbook(rows))
        self.assertEqual(self.request(content, token=self.token)[0], 422)
        self.assertEqual(self.request(content, token=self.token, endpoint='commit')[0], 422)

    def test_exact_file_retry_and_concurrent_commit_do_not_duplicate_polls(self):
        from concurrent.futures import ThreadPoolExecutor
        content = self.workbook([
            ['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3', 'Seçenek4', 'Seçenek5', 'Seçenek6'],
            ['Choice?', 'One', 'Two'],
            ['Another?', 'Yes', 'No'],
        ])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.request(
                content, token=self.token, endpoint='commit'), range(2)))
        self.assertEqual([status for status, _ in results], [201, 201], results)
        self.assertEqual(results[0][1]['poll_ids'], results[1][1]['poll_ids'])
        self.assertEqual(sorted([r['already_imported'] for _, r in results]), [False, True])
        status, retry = self.request(content, token=self.token, endpoint='commit')
        self.assertEqual(status, 201)
        self.assertTrue(retry['already_imported'])
        self.assertEqual(retry['poll_ids'], results[0][1]['poll_ids'])
        with main.db_session() as db:
            owner = db.query(main.User.id).filter_by(email=self.email).scalar()
            self.assertEqual(db.query(main.PollDefinition).filter_by(owner_id=owner).count(), 2)
            self.assertEqual(db.query(main.PollImportBatch).filter_by(owner_id=owner).count(), 1)

    def test_row_limit_fail_closed(self):
        rows = [['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                 'Seçenek4', 'Seçenek5', 'Seçenek6']]
        rows.extend([[f'Question {i}?', 'Yes', 'No'] for i in range(101)])
        self.assertEqual(self.request(self.workbook(rows), token=self.token)[0], 422)


if __name__ == '__main__':
    unittest.main()
