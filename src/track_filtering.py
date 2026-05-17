"""Light filtering — skip obvious non-songs and unplayable tracks."""

from datetime import datetime

MIN_DURATION_SEC = 60
MAX_DURATION_SEC = 600


def should_skip_track_manual(track_name: str, album_name: str) -> tuple[bool, str]:
    """Skip intros, skits, karaoke, and live venue recordings."""
    track_lower = track_name.lower()
    album_lower = album_name.lower()

    non_song_indicators = [
        "intro", "outro", "skit", "interlude", "spoken word", "instrumental",
        "demo", "acapella", "a capella", "karaoke", "backing track",
        "dialogue", "monologue", "teaser", "preview", "snippet",
    ]
    for indicator in non_song_indicators:
        if indicator in track_lower:
            return True, f"contains '{indicator}'"

    live_indicators = [
        "live at", "live from", "live in", "concert",
        "madison square garden", "wembley", "o2 arena",
    ]
    for indicator in live_indicators:
        if indicator in track_lower or indicator in album_lower:
            return True, "live recording"

    return False, ""


def should_skip_low_quality_track(track: dict) -> tuple[bool, str]:
    """Skip very short/long or unplayable tracks."""
    duration_sec = track.get("duration_ms", 0) / 1000

    if duration_sec < MIN_DURATION_SEC:
        return True, f"too short ({duration_sec:.0f}s)"
    if duration_sec > MAX_DURATION_SEC:
        return True, f"too long ({duration_sec / 60:.0f} min)"

    if track.get("is_playable") is False:
        return True, "not playable in your region"

    return False, ""
