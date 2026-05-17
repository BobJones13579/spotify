#!/usr/bin/env bash
# Run the playlist updater from the project root.
set -e
cd "$(dirname "$0")"
source venv/bin/activate
python -m pip install --upgrade pip -q
pip install -q -r requirements.txt

if [[ "${1:-}" == "test" ]]; then
  python -m unittest discover -s tests -v
  exit 0
fi

cd src
python artist_playlist_ai.py "$@"
