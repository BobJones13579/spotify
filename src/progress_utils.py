"""Save and resume progress if a long run is interrupted."""

import json
import os
from datetime import datetime


def save_progress(artist_name, processed_album_ids, track_uris, track_names_seen):
    progress_file = f"progress_{artist_name.replace(' ', '_').lower()}.json"
    data = {
        "artist_name": artist_name,
        "processed_albums": processed_album_ids,
        "track_uris": track_uris,
        "track_names_seen": list(track_names_seen),
        "timestamp": datetime.now().isoformat(),
    }
    with open(progress_file, "w") as f:
        json.dump(data, f, indent=2)


def load_progress(artist_name):
    progress_file = f"progress_{artist_name.replace(' ', '_').lower()}.json"
    if not os.path.exists(progress_file):
        return None
    try:
        with open(progress_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def estimate_remaining_time(total_albums, processed_albums, start_time):
    if processed_albums == 0:
        return None
    elapsed = (datetime.now() - start_time).total_seconds()
    if elapsed <= 0:
        return None
    rate = processed_albums / elapsed
    remaining = (total_albums - processed_albums) / rate
    return int(remaining)
