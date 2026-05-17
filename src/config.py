"""Configuration for the Spotify playlist creator."""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env from project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ============================================================================
# SPOTIFY API CONFIGURATION
# ============================================================================

# Spotify API Credentials
# Get these from: https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private"

# Spotify API Settings
SPOTIFY_REQUESTS_TIMEOUT = 30
SPOTIFY_RETRIES = 10

# ============================================================================
# LAST.FM API CONFIGURATION
# ============================================================================

# Last.fm API Credentials (optional - for enhanced streams estimation)
# Get your API key from: https://www.last.fm/api/
# For security, set LASTFM_API_KEY environment variable instead of hardcoding
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")

# ============================================================================
# AI CONFIGURATION
# ============================================================================

# AI System Settings
AI_ENABLED = True  # Set to False to disable AI and use only manual rules
AI_MODEL = "llama3.1"  # The Ollama model to use (llama3.1, mistral, codellama)
AI_TIMEOUT = 30  # Timeout for AI requests in seconds
AI_OLLAMA_URL = "http://localhost:11434/api/generate"

# AI Model Options
AVAILABLE_AI_MODELS = [
    "llama3.1",
    "mistral", 
    "codellama",
    "llama2"
]

# ============================================================================
# POPULARITY FILTERING
# ============================================================================

# Popularity filtering (off by default — add tracks, curate in Spotify)
ENABLE_POPULARITY_FILTER = os.getenv("ENABLE_POPULARITY_FILTER", "false").lower() in (
    "true", "1", "yes", "on"
)
MIN_POPULARITY_THRESHOLD = int(os.getenv("MIN_POPULARITY_THRESHOLD", "5"))
POPULARITY_RATIO_THRESHOLD = float(os.getenv("POPULARITY_RATIO_THRESHOLD", "0.01"))

LOG_POPULARITY_DECISIONS = False
LOG_AI_DECISIONS = True  # Log AI decision reasoning

# ============================================================================
# ARTIST CONFIGURATION
# ============================================================================

# Default Artist (for single artist mode)
DEFAULT_ARTIST_NAME = "Taylor Swift"

# Batch Artists (for batch processing mode)
BATCH_ARTISTS: List[str] = [
    "Taylor Swift",
    "Niall Horan", 
    "Chappell Roan"
]

# ============================================================================
# STREAMLIT CONFIGURATION
# ============================================================================

# Page Configuration
PAGE_TITLE = "🎵 AI Playlist Creator"
PAGE_ICON = "🎵"
LAYOUT = "wide"

# UI Settings
SIDEBAR_EXPANDED = True
SHOW_PROGRESS = True
REAL_TIME_LOGS = True

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================

# Batch Processing
BATCH_SIZE = 100  # Number of tracks to add to playlist per batch
MAX_ARTISTS_BATCH = 10  # Maximum number of artists to process in batch mode

# Performance Settings
ENABLE_CACHING = True  # Enable AI response caching
CACHE_SIZE_LIMIT = 1000  # Maximum number of cached AI responses

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_config() -> List[str]:
    """
    Validate configuration settings and return any errors.
    
    Returns:
        List of error messages (empty if no errors)
    """
    errors = []
    
    # Validate Spotify credentials
    if not SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_ID == "your_client_id_here":
        errors.append("SPOTIFY_CLIENT_ID is not set")
    
    if not SPOTIFY_CLIENT_SECRET or SPOTIFY_CLIENT_SECRET == "your_client_secret_here":
        errors.append("SPOTIFY_CLIENT_SECRET is not set")
    
    # Validate popularity thresholds
    if not 0 <= MIN_POPULARITY_THRESHOLD <= 100:
        errors.append("MIN_POPULARITY_THRESHOLD must be between 0 and 100")
    
    if not 0.0 <= POPULARITY_RATIO_THRESHOLD <= 1.0:
        errors.append("POPULARITY_RATIO_THRESHOLD must be between 0.0 and 1.0")
    
    return errors

def get_config_summary() -> dict:
    """
    Get a summary of current configuration for display in the UI.
    
    Returns:
        Dictionary with configuration summary
    """
    return {
        "ai_enabled": AI_ENABLED,
        "ai_model": AI_MODEL,
        "min_popularity": MIN_POPULARITY_THRESHOLD,
        "popularity_ratio": POPULARITY_RATIO_THRESHOLD,
        "default_artist": DEFAULT_ARTIST_NAME,
        "batch_artists_count": len(BATCH_ARTISTS),
        "spotify_configured": bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET),
    }

# ============================================================================
# ENVIRONMENT VARIABLE HELPERS
# ============================================================================

def load_from_env() -> None:
    """
    Load configuration from environment variables.
    This allows for secure credential management in production.
    """
    global SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    
    # Load from environment if available
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", SPOTIFY_CLIENT_ID)
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", SPOTIFY_CLIENT_SECRET)
    
    # Load other settings from environment
    ai_enabled = os.getenv("AI_ENABLED")
    if ai_enabled is not None:
        global AI_ENABLED
        AI_ENABLED = ai_enabled.lower() in ("true", "1", "yes", "on")

# Load environment variables on import
load_from_env()

# Validate configuration on import
config_errors = validate_config()
if config_errors:
    print("⚠️  Configuration warnings:")
    for error in config_errors:
        print(f"   - {error}")
    print("\nPlease check your configuration in src/config.py")
