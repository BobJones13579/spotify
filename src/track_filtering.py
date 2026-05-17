"""
Track Filtering Module

Handles all track filtering logic including popularity analysis, manual filtering,
and quality checks.
"""

from datetime import datetime, date

# Conservative Popularity Filtering (reduces false positives while still filtering unpopular tracks)
MIN_POPULARITY_THRESHOLD = 10   # Lower threshold for albums/compilations (more conservative)
SINGLE_POPULARITY_THRESHOLD = 15  # Lower threshold for singles (more conservative)
POPULARITY_RATIO_THRESHOLD = 0.10  # Album tracks must have at least 10% of album's max popularity (more conservative)
LOG_POPULARITY_DECISIONS = True  # Log popularity filtering decisions

# Conservative time adjustment multipliers for new releases
NEW_SONG_BOOST_30_DAYS = 1.2    # +20% boost for songs < 30 days old (more conservative)
NEW_SONG_BOOST_90_DAYS = 1.15   # +15% boost for songs < 90 days old (more conservative)
NEW_SONG_BOOST_1_YEAR = 1.05    # +5% boost for songs < 1 year old (more conservative)

def log(message: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def calculate_custom_popularity_score(track, album_tracks, album_name, album_type):
    """
    Calculate our own popularity score based on available data and release date.
    
    Args:
        track: Spotify track object
        album_tracks: List of all tracks in the album
        album_name: Name of the album
        album_type: Type of album (album, single, compilation)
        
    Returns:
        tuple: (custom_score, spotify_popularity, release_date, days_since_release)
    """
    
    # Get base popularity from Spotify
    spotify_popularity = track.get('popularity', 0)
    
    # Parse release date
    release_date_str = track.get('album', {}).get('release_date', '1900-01-01')
    try:
        if len(release_date_str) == 4:  # Year only
            release_date = datetime.strptime(release_date_str, '%Y').date()
        elif len(release_date_str) == 7:  # Year-month
            release_date = datetime.strptime(release_date_str, '%Y-%m').date()
        else:  # Full date
            release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
    except ValueError:
        release_date = date(1900, 1, 1)  # Fallback to old date
    
    # Calculate days since release
    days_since_release = (date.today() - release_date).days
    
    # Apply time-based multipliers
    base_score = spotify_popularity
    
    if days_since_release < 30:
        time_multiplier = NEW_SONG_BOOST_30_DAYS
    elif days_since_release < 90:
        time_multiplier = NEW_SONG_BOOST_90_DAYS
    elif days_since_release < 365:
        time_multiplier = NEW_SONG_BOOST_1_YEAR
    else:
        time_multiplier = 1.0
    
    custom_score = min(100, base_score * time_multiplier)
    
    return custom_score, spotify_popularity, release_date, days_since_release

def analyze_track_popularity(track, album_tracks, album_name, album_type, album_track_details=None):
    """
    Analyze track popularity using our custom scoring system.
    
    Args:
        track: Full track object from Spotify
        album_tracks: List of all tracks in the album
        album_name: Name of the album
        album_type: Type of album (album, single, compilation)
        album_track_details: Pre-fetched track details to avoid API calls
        
    Returns:
        tuple: (should_skip, reason, custom_score)
    """
    
    custom_score, spotify_popularity, release_date, days_since_release = calculate_custom_popularity_score(
        track, album_tracks, album_name, album_type
    )
    
    if album_type == 'album':
        # For albums, use relative popularity (must be at least X% of album's max)
        # Use pre-fetched track details if available to avoid API calls
        if album_track_details:
            album_scores = [t.get('popularity', 0) for t in album_track_details]
        else:
            # Fallback: use current track's popularity as reference
            album_scores = [spotify_popularity]
        
        if album_scores:
            max_album_score = max(album_scores)
            if max_album_score > 0:
                popularity_ratio = custom_score / max_album_score
                if popularity_ratio < POPULARITY_RATIO_THRESHOLD:
                    reason = f"Album track too unpopular: {custom_score:.1f}/{max_album_score} ({popularity_ratio:.1%} < {POPULARITY_RATIO_THRESHOLD:.1%})"
                    if LOG_POPULARITY_DECISIONS:
                        log(f"     📊 {reason} (released {days_since_release} days ago)")
                    return True, reason, custom_score
                    
    elif album_type == 'single':
        # For singles, use absolute threshold
        if custom_score < SINGLE_POPULARITY_THRESHOLD:
            reason = f"Single too unpopular: {custom_score:.1f}/100 (min: {SINGLE_POPULARITY_THRESHOLD})"
            if LOG_POPULARITY_DECISIONS:
                log(f"     📊 {reason} (released {days_since_release} days ago)")
            return True, reason, custom_score
            
    elif album_type == 'compilation':
        # For compilations, use minimum threshold
        if custom_score < MIN_POPULARITY_THRESHOLD:
            reason = f"Compilation track too unpopular: {custom_score:.1f}/100 (min: {MIN_POPULARITY_THRESHOLD})"
            if LOG_POPULARITY_DECISIONS:
                log(f"     📊 {reason}")
            return True, reason, custom_score
    
    if LOG_POPULARITY_DECISIONS:
        log(f"     📊 {album_type.title()} OK: {custom_score:.1f}/100")
    
    return False, f"Custom popularity acceptable: {custom_score:.1f}/100", custom_score

def should_skip_track_manual(track_name: str, album_name: str, artist_name: str) -> tuple[bool, str]:
    """
    Manual track filtering using traditional rule-based logic.
    
    This is our primary filtering method - fast, reliable, and objective.
    """
    
    track_lower = track_name.lower()
    
    # Check for acoustic songs (user preference)
    acoustic_indicators = ['acoustic', 'unplugged', 'stripped']
    for indicator in acoustic_indicators:
        if indicator in track_lower:
            return True, f"Manual: Acoustic version - {indicator}"
    
    # Check for obvious non-songs (keep soundtracks, remasters, EPs, etc.)
    non_song_indicators = [
        'intro', 'outro', 'skit', 'interlude', 'spoken word', 'instrumental',
        'demo', 'acapella', 'a capella', 'karaoke', 'backing track',
        'piano version', 'orchestral version', 'strings version',
        'dialogue', 'monologue', 'narrative', 'recitation',
        'teaser', 'preview', 'snippet', 'clip', 'trailer'
    ]
    
    for indicator in non_song_indicators:
        if indicator in track_lower:
            return True, f"Manual: Contains '{indicator}' - likely not a real song"
    
    # Check for very short tracks (likely intros/outros)
    if any(short_indicator in track_lower for short_indicator in ['intro', 'outro', 'skit']):
        return True, "Manual: Short track - likely intro/outro/skit"
    
    # Check for live recordings with crowd noise
    if should_skip_live_recording(track_name, album_name):
        return True, "Manual: Live concert recording with crowd noise"
    
    # Check for duplicates (basic check)
    if should_skip_duplicate_track(track_name, album_name, set(), None, None):  # Empty set for manual check
        return True, "Manual: Appears to be a duplicate"
    
    return False, "Manual: Passed all manual filters"

def should_skip_low_quality_track(track: dict) -> tuple[bool, str]:
    """
    Check if track should be skipped based on quality metrics.
    
    Args:
        track: Full track object from Spotify API
        
    Returns:
        tuple: (should_skip, reason)
    """
    
    # Check track duration (very short tracks are likely intros/outros)
    duration_ms = track.get('duration_ms', 0)
    duration_seconds = duration_ms / 1000
    
    if duration_seconds < 60:  # Less than 1 minute
        return True, f"Quality: Too short ({duration_seconds:.1f}s) - likely intro/outro"
    
    if duration_seconds > 600:  # More than 10 minutes
        return True, f"Quality: Too long ({duration_seconds/60:.1f}min) - likely extended version"
    
    # Check if track is available in your market (skip unplayable tracks)
    available_markets = track.get('available_markets', [])
    if not available_markets:  # No markets available
        return True, "Quality: Not available in your market - can't play it"
    
    # Keep explicit content (user preference: don't filter explicit vs clean)
    
    return False, "Quality: Passed all quality checks"

def should_skip_live_recording(track_name: str, album_name: str) -> bool:
    """
    Check if this is a live recording with crowd noise that should be skipped.
    
    Args:
        track_name: Name of the track
        album_name: Name of the album  
        
    Returns:
        bool: True if should skip this track
    """
    
    track_lower = track_name.lower()
    album_lower = album_name.lower()
    
    # Live recording indicators (with crowd noise)
    live_indicators = [
        'live at', 'live from', 'live in', 'concert', 'venue',
        'madison square garden', 'wembley', 'o2 arena', 'hollywood bowl'
    ]
    
    for indicator in live_indicators:
        if indicator in track_lower or indicator in album_lower:
            return True
    
    return False

def should_skip_duplicate_track(track_name, album_name, track_names_seen, track_release_date, existing_track_date):
    """
    Enhanced duplicate detection with better logic.
    
    Args:
        track_name: Name of the track
        album_name: Name of the album
        track_names_seen: Set of track names already processed
        track_release_date: Release date of current track
        existing_track_date: Release date of existing track
        
    Returns:
        bool: True if this track should be skipped as a duplicate
    """
    
    # Skip if exact name already seen (first version wins)
    if track_name in track_names_seen:
        return True
    
    # Keep legitimate versions (remixes, edits, features)
    track_lower = track_name.lower()
    featuring_indicators = ['feat.', 'featuring', 'ft.', 'with', '&', ' x ', ' duet with', ' featuring ', ' feat ', ' ft ', ' presents ', ' meets ']
    for indicator in featuring_indicators:
        if indicator in track_lower:
            return False  # Keep featured versions
    
    # Keep legitimate version indicators
    legitimate_version_indicators = ['remix', 'edit', 'version', 'mix', 'radio edit', 'extended', 'club mix', 'dub', 'clean', 'explicit', 'demo', 'instrumental', 'stripped', 'unplugged', 'piano version', 'orchestral']
    for indicator in legitimate_version_indicators:
        if indicator in track_lower:
            return False  # Keep legitimate versions
    
    # Skip re-releases and greatest hits
    album_lower = album_name.lower()
    duplicate_album_indicators = ['deluxe', 'anniversary', 'expanded', 'extended', 'super deluxe', 'greatest hits', 'best of', 'collection', 'anthology', 'compilation', 'gold', 'platinum', 'special edition', 'limited edition', 'remaster', 'remastered', 'reissue', 're-release']
    for indicator in duplicate_album_indicators:
        if indicator in album_lower:
            return True  # Skip re-releases
    
    return False
