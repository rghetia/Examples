from tests.common import HTTPTestCase

class ValidationTests(HTTPTestCase):
    def assert_bad(self, query):
        status, body, _ = self.request('/api/v1/subscriptions?' + query)
        self.assertEqual(status, 400, body)
        self.assertTrue(body.get('error'))

    def test_VL_01_zero(self): self.assert_bad('limit=0')
    def test_VL_02_negative(self): self.assert_bad('limit=-1')
    def test_VL_03_text(self): self.assert_bad('limit=abc')
    def test_VL_04_decimal(self): self.assert_bad('limit=1.5')
    def test_VL_05_space(self): self.assert_bad('limit=%20')
    def test_VL_06_duplicate_limit(self): self.assert_bad('limit=2&limit=3')
    def test_VL_07_unknown_cursor(self): self.assert_bad('start_after=sub_unknown')
    def test_VL_08_duplicate_cursor(self): self.assert_bad('start_after=sub_001&start_after=sub_002')
    def test_VL_09_unknown_parameter(self): self.assert_bad('unknown=value')
    def test_VL_10_large_positive_limit(self): self.assert_ids('/api/v1/subscriptions?limit=999999999999999999', range(1, 6))
