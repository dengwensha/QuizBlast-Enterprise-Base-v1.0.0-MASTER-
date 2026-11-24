"""POLL-01D-01 Excel preview: owner-only, bounded, no writes."""
from io import BytesIO
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

    def test_row_limit_fail_closed(self):
        rows = [['Soru', 'Seçenek1', 'Seçenek2', 'Seçenek3',
                 'Seçenek4', 'Seçenek5', 'Seçenek6']]
        rows.extend([[f'Question {i}?', 'Yes', 'No'] for i in range(101)])
        self.assertEqual(self.request(self.workbook(rows), token=self.token)[0], 422)


if __name__ == '__main__':
    unittest.main()
