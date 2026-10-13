import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import subscription_server as server
from tests.common import FIXTURES

class SortingTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subscription.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(server, "DATA_FILE", path):
                return server.load_subscriptions()

    def test_SO_01_unsorted(self):
        self.assertEqual([x['id'] for x in self.load(FIXTURES[::-1])], [x['id'] for x in FIXTURES])

    def test_SO_02_already_sorted(self):
        self.assertEqual(self.load(FIXTURES), FIXTURES)

    def test_SO_03_single(self):
        self.assertEqual(self.load(FIXTURES[:1]), FIXTURES[:1])

    def test_SO_04_mixed_case(self):
        data = [{'id': i} for i in ['sub_a', 'sub_B', 'sub_A']]
        self.assertEqual([x['id'] for x in self.load(data)], ['sub_A', 'sub_B', 'sub_a'])
