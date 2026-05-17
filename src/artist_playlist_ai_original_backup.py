#!/usr/bin/env python3
"""
AI-Optimized Spotify Playlist Creator

Creates comprehensive Spotify playlists for artists using AI-optimized processing
to handle large discographies without rate limiting issues.

Features:
- Intelligent progress persistence and resume capability
- Adaptive rate limiting with exponential backoff
- Batch API optimization and smart error recovery
- Advanced popularity filtering with time-based adjustments
- Comprehensive discography processing (albums, singles, compilations)

Usage:
- python artist_playlist_ai.py        # Single artist
- python artist_playlist_ai.py batch  # Multiple artists
- python artist_playlist_ai.py undo   # Remove tracks from last run
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, date
import requests
import time
import random
import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPE
)

# ============================================================================
# 🎯 CONFIGURATION - EDIT THESE SETTINGS HERE!
# ============================================================================

# 🎵 CHANGE THIS TO CREATE PLAYLISTS FOR DIFFERENT ARTISTS
ARTIST_NAME = "Bruno Mars"

# 👉 Batch mode - uncomment to process multiple artists - python artist_playlist_ai.py batch
# ARTISTS = ["Air Supply", "Lainey Wilson", "Billie Eilish"]

# 📊 Custom Popularity Filtering (more selective to avoid very unpopular tracks)
MIN_POPULARITY_THRESHOLD = 15  # Minimum for albums/compilations (after time adjustments)
SINGLE_POPULARITY_THRESHOLD = 20  # Threshold for singles (after time adjustments)
POPULARITY_RATIO_THRESHOLD = 0.15  # Album tracks must have at least 15% of album's max popularity
LOG_POPULARITY_DECISIONS = True  # Log popularity filtering decisions

# Time adjustment multipliers for new releases
NEW_SONG_BOOST_30_DAYS = 1.5    # +50% boost for songs < 30 days old
NEW_SONG_BOOST_90_DAYS = 1.3    # +30% boost for songs < 90 days old  
NEW_SONG_BOOST_1_YEAR = 1.1     # +10% boost for songs < 1 year old

# Re-evaluation settings
RE_EVALUATE_DAYS = 90  # Re-evaluate releases from last 90 days for popularity changes

# AI-OPTIMIZED COMPREHENSIVE MODE - Get EVERYTHING intelligently
COMPREHENSIVE_MODE = True  # Process ALL albums/tracks (no limits)
AI_OPTIMIZED_PROCESSING = True  # Use AI-driven optimization patterns

# Album type filtering (comprehensive - include everything)
INCLUDE_ALBUM_TYPES = ["album", "single", "compilation"]  # Include ALL types for comprehensive coverage

# AI-optimized processing settings
BATCH_SIZE_ALBUMS = 20  # Process albums in batches for efficiency
BATCH_SIZE_TRACKS = 50  # Maximum tracks per batch request
ADAPTIVE_DELAY_BASE = 0.2  # Base delay that adapts based on API response
PROGRESS_SAVE_INTERVAL = 5  # Save progress every N albums processed

# AI-Enhanced Rate Limiting Intelligence
AI_RATE_LIMIT_LEARNING = True  # Enable AI learning from rate limit patterns
MAX_CONSECUTIVE_RATE_LIMITS = 3  # Stop if we hit rate limits too many times in a row
INTELLIGENT_BACKOFF_MULTIPLIER = 1.5  # AI adjusts backoff based on patterns

# ============================================================================
# RATE LIMITING & RETRY LOGIC
# ============================================================================

# AI Learning State (global variables for learning across calls)
_ai_rate_limit_count = 0
_ai_consecutive_rate_limits = 0
_ai_adaptive_delay = 0.2  # Will be set from config

def safe_spotify_call(func, *args, max_retries=5, base_delay=2, **kwargs):
    """
    AI-Enhanced Spotify API call with intelligent rate limiting and learning.
    Learns from rate limit patterns and adapts behavior accordingly.
    
    Args:
        func: Spotify API function to call
        *args: Arguments for the function
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (AI-adaptive)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the Spotify API call
    """
    global _ai_rate_limit_count, _ai_consecutive_rate_limits, _ai_adaptive_delay
    
    for attempt in range(max_retries + 1):
        try:
            # AI-Enhanced delay calculation
            if attempt > 0:
                # AI learns from previous rate limits and adjusts delay
                if AI_RATE_LIMIT_LEARNING and _ai_rate_limit_count > 0:
                    # Increase delay based on learning
                    delay = base_delay * (2 ** attempt) * (1 + _ai_rate_limit_count * 0.1) + random.uniform(0, 2)
                else:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                
                log(f"     🤖 AI-Adaptive delay: {delay:.1f}s (learned from {_ai_rate_limit_count} previous rate limits)")
                time.sleep(delay)
            elif attempt == 0:
                # Use AI-learned adaptive delay
                time.sleep(_ai_adaptive_delay)
                
            result = func(*args, **kwargs)
            
            # AI Learning: Reset consecutive rate limit counter on success
            if _ai_consecutive_rate_limits > 0:
                log(f"     🎯 AI Learning: Reset consecutive rate limit counter (was {_ai_consecutive_rate_limits})")
                _ai_consecutive_rate_limits = 0
            
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # AI-Enhanced 429 Rate Limit handling
            if 'rate' in error_msg or 'limit' in error_msg or '429' in error_msg:
                _ai_rate_limit_count += 1
                _ai_consecutive_rate_limits += 1
                
                # AI Learning: Stop if too many consecutive rate limits
                if _ai_consecutive_rate_limits >= MAX_CONSECUTIVE_RATE_LIMITS:
                    log(f"     🛑 AI Decision: Too many consecutive rate limits ({_ai_consecutive_rate_limits}), stopping to prevent API abuse")
                    raise Exception(f"AI detected excessive rate limiting - stopping to prevent API abuse")
                
                if attempt < max_retries:
                    # Extract retry-after header if available
                    if hasattr(e, 'response') and e.response:
                        retry_after = e.response.headers.get('Retry-After')
                        if retry_after:
                            delay = int(retry_after) + random.uniform(0, 5)
                            log(f"     🤖 AI Learning: Server requested {retry_after}s wait, adapting future delays")
                            # AI Learning: Update adaptive delay based on server response
                            _ai_adaptive_delay = max(_ai_adaptive_delay * INTELLIGENT_BACKOFF_MULTIPLIER, float(retry_after) / 10)
                            time.sleep(delay)
                            continue
                    continue
                else:
                    log(f"     ❌ Rate limit exceeded after {max_retries} retries (AI learned from {_ai_rate_limit_count} total rate limits)")
                    raise
            elif 'timeout' in error_msg or 'connection' in error_msg:
                if attempt < max_retries:
                    continue
                else:
                    log(f"     ❌ Network error after {max_retries} retries")
                    raise
            else:
                # Non-rate-limit error, don't retry
                raise

def get_artist_with_retry(sp, artist_name):
    """Get artist with retry logic."""
    return safe_spotify_call(sp.search, q=f'artist:{artist_name}', type='artist', limit=1)

def get_albums_with_retry(sp, artist_id, album_type, limit=50):
    """Get ALL albums with comprehensive pagination and proper rate limiting."""
    all_albums = []
    offset = 0
    batch_size = 50  # Use max batch size for efficiency
    
    log(f"     🔍 Starting comprehensive album fetch for {album_type}...")
    
    while True:
        log(f"     📥 Fetching albums batch (offset {offset}, limit {batch_size})...")
        try:
            results = safe_spotify_call(
                sp.artist_albums, 
                artist_id, 
                album_type=album_type, 
                limit=batch_size,
                offset=offset
            )
            
            if not results['items']:
                log(f"     ✅ No more albums found at offset {offset}")
                break
                
            all_albums.extend(results['items'])
            log(f"     📊 Collected {len(all_albums)} albums so far...")
            
            # If we got fewer items than requested, we've reached the end
            if len(results['items']) < batch_size:
                log(f"     ✅ Reached end of album list (got {len(results['items'])} < {batch_size})")
                break
                
            offset += len(results['items'])
            
            # Add delay between batches to respect rate limits
            time.sleep(0.5)  # Conservative delay between album fetches
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'rate' in error_msg or '429' in error_msg:
                log(f"     ⏳ Rate limit hit at offset {offset}, waiting longer...")
                time.sleep(10)  # Wait longer for rate limits
                continue
            else:
                log(f"     ❌ Error fetching albums at offset {offset}: {e}")
                break
    
    log(f"     🎯 Comprehensive fetch complete: {len(all_albums)} total albums found")
    return all_albums

def get_tracks_with_retry(sp, album_id):
    """Get album tracks with retry logic."""
    return safe_spotify_call(sp.album_tracks, album_id, limit=50)

def get_track_details_batch(sp, track_ids):
    """AI-optimized batch track details fetching with intelligent error handling."""
    if not track_ids:
        return []
    
    all_tracks = []
    batch_size = BATCH_SIZE_TRACKS
    
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        try:
            tracks = safe_spotify_call(sp.tracks, batch)
            all_tracks.extend(tracks['tracks'])
            
            # Adaptive delay based on batch size and API response
            if i + batch_size < len(track_ids):
                delay = ADAPTIVE_DELAY_BASE * (len(batch) / 50)  # Scale delay with batch size
                time.sleep(delay)
                
        except Exception as e:
            log(f"     ⚠️  Error fetching track batch: {e}")
            # Add empty tracks for failed batch to maintain order
            all_tracks.extend([None] * len(batch))
    
    return all_tracks

def get_album_details_batch(sp, album_ids):
    """Get multiple album details in one API call (Spotify supports up to 20 albums per request)."""
    if not album_ids:
        return []
    
    all_albums = []
    batch_size = 20  # Spotify's limit for album batch requests
    
    for i in range(0, len(album_ids), batch_size):
        batch = album_ids[i:i + batch_size]
        try:
            albums = safe_spotify_call(sp.albums, batch)
            all_albums.extend(albums['albums'])
            
            # Small delay between album batches
            if i + batch_size < len(album_ids):
                time.sleep(ADAPTIVE_DELAY_BASE)
                
        except Exception as e:
            log(f"     ⚠️  Error fetching album batch: {e}")
            # Add empty albums for failed batch
            all_albums.extend([None] * len(batch))
    
    return all_albums

def get_track_details_with_retry(sp, track_id):
    """Get individual track details with retry logic."""
    return safe_spotify_call(sp.track, track_id)

def get_playlist_tracks_with_retry(sp, playlist_id, limit=100):
    """Get playlist tracks with retry logic."""
    return safe_spotify_call(sp.playlist_tracks, playlist_id, limit=limit)

def create_playlist_with_retry(sp, user_id, name, public=True, description=""):
    """Create playlist with retry logic."""
    return safe_spotify_call(sp.user_playlist_create, user_id, name, public, description)

def add_tracks_to_playlist_with_retry(sp, playlist_id, track_uris):
    """Add tracks to playlist with retry logic and batching."""
    # Spotify allows max 100 tracks per request
    batch_size = 100
    total_added = 0
    
    for i in range(0, len(track_uris), batch_size):
        batch = track_uris[i:i + batch_size]
        log(f"     📤 Adding batch {i//batch_size + 1}/{(len(track_uris) + batch_size - 1)//batch_size} ({len(batch)} tracks)")
        
        try:
            safe_spotify_call(sp.playlist_add_items, playlist_id, batch)
            total_added += len(batch)
            
            # Add delay between batches
            if i + batch_size < len(track_uris):
                time.sleep(0.5)
                
        except Exception as e:
            log(f"     ❌ Error adding batch {i//batch_size + 1}: {e}")
            raise
    
    return total_added

# ============================================================================
# SPOTIFY SETUP
# ============================================================================

def get_spotify_client():
    """Get Spotify client with OAuth authentication."""
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE
        )
    )

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log(message: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def save_progress(artist_name, processed_albums, track_uris, track_names_seen):
    """Save processing progress to resume later if needed."""
    progress_file = f"progress_{artist_name.replace(' ', '_').lower()}.json"
    progress_data = {
        'artist_name': artist_name,
        'processed_albums': [album['id'] for album in processed_albums],
        'track_uris': track_uris,
        'track_names_seen': list(track_names_seen),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        log(f"💾 Progress saved to {progress_file}")
    except Exception as e:
        log(f"⚠️  Could not save progress: {e}")

def load_progress(artist_name):
    """Load processing progress if available."""
    progress_file = f"progress_{artist_name.replace(' ', '_').lower()}.json"
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            log(f"📂 Resuming from saved progress: {len(progress_data['processed_albums'])} albums already processed")
            return progress_data
        except Exception as e:
            log(f"⚠️  Could not load progress: {e}")
    
    return None

def ai_estimate_processing_time(total_albums, processed_albums, start_time):
    """
    AI-enhanced processing time estimation based on current performance.
    
    Args:
        total_albums: Total number of albums to process
        processed_albums: Number of albums already processed
        start_time: When processing started
        
    Returns:
        tuple: (estimated_remaining_seconds, estimated_total_seconds)
    """
    if processed_albums == 0:
        return None, None
    
    # Calculate current processing rate
    elapsed_time = (datetime.now() - start_time).total_seconds()
    albums_per_second = processed_albums / elapsed_time if elapsed_time > 0 else 0
    
    # AI Learning: Adjust estimate based on rate limit patterns
    global _ai_rate_limit_count
    if _ai_rate_limit_count > 0:
        # If we've hit rate limits, assume slower processing going forward
        albums_per_second *= (1 - _ai_rate_limit_count * 0.1)
    
    if albums_per_second > 0:
        remaining_albums = total_albums - processed_albums
        estimated_remaining = remaining_albums / albums_per_second
        estimated_total = total_albums / albums_per_second
        return estimated_remaining, estimated_total
    
    return None, None

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

def get_or_create_playlist(sp, artist_name):
    """Check if playlist already exists; if not, create one."""
    log(f"Checking for existing playlist: '{artist_name}'")
    me = sp.me()
    playlists = sp.current_user_playlists(limit=50)
    
    # Check all pages of playlists
    while playlists:
        for pl in playlists['items']:
            if pl['name'].lower() == artist_name.lower():
                log(f"Found existing playlist: {pl['name']}")
                return pl['id'], True  # Return playlist_id and exists=True
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            break

    # Create new playlist if not found
    log(f"Creating new playlist: '{artist_name}'")
    try:
        playlist = create_playlist_with_retry(
            sp, me['id'], artist_name, public=True, 
            description=f"Complete discography of {artist_name} (auto-generated)"
        )
        log(f"✅ Created playlist: {playlist['name']}")
        return playlist['id'], False  # Return playlist_id and exists=False
    except Exception as e:
        log(f"❌ Failed to create playlist: {e}")
        raise

def get_latest_release_date_from_playlist(sp, playlist_id):
    """Get the latest release date from existing playlist tracks."""
    log("Analyzing existing playlist to find latest release date...")
    
    tracks = get_playlist_tracks_with_retry(sp, playlist_id, limit=100)
    all_tracks = tracks['items']
    
    # Get all tracks (handle pagination)
    while tracks['next']:
        tracks = safe_spotify_call(sp.next, tracks)
        all_tracks.extend(tracks['items'])
    
    log(f"Found {len(all_tracks)} tracks in existing playlist")
    
    latest_date = None
    for item in all_tracks:
        track = item['track']
        if track and track.get('album'):
            release_date = track['album'].get('release_date', '1900-01-01')
    
    if latest_date:
        log(f"📅 Latest release date in existing playlist: {latest_date}")
        return latest_date
    else:
        log("⚠️  Could not determine latest date from playlist")
        return None

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_artist(artist_name, sp=None):
    """Process a single artist and create/update their playlist."""
    
    if sp is None:
        sp = get_spotify_client()
    
    log(f"🎵 Building playlist for: {artist_name}")
    log(f"⚙️  Using manual filtering (fast, reliable)")
    
    # Find artist
    log(f"Searching for artist: {artist_name}")
    results = get_artist_with_retry(sp, artist_name)
    
    if not results['artists']['items']:
        log(f"❌ Artist '{artist_name}' not found")
        return
    
    artist = results['artists']['items'][0]
    artist_id = artist['id']
    log(f"Found artist: {artist['name']} (ID: {artist_id})")
    
    # Get or create playlist
    playlist_id, playlist_exists = get_or_create_playlist(sp, artist_name)
    
    # Get latest release date from existing playlist (for incremental updates)
    latest_existing_date = None
    if playlist_exists:
        latest_existing_date = get_latest_release_date_from_playlist(sp, playlist_id)
        if latest_existing_date:
            existing_tracks_count = len(get_playlist_tracks_with_retry(sp, playlist_id, limit=100)['items'])
            log(f"📊 Existing playlist has {existing_tracks_count} tracks")
            log(f"Will only add releases after: {latest_existing_date}")
        else:
            log("Could not determine latest date - will add all tracks (may create duplicates)")

    # AI-OPTIMIZED COMPREHENSIVE MODE: Get ALL albums intelligently
    album_types_str = ",".join(INCLUDE_ALBUM_TYPES)
    log(f"🤖 AI-OPTIMIZED MODE: Fetching ALL discography ({album_types_str})...")
    
    # Check for existing progress
    progress_data = load_progress(artist_name)
    processed_album_ids = set(progress_data['processed_albums']) if progress_data else set()
    
    albums = get_albums_with_retry(sp, artist_id, album_types_str, limit=50)
    
    # Sort by release date (oldest first for chronological order)
    albums = sorted(albums, key=lambda x: x.get('release_date', '1900-01-01'))
    
    # Filter out already processed albums
    if progress_data:
        albums = [album for album in albums if album['id'] not in processed_album_ids]
        log(f"📂 Resuming: {len(albums)} albums remaining to process")
    
    original_album_count = len(albums)
    log(f"🎵 Total releases to process: {original_album_count}")
    
    if original_album_count == 0:
        log("✅ All albums already processed!")
        return
    
    # Count by type
    albums_count = len([a for a in albums if a['album_type'] == 'album'])
    singles_count = len([a for a in albums if a['album_type'] == 'single'])
    compilations_count = len([a for a in albums if a['album_type'] == 'compilation'])
    
    log(f"Processing {albums_count} albums, {singles_count} singles, {compilations_count} compilations")

    # AI-OPTIMIZED track collection with progress persistence
    log("🤖 AI-OPTIMIZED: Processing tracks with intelligent batching...")
    
    # Initialize track collection
    track_uris = []
    track_names_seen = set()
    
    # Load existing progress if available
    if progress_data:
        track_uris = progress_data['track_uris']
        track_names_seen = set(progress_data['track_names_seen'])
        log(f"📂 Resuming with {len(track_uris)} tracks already collected")
    
    # If playlist exists, add existing track names to avoid duplicates
    if playlist_exists and not progress_data:
        existing_tracks = get_playlist_tracks_with_retry(sp, playlist_id, limit=100)
        for item in existing_tracks['items']:
            if item['track']:
                track_names_seen.add(item['track']['name'])
        log(f"📋 Loaded {len(track_names_seen)} existing track names to avoid duplicates")
    
    # Statistics tracking
    new_releases_count = 0
    duplicates_skipped = 0
    popularity_skipped = 0
    manual_skipped = 0
    processed_albums = []
    
    # AI-Enhanced timing
    processing_start_time = datetime.now()
    log(f"🤖 AI Processing started at {processing_start_time.strftime('%H:%M:%S')}")
    
    # 🔄 RE-EVALUATION: Check recent releases for popularity changes
    today = date.today()
    re_evaluation_count = 0
    
    log(f"🔍 Checking for recent releases to re-evaluate (last {RE_EVALUATE_DAYS} days)...")
    
    for album in albums:
        album_date_str = album.get('release_date', '1900-01-01')
        try:
            if len(album_date_str) == 4:
                album_date = datetime.strptime(album_date_str, '%Y').date()
            elif len(album_date_str) == 7:
                album_date = datetime.strptime(album_date_str, '%Y-%m').date()
            else:
                album_date = datetime.strptime(album_date_str, '%Y-%m-%d').date()
        except ValueError:
            continue
            
        days_since_release = (today - album_date).days
        
        if days_since_release <= RE_EVALUATE_DAYS:
            re_evaluation_count += 1
            album_name = album.get('name', 'Unknown Album')
            album_type = album.get('album_type', 'unknown')
            log(f"  🔄 Re-evaluating recent {album_type}: {album_name} (released {days_since_release} days ago)")
    
    if re_evaluation_count > 0:
        log(f"📊 Found {re_evaluation_count} recent releases to re-evaluate for popularity changes")
    else:
        log(f"📊 No recent releases found within last {RE_EVALUATE_DAYS} days")
    
    # AI-OPTIMIZED: Process albums in intelligent batches
    for i, album in enumerate(albums, 1):
        album_date_str = album.get('release_date', '1900-01-01')
        album_name = album.get('name', 'Unknown Album')
        album_type = album.get('album_type', 'unknown')
        
        # Parse album date for re-evaluation logic
        try:
            if len(album_date_str) == 4:
                album_date = datetime.strptime(album_date_str, '%Y').date()
            elif len(album_date_str) == 7:
                album_date = datetime.strptime(album_date_str, '%Y-%m').date()
            else:
                album_date = datetime.strptime(album_date_str, '%Y-%m-%d').date()
        except ValueError:
            album_date = date(1900, 1, 1)  # Fallback to old date
        
        # Skip if this release is older than or equal to our latest existing date
        if latest_existing_date and album_date_str <= latest_existing_date:
            log(f"  ⏭️  Skipping existing {album_type}: {album_name} ({album_date_str}) - already in playlist")
            continue
            
        new_releases_count += 1
        tracks = get_tracks_with_retry(sp, album['id'])
        
        # Log the release being processed
        log(f"  🔍 Processing {album_type.title()}: {album_name} ({album_date_str})")
        
        # 🚀 AI-OPTIMIZATION: Get all track details in one batch call
        track_ids = [track['id'] for track in tracks['items']]
        track_details = get_track_details_batch(sp, track_ids)
        
        # Create a mapping of track_id to full track details
        track_details_map = {}
        for j, track_id in enumerate(track_ids):
            if j < len(track_details) and track_details[j]:
                track_details_map[track_id] = track_details[j]
        
        for track in tracks['items']:
            track_name = track['name']
            track_id = track['id']
            
            # Get full track details from our batch call
            full_track = track_details_map.get(track_id, track)
            track_popularity = full_track.get('popularity', 0)
            
            # 🎯 STEP 0: Quality check first (fastest filter)
            should_skip_quality, quality_reason = should_skip_low_quality_track(full_track)
            if should_skip_quality:
                log(f"     ⏭️  Skipped (quality): {track_name} - {quality_reason}")
                continue
            
            # 📊 STEP 1: Analyze popularity first (smart filtering based on album type)
            should_skip_popularity, popularity_reason, actual_popularity = analyze_track_popularity(
                full_track, tracks['items'], album_name, album_type, track_details
            )
            
            if should_skip_popularity:
                log(f"     ⏭️  Skipped (unpopular): {track_name} - {popularity_reason}")
                popularity_skipped += 1
                continue
            
            # ⚙️ STEP 2: Manual filtering (fast, reliable keyword-based filtering)
            should_skip, manual_reason = should_skip_track_manual(
                track_name, album_name, artist_name
            )
            
            if should_skip:
                log(f"     ⏭️  Skipped (not song): {track_name} - {manual_reason}")
                manual_skipped += 1
                continue
            
            # 🔄 STEP 3: Basic duplicate check (exact name matches)
            if track_name in track_names_seen:
                log(f"     ⏭️  Skipped (duplicate): {track_name} - exact name already seen")
                duplicates_skipped += 1
                continue
            
            # ✅ STEP 4: Track passed all filters
            track_uris.append(track['uri'])
            track_names_seen.add(track_name)
            
            # Special logging for re-evaluated tracks
            days_since_release = (today - album_date).days
            if days_since_release <= RE_EVALUATE_DAYS:
                log(f"     🔄 Re-added (now popular): {track_name} (popularity: {actual_popularity:.1f}/100, released {days_since_release} days ago)")
            else:
                log(f"     ✓ Added: {track_name} (popularity: {actual_popularity:.1f}/100)")
        
        # Mark album as processed
        processed_albums.append(album)
        
        # AI-OPTIMIZED: Save progress periodically
        if i % PROGRESS_SAVE_INTERVAL == 0:
            save_progress(artist_name, processed_albums, track_uris, track_names_seen)
            log(f"  💾 Progress saved: {i}/{len(albums)} albums processed")
        
        # AI-Enhanced progress update with intelligent ETA estimation
        if i % 5 == 0:  # Progress update every 5 albums
            estimated_remaining, estimated_total = ai_estimate_processing_time(len(albums), i, processing_start_time)
            
            if estimated_remaining is not None:
                remaining_minutes = int(estimated_remaining // 60)
                remaining_seconds = int(estimated_remaining % 60)
                total_minutes = int(estimated_total // 60)
                total_seconds = int(estimated_total % 60)
                
                log(f"  🤖 AI Progress: {i}/{len(albums)} albums ({i/len(albums)*100:.1f}%)")
                log(f"     ⏱️  ETA: {remaining_minutes}m {remaining_seconds}s remaining (Total: {total_minutes}m {total_seconds}s)")
            else:
                log(f"  📊 Progress: {i}/{len(albums)} albums ({i/len(albums)*100:.1f}%) - Calculating ETA...")
        
        # Adaptive delay based on processing speed
        if i < len(albums) - 1:
            delay = ADAPTIVE_DELAY_BASE * (1 + (i / len(albums)))  # Increase delay as we progress
            time.sleep(delay)
    
    if playlist_exists and latest_existing_date:
        log(f"Found {new_releases_count} new releases since {latest_existing_date}")
    else:
        log(f"Processing all {len(albums)} releases")

    # Remove duplicates while preserving chronological order
    original_count = len(track_uris)
    unique_track_uris = []
    seen = set()
    for uri in track_uris:
        if uri not in seen:
            unique_track_uris.append(uri)
            seen.add(uri)
    final_count = len(unique_track_uris)
    
    if original_count != final_count:
        log(f"Removed {original_count - final_count} duplicate track URIs")

    # Summary statistics
    log(f"📊 COLLECTION STATS:")
    log(f"   • Collected {final_count} unique tracks")
    log(f"   • Manual filtering removed {manual_skipped} tracks")
    log(f"   • Popularity filtering removed {popularity_skipped} tracks")

    # Add tracks to playlist
    if track_uris:
        log(f"Adding {final_count} tracks to playlist...")
        add_tracks_to_playlist_with_retry(sp, playlist_id, unique_track_uris)
        
        if playlist_exists:
            log(f"✅ Successfully added {final_count} new tracks to existing '{artist_name}' playlist")
        else:
            log(f"✅ Successfully created new '{artist_name}' playlist with {final_count} tracks")
        
        # Clean up progress file after successful completion
        progress_file = f"progress_{artist_name.replace(' ', '_').lower()}.json"
        if os.path.exists(progress_file):
            os.remove(progress_file)
            log(f"🧹 Cleaned up progress file: {progress_file}")
    else:
        log("ℹ️  No new tracks to add")

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Main function to handle command line arguments."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "batch":
            log("🚀 Starting batch processing...")
            if 'ARTISTS' in globals() and globals().get('ARTISTS'):
                for artist in globals()['ARTISTS']:
                    try:
                        process_artist(artist)
                        log(f"✅ Completed: {artist}")
                        import time
                        time.sleep(2)  # Brief pause between artists
                    except Exception as e:
                        log(f"❌ Failed to process {artist}: {e}")
                        continue
            else:
                log("❌ ARTISTS list not defined. Please uncomment and configure the ARTISTS list.")
            return
                
        elif command == "undo":
            log("🔄 Undo functionality not implemented yet")
            return
            
            
        else:
            log(f"❌ Unknown command: {command}")
            log("Available commands: batch, undo")
            return
    else:
        # Single artist mode - use configured artist
        if 'ARTIST_NAME' in globals() and ARTIST_NAME:
            log(f"🎵 Processing artist: {ARTIST_NAME}")
            process_artist(ARTIST_NAME)
        else:
            log("❌ ARTIST_NAME not defined. Please configure ARTIST_NAME.")
            return

if __name__ == "__main__":
    main()
