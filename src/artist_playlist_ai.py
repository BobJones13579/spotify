#!/usr/bin/env python3
"""
Spotify playlist updater — refresh an artist playlist with new releases only.

  ./run.sh                  # uses ARTIST_NAME below
  ./run.sh "The Script"     # or pass artist on command line
  ./run.sh batch            # uses ARTISTS list below
"""

import os
import sys
import time
from datetime import datetime

from config import INCLUDE_ALBUM_TYPES, validate_config
from progress_utils import estimate_remaining_time, load_progress, save_progress
from spotify_client import (
    add_tracks_to_playlist_with_retry,
    get_albums_with_retry,
    get_artist_with_retry,
    get_latest_release_date_from_playlist,
    get_or_create_playlist,
    get_playlist_track_names,
    get_spotify_client,
    get_track_details_batch,
    get_tracks_with_retry,
    log,
)
from track_filtering import should_skip_low_quality_track, should_skip_track_manual

# --- Edit these ---
ARTIST_NAME = "Sia"
ARTISTS = []  # batch mode, e.g. ["The Script", "Taylor Swift"]

BATCH_SIZE_TRACKS = 50
PROGRESS_SAVE_EVERY = 10  # albums
API_DELAY = 0.2


def process_artist(artist_name: str, sp=None) -> None:
    if sp is None:
        sp = get_spotify_client()

    log(f"Artist: {artist_name}")

    results = get_artist_with_retry(sp, artist_name)
    if not results["artists"]["items"]:
        log(f"Artist not found: {artist_name}")
        return

    artist = results["artists"]["items"][0]
    artist_id = artist["id"]
    log(f"Found: {artist['name']}")

    playlist_id, playlist_exists = get_or_create_playlist(sp, artist_name)

    latest_existing_date = None
    track_names_seen: set[str] = set()

    if playlist_exists:
        latest_existing_date = get_latest_release_date_from_playlist(sp, playlist_id)
        track_names_seen = get_playlist_track_names(sp, playlist_id)
        if latest_existing_date:
            log(f"Refresh mode — only releases after {latest_existing_date}")
            log(f"Skipping {len(track_names_seen)} track names already on playlist")
        else:
            log("Could not read playlist dates — may add duplicates")

    album_types = ",".join(INCLUDE_ALBUM_TYPES)
    progress = load_progress(artist_name)
    processed_ids = set(progress["processed_albums"]) if progress else set()

    albums = get_albums_with_retry(sp, artist_id, album_types)
    albums = sorted(albums, key=lambda x: x.get("release_date", "1900-01-01"))

    if progress:
        albums = [a for a in albums if a["id"] not in processed_ids]
        log(f"Resuming — {len(albums)} releases left")

    if not albums:
        log("Nothing to process.")
        return

    track_uris: list[str] = progress["track_uris"] if progress else []
    if progress:
        track_names_seen |= set(progress["track_names_seen"])

    manual_skipped = 0
    quality_skipped = 0
    duplicate_skipped = 0
    releases_added = 0
    start_time = datetime.now()

    for i, album in enumerate(albums, 1):
        album_date = album.get("release_date", "1900-01-01")
        album_name = album.get("name", "Unknown")
        album_type = album.get("album_type", "album")

        if latest_existing_date and album_date <= latest_existing_date:
            continue

        releases_added += 1
        log(f"[{i}/{len(albums)}] {album_type}: {album_name} ({album_date})")

        tracks = get_tracks_with_retry(sp, album["id"])
        track_ids = [t["id"] for t in tracks["items"]]
        details = get_track_details_batch(sp, track_ids, BATCH_SIZE_TRACKS)
        details_map = {
            tid: details[j]
            for j, tid in enumerate(track_ids)
            if j < len(details) and details[j]
        }

        added_this_album = 0
        for track in tracks["items"]:
            name = track["name"]
            full = details_map.get(track["id"], track)

            skip, reason = should_skip_low_quality_track(full)
            if skip:
                quality_skipped += 1
                continue

            skip, reason = should_skip_track_manual(name, album_name)
            if skip:
                manual_skipped += 1
                continue

            if name in track_names_seen:
                duplicate_skipped += 1
                continue

            track_uris.append(track["uri"])
            track_names_seen.add(name)
            added_this_album += 1
            log(f"  + {name}")

        if added_this_album == 0:
            log("  (no new tracks from this release)")

        processed_ids.add(album["id"])

        if i % PROGRESS_SAVE_EVERY == 0:
            save_progress(artist_name, list(processed_ids), track_uris, track_names_seen)

        if i % 5 == 0 and i < len(albums):
            eta = estimate_remaining_time(len(albums), i, start_time)
            if eta is not None:
                log(f"Progress: {i}/{len(albums)} (~{eta // 60}m {eta % 60}s left)")

        if i < len(albums):
            time.sleep(API_DELAY)

    to_add = list(dict.fromkeys(track_uris))

    log("---")
    log(f"Releases checked: {releases_added}")
    log(f"Tracks to add: {len(to_add)}")
    if manual_skipped:
        log(f"Skipped (not a song): {manual_skipped}")
    if quality_skipped:
        log(f"Skipped (quality): {quality_skipped}")
    if duplicate_skipped:
        log(f"Skipped (duplicate name): {duplicate_skipped}")

    if to_add:
        log(f"Adding {len(to_add)} tracks to playlist...")
        add_tracks_to_playlist_with_retry(sp, playlist_id, to_add)
        log(f"Done — added {len(to_add)} tracks to '{artist_name}'")
    else:
        log("No new tracks to add.")

    progress_file = f"progress_{artist_name.replace(' ', '_').lower()}.json"
    if os.path.exists(progress_file):
        os.remove(progress_file)


def main() -> None:
    errors = validate_config()
    if errors:
        log("Missing Spotify credentials in .env:")
        for err in errors:
            log(f"  - {err}")
        sys.exit(1)

    try:
        sp = get_spotify_client()
        me = sp.current_user()
        log(f"Signed in as {me['display_name']}")
    except Exception as e:
        log(f"Spotify login failed: {e}")
        sys.exit(1)

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "batch":
            if not ARTISTS:
                log("ARTISTS list is empty in artist_playlist_ai.py")
                return
            for name in ARTISTS:
                try:
                    process_artist(name, sp)
                    time.sleep(2)
                except Exception as e:
                    log(f"Failed {name}: {e}")
            return
        if arg == "undo":
            log("Undo not implemented.")
            return
        process_artist(" ".join(sys.argv[1:]), sp)
        return

    if not ARTIST_NAME:
        log("Set ARTIST_NAME or pass an artist name.")
        return
    process_artist(ARTIST_NAME, sp)


if __name__ == "__main__":
    main()
