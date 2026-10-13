import http.client
import json
import threading
import unittest
from http.server import HTTPServer
from unittest.mock import patch

import subscription_server as server

FIXTURES = [dict(id=f'sub_{i:03d}', merchant_id=f'merch_{i}', amount_cents=i*1000,
                 currency='usd', status='active', metadata={'plan_tier': 'pro'}) for i in range(1, 6)]

class HTTPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(('127.0.0.1', 0), server.SubscriptionHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=3)
        cls.httpd.server_close()

    def setUp(self):
        self.original_data = server.SUBSCRIPTIONS
        self.original_index = server.INDEX_BY_ID
        server.SUBSCRIPTIONS = [dict(item) for item in FIXTURES]
        server.INDEX_BY_ID = {item['id']: i for i, item in enumerate(server.SUBSCRIPTIONS)}
        server.SubscriptionHandler.last_request_time = float('-inf')
        self.now = 100.0
        self.clock = patch.object(server.time, 'monotonic', side_effect=lambda: self.now)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        server.SUBSCRIPTIONS = self.original_data
        server.INDEX_BY_ID = self.original_index
        server.SubscriptionHandler.last_request_time = float('-inf')

    def request(self, path='/api/v1/subscriptions', method='GET'):
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=3)
        try:
            conn.request(method, path)
            response = conn.getresponse()
            status = response.status
            headers = dict(response.getheaders())
            body = json.loads(response.read())
            return status, body, headers
        finally:
            conn.close()

    def assert_ids(self, path, expected):
        status, body, _ = self.request(path)
        self.assertEqual(status, 200, body)
        self.assertEqual([x['id'] for x in body['data']], [f'sub_{i:03d}' for i in expected])
        return body
