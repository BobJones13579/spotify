"""Spotify API helpers with retries and rate-limit handling."""

import random
import time
from datetime import datetime

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPE,
)

_rate_limit_hits = 0
_request_delay = 0.2
MAX_CONSECUTIVE_RATE_LIMITS = 3


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def safe_spotify_call(func, *args, max_retries=5, base_delay=2, **kwargs):
    global _rate_limit_hits, _request_delay

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                log(f"Retrying in {delay:.0f}s...")
                time.sleep(delay)
            else:
                time.sleep(_request_delay)

            result = func(*args, **kwargs)
            return result

        except Exception as e:
            error_msg = str(e).lower()

            if "rate" in error_msg or "limit" in error_msg or "429" in error_msg:
                _rate_limit_hits += 1
                if _rate_limit_hits >= MAX_CONSECUTIVE_RATE_LIMITS:
                    raise RuntimeError("Too many rate limits — try again in a few minutes") from e
                if attempt < max_retries:
                    if hasattr(e, "response") and e.response:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            time.sleep(int(retry_after) + 1)
                            _request_delay = max(_request_delay, float(retry_after) / 10)
                            continue
                    continue
                raise

            if ("timeout" in error_msg or "connection" in error_msg) and attempt < max_retries:
                continue
            raise


def get_spotify_client():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
        )
    )


def resolve_artist(sp, artist_name: str) -> dict | None:
    """
    Find the correct artist — exact name match first, then highest popularity.
    (artist:Sia wrongly returns 'Artists Against' as the first hit.)
    """
    queries = [f'artist:"{artist_name}"', artist_name]
    items = []
    seen_ids = set()

    for q in queries:
        results = safe_spotify_call(sp.search, q=q, type="artist", limit=20)
        for artist in results["artists"]["items"]:
            if artist["id"] not in seen_ids:
                seen_ids.add(artist["id"])
                items.append(artist)
        if items:
            break

    if not items:
        return None

    target = artist_name.strip().lower()
    exact = [a for a in items if a["name"].strip().lower() == target]
    if exact:
        return max(exact, key=lambda a: a.get("popularity", 0))
    return max(items, key=lambda a: a.get("popularity", 0))


def get_artist_with_retry(sp, artist_name):
    artist = resolve_artist(sp, artist_name)
    return {"artists": {"items": [artist] if artist else []}}


def get_albums_with_retry(sp, artist_id, album_types):
    all_albums = []
    offset = 0
    batch_size = 50

    while True:
        results = safe_spotify_call(
            sp.artist_albums,
            artist_id,
            album_type=album_types,
            limit=batch_size,
            offset=offset,
        )
        if not results["items"]:
            break
        all_albums.extend(results["items"])
        if len(results["items"]) < batch_size:
            break
        offset += len(results["items"])
        time.sleep(0.3)

    return all_albums


def get_tracks_with_retry(sp, album_id):
    """All tracks on an album (paginated — some albums exceed 50 tracks)."""
    all_items = []
    offset = 0
    while True:
        page = safe_spotify_call(sp.album_tracks, album_id, limit=50, offset=offset)
        all_items.extend(page["items"])
        if not page.get("next"):
            break
        offset += len(page["items"])
    return {"items": all_items}


def get_track_details_batch(sp, track_ids, batch_size=50):
    if not track_ids:
        return []
    all_tracks = []
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i : i + batch_size]
        tracks = safe_spotify_call(sp.tracks, batch)
        all_tracks.extend(tracks["tracks"])
        if i + batch_size < len(track_ids):
            time.sleep(0.2)
    return all_tracks


def get_playlist_tracks_all(sp, playlist_id):
    """Return every track item in a playlist (handles pagination)."""
    tracks = safe_spotify_call(sp.playlist_tracks, playlist_id, limit=100)
    items = list(tracks["items"])
    while tracks.get("next"):
        tracks = safe_spotify_call(sp.next, tracks)
        items.extend(tracks["items"])
    return items


def get_playlist_track_uris(sp, playlist_id) -> set[str]:
    uris = set()
    for item in get_playlist_tracks_all(sp, playlist_id):
        track = item.get("track")
        if track and track.get("uri"):
            uris.add(track["uri"])
    return uris


def get_latest_release_date_from_playlist(sp, playlist_id) -> str | None:
    """Newest album release_date among tracks already on the playlist."""
    from date_utils import parse_release_date

    items = get_playlist_tracks_all(sp, playlist_id)
    log(f"Playlist has {len(items)} tracks")

    latest = None
    latest_parsed = None
    for item in items:
        track = item.get("track")
        if track and track.get("album"):
            raw = track["album"].get("release_date", "1900-01-01")
            parsed = parse_release_date(raw)
            if latest_parsed is None or parsed > latest_parsed:
                latest_parsed = parsed
                latest = raw

    if latest:
        log(f"Newest release on playlist: {latest}")
    return latest


def get_or_create_playlist(sp, artist_name):
    log(f"Looking for playlist: {artist_name}")
    playlists = sp.current_user_playlists(limit=50)
    while playlists:
        for pl in playlists["items"]:
            if pl["name"].lower() == artist_name.lower():
                log(f"Using existing playlist: {pl['name']}")
                return pl["id"], True
        if playlists.get("next"):
            playlists = sp.next(playlists)
        else:
            break

    me = sp.me()
    log(f"Creating playlist: {artist_name}")
    playlist = safe_spotify_call(
        sp.user_playlist_create,
        me["id"],
        artist_name,
        True,
        f"Discography — {artist_name}",
    )
    return playlist["id"], False


def add_tracks_to_playlist_with_retry(sp, playlist_id, track_uris):
    batch_size = 100
    for i in range(0, len(track_uris), batch_size):
        batch = track_uris[i : i + batch_size]
        safe_spotify_call(sp.playlist_add_items, playlist_id, batch)
        if i + batch_size < len(track_uris):
            time.sleep(0.3)
    return len(track_uris)
