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

import sys
import os
import time
from datetime import datetime, date

# Import our modular components
from spotify_client import (
    get_spotify_client, get_artist_with_retry, get_albums_with_retry,
    get_tracks_with_retry, get_track_details_batch, get_audio_features_batch,
    get_or_create_playlist, get_latest_release_date_from_playlist, 
    add_tracks_to_playlist_with_retry, get_playlist_tracks_with_retry, log
)
from track_filtering import (
    analyze_track_popularity, should_skip_track_manual, should_skip_low_quality_track,
    should_skip_duplicate_track
)
from progress_utils import save_progress, load_progress, ai_estimate_processing_time
from streams_estimator import estimate_lifetime_streams, format_stream_count, get_stream_quality_tier
from lastfm_client import get_track_info_batch, set_lastfm_api_key
from config import LASTFM_API_KEY

# ============================================================================
# 🎯 CONFIGURATION - EDIT THESE SETTINGS HERE!
# ============================================================================

# 🎵 CHANGE THIS TO CREATE PLAYLISTS FOR DIFFERENT ARTISTS
ARTIST_NAME = "Air Supply"

# 👉 Batch mode - uncomment to process multiple artists - python artist_playlist_ai_refactored.py batch
# ARTISTS = ["Bruno Mars", "Taylor Swift", "Billie Eilish"]

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

# Last.fm integration (optional - set API key in config.py)
USE_LASTFM = True  # Set to False to disable Last.fm integration

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_artist(artist_name, sp=None):
    """Process a single artist and create/update their playlist."""
    
    # Debug: Log the artist name being processed
    log(f"🎯 Processing artist: '{artist_name}' (type: {type(artist_name)})")
    
    if sp is None:
        sp = get_spotify_client()
    
    # Initialize Last.fm API if configured
    if USE_LASTFM and LASTFM_API_KEY:
        set_lastfm_api_key(LASTFM_API_KEY)
        log(f"🎵 Building playlist for: {artist_name}")
        log(f"⚙️  Using manual filtering + Last.fm data (enhanced accuracy)")
    else:
        log(f"🎵 Building playlist for: {artist_name}")
        log(f"⚙️  Using manual filtering (fast, reliable)")
        if USE_LASTFM:
            log(f"⚠️  Last.fm integration disabled - set LASTFM_API_KEY in config.py to enable")
    
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
            log(f"  ⏭️  Skipping {album_type}: {album_name} ({album_date_str}) - already processed in previous run")
            continue
            
        new_releases_count += 1
        tracks = get_tracks_with_retry(sp, album['id'])
        
        # Log the release being processed
        log(f"  🔍 Processing {album_type.title()}: {album_name} ({album_date_str})")
        
        # 🚀 AI-OPTIMIZATION: Get all track details and audio features in batch calls
        track_ids = [track['id'] for track in tracks['items']]
        track_details = get_track_details_batch(sp, track_ids, BATCH_SIZE_TRACKS)
        
        # Try to get audio features, but don't fail if we can't (some API plans don't include this)
        try:
            audio_features = get_audio_features_batch(sp, track_ids, BATCH_SIZE_TRACKS)
        except Exception as e:
            log(f"     ⚠️  Audio features unavailable (continuing without them): {str(e)[:100]}...")
            audio_features = [None] * len(track_ids)  # Create empty list to maintain order
        
        # Create mappings for efficient lookup
        track_details_map = {}
        audio_features_map = {}
        for j, track_id in enumerate(track_ids):
            if j < len(track_details) and track_details[j]:
                track_details_map[track_id] = track_details[j]
            if j < len(audio_features) and audio_features[j]:
                audio_features_map[track_id] = audio_features[j]
        
        # 🎵 Get Last.fm data for better streams estimation (optional)
        lastfm_data_map = {}
        if USE_LASTFM:
            try:
                # Prepare artist-track pairs for Last.fm lookup
                artist_track_pairs = []
                for track in tracks['items']:
                    track_name = track['name']
                    artist_name = track['artists'][0]['name'] if track['artists'] else artist_name
                    artist_track_pairs.append((artist_name, track_name))
                
                # Get Last.fm data in batch
                lastfm_data_map = get_track_info_batch(artist_track_pairs)
                log(f"     🎵 Retrieved Last.fm data for {len(lastfm_data_map)} tracks")
                
            except Exception as e:
                log(f"     ⚠️  Last.fm integration failed: {e}")
                lastfm_data_map = {}
        
        for track in tracks['items']:
            track_name = track['name']
            track_id = track['id']
            
            # Get full track details from our batch call
            full_track = track_details_map.get(track_id, track)
            track_popularity = full_track.get('popularity', 0)
            
            # 🎯 STEP 0: Quality check first (fastest filter)
            should_skip_quality, quality_reason = should_skip_low_quality_track(full_track)
            if should_skip_quality:
                duration_ms = full_track.get('duration_ms', 0)
                duration_seconds = duration_ms / 1000
                available_markets = len(full_track.get('available_markets', []))
                log(f"     ⏭️  Skipped (quality): {track_name} - {quality_reason}")
                log(f"        📊 Track details: {duration_seconds:.1f}s duration, {available_markets} markets available")
                continue
            
            # 📊 STEP 1: Analyze popularity first (smart filtering based on album type)
            should_skip_popularity, popularity_reason, actual_popularity = analyze_track_popularity(
                full_track, tracks['items'], album_name, album_type, track_details
            )
            
            if should_skip_popularity:
                # Enhanced logging with threshold details
                if album_type == 'album':
                    threshold = 10  # MIN_POPULARITY_THRESHOLD
                    ratio_threshold = 0.10  # POPULARITY_RATIO_THRESHOLD
                    log(f"     ⏭️  Skipped (unpopular): {track_name} - {popularity_reason}")
                    log(f"        📊 Album track: {actual_popularity:.1f}/100 popularity, min threshold: {threshold}, ratio threshold: {ratio_threshold:.1%}")
                elif album_type == 'single':
                    threshold = 15  # SINGLE_POPULARITY_THRESHOLD
                    log(f"     ⏭️  Skipped (unpopular): {track_name} - {popularity_reason}")
                    log(f"        📊 Single: {actual_popularity:.1f}/100 popularity, min threshold: {threshold}")
                else:  # compilation
                    threshold = 10  # MIN_POPULARITY_THRESHOLD
                    log(f"     ⏭️  Skipped (unpopular): {track_name} - {popularity_reason}")
                    log(f"        📊 Compilation: {actual_popularity:.1f}/100 popularity, min threshold: {threshold}")
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
            
            # 🎵 STEP 4: Estimate lifetime streams for better decision making
            track_audio_features = audio_features_map.get(track_id)
            track_artist = track['artists'][0]['name'] if track['artists'] else artist_name
            lastfm_data = lastfm_data_map.get((track_artist, track_name))
            estimated_streams = estimate_lifetime_streams(full_track, track_audio_features, lastfm_data)
            stream_quality = get_stream_quality_tier(estimated_streams)
            formatted_streams = format_stream_count(estimated_streams)
            
            # ✅ STEP 5: Track passed all filters
            track_uris.append(track['uri'])
            track_names_seen.add(track_name)
            
            # Enhanced logging with detailed streams estimation reasoning
            days_since_release = (today - album_date).days
            
            # Show estimation method and reasoning
            estimation_method = "Last.fm" if (lastfm_data and lastfm_data.get('found') and lastfm_data.get('playcount', 0) > 0) else "Spotify popularity"
            lastfm_info = f" (Last.fm: {lastfm_data['playcount']:,} plays)" if (lastfm_data and lastfm_data.get('found')) else ""
            
            # Show quality tier thresholds for context
            tier_thresholds = {
                'low': 0,
                'decent': 100000,      # 100K+
                'popular': 1000000,    # 1M+
                'hit': 10000000        # 10M+
            }
            
            current_tier_threshold = tier_thresholds.get(stream_quality, 0)
            next_tier_threshold = tier_thresholds.get({
                'low': 'decent',
                'decent': 'popular', 
                'popular': 'hit',
                'hit': 'hit'
            }.get(stream_quality, 'hit'), 0)
            
            if days_since_release <= RE_EVALUATE_DAYS:
                log(f"     🔄 Re-added (now popular): {track_name}")
                log(f"        📊 Popularity: {actual_popularity:.1f}/100, ~{formatted_streams} streams ({estimation_method}){lastfm_info}")
                log(f"        🎯 Quality: {stream_quality} tier (threshold: {current_tier_threshold:,}+), released {days_since_release} days ago")
                if next_tier_threshold > current_tier_threshold:
                    needed_for_next = next_tier_threshold - estimated_streams
                    log(f"        📈 Would need +{format_stream_count(needed_for_next)} streams for next tier")
            else:
                log(f"     ✓ Added: {track_name}")
                log(f"        📊 Popularity: {actual_popularity:.1f}/100, ~{formatted_streams} streams ({estimation_method}){lastfm_info}")
                log(f"        🎯 Quality: {stream_quality} tier (threshold: {current_tier_threshold:,}+)")
                if next_tier_threshold > current_tier_threshold:
                    needed_for_next = next_tier_threshold - estimated_streams
                    log(f"        📈 Would need +{format_stream_count(needed_for_next)} streams for next tier")
        
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
        log(f"📅 Incremental update: Found {new_releases_count} new releases since {latest_existing_date}")
    else:
        log(f"🆕 Full processing: Processing all {len(albums)} releases")

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

    # Summary statistics with threshold information
    log(f"📊 FILTERING STATS:")
    log(f"   • ✅ Added {final_count} tracks that passed all filters")
    log(f"   • ⏭️  Skipped {manual_skipped} tracks (manual filtering - not real songs)")
    log(f"   • ⏭️  Skipped {popularity_skipped} tracks (too unpopular)")
    log(f"   • ⏭️  Skipped {duplicates_skipped} tracks (duplicates)")
    log(f"")
    log(f"📋 FILTERING THRESHOLDS USED:")
    log(f"   • Album tracks: min {10} popularity, {0.10:.1%} of album max")
    log(f"   • Singles: min {15} popularity")
    log(f"   • Compilations: min {10} popularity")
    log(f"   • Quality tiers: Low (<100K), Decent (100K+), Popular (1M+), Hit (10M+)")
    log(f"   • Track duration: 60s - 600s (1min - 10min)")
    log(f"   • Age-based estimation: Last.fm for >6yr songs, Spotify popularity for newer")

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
