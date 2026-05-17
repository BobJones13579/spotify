"""
Progress Utilities Module

Handles progress saving, loading, and ETA estimation for long-running operations.
"""

import json
import os
from datetime import datetime

def log(message: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def save_progress(artist_name, processed_albums, track_uris, track_names_seen):
    """Save processing progress to resume later if needed."""
    # Debug: Log the artist name being used for progress file
    log(f"💾 Saving progress for artist: '{artist_name}' (type: {type(artist_name)})")
    
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
    # Note: This would need access to the rate limit count from spotify_client
    # For now, we'll use a simple estimation
    
    if albums_per_second > 0:
        remaining_albums = total_albums - processed_albums
        estimated_remaining = remaining_albums / albums_per_second
        estimated_total = total_albums / albums_per_second
        return estimated_remaining, estimated_total
    
    return None, None
