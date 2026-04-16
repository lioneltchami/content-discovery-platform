"""
One-time data cleanup script for movies JSON files.

Fixes:
1. Unifies JSON schema — cartoon subcategories now use same top-level structure as main categories
2. Fixes category casing — normalizes "Hindi" → "hindi", "English" → "english", etc.
3. Strips thumbnail query strings — reduces file size ~30-40%
4. Removes show_name leak from individual movie entries
5. Defaults null duration/view_count to 0
6. Applies cartoon consolidation map to existing data
"""

import json
import os
import re
from datetime import datetime

OUTPUT_DIR = "movies"

CARTOON_CONSOLIDATION_MAP = {
    "cartoons/adoraemon": "cartoons/doraemon",
    "cartoons/doraemon_2026": "cartoons/doraemon",
    "cartoons/doraemon_episode_2026": "cartoons/doraemon",
    "cartoons/doraemon_today_2026": "cartoons/doraemon",
    "cartoons/kris_roll_no_21": "cartoons/roll_no_21",
    "cartoons/oggy_and_the_cockroaches_bad_buzz": "cartoons/oggy_and_the_cockroaches",
    "cartoons/mr_bean_is_homeless": "cartoons/mr_bean",
    "cartoons/mr_bean_in_the_snow_cold": "cartoons/mr_bean",
    "cartoons/mr_bean_s_amazing_new_perfume": "cartoons/mr_bean",
    "cartoons/safari_bean": "cartoons/mr_bean",
    "cartoons/farmer_bean": "cartoons/mr_bean",
    "cartoons/scientist_bean": "cartoons/mr_bean",
    "cartoons/bean_books_a_holiday": "cartoons/mr_bean",
    "cartoons/mr_hates_the_rain": "cartoons/mr_bean",
    "cartoons/what_did_mr_bean_hatch": "cartoons/mr_bean",
    "cartoons/teddy_hotel": "cartoons/mr_bean",
    "cartoons/camping": "cartoons/mr_bean",
    "cartoons/good_dog": "cartoons/mr_bean",
    "cartoons/dopahar_ka_khaana": "cartoons/various_cartoons",
    "cartoons/bas_karo_henry": "cartoons/various_cartoons",
    "cartoons/vrindavan_mein_non": "cartoons/various_cartoons",
    "cartoons/16_march_2026": "cartoons/various_cartoons",
    "cartoons/a_monster": "cartoons/various_cartoons",
    "cartoons/a_new_car_for_christmas": "cartoons/various_cartoons",
    "cartoons/christmas_cruise": "cartoons/various_cartoons",
    "cartoons/pishachini": "cartoons/various_cartoons",
    "cartoons/richie_rich_3_urdu_by_pogo": "cartoons/various_cartoons",
    "cartoons/the_great_bottle_chase": "cartoons/various_cartoons",
    "cartoons/the_land_before_time_full": "cartoons/various_cartoons",
    "cartoons/the_vault": "cartoons/various_cartoons",
    "cartoons/live_phineas_and_ferb_season_1_full": "cartoons/various_cartoons",
    "cartoons/johnny_test_hd": "cartoons/various_cartoons",
    "cartoons/the_daltons": "cartoons/various_cartoons",
}


def strip_thumbnail_qs(url):
    """Remove query string from YouTube thumbnail URLs."""
    if url and "?" in url:
        return url.split("?")[0]
    return url


def clean_entry(entry):
    """Clean a single movie/episode entry."""
    entry["category"] = entry.get("category", "").lower()
    entry["category"] = CARTOON_CONSOLIDATION_MAP.get(entry["category"], entry["category"])
    entry["thumbnail"] = strip_thumbnail_qs(entry.get("thumbnail"))
    entry["duration"] = entry.get("duration") or 0
    entry["view_count"] = entry.get("view_count") or 0
    entry.pop("show_name", None)
    return entry


def load_json(filepath):
    """Load a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filepath):
    """Save JSON with consistent formatting."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_category_file(filepath, cat_name):
    """Process a single category JSON file — unify schema and clean entries."""
    data = load_json(filepath)
    is_cartoon_sub = "episodes" in data

    # Extract items from either schema
    items = data.get("episodes", data.get("movies", []))
    items = [clean_entry(e) for e in items]

    # Deduplicate
    items = list({m["id"]: m for m in items}.values())

    # Unified schema for all files
    now = datetime.utcnow().isoformat() + "Z"
    if cat_name.startswith("cartoons/"):
        basename = cat_name.split("/")[-1]
        show_name = data.get("show_name", basename.replace("_", " ").title())
        output = {
            "last_updated": now,
            "show_name": show_name,
            "language": data.get("language", "Hindi"),
            "category": "cartoons",
            "total_episodes": len(items),
            "episodes": items,
        }
    else:
        output = {
            "last_updated": now,
            "total_movies": len(items),
            "movies": items,
        }

    save_json(output, filepath)
    return items, cat_name


def main():
    stats = {"files": 0, "entries_before": 0, "entries_after": 0, "casing_fixed": 0, "thumbs_stripped": 0, "show_name_removed": 0, "consolidated": 0}

    # ── 1. Process all per-category files ──
    all_items = []

    # Main categories
    for cat_dir in sorted(os.listdir(OUTPUT_DIR)):
        cat_path = os.path.join(OUTPUT_DIR, cat_dir)
        if not os.path.isdir(cat_path) or cat_dir == "cartoons":
            continue
        json_file = os.path.join(cat_path, f"{cat_dir}.json")
        if os.path.isfile(json_file):
            items, _ = process_category_file(json_file, cat_dir)
            all_items.extend(items)
            stats["files"] += 1
            print(f"  ✓ {cat_dir}: {len(items)} entries")

    # Cartoon subcategories
    cartoons_dir = os.path.join(OUTPUT_DIR, "cartoons")
    if os.path.isdir(cartoons_dir):
        # First pass: collect all items, applying consolidation
        consolidated = {}
        dirs_to_remove = []

        for show_dir in sorted(os.listdir(cartoons_dir)):
            show_path = os.path.join(cartoons_dir, show_dir)
            if not os.path.isdir(show_path):
                continue
            json_file = os.path.join(show_path, f"{show_dir}.json")
            if not os.path.isfile(json_file):
                continue

            source_cat = f"cartoons/{show_dir}"
            target_cat = CARTOON_CONSOLIDATION_MAP.get(source_cat, source_cat)

            data = load_json(json_file)
            items = data.get("episodes", data.get("movies", []))
            items = [clean_entry(e) for e in items]
            # Update category to target
            for item in items:
                item["category"] = target_cat

            target_basename = target_cat.split("/")[-1]
            consolidated.setdefault(target_basename, {"items": [], "show_name": None})
            consolidated[target_basename]["items"].extend(items)
            if not consolidated[target_basename]["show_name"]:
                consolidated[target_basename]["show_name"] = data.get("show_name", target_basename.replace("_", " ").title())

            if source_cat != target_cat:
                dirs_to_remove.append(show_path)
                stats["consolidated"] += len(items)

        # Second pass: write consolidated files
        for basename, info in sorted(consolidated.items()):
            items = list({m["id"]: m for m in info["items"]}.values())
            target_dir = os.path.join(cartoons_dir, basename)
            target_file = os.path.join(target_dir, f"{basename}.json")

            now = datetime.utcnow().isoformat() + "Z"
            output = {
                "last_updated": now,
                "show_name": info["show_name"],
                "language": "Hindi",
                "category": "cartoons",
                "total_episodes": len(items),
                "episodes": items,
            }
            save_json(output, target_file)
            all_items.extend(items)
            stats["files"] += 1
            print(f"  ✓ cartoons/{basename}: {len(items)} entries")

        # Remove orphan directories
        import shutil
        for d in dirs_to_remove:
            if os.path.exists(d):
                shutil.rmtree(d)
                print(f"  🗑 Removed orphan: {d}")

    # Also process cartoons/cartoons.json (the top-level cartoons category)
    cartoons_json = os.path.join(OUTPUT_DIR, "cartoons", "cartoons.json")
    if os.path.isfile(cartoons_json):
        data = load_json(cartoons_json)
        items = data.get("movies", data.get("episodes", []))
        items = [clean_entry(e) for e in items]
        items = list({m["id"]: m for m in items}.values())
        now = datetime.utcnow().isoformat() + "Z"
        output = {
            "last_updated": now,
            "total_movies": len(items),
            "movies": items,
        }
        save_json(output, cartoons_json)
        all_items.extend(items)
        stats["files"] += 1
        print(f"  ✓ cartoons (top-level): {len(items)} entries")

    # ── 2. Rebuild combined movies.json ──
    unique_all = list({m["id"]: m for m in all_items}.values())
    now = datetime.utcnow().isoformat() + "Z"
    combined = {
        "last_updated": now,
        "total_movies": len(unique_all),
        "movies": unique_all,
    }
    combined_file = os.path.join(OUTPUT_DIR, "movies.json")
    save_json(combined, combined_file)
    stats["files"] += 1

    # ── 3. Report ──
    old_size = os.path.getsize(combined_file)
    print(f"\n{'='*50}")
    print(f"Cleanup complete!")
    print(f"  Files processed: {stats['files']}")
    print(f"  Total unique entries: {len(unique_all)}")
    print(f"  Entries consolidated from orphans: {stats['consolidated']}")
    print(f"  movies.json size: {old_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
