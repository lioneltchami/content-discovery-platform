#!/usr/bin/env python3
"""Enrich movie entries with TMDB metadata."""

import argparse
import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
CACHE_PATH = Path(__file__).parent / ".tmdb_cache.json"
MOVIES_PATH = Path(__file__).parent.parent / "movies" / "movies.json"
MOVIE_CATEGORIES = {"hindi", "marathi", "english", "tamil", "telugu", "kannada"}
LANG_MAP = {"hindi": "hi", "tamil": "ta", "telugu": "te", "kannada": "kn", "marathi": "mr", "english": "en"}

# Patterns to strip from YouTube titles before searching TMDB
CLEAN_PATTERNS = [
    r"\(?full\s+movie\)?", r"\(?hd\)?", r"\(?4k\)?", r"\(?uhd\)?",
    r"\b(super)?hit\b", r"\bnew\b", r"\blatest\b", r"\bbollywood\b",
    r"\bhollywood\b", r"\bsouth\s*(indian|dubbed)?\b", r"\bhindi\s*dubbed\b",
    r"\bfull\s*(hd|length)\b", r"\bofficial\b", r"\bengine\b",
    r"\b(action|drama|thriller|comedy)\s*movie[s]?\b",
    r"\b(20\d{2}|19\d{2})\b", r"[|\-–—].*$", r"\s{2,}",
]


def clean_title(title):
    t = title
    for pat in CLEAN_PATTERNS:
        t = re.sub(pat, " ", t, flags=re.IGNORECASE)
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split()).strip()


def tmdb_get(path, params, api_key):
    params["api_key"] = api_key
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def search_movie(title, lang_code, api_key):
    params = {"query": title}
    if lang_code:
        params["language"] = lang_code
    data = tmdb_get("/search/movie", params, api_key)
    results = data.get("results", [])
    return results[0] if results else None


def get_genres(movie_id, api_key):
    data = tmdb_get(f"/movie/{movie_id}", {}, api_key)
    return [g["name"] for g in data.get("genres", [])]


def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def enrich(args):
    api_key = args.api_key or os.environ.get("TMDB_API_KEY")
    if not api_key:
        raise SystemExit("Error: TMDB API key required via --api-key or TMDB_API_KEY env var")

    data = json.loads(MOVIES_PATH.read_text(encoding="utf-8"))
    cache = load_cache()

    movies = [m for m in data["movies"] if m["category"] in MOVIE_CATEGORIES]
    if args.category:
        if args.category not in MOVIE_CATEGORIES:
            raise SystemExit(f"Error: '{args.category}' is not a movie category. Choose from: {', '.join(sorted(MOVIE_CATEGORIES))}")
        movies = [m for m in movies if m["category"] == args.category]
    if args.max:
        movies = movies[: args.max]

    matched = skipped = cached_hits = errors = 0
    total = len(movies)
    print(f"Processing {total} movies{f' (category: {args.category})' if args.category else ''}...")
    if args.dry_run:
        print("[DRY RUN] No files will be modified.\n")

    for i, movie in enumerate(movies, 1):
        title = movie["title"]
        cleaned = clean_title(title)
        if not cleaned:
            skipped += 1
            continue

        cache_key = f"{cleaned}|{movie['category']}"

        if cache_key in cache:
            result = cache[cache_key]
            cached_hits += 1
        else:
            lang_code = LANG_MAP.get(movie["category"])
            try:
                result = search_movie(cleaned, lang_code, api_key)
                if result:
                    genres = get_genres(result["id"], api_key)
                    result["_genres"] = genres
                    time.sleep(0.1)
                cache[cache_key] = result
                time.sleep(0.1)
            except Exception as e:
                print(f"  [{i}/{total}] Error for '{cleaned}': {e}")
                errors += 1
                continue

        if result:
            movie["tmdb_id"] = result["id"]
            movie["tmdb_rating"] = result.get("vote_average")
            poster = result.get("poster_path")
            movie["tmdb_poster"] = f"{POSTER_BASE}{poster}" if poster else None
            movie["genres"] = result.get("_genres", [])
            rd = result.get("release_date", "")
            movie["release_year"] = int(rd[:4]) if rd and len(rd) >= 4 else None
            overview = result.get("overview", "")
            movie["plot"] = overview[:300] if overview else None
            matched += 1
            print(f"  [{i}/{total}] ✓ {title[:60]} → TMDB #{result['id']}")
        else:
            skipped += 1
            print(f"  [{i}/{total}] ✗ {title[:60]} — no match")

    if not args.dry_run:
        MOVIES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        save_cache(cache)
        print("\nFiles saved.")
    else:
        save_cache(cache)
        print("\n[DRY RUN] movies.json not modified. Cache updated.")

    print(f"\n--- Summary ---")
    print(f"Total processed: {total}")
    print(f"Matched:         {matched}")
    print(f"No match:        {skipped}")
    print(f"Cache hits:      {cached_hits}")
    print(f"Errors:          {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich movies with TMDB metadata")
    parser.add_argument("--api-key", help="TMDB API key (overrides TMDB_API_KEY env var)")
    parser.add_argument("--category", choices=sorted(MOVIE_CATEGORIES), help="Only enrich a specific category")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving to movies.json")
    parser.add_argument("--max", type=int, help="Max entries to process")
    args = parser.parse_args()
    enrich(args)
