"""Unit tests for artist name resolution (no Spotify API calls)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from spotify_client import resolve_artist


class TestResolveArtist(unittest.TestCase):
    def _mock_spotify(self, artists_by_query):
        sp = MagicMock()

        def search(q, type, limit):
            return {"artists": {"items": artists_by_query.get(q, [])}}

        sp.search = search
        return sp

    def test_sia_picks_exact_match_not_artists_against(self):
        """artist:Sia used to return 'Artists Against' first — must pick 'Sia'."""
        sp = self._mock_spotify(
            {
                'artist:"Sia"': [
                    {"id": "1", "name": "Artists Against", "popularity": 15},
                    {"id": "2", "name": "Sia", "popularity": 86},
                ],
            }
        )
        artist = resolve_artist(sp, "Sia")
        self.assertEqual(artist["name"], "Sia")
        self.assertEqual(artist["id"], "2")

    def test_falls_back_to_popularity_without_exact_match(self):
        sp = self._mock_spotify(
            {
                'artist:"Obscure"': [
                    {"id": "a", "name": "Obscure Band A", "popularity": 10},
                    {"id": "b", "name": "Obscure Band B", "popularity": 50},
                ],
            }
        )
        artist = resolve_artist(sp, "Obscure")
        self.assertEqual(artist["id"], "b")


if __name__ == "__main__":
    unittest.main()
