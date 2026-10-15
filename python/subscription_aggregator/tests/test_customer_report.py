import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tests.common import HTTPTestCase
import subscription_server as server

REPORT = {'customer_id':'customer_A','report_date':'2026-10-15 00:23:50 -08:00',
          'active_subscriptions':['sub_1092aB','sub_1092aC'],'total_cost':15999,'currency':'usd'}

class TestCustomerReport(HTTPTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.file_patch = patch.object(server, 'REPORT_FILE', Path(self.tmp.name) / 'received_customer_report.json')
        self.file_patch.start()

    def tearDown(self):
        self.file_patch.stop()
        self.tmp.cleanup()
        super().tearDown()

    def post(self, data, content_type='application/json'):
        import http.client
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=3)
        try:
            body = data if isinstance(data, str) else json.dumps(data)
            conn.request('POST', '/api/v1/customer_report', body=body,
                         headers={'Content-Type': content_type})
            res = conn.getresponse()
            return res.status, json.loads(res.read())
        finally:
            conn.close()

    def test_success(self):
        status, body = self.post([REPORT])
        self.assertEqual((status, body['count']), (201, 1))
        self.assertEqual(json.loads(server.REPORT_FILE.read_text()), [REPORT])

    def test_multiple_reports(self):
        other = {**REPORT, 'customer_id':'customer_B'}
        status, body = self.post([REPORT, other])
        self.assertEqual((status, body['count']), (201, 2))
        self.assertEqual(json.loads(server.REPORT_FILE.read_text()), [REPORT, other])

    def test_appends_existing(self):
        self.post([REPORT])
        self.post([{**REPORT, 'customer_id':'customer_B'}])
        self.assertEqual(len(json.loads(server.REPORT_FILE.read_text())), 2)

    def test_invalid_json(self):
        status, _ = self.post('[{')
        self.assertEqual(status, 400)
        self.assertFalse(server.REPORT_FILE.exists())

    def test_invalid_report(self):
        for data in ({'reports':[REPORT]}, [{'customer_id':'A'}], [{**REPORT, 'total_cost':True}],
                     [{**REPORT, 'report_date':'bad'}], [{**REPORT, 'active_subscriptions':[1]}]):
            with self.subTest(data=data):
                status, _ = self.post(data)
                self.assertEqual(status, 400)
        self.assertFalse(server.REPORT_FILE.exists())

    def test_invalid_content_type(self):
        status, _ = self.post([REPORT], 'text/plain')
        self.assertEqual(status, 415)

    def test_corrupt_existing_file_preserved(self):
        server.REPORT_FILE.write_text('invalid')
        status, _ = self.post([REPORT])
        self.assertEqual(status, 500)
        self.assertEqual(server.REPORT_FILE.read_text(), 'invalid')

    def test_empty_array(self):
        status, body = self.post([])
        self.assertEqual((status, body['count']), (201, 0))
