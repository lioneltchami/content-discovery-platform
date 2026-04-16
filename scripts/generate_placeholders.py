#!/usr/bin/env python3
"""Generate thumbnail placeholder colors for movie entries.

Since downloading thousands of thumbnails to compute ThumbHash is slow,
we use a deterministic color generation based on the video ID + category.
This gives each card a unique-ish colored placeholder while images load.
"""
import json, os, hashlib

MOVIES_PATH = os.path.join(os.path.dirname(__file__), '..', 'movies', 'movies.json')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'movies', 'placeholders.json')

# Muted color palettes per content type
PALETTES = {
    'movie': ['#1a1a2e', '#16213e', '#0f3460', '#1b1b2f', '#162447', '#1f4068'],
    'show': ['#2d132c', '#1a1a2e', '#1b262c', '#0f3460', '#222831', '#393e46'],
    'cartoon': ['#2b2e4a', '#e84545', '#903749', '#53354a', '#a12568', '#3b185f'],
    'music': ['#1b1b2f', '#1a1a40', '#270082', '#7a0bc0', '#fa58b6', '#2d033b'],
    'tutorial': ['#0a1931', '#150050', '#000d6b', '#0c2d57', '#1a3c40', '#1d3557'],
    'sermon': ['#2c2c54', '#474787', '#1b1464', '#2c003e', '#512b58', '#3b0944'],
    'default': ['#1a1a2e', '#16213e', '#0f3460', '#1b1b2f', '#162447', '#1f4068'],
}

def get_placeholder_color(video_id, category):
    """Generate a deterministic muted color for a video."""
    h = int(hashlib.md5(video_id.encode()).hexdigest()[:8], 16)
    content_type = 'default'
    for t in PALETTES:
        if t in category:
            content_type = t
            break
    palette = PALETTES[content_type]
    return palette[h % len(palette)]

def main():
    with open(MOVIES_PATH, encoding='utf-8') as f:
        data = json.load(f)

    placeholders = {}
    for m in data.get('movies', []):
        placeholders[m['id']] = get_placeholder_color(m['id'], m.get('category', ''))

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(placeholders, f, ensure_ascii=False)

    print(f'Generated {len(placeholders)} placeholder colors')

if __name__ == '__main__':
    main()
