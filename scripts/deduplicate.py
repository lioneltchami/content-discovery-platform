#!/usr/bin/env python3
"""Deduplicate movie entries using fuzzy title matching.

Uses RapidFuzz for fast fuzzy string matching to detect re-uploads
of the same content across different YouTube/Dailymotion channels.

Install: pip install rapidfuzz
"""
import argparse
import json
import os
import re
from collections import defaultdict

try:
    from rapidfuzz import fuzz, process
except ImportError:
    print('Error: rapidfuzz is required. Install with: pip install rapidfuzz')
    exit(1)

MOVIES_PATH = os.path.join(os.path.dirname(__file__), '..', 'movies', 'movies.json')

# Words to strip before comparing titles
STRIP_WORDS = re.compile(
    r'\b(full|movie|hd|4k|1080p|720p|480p|official|free|new|latest|'
    r'hindi|english|dubbed|sub|subtitles|subtitle|watch|online|'
    r'\d{4})\b', re.IGNORECASE
)

def normalize_title(title):
    """Normalize a title for comparison."""
    t = STRIP_WORDS.sub('', title)
    t = re.sub(r'[^a-zA-Z0-9\s]', '', t)  # Remove special chars
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t

def find_duplicates(movies, threshold=82):
    """Find groups of duplicate movies using fuzzy matching + duration."""
    # Group by category first (only compare within same category)
    by_category = defaultdict(list)
    for m in movies:
        by_category[m.get('category', '')].append(m)
    
    duplicates = []  # List of (keep_id, remove_ids) tuples
    
    for cat, items in by_category.items():
        if len(items) < 2:
            continue
        
        normalized = [(normalize_title(m['title']), m) for m in items]
        seen = set()
        
        for i, (norm_i, movie_i) in enumerate(normalized):
            if movie_i['id'] in seen:
                continue
            
            group = [movie_i]
            for j in range(i + 1, len(normalized)):
                norm_j, movie_j = normalized[j]
                if movie_j['id'] in seen:
                    continue
                
                # Fuzzy title match
                score = fuzz.token_sort_ratio(norm_i, norm_j)
                if score < threshold:
                    continue
                
                # Duration check: within 10% tolerance
                dur_i = movie_i.get('duration', 0) or 0
                dur_j = movie_j.get('duration', 0) or 0
                if dur_i > 0 and dur_j > 0:
                    ratio = min(dur_i, dur_j) / max(dur_i, dur_j)
                    if ratio < 0.9:
                        continue
                
                group.append(movie_j)
                seen.add(movie_j['id'])
            
            if len(group) > 1:
                # Keep the one with highest view count
                group.sort(key=lambda m: m.get('view_count', 0) or 0, reverse=True)
                keep = group[0]
                remove = [m['id'] for m in group[1:]]
                duplicates.append((keep, remove))
                seen.add(keep['id'])
    
    return duplicates

def main():
    parser = argparse.ArgumentParser(description='Deduplicate movies by fuzzy title matching')
    parser.add_argument('--threshold', type=int, default=82, help='Fuzzy match threshold (0-100, default: 82)')
    parser.add_argument('--dry-run', action='store_true', help='Show duplicates without removing')
    args = parser.parse_args()
    
    with open(MOVIES_PATH, encoding='utf-8') as f:
        data = json.load(f)
    movies = data.get('movies', [])
    print(f'Loaded {len(movies)} movies')
    
    duplicates = find_duplicates(movies, args.threshold)
    
    total_remove = sum(len(r) for _, r in duplicates)
    print(f'Found {len(duplicates)} duplicate groups ({total_remove} entries to remove)')
    
    for keep, remove_ids in duplicates:
        print(f'  KEEP: "{keep["title"]}" ({keep.get("view_count",0)} views)')
        for rid in remove_ids:
            m = next((x for x in movies if x['id'] == rid), None)
            if m:
                print(f'    REMOVE: "{m["title"]}" ({m.get("view_count",0)} views)')
    
    if args.dry_run:
        print('\nDry run — no changes made.')
        return
    
    if total_remove == 0:
        print('No duplicates found.')
        return
    
    # Remove duplicates
    remove_set = set()
    for _, remove_ids in duplicates:
        remove_set.update(remove_ids)
    
    cleaned = [m for m in movies if m['id'] not in remove_set]
    data['movies'] = cleaned
    data['total_movies'] = len(cleaned)
    
    with open(MOVIES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f'\nRemoved {total_remove} duplicates. {len(cleaned)} movies remaining.')

if __name__ == '__main__':
    main()
