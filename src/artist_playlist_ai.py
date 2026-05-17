#!/usr/bin/env python3
"""
Spotify playlist updater — add new releases to an artist playlist.

  ./run.sh                  # uses ARTIST_NAME below
  ./run.sh "The Script"
  ./run.sh batch
"""

import os
import sys
import time

from config import INCLUDE_ALBUM_TYPES, validate_config
from date_utils import is_after_cutoff
from progress_utils import load_progress, save_progress
from run_log import RunTotals, SkipBucket, format_artists, log
from spotify_client import (
    add_tracks_to_playlist_with_retry,
    get_albums_with_retry,
    get_artist_with_retry,
    get_latest_release_date_from_playlist,
    get_or_create_playlist,
    get_playlist_track_uris,
    get_spotify_client,
    get_track_details_batch,
    get_tracks_with_retry,
)
from track_filtering import should_skip_low_quality_track, should_skip_track_manual

ARTIST_NAME = "Sia"
ARTISTS = []

BATCH_SIZE_TRACKS = 50
PROGRESS_SAVE_EVERY = 10
API_DELAY = 0.2


def process_artist(artist_name: str, sp=None) -> None:
    if sp is None:
        sp = get_spotify_client()

    results = get_artist_with_retry(sp, artist_name)
    if not results["artists"]["items"]:
        log(f"Artist not found: {artist_name}")
        return

    artist = results["artists"]["items"][0]
    artist_id = artist["id"]

    playlist_id, playlist_exists = get_or_create_playlist(sp, artist_name)
    if playlist_exists:
        log(f"Playlist: '{artist_name}' (existing)")
    else:
        log(f"Playlist: '{artist_name}' (created new)")

    latest_existing_date = None
    playlist_uris: set[str] = set()

    if playlist_exists:
        playlist_uris = get_playlist_track_uris(sp, playlist_id)
        latest_existing_date = get_latest_release_date_from_playlist(sp, playlist_id)

    log("")
    log(f"=== {artist['name']} ===")
    if playlist_exists and latest_existing_date:
        log(
            f"Mode: refresh — add tracks from releases AFTER {latest_existing_date}"
        )
        log(
            f"Playlist: {len(playlist_uris)} tracks | "
            f"Older releases on or before that date are ignored"
        )
    elif playlist_exists:
        log("Mode: full scan (could not read newest date on playlist)")
    else:
        log("Mode: new playlist — adding full discography")

    album_types = ",".join(INCLUDE_ALBUM_TYPES)
    progress = load_progress(artist_name)
    processed_ids = set(progress["processed_albums"]) if progress else set()

    all_albums = get_albums_with_retry(sp, artist_id, album_types)
    all_albums = sorted(all_albums, key=lambda x: x.get("release_date", "1900-01-01"))

    if progress:
        all_albums = [a for a in all_albums if a["id"] not in processed_ids]
        log(f"Resuming interrupted run — {len(all_albums)} releases left")

    new_releases = []
    totals = RunTotals()

    for album in all_albums:
        album_date = album.get("release_date", "1900-01-01")
        if latest_existing_date and not is_after_cutoff(album_date, latest_existing_date):
            totals.releases_before_cutoff += 1
            continue
        new_releases.append(album)

    log(f"Spotify discography: {len(all_albums)} releases | New to check: {len(new_releases)}")
    if totals.releases_before_cutoff:
        log(f"(Skipped {totals.releases_before_cutoff} releases on/before {latest_existing_date})")
    log("")

    if not new_releases:
        log("Nothing new to add — playlist is up to date for this cutoff.")
        return

    initial_playlist_uris = set(playlist_uris)
    track_uris: list[str] = list(progress["track_uris"]) if progress else []
    uris_seen: set[str] = set(playlist_uris)
    if progress:
        uris_seen |= set(progress["track_uris"])

    for i, album in enumerate(new_releases, 1):
        album_date = album.get("release_date", "1900-01-01")
        album_name = album.get("name", "Unknown")
        album_type = album.get("album_type", "album")
        bucket = SkipBucket()
        added_names: list[str] = []

        why = (
            f"release date {album_date} is after playlist cutoff {latest_existing_date}"
            if latest_existing_date
            else "new playlist — including all discography"
        )
        log(f"[{i}/{len(new_releases)}] {album_type.upper()}: {album_name} ({album_date})")
        log(f"  why: {why}")

        tracks = get_tracks_with_retry(sp, album["id"])
        track_ids = [t["id"] for t in tracks["items"]]
        details = get_track_details_batch(sp, track_ids, BATCH_SIZE_TRACKS)
        details_map = {
            tid: details[j]
            for j, tid in enumerate(track_ids)
            if j < len(details) and details[j]
        }

        for track in tracks["items"]:
            name = track["name"]
            full = details_map.get(track["id"], track)
            uri = track["uri"]

            skip, reason = should_skip_low_quality_track(full)
            if skip:
                bucket.add_quality(name, reason)
                continue

            skip, reason = should_skip_track_manual(name, album_name)
            if skip:
                bucket.add_manual(name, reason)
                continue

            if uri in uris_seen:
                bucket.add_duplicate(name)
                continue

            track_uris.append(uri)
            uris_seen.add(uri)
            feat = format_artists(full)
            added_names.append(f"{name} — {feat}")

        for line in bucket.format_lines():
            log(line)

        if added_names:
            log(f"  + {len(added_names)} new track(s):")
            for entry in added_names[:5]:
                log(f"      {entry}")
            if len(added_names) > 5:
                log(f"      ... +{len(added_names) - 5} more")
        else:
            log("  + 0 new tracks (all skipped or already on playlist)")

        log("")
        totals.absorb_release(len(added_names), bucket)
        processed_ids.add(album["id"])

        if i % PROGRESS_SAVE_EVERY == 0:
            save_progress(artist_name, list(processed_ids), track_uris, list(uris_seen))

        if i < len(new_releases):
            time.sleep(API_DELAY)

    to_add = [u for u in dict.fromkeys(track_uris) if u not in initial_playlist_uris]

    log("=== Summary ===")
    log(f"Releases scanned (after cutoff): {totals.releases_checked}")
    log(f"New tracks to add: {len(to_add)}")
    if totals.skip_duplicate:
        log(
            f"Skipped {totals.skip_duplicate} — already on playlist "
            f"(same Spotify track, often a remix you already have)"
        )
    if totals.skip_manual:
        log(f"Skipped {totals.skip_manual} — filtered (intro/skit/karaoke/live)")
    if totals.skip_quality:
        log(f"Skipped {totals.skip_quality} — too short/long or not playable")

    if to_add:
        log(f"Uploading {len(to_add)} tracks to Spotify...")
        add_tracks_to_playlist_with_retry(sp, playlist_id, to_add)
        log(f"Done. Playlist '{artist_name}' updated (+{len(to_add)} tracks).")
    else:
        log("No upload needed — no new tracks passed filters.")

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
