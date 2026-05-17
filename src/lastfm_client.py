#!/usr/bin/env python3
"""
Last.fm API Client

Provides access to Last.fm's extensive music database including actual play counts
and listener counts for tracks. This data can significantly improve our streams estimation.

Last.fm API is free for non-commercial use with no rate limits.
"""

import requests
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Last.fm API configuration
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"
LASTFM_API_KEY = None  # Set this in config.py

def log(message: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def set_lastfm_api_key(api_key: str):
    """Set the Last.fm API key."""
    global LASTFM_API_KEY
    LASTFM_API_KEY = api_key

def get_track_info(artist_name: str, track_name: str) -> Optional[Dict[str, Any]]:
    """
    Get track information from Last.fm including play counts and listener counts.
    
    Args:
        artist_name: Name of the artist
        track_name: Name of the track
    
    Returns:
        Dictionary with track info including playcount and listeners, or None if not found
    """
    if not LASTFM_API_KEY:
        log("⚠️  Last.fm API key not set - skipping Last.fm data")
        return None
    
    try:
        params = {
            'method': 'track.getInfo',
            'api_key': LASTFM_API_KEY,
            'artist': artist_name,
            'track': track_name,
            'format': 'json'
        }
        
        response = requests.get(LASTFM_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if track was found
        if 'track' in data and data['track']:
            track_info = data['track']
            
            # Extract relevant data
            result = {
                'name': track_info.get('name', track_name),
                'artist': track_info.get('artist', {}).get('name', artist_name),
                'playcount': int(track_info.get('playcount', 0)),
                'listeners': int(track_info.get('listeners', 0)),
                'url': track_info.get('url', ''),
                'mbid': track_info.get('mbid', ''),
                'found': True
            }
            
            return result
        else:
            # Track not found
            return {
                'name': track_name,
                'artist': artist_name,
                'playcount': 0,
                'listeners': 0,
                'found': False
            }
            
    except requests.exceptions.RequestException as e:
        log(f"⚠️  Last.fm API error for {artist_name} - {track_name}: {e}")
        return None
    except (ValueError, KeyError) as e:
        log(f"⚠️  Last.fm data parsing error for {artist_name} - {track_name}: {e}")
        return None

def get_track_info_batch(artist_track_pairs: list) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Get track information for multiple artist-track pairs.
    
    Args:
        artist_track_pairs: List of (artist_name, track_name) tuples
    
    Returns:
        Dictionary mapping (artist, track) tuples to track info
    """
    results = {}
    
    for artist_name, track_name in artist_track_pairs:
        # Small delay to be respectful to Last.fm
        time.sleep(0.1)
        
        track_info = get_track_info(artist_name, track_name)
        if track_info:
            results[(artist_name, track_name)] = track_info
    
    return results

def estimate_streams_from_lastfm(lastfm_data: Dict[str, Any]) -> Optional[int]:
    """
    Estimate Spotify streams from Last.fm data.
    
    Last.fm playcount is typically much lower than Spotify streams because:
    1. Last.fm has fewer users
    2. Last.fm tracks scrobbles (listens), not streams
    3. Spotify has much larger user base
    
    Rough conversion factor: Last.fm playcount × 10-50 = estimated Spotify streams
    """
    if not lastfm_data or not lastfm_data.get('found'):
        return None
    
    playcount = lastfm_data.get('playcount', 0)
    listeners = lastfm_data.get('listeners', 0)
    
    if playcount == 0:
        return None
    
    # Conversion factor based on typical ratios
    # Last.fm playcount is usually 1/20 to 1/50 of Spotify streams
    conversion_factor = 25  # Middle ground
    
    estimated_spotify_streams = playcount * conversion_factor
    
    return int(estimated_spotify_streams)

# Example usage and testing
if __name__ == "__main__":
    # Test with a known track
    test_artist = "Air Supply"
    test_track = "All Out of Love"
    
    print(f"Testing Last.fm API with: {test_artist} - {test_track}")
    
    # Note: You'll need to set your API key first
    # set_lastfm_api_key("your_api_key_here")
    
    track_info = get_track_info(test_artist, test_track)
    if track_info:
        print(f"Last.fm data: {track_info}")
        estimated = estimate_streams_from_lastfm(track_info)
        if estimated:
            print(f"Estimated Spotify streams: {estimated:,}")
    else:
        print("No Last.fm data found")
