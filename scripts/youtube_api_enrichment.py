#!/usr/bin/env python3
"""Enrich movie metadata using YouTube Data API v3.

Fetches missing view_count, duration, like_count, and description
for entries in movies/movies.json and per-category files.
Uses only stdlib — no external dependencies.
"""

import argparse
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime

API_BASE = "https://www.googleapis.com/youtube/v3/videos"
BATCH_SIZE = 50
OUTPUT_DIR = "movies"


def parse_iso8601_duration(iso):
    """Parse ISO 8601 duration (PT1H23M45S) to seconds."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mn, s = (int(v) if v else 0 for v in m.groups())
    return h * 3600 + mn * 60 + s


def fetch_batch(ids, api_key):
    """Fetch metadata for up to 50 video IDs. Returns dict keyed by video ID."""
    params = urllib.request.quote(",".join(ids))
    url = f"{API_BASE}?part=contentDetails,statistics,snippet&id={params}&key={api_key}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    result = {}
    for item in data.get("items", []):
        vid = item["id"]
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        snippet = item.get("snippet", {})
        result[vid] = {
            "view_count": int(stats.get("viewCount", 0)),
            "duration": parse_iso8601_duration(content.get("duration")),
            "like_count": int(stats.get("likeCount", 0)),
            "description": (snippet.get("description") or "")[:200],
        }
    return result


def needs_enrichment(entry, enrich_all):
    """Check if an entry needs enrichment."""
    if enrich_all:
        return True
    return entry.get("view_count", 0) == 0 or entry.get("duration", 0) == 0


def enrich_entries(entries, api_key, enrich_all, dry_run):
    """Enrich a list of entries in-place. Returns (enriched_count, quota_used)."""
    to_enrich = [(i, e) for i, e in enumerate(entries) if needs_enrichment(e, enrich_all)]
    if not to_enrich:
        return 0, 0

    enriched = 0
    quota = 0

    for batch_start in range(0, len(to_enrich), BATCH_SIZE):
        batch = to_enrich[batch_start:batch_start + BATCH_SIZE]
        ids = [e["id"] for _, e in batch]
        try:
            metadata = fetch_batch(ids, api_key)
            quota += 1
        except urllib.error.HTTPError as exc:
            print(f"  API error (HTTP {exc.code}): {exc.read().decode()[:200]}")
            continue
        except Exception as exc:
            print(f"  Request failed: {exc}")
            continue

        for idx, entry in batch:
            vid = entry["id"]
            if vid not in metadata:
                continue
            meta = metadata[vid]
            if dry_run:
                print(f"  [dry-run] {vid}: view_count {entry.get('view_count',0)}->{meta['view_count']}, "
                      f"duration {entry.get('duration',0)}->{meta['duration']}, "
                      f"like_count->{meta['like_count']}")
            else:
                entry["view_count"] = meta["view_count"]
                entry["duration"] = meta["duration"]
                entry["like_count"] = meta["like_count"]
                if meta["description"]:
                    entry["description"] = meta["description"]
            enriched += 1

    return enriched, quota


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def find_category_files():
    """Discover all per-category JSON files under movies/."""
    files = {}
    for root, _, filenames in os.walk(OUTPUT_DIR):
        for fn in filenames:
            fp = os.path.join(root, fn)
            # Skip the combined file
            if fp == os.path.join(OUTPUT_DIR, "movies.json"):
                continue
            if fn.endswith(".json"):
                files[fp] = fn
    return files


def get_entries_key(data):
    """Return the key used for entries: 'episodes' for cartoons, 'movies' otherwise."""
    if "episodes" in data:
        return "episodes"
    return "movies"


def main():
    parser = argparse.ArgumentParser(description="Enrich movie metadata via YouTube Data API v3")
    parser.add_argument("--api-key", help="YouTube API key (overrides YOUTUBE_API_KEY env var)")
    parser.add_argument("--enrich-all", action="store_true", help="Re-fetch all entries, not just missing")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without saving")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: Provide API key via --api-key or YOUTUBE_API_KEY env var")
        raise SystemExit(1)

    combined_path = os.path.join(OUTPUT_DIR, "movies.json")
    if not os.path.exists(combined_path):
        print(f"Error: {combined_path} not found")
        raise SystemExit(1)

    # Build a global enrichment cache from the combined file
    print(f"Loading {combined_path}...")
    combined = load_json(combined_path)
    entries = combined.get("movies", [])
    print(f"  {len(entries)} entries, enriching...")

    total_enriched, total_quota = enrich_entries(entries, api_key, args.enrich_all, args.dry_run)

    # Build lookup of enriched data by ID for per-category updates
    enriched_lookup = {e["id"]: e for e in entries}

    if not args.dry_run:
        combined["last_updated"] = datetime.utcnow().isoformat() + "Z"
        combined["total_movies"] = len(entries)
        save_json(combined, combined_path)
        print(f"  Saved {combined_path}")

    # Update per-category files using enriched data from combined
    cat_files = find_category_files()
    for fp, fn in sorted(cat_files.items()):
        data = load_json(fp)
        key = get_entries_key(data)
        cat_entries = data.get(key, [])
        updated = 0
        for entry in cat_entries:
            enriched = enriched_lookup.get(entry["id"])
            if enriched and not args.dry_run:
                for field in ("view_count", "duration", "like_count", "description"):
                    if field in enriched:
                        entry[field] = enriched[field]
                updated += 1
        if updated and not args.dry_run:
            data["last_updated"] = datetime.utcnow().isoformat() + "Z"
            if "total_movies" in data:
                data["total_movies"] = len(cat_entries)
            if "total_episodes" in data:
                data["total_episodes"] = len(cat_entries)
            save_json(data, fp)
            print(f"  Updated {fp} ({updated} entries)")

    # Summary
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Entries enriched: {total_enriched}")
    print(f"  API calls (quota units): {total_quota}")


if __name__ == "__main__":
    main()
