from tests.common import HTTPTestCase

class PaginationTests(HTTPTestCase):
    def test_PG_01_no_parameters(self): self.assert_ids('/api/v1/subscriptions', range(1, 6))
    def test_PG_02_limit_two(self): self.assert_ids('/api/v1/subscriptions?limit=2', [1, 2])
    def test_PG_03_limit_one(self): self.assert_ids('/api/v1/subscriptions?limit=1', [1])
    def test_PG_04_limit_five(self): self.assert_ids('/api/v1/subscriptions?limit=5', range(1, 6))
    def test_PG_05_limit_ten(self): self.assert_ids('/api/v1/subscriptions?limit=10', range(1, 6))
    def test_PG_06_after_two(self): self.assert_ids('/api/v1/subscriptions?start_after=sub_002', [3, 4, 5])
    def test_PG_07_after_two_limit_two(self): self.assert_ids('/api/v1/subscriptions?start_after=sub_002&limit=2', [3, 4])
    def test_PG_08_after_four_limit_five(self): self.assert_ids('/api/v1/subscriptions?start_after=sub_004&limit=5', [5])
    def test_PG_09_after_last(self): self.assert_ids('/api/v1/subscriptions?start_after=sub_005', [])
    def test_PG_10_empty_cursor(self): self.assert_ids('/api/v1/subscriptions?start_after=&limit=2', [1, 2])
