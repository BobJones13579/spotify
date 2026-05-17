"""Unit tests for release date parsing and cutoff logic."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from date_utils import is_after_cutoff, parse_release_date


class TestParseReleaseDate(unittest.TestCase):
    def test_full_date(self):
        self.assertEqual(parse_release_date("2024-09-13"), date(2024, 9, 13))

    def test_year_month(self):
        self.assertEqual(parse_release_date("2024-09"), date(2024, 9, 28))

    def test_year_only(self):
        self.assertEqual(parse_release_date("2024"), date(2024, 12, 31))


class TestIsAfterCutoff(unittest.TestCase):
    def test_album_after_cutoff(self):
        self.assertTrue(is_after_cutoff("2024-10-01", "2024-09-13"))

    def test_album_on_cutoff_not_included(self):
        self.assertFalse(is_after_cutoff("2024-09-13", "2024-09-13"))

    def test_year_only_vs_full_date(self):
        # Album in 2022 is after cutoff 2021-10-22
        self.assertTrue(is_after_cutoff("2022-01-14", "2021-10-22"))

    def test_string_compare_bug_fixed(self):
        # Old bug: "2024-09-30" <= "2024-09" as strings is False, but as dates:
        self.assertTrue(is_after_cutoff("2024-09-30", "2024-09"))

    def test_no_cutoff(self):
        self.assertTrue(is_after_cutoff("1900-01-01", ""))


if __name__ == "__main__":
    unittest.main()
