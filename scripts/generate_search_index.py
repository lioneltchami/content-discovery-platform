#!/usr/bin/env python3
"""Pre-generate a search index from movies.json."""

import json, re, os
from datetime import datetime, timezone

STOP_WORDS = {'the','a','an','in','of','for','and','or','is','to','full','movie','hindi','episode','hd','new','latest'}
MOVIES_PATH = os.path.join(os.path.dirname(__file__), '..', 'movies', 'movies.json')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'movies')

def tokenize(text):
    return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if w not in STOP_WORDS and len(w) > 1]

def main():
    with open(MOVIES_PATH, encoding='utf-8') as f:
        data = json.load(f)

    index = {}
    titles = {}

    for m in data.get('movies', []):
        mid = m['id']
        titles[mid] = m['title']
        words = set(tokenize(m.get('title', '') + ' ' + (m.get('uploader') or '')))
        for w in words:
            index.setdefault(w, []).append(mid)

    search_index = {
        'version': 1,
        'total_entries': len(index),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'index': index,
    }

    with open(os.path.join(OUT_DIR, 'search_index.json'), 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False)

    with open(os.path.join(OUT_DIR, 'search_titles.json'), 'w', encoding='utf-8') as f:
        json.dump(titles, f, ensure_ascii=False)

    print(f"Search index: {len(index)} words, {len(titles)} movies")

if __name__ == '__main__':
    main()
