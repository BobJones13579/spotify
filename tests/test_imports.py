"""Smoke test — all modules import without side effects."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class TestImports(unittest.TestCase):
    def test_import_main_modules(self):
        import artist_playlist_ai  # noqa: F401
        import config  # noqa: F401
        import date_utils  # noqa: F401
        import progress_utils  # noqa: F401
        import run_log  # noqa: F401
        import spotify_client  # noqa: F401
        import track_filtering  # noqa: F401


if __name__ == "__main__":
    unittest.main()
