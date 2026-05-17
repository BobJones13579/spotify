# Spotify Playlist Updater

Adds **new releases only** to an artist playlist (matches playlist name to artist name). Curate in Spotify after.

## Run

```bash
./run.sh                  # ARTIST_NAME in src/artist_playlist_ai.py
./run.sh "The Script"
./run.sh batch            # edit ARTISTS list first
./run.sh test             # run unit tests
```

Credentials in `.env` (see `.env.example`). First run opens browser for Spotify login.

## What it does

1. Finds playlist named like the artist (or creates one)
2. Finds newest release date already on the playlist
3. Adds tracks from releases **after** that date
4. Light filters: skips skits/intros/karaoke, very short/long, unplayable tracks

## Layout

```
src/artist_playlist_ai.py   # main — set ARTIST_NAME here
src/spotify_client.py
src/track_filtering.py
src/config.py
```

https://github.com/BobJones13579/spotify
