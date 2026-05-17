"""
Spotify API Client Module

Handles all Spotify API interactions with intelligent rate limiting and retry logic.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import random
from datetime import datetime

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPE
)

# AI Learning State (global variables for learning across calls)
_ai_rate_limit_count = 0
_ai_consecutive_rate_limits = 0
_ai_adaptive_delay = 0.2

# AI-Enhanced Rate Limiting Intelligence
AI_RATE_LIMIT_LEARNING = True
MAX_CONSECUTIVE_RATE_LIMITS = 3
INTELLIGENT_BACKOFF_MULTIPLIER = 1.5

def log(message: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def safe_spotify_call(func, *args, max_retries=5, base_delay=2, **kwargs):
    """
    AI-Enhanced Spotify API call with intelligent rate limiting and learning.
    Learns from rate limit patterns and adapts behavior accordingly.
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

def get_track_details_batch(sp, track_ids, batch_size=50):
    """AI-optimized batch track details fetching with intelligent error handling."""
    if not track_ids:
        return []
    
    all_tracks = []
    
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        try:
            tracks = safe_spotify_call(sp.tracks, batch)
            all_tracks.extend(tracks['tracks'])
            
            # Adaptive delay based on batch size and API response
            if i + batch_size < len(track_ids):
                delay = 0.2 * (len(batch) / 50)  # Scale delay with batch size
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
                time.sleep(0.2)
                
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

def get_audio_features_batch(sp, track_ids, batch_size=100):
    """
    Get audio features for multiple tracks in batches.
    Audio features include danceability, energy, valence, etc.
    
    Note: Audio features API requires premium Spotify API access.
    If unavailable, returns None for all tracks.
    """
    all_audio_features = []
    
    # Process in batches (audio features API allows up to 100 tracks per request)
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        
        try:
            # Get audio features for this batch
            audio_features = safe_spotify_call(sp.audio_features, batch)
            all_audio_features.extend(audio_features)
            
            # Small delay between batches
            time.sleep(0.1)
            
        except Exception as e:
            error_msg = str(e).lower()
            if '403' in error_msg or 'forbidden' in error_msg:
                log(f"     ⚠️  Audio features API not available (403 Forbidden) - continuing without audio features")
                # Return None for all tracks if we can't access audio features
                return [None] * len(track_ids)
            else:
                log(f"Error fetching audio features batch: {e}")
                # Add None for failed tracks
                all_audio_features.extend([None] * len(batch))
    
    return all_audio_features

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
            
            # Compare and find the latest date
            if latest_date is None or release_date > latest_date:
                latest_date = release_date
    
    if latest_date:
        log(f"📅 Latest release date in existing playlist: {latest_date}")
        return latest_date
    else:
        log("⚠️  Could not determine latest date from playlist")
        return None
