#!/usr/bin/env bash
# Run the playlist creator from the project root.
set -e
cd "$(dirname "$0")"
source venv/bin/activate
pip install -q -r requirements.txt
cd src
python artist_playlist_ai.py "$@"
