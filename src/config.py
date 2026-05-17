"""Configuration — credentials load from .env in the project root."""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private"

# Release types to include from Spotify
INCLUDE_ALBUM_TYPES = ["album", "single", "compilation"]


def validate_config() -> List[str]:
    errors = []
    if not SPOTIFY_CLIENT_ID:
        errors.append("SPOTIFY_CLIENT_ID is not set in .env")
    if not SPOTIFY_CLIENT_SECRET:
        errors.append("SPOTIFY_CLIENT_SECRET is not set in .env")
    return errors
