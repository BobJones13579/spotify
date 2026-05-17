"""Tests for console reporting helpers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from run_log import SkipBucket


class TestSkipBucket(unittest.TestCase):
    def test_format_duplicate_summary(self):
        b = SkipBucket()
        b.add_duplicate("Snowman")
        b.add_duplicate("Gimme Love")
        b.add_duplicate("Gimme Love - Remix")
        lines = b.format_lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("already on playlist", lines[0])
        self.assertIn("+1 more", lines[0])

    def test_empty_bucket(self):
        self.assertFalse(SkipBucket().has_skips())


if __name__ == "__main__":
    unittest.main()
