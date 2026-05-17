# Simple Spotify Playlist Creator

A simple command-line tool that creates AI-enhanced Spotify playlists for artists. Just change one line of code to specify the artist and run it!

## Features

- 🎵 **Simple Command Line Interface** - No web UI, just edit one line and run
- 🤖 **AI-Optimized Processing** - Handles large discographies with intelligent rate limiting
- 📊 **Smart Filtering** - Filters tracks based on popularity and content analysis
- 🔄 **Incremental Updates** - Only adds new releases since last run
- 💾 **Progress Saving** - Can resume from interruptions
- 📈 **Comprehensive Processing** - Gets entire discographies (albums, singles, compilations)

## Quick Start

1. **Edit the artist name** in `spotify_playlist.py`:
   ```python
   # 🎵 CHANGE THIS LINE TO CREATE PLAYLISTS FOR DIFFERENT ARTISTS
   ARTIST_NAME = "Taylor Swift"  # Replace with your desired artist name
   ```

2. **Run the script**:
   ```bash
   ./run.sh
   ```
   
   Or directly:
   ```bash
   python spotify_playlist.py
   ```

That's it! The script will create a playlist for your specified artist.

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Spotify API

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy your Client ID and Client Secret
4. Update `src/config.py` with your credentials:
   ```python
   SPOTIFY_CLIENT_ID = "your_client_id_here"
   SPOTIFY_CLIENT_SECRET = "your_client_secret_here"
   ```

## Usage

### Basic Usage

1. Open `spotify_playlist.py`
2. Change the `ARTIST_NAME` variable to your desired artist
3. Run the script

### Example Output

```
🎵 Simple Spotify Playlist Creator
==================================================
🎤 Creating playlist for: Taylor Swift
🤖 Using your proven AI-optimized engine
==================================================
🚀 Starting playlist creation for Taylor Swift...
[10:30:15] 🎵 Building playlist for: Taylor Swift
[10:30:15] ⚙️  Using manual filtering (fast, reliable)
[10:30:15] Searching for artist: Taylor Swift
[10:30:16] Found artist: Taylor Swift (ID: 06HL4z0CvFAxyc27GXpf02)
[10:30:16] Checking for existing playlist: 'Taylor Swift'
[10:30:17] Found existing playlist: 37i9dQZF1DXcBWIGoYBM5M
[10:30:17] 🤖 AI-OPTIMIZED MODE: Fetching ALL discography (album,single,compilation)...
[10:30:18] 🎵 Total releases to process: 59
[10:30:18] Processing 12 albums, 45 singles, 2 compilations
[10:30:18] 🤖 AI-OPTIMIZED: Processing tracks with intelligent batching...
  🔍 Processing Album: Taylor Swift (2006-10-24)
     ✓ Added: Tim McGraw (popularity: 45.0/100)
     ✓ Added: Picture To Burn (popularity: 42.0/100)
  ...

==================================================
✅ Script completed successfully!
🎉 Check your Spotify for the new playlist!
```

## How It Works

The script uses your proven `artist_playlist_ai.py` engine which:

1. **Artist Search** - Finds the artist on Spotify
2. **Playlist Management** - Creates or finds existing playlist
3. **Incremental Updates** - Only processes new releases since last run
4. **Smart Filtering** - Applies popularity and content filters
5. **Progress Saving** - Saves progress every 5 albums for resumability
6. **Playlist Update** - Adds filtered tracks to playlist

## Project Structure

```
spotify-playlist-app/
├── spotify_playlist.py    # Main script - edit this to change artist
├── run.sh                 # Launch script
├── requirements.txt       # Python dependencies (just spotipy + requests)
├── README.md             # This file
└── src/                  # Core files
    ├── artist_playlist_ai.py    # Your proven AI-optimized engine
    └── config.py                # Spotify API credentials
```

## Advanced Features

Your `artist_playlist_ai.py` includes:

- **AI-Optimized Processing** - Handles large discographies (like Air Supply's 33+ albums)
- **Intelligent Rate Limiting** - Learns from API responses and adapts
- **Progress Persistence** - Can resume from interruptions
- **Batch API Optimization** - Reduces API calls by 95%
- **Real-time ETA Estimation** - Shows progress and time remaining
- **Smart Error Recovery** - Handles rate limits and network issues gracefully

## Troubleshooting

**"Connection refused"**: Make sure your Spotify API credentials are correct in `src/config.py`

**"Artist not found"**: Check artist name spelling

**"Rate limit exceeded"**: The script will automatically handle this with intelligent backoff

## License

This project is open source and available under the MIT License.