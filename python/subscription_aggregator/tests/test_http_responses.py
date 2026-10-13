from tests.common import HTTPTestCase

class HTTPResponseTests(HTTPTestCase):
    def test_HTTP_01_success(self):
        self.assertEqual(self.request()[0], 200)

    def test_HTTP_02_bad_input(self):
        status, body, headers = self.request('/api/v1/subscriptions?limit=bad')
        self.assertEqual(status, 400)
        self.assertIn('error', body)
        self.assertIn('application/json', headers['Content-Type'])

    def test_HTTP_03_rate_limit(self):
        self.request()
        status, body, headers = self.request()
        self.assertEqual(status, 429)
        self.assertEqual(headers['Retry-After'], '1')
        self.assertIn('error', body)

    def test_HTTP_04_unknown_route(self):
        self.assertEqual(self.request('/other')[0], 404)

    def test_HTTP_05_post_method(self):
        status, body, headers = self.request(method='POST')
        self.assertEqual(status, 405)
        self.assertEqual(headers['Allow'], 'GET')

    def test_HTTP_06_response_shape(self):
        body = self.assert_ids('/api/v1/subscriptions?limit=2', [1, 2])
        self.assertEqual(body['count'], 2)
        self.assertTrue(body['has_more'])
        self.assertEqual(body['next_cursor'], 'sub_002')
        self.now += 1
        last = self.assert_ids('/api/v1/subscriptions?start_after=sub_004&limit=2', [5])
        self.assertFalse(last['has_more'])
        self.assertEqual(last['next_cursor'], 'sub_005')
