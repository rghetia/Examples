from tests.common import HTTPTestCase

class RateLimiterTests(HTTPTestCase):
    def test_RL_01_first_request(self):
        self.assertEqual(self.request()[0], 200)

    def test_RL_02_second_at_half_second(self):
        self.assertEqual(self.request()[0], 200)
        self.now += .5
        self.assertEqual(self.request()[0], 429)

    def test_RL_03_second_at_one_second(self):
        self.assertEqual(self.request()[0], 200)
        self.now += 1.0
        self.assertEqual(self.request()[0], 200)

    def test_RL_04_three_same_time(self):
        self.assertEqual([self.request()[0] for _ in range(3)], [200, 429, 429])

    def test_RL_05_invalid_after_valid(self):
        self.assertEqual(self.request()[0], 200)
        self.assertEqual(self.request('/api/v1/subscriptions?limit=-1')[0], 429)

    def test_RL_06_window_expires(self):
        self.assertEqual(self.request()[0], 200)
        self.now += .9
        status, body, headers = self.request()
        self.assertEqual(status, 429)
        self.assertEqual(headers['Retry-After'], '1')
        self.now += .1
        self.assertEqual(self.request()[0], 200)
