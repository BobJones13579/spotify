# Spotify Playlist Creator

Adds an artist's full discography to a Spotify playlist. You curate in Spotify afterward (remove what you don't want).

## Quick start

1. **Credentials** — copy `.env.example` to `.env` and add your [Spotify app](https://developer.spotify.com/dashboard) Client ID and Secret.

2. **Run** — edit `ARTIST_NAME` in `src/artist_playlist_ai.py`, then:

```bash
./run.sh
```

Or pass an artist name:

```bash
./run.sh "Taylor Swift"
```

Batch (edit `ARTISTS` in `src/artist_playlist_ai.py`):

```bash
./run.sh batch
```

First run opens a browser for Spotify login. Your token is cached in `.cache/` (gitignored).

## Filtering (default: minimal)

| Filter | Default |
|--------|---------|
| Popularity | **Off** — adds almost everything |
| Manual | Skips intros/skits/karaoke/live venue recordings |
| Quality | Skips &lt;1 min, &gt;10 min, unplayable tracks |
| Duplicates | Skips exact same track name in one run |

Turn popularity filtering on in `.env`:

```
ENABLE_POPULARITY_FILTER=true
```

## Project layout

```
spotify-playlist-app/
├── .env              # your API keys (not in git)
├── run.sh            # run this
├── requirements.txt
└── src/
    ├── artist_playlist_ai.py   # main script — set ARTIST_NAME here
    ├── spotify_client.py
    ├── track_filtering.py
    ├── progress_utils.py
    └── config.py
```

Repo: https://github.com/BobJones13579/spotify
