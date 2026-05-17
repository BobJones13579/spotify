# Lifetime Streams Estimator Design

## Overview
Create a proxy for Spotify's lifetime streams metric to enable better track filtering based on actual popularity rather than just relative popularity scores.

## Goal
Distinguish between tracks with significantly different stream counts (e.g., 10K vs 1M streams) to replicate the filtering behavior the user relies on when manually curating playlists.

## Approach: Multi-Factor Heuristic Formula

### Core Formula
```
estimated_lifetime_streams = base_popularity * age_factor * audio_quality_score * album_type_multiplier * artist_factor * scale_factor
```

### Factors

1. **Base Popularity (0-100)**
   - Spotify's current popularity score
   - Primary indicator of stream count

2. **Age Factor**
   - Older songs have had more time to accumulate streams
   - Formula: `min(1.0 + (days_since_release / 365.25) * 0.1, 3.0)`
   - Caps at 3x multiplier for very old songs

3. **Audio Quality Score**
   - Commercial appeal based on audio features
   - Formula: `(danceability + energy + valence) / 3`
   - Higher scores = more mainstream/commercial appeal

4. **Album Type Multiplier**
   - Singles: 2.0x (typically get more streams)
   - Albums: 1.0x (baseline)
   - Compilations: 1.5x (moderate boost)

5. **Artist Factor**
   - Popular artists amplify track streams
   - Formula: `1.0 + (artist_popularity / 100) * 0.5`
   - Range: 1.0x to 1.5x

6. **Scale Factor**
   - Converts to realistic stream count range
   - Base: 10,000 (so 100 popularity = ~1M streams for new hit)

## Implementation Phases

### Phase 1: Basic Heuristic (Current)
- Implement core formula
- Integrate with existing track filtering
- Test with known tracks for validation

### Phase 2: External Data Integration
- Add Last.fm API for actual play counts
- YouTube API for video view counts
- Calibration system for accuracy improvement

### Phase 3: Machine Learning
- Train model on collected external data
- Replace heuristic with ML model
- Continuous improvement with more data

## Expected Output Ranges
- Low-quality tracks: 1K - 50K streams
- Decent tracks: 50K - 500K streams  
- Popular tracks: 500K - 5M streams
- Hit songs: 5M+ streams

This should provide the discrimination needed for effective filtering.
