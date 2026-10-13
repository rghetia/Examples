import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import subscription_server as server
from tests.common import FIXTURES

class DataLoadingTests(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'subscription.json'
            if text is not None:
                path.write_text(text, encoding='utf-8')
            with patch.object(server, 'DATA_FILE', path):
                return server.load_subscriptions()

    def test_DL_01_valid_array(self):
        self.assertEqual(len(self.load(json.dumps(FIXTURES))), 5)

    def test_DL_02_single_object(self):
        self.assertEqual(self.load(json.dumps(FIXTURES[0])), [FIXTURES[0]])

    def test_DL_03_empty_array(self):
        self.assertEqual(self.load('[]'), [])

    def test_DL_04_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            self.load(None)

    def test_DL_05_malformed_json(self):
        with self.assertRaises(json.JSONDecodeError):
            self.load('{broken')

    def test_DL_06_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.load(json.dumps([FIXTURES[0], FIXTURES[0]]))
