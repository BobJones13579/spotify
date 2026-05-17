#!/usr/bin/env python3
"""
Pragmatic Lifetime Streams Estimator

A practical, conservative approach to estimating stream counts that balances accuracy
with simplicity. Designed to reduce false positives while still filtering out genuinely
unpopular tracks for playlist automation.

Strategy:
- For very old songs (>6 years): Use Last.fm data (proven 67% accuracy)
- For newer songs (<6 years): Use Spotify popularity with conservative multipliers
- Focus on reducing false positives rather than perfect accuracy
"""

import math
from datetime import datetime, date
from typing import Dict, Any, Optional

def estimate_lifetime_streams(track_data: Dict[str, Any], audio_features: Optional[Dict[str, Any]] = None, lastfm_data: Optional[Dict[str, Any]] = None) -> int:
    """
    Pragmatic streams estimation using age-based hybrid approach.
    
    Args:
        track_data: Track metadata from Spotify API
        audio_features: Audio features from Spotify API (unused - kept for compatibility)
        lastfm_data: Last.fm data with actual play counts
    
    Returns:
        Estimated lifetime stream count (conservative estimates)
    """
    
    # Get track age
    track_age_days = _get_track_age_days(track_data)
    
    # Age-based hybrid approach
    if track_age_days > 2190:  # >6 years old
        # Use Last.fm for old songs (67% accuracy proven)
        if lastfm_data and lastfm_data.get('found') and lastfm_data.get('playcount', 0) > 0:
            return _estimate_from_lastfm_conservative(lastfm_data, track_data)
    
    # For newer songs or when Last.fm data unavailable, use conservative Spotify-based estimate
    return _estimate_from_spotify_conservative(track_data)

def _get_track_age_days(track_data: Dict[str, Any]) -> int:
    """Calculate track age in days."""
    try:
        release_date_str = track_data.get('album', {}).get('release_date', '1900-01-01')
        
        # Parse different date formats
        if len(release_date_str) == 4:  # Year only
            release_date = datetime.strptime(release_date_str, '%Y').date()
        elif len(release_date_str) == 7:  # Year-Month
            release_date = datetime.strptime(release_date_str, '%Y-%m').date()
        else:  # Full date
            release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
        
        # Calculate days since release
        days_since_release = (date.today() - release_date).days
        return max(0, days_since_release)
        
    except (ValueError, TypeError):
        return 0  # Fallback for invalid dates

def _estimate_from_lastfm_conservative(lastfm_data: Dict[str, Any], track_data: Dict[str, Any]) -> int:
    """Conservative Last.fm estimation for old songs (proven 67% accuracy)."""
    playcount = lastfm_data.get('playcount', 0)
    
    # Conservative conversion factor for old songs
    # Based on your data showing 67% accuracy for songs >6 years old
    # Using 200x instead of 220x to be more conservative
    base_conversion = 200
    
    estimated_streams = playcount * base_conversion
    return int(estimated_streams)

def _estimate_from_spotify_conservative(track_data: Dict[str, Any]) -> int:
    """
    Conservative Spotify popularity-based estimation for newer songs.
    
    Uses conservative multipliers to reduce false positives while still
    filtering out genuinely unpopular tracks.
    """
    popularity = track_data.get('popularity', 50)
    
    # Conservative base multiplier (3M streams per popularity point instead of 5M)
    # This reduces false positives while maintaining discrimination
    base_multiplier = 3000000
    
    # Apply album type multiplier (conservative)
    album_type = track_data.get('album', {}).get('album_type', 'album')
    if album_type == 'single':
        type_multiplier = 1.2  # Singles get slight boost
    elif album_type == 'compilation':
        type_multiplier = 1.1  # Compilations get slight boost
    else:
        type_multiplier = 1.0  # Albums baseline
    
    estimated_streams = popularity * base_multiplier * type_multiplier
    return int(estimated_streams)

# Removed complex heuristic functions - using simpler, more conservative approach

def format_stream_count(stream_count: int) -> str:
    """
    Format stream count in human-readable format.
    
    Examples:
        1234 -> "1.2K"
        1234567 -> "1.2M"
        1234567890 -> "1.2B"
    """
    if stream_count >= 1_000_000_000:
        return f"{stream_count / 1_000_000_000:.1f}B"
    elif stream_count >= 1_000_000:
        return f"{stream_count / 1_000_000:.1f}M"
    elif stream_count >= 1_000:
        return f"{stream_count / 1_000:.1f}K"
    else:
        return str(stream_count)

def get_stream_quality_tier(stream_count: int) -> str:
    """
    Categorize stream count into conservative quality tiers.
    
    More conservative thresholds to reduce false positives while still
    filtering out genuinely unpopular tracks.
            
    Returns:
        Quality tier: 'low', 'decent', 'popular', 'hit'
    """
    if stream_count >= 10_000_000:  # 10M+ = hit (more conservative)
        return 'hit'
    elif stream_count >= 1_000_000:  # 1M+ = popular (more conservative)
        return 'popular'
    elif stream_count >= 100_000:   # 100K+ = decent (more conservative)
        return 'decent'
    else:
        return 'low'

# Example usage and testing
if __name__ == "__main__":
    # Test with sample data - newer song (will use Spotify popularity)
    sample_track_new = {
        'popularity': 75,
        'album': {
            'release_date': '2020-01-01',  # <6 years old
            'album_type': 'single'
        }
    }
    
    # Test with sample data - old song (will use Last.fm if available)
    sample_track_old = {
        'popularity': 65,
        'album': {
            'release_date': '2010-01-01',  # >6 years old
            'album_type': 'album'
        }
    }
    
    sample_lastfm_data = {
        'found': True,
        'playcount': 50000,  # 50K Last.fm plays
        'listeners': 5000
    }
    
    print("=== Pragmatic Streams Estimation Test ===")
    
    # Test newer song (Spotify-based)
    estimated_new = estimate_lifetime_streams(sample_track_new, None, None)
    print(f"New song (2020): {format_stream_count(estimated_new)} - {get_stream_quality_tier(estimated_new)} tier")
    
    # Test old song with Last.fm data
    estimated_old = estimate_lifetime_streams(sample_track_old, None, sample_lastfm_data)
    print(f"Old song with Last.fm: {format_stream_count(estimated_old)} - {get_stream_quality_tier(estimated_old)} tier")
    
    # Test old song without Last.fm data (fallback)
    estimated_old_fallback = estimate_lifetime_streams(sample_track_old, None, None)
    print(f"Old song without Last.fm: {format_stream_count(estimated_old_fallback)} - {get_stream_quality_tier(estimated_old_fallback)} tier")
