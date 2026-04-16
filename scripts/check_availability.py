#!/usr/bin/env python3
"""Check availability of YouTube videos in the movie database."""

import argparse
import json
import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

MOVIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "movies")
OEMBED_URL = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={id}&format=json"


def check_video(video_id):
    """Return (video_id, status) where status is 'available', 'unavailable', or 'error'."""
    url = OEMBED_URL.format(id=video_id)
    req = urllib.request.Request(url, method="HEAD")
    try:
        urllib.request.urlopen(req, timeout=10)
        return (video_id, "available")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            return (video_id, "unavailable")
        return (video_id, "error")
    except Exception:
        return (video_id, "error")


def load_movies(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_all(video_ids, max_workers=10):
    results = {"available": [], "unavailable": [], "error": []}
    total = len(video_ids)
    done = 0

    for batch_start in range(0, total, max_workers):
        batch = video_ids[batch_start:batch_start + max_workers]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_video, vid): vid for vid in batch}
            for future in as_completed(futures):
                vid, status = future.result()
                results[status].append(vid)
                done += 1
                print(f"\r  Checked {done}/{total}...", end="", flush=True)
        if batch_start + max_workers < total:
            time.sleep(0.5)

    print()
    return results


def write_report(results, report_path):
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_checked": sum(len(v) for v in results.values()),
        "available": len(results["available"]),
        "unavailable": len(results["unavailable"]),
        "errors": len(results["error"]),
        "unavailable_ids": results["unavailable"],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


def find_all_json_files(movies_dir):
    """Find all JSON data files under movies/."""
    json_files = []
    for root, _, files in os.walk(movies_dir):
        for fname in files:
            if fname.endswith(".json") and fname != "availability_report.json":
                json_files.append(os.path.join(root, fname))
    return json_files


def prune_unavailable(unavailable_ids, movies_dir):
    """Remove unavailable entries from all JSON files."""
    bad = set(unavailable_ids)
    if not bad:
        print("No unavailable videos to prune.")
        return

    for path in find_all_json_files(movies_dir):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Determine list key: "movies" or "episodes"
        list_key = "episodes" if "episodes" in data else "movies" if "movies" in data else None
        if not list_key:
            continue

        original = len(data[list_key])
        data[list_key] = [e for e in data[list_key] if e.get("id") not in bad]
        removed = original - len(data[list_key])

        if removed:
            count_key = "total_episodes" if list_key == "episodes" else "total_movies"
            data[count_key] = len(data[list_key])
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Pruned {removed} from {os.path.relpath(path, movies_dir)}")


def main():
    parser = argparse.ArgumentParser(description="Check YouTube video availability")
    parser.add_argument("--prune", action="store_true", help="Remove unavailable videos from all JSON files")
    parser.add_argument("--max-check", type=int, default=0, help="Max videos to check (default: all)")
    args = parser.parse_args()

    movies_json = os.path.join(MOVIES_DIR, "movies.json")
    data = load_movies(movies_json)
    ids = [m["id"] for m in data.get("movies", [])]

    if args.max_check > 0:
        ids = ids[:args.max_check]

    print(f"Checking {len(ids)} videos...")
    results = check_all(ids)

    report_path = os.path.join(MOVIES_DIR, "availability_report.json")
    report = write_report(results, report_path)

    print(f"\n=== Availability Report ===")
    print(f"  Total checked: {report['total_checked']}")
    print(f"  Available:     {report['available']}")
    print(f"  Unavailable:   {report['unavailable']}")
    print(f"  Errors:        {report['errors']}")
    print(f"  Report saved:  {report_path}")

    if args.prune and results["unavailable"]:
        print(f"\nPruning {len(results['unavailable'])} unavailable videos...")
        prune_unavailable(results["unavailable"], MOVIES_DIR)
        print("Pruning complete.")


if __name__ == "__main__":
    main()
