import yt_dlp
import json
import os
import time
import re
import yaml
from datetime import datetime


def load_config():
    """Load config.yaml from the project root (relative to this script's location)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, '..', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# Load configuration
config = load_config()

# Build CATEGORIES from config
CATEGORIES = {name: cat['query'] for name, cat in config['categories'].items()}

# Build CARTOON_CATEGORIES from config
CARTOON_CATEGORIES = {
    f"cartoons/{name}": show['query']
    for name, show in config.get('cartoon_shows', {}).items()
}

# Consolidation map for fragmented cartoon subcategories
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

# Merge all categories
ALL_CATEGORIES = {**CATEGORIES, **CARTOON_CATEGORIES}

# Settings from config
RESULTS_PER_CATEGORY = config['scraper']['results_per_category']
OUTPUT_DIR = config['scraper']['output_dir']

# Build a min_duration lookup from config
_MIN_DURATION = {}
for name, cat in config['categories'].items():
    _MIN_DURATION[name] = cat.get('min_duration', 2400)
for name in config.get('cartoon_shows', {}):
    _MIN_DURATION[f"cartoons/{name}"] = config['cartoon_shows'][name].get('min_duration', 600)


def extract_cartoon_name_and_category(title):
    """Extract cartoon name from video title."""
    delimiters = r'[|\-:]'
    parts = re.split(delimiters, title)

    if parts:
        name = parts[0].strip()
        name = re.sub(r'(?i)\b(hindi|full episode|cartoon|episodes|kids|in hindi|new episode|latest)\b', '', name).strip()
        name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
        name = re.sub(r'[^a-zA-Z0-9]+$', '', name)
        name = name.strip()

        if 2 < len(name) < 40:
            sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
            return name, f"cartoons/{sanitized}"

    return "Various Cartoons", "cartoons/various_cartoons"


def generate_site_config(config):
    """Write website/site-config.json from the config for the frontend."""
    categories_list = []
    for name, cat in config['categories'].items():
        categories_list.append({
            "key": name,
            "display_name": cat.get('display_name', name.replace('_', ' ').title()),
            "icon": cat.get('icon', '📁'),
            "type": cat.get('type', 'movie'),
        })

    cartoon_shows_list = []
    for name, show in config.get('cartoon_shows', {}).items():
        cartoon_shows_list.append({
            "key": f"cartoons/{name}",
            "display_name": show.get('display_name', name.replace('_', ' ').title()),
            "icon": show.get('icon', '📺'),
        })

    site_config = {
        "site": config.get('site', {}),
        "categories": categories_list,
        "cartoon_shows": cartoon_shows_list,
        "sponsorship": config.get('sponsorship', {}),
        "api_base_url": config['scraper']['output_dir'],
        "sources": config['scraper'].get('default_sources', ['youtube']),
    }

    os.makedirs('website', exist_ok=True)
    filepath = os.path.join('website', 'site-config.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(site_config, f, indent=2, ensure_ascii=False)
    print(f"Generated {filepath}")


def detect_language_tags(title):
    """Detect subtitle/dub language tags from video title."""
    tags = {}
    title_lower = title.lower()
    dub_patterns = [
        (r'hindi\s*dub', 'hindi'), (r'english\s*dub', 'english'),
        (r'french\s*dub', 'french'), (r'spanish\s*dub', 'spanish'),
        (r'dubbed\s*in\s*(\w+)', None),
    ]
    for pattern, lang in dub_patterns:
        m = re.search(pattern, title_lower)
        if m:
            tags['dubbed'] = lang or m.group(1)
            break
    sub_patterns = [
        (r'eng(?:lish)?\s*sub', 'english'), (r'hindi\s*sub', 'hindi'),
        (r'with\s*subtitles', 'english'), (r'sub(?:titled)?\s*in\s*(\w+)', None),
    ]
    for pattern, lang in sub_patterns:
        m = re.search(pattern, title_lower)
        if m:
            tags['subtitles'] = lang or m.group(1)
            break
    return tags


def scrape_movies():
    """Scrape movies from YouTube and Dailymotion, return them grouped by category."""
    all_movies = []
    default_sources = config['scraper'].get('default_sources', ['youtube'])

    # Search prefix per source
    SEARCH_PREFIXES = {
        'youtube': 'ytsearch',
        'dailymotion': 'dmsearch',
    }

    # yt-dlp options for fast metadata extraction without downloading videos
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for category, query in ALL_CATEGORIES.items():
            # Determine sources for this category
            cat_config = config['categories'].get(category) or config.get('cartoon_shows', {}).get(category.split('/')[-1], {})
            sources = cat_config.get('sources', default_sources) if cat_config else default_sources

            for source in sources:
                prefix = SEARCH_PREFIXES.get(source)
                if not prefix:
                    print(f"Unknown source '{source}' for {category}, skipping")
                    continue

                print(f"Searching for {category} on {source}...")
                search_query = f"{prefix}{RESULTS_PER_CATEGORY}:{query}"

                try:
                    result = ydl.extract_info(search_query, download=False)
                except Exception as e:
                    print(f"Error scraping {category} from {source}: {e}")
                    continue

                if 'entries' not in result:
                    continue

                for video in result['entries']:
                    try:
                        if not video:
                            continue

                        duration = video.get('duration', 0)
                        min_duration = _MIN_DURATION.get(category, 600 if category.startswith("cartoons/") else 2400)
                        if duration and duration < min_duration:
                            continue

                        video_id = video.get('id')
                        if source == 'dailymotion':
                            url = f"https://www.dailymotion.com/video/{video_id}"
                        else:
                            url = video.get('url') or f"https://www.youtube.com/watch?v={video_id}"

                        movie_data = {
                            "id": video_id,
                            "title": video.get('title'),
                            "url": url,
                            "duration": duration if duration is not None else 0,
                            "view_count": video.get('view_count') if video.get('view_count') is not None else 0,
                            "uploader": video.get('uploader'),
                            "category": category.lower(),
                            "thumbnail": video.get('thumbnails', [{}])[-1].get('url', '') if video.get('thumbnails') else None,
                            "added_date": datetime.utcnow().isoformat() + "Z",
                            "source": source,
                        }

                        lang_tags = detect_language_tags(movie_data['title'])
                        if lang_tags:
                            movie_data.update(lang_tags)

                        if movie_data['id'] and movie_data['title']:
                            if category == "cartoons_auto":
                                detected_name, new_category = extract_cartoon_name_and_category(movie_data['title'])
                                movie_data['category'] = new_category
                                movie_data['show_name'] = detected_name

                            all_movies.append(movie_data)
                            print(f"[{time.strftime('%X')}] Added ({source}): {movie_data['title']}")
                            time.sleep(0.2)
                    except Exception as e:
                        print(f"Error processing video in {category} ({source}): {e}")

                time.sleep(2)  # Delay between searches

    # Remove duplicates based on video ID
    unique_movies = {movie['id']: movie for movie in all_movies}.values()

    return list(unique_movies)


def load_existing(filepath):
    """Load existing movies from a JSON file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                movies = existing_data.get('episodes', existing_data.get('movies', []))
                print(f"  Loaded {len(movies)} existing movies from {filepath}")
                return movies
        except Exception as e:
            print(f"  Could not read existing file {filepath}: {e}")
    return []


def save_json(movies_list, filepath, show_name=None, is_cartoon=False):
    """Save a list of movies to a JSON file with metadata."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if is_cartoon:
        output = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "show_name": show_name or "Unknown Cartoon",
            "language": "Hindi",
            "category": "cartoons",
            "description": f"Auto-generated category for {show_name or 'videos'}.",
            "total_episodes": len(movies_list),
            "episodes": movies_list
        }
    else:
        output = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_movies": len(movies_list),
            "movies": movies_list
        }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"  Saved {len(movies_list)} items to {filepath}")


def save_paginated(items, base_dir, page_size=50):
    """Split items into paginated JSON files."""
    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    pages_dir = os.path.join(base_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    for i in range(total_pages):
        page_items = items[i * page_size:(i + 1) * page_size]
        page_data = {
            "page": i + 1,
            "total_pages": total_pages,
            "total_items": total_items,
            "items": page_items
        }
        with open(os.path.join(pages_dir, f"page-{i + 1}.json"), 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=4, ensure_ascii=False)

    meta = {
        "total_items": total_items,
        "total_pages": total_pages,
        "page_size": page_size,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }
    with open(os.path.join(pages_dir, "meta.json"), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
    print(f"  Saved {total_pages} page(s) to {pages_dir}")


def generate_changelog(new_ids, output_dir):
    """Record new entries in a changelog file."""
    changelog_file = os.path.join(output_dir, 'changelog.json')
    history = []
    if os.path.exists(changelog_file):
        with open(changelog_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            history = data.get('history', [])
    entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'added': list(new_ids),
        'added_count': len(new_ids),
    }
    history.insert(0, entry)
    history = history[:50]
    output = {
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'history': history,
    }
    with open(changelog_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f'  Changelog: {len(new_ids)} new entries recorded')


def save_all(new_movies):
    """Save movies per-category into folders AND into a combined file."""

    # ── 1. Group new movies by category ──
    by_category = {}
    for movie in new_movies:
        cat = movie.get('category', 'uncategorized')
        # Issue 6: Consolidate fragmented cartoon subcategories
        cat = CARTOON_CONSOLIDATION_MAP.get(cat, cat)
        by_category.setdefault(cat, []).append(movie)

    # ── 2. Save per-category files ──
    all_cat_keys = set(ALL_CATEGORIES.keys()) | set(by_category.keys())

    for cat in all_cat_keys:
        if cat == "cartoons_auto":
            continue

        cat_dir = os.path.join(OUTPUT_DIR, cat)
        # For cartoon subcategories like "cartoons/oggy_and_the_cockroaches",
        # the filename should be the last part (e.g. "oggy_and_the_cockroaches.json")
        cat_basename = cat.split("/")[-1]
        cat_file = os.path.join(cat_dir, f"{cat_basename}.json")

        existing = load_existing(cat_file)
        combined = existing + by_category.get(cat, [])
        unique = list({m['id']: m for m in combined}.values())

        # Preserve added_date from existing entries
        existing_dates = {m['id']: m.get('added_date') for m in existing}
        for m in unique:
            if m['id'] in existing_dates and existing_dates[m['id']]:
                m['added_date'] = existing_dates[m['id']]

        # Issue 5: Strip show_name from non-cartoon per-category saves
        is_cartoon = cat.startswith("cartoons/")
        if not is_cartoon:
            for m in unique:
                m.pop('show_name', None)

        print(f"[{cat}] {len(unique)} total movies")

        # Infer show name and if it is a cartoon
        show_name = cat_basename.replace('_', ' ').title()
        if unique and 'show_name' in unique[0]:
            show_name = unique[0]['show_name']

        save_json(unique, cat_file, show_name=show_name, is_cartoon=is_cartoon)

    # ── 3. Save combined file (all categories) ──
    combined_file = os.path.join(OUTPUT_DIR, "movies.json")
    existing_all = load_existing(combined_file)
    combined_all = existing_all + new_movies
    unique_all = list({m['id']: m for m in combined_all}.values())

    # Preserve added_date from existing entries
    existing_dates = {m['id']: m.get('added_date') for m in existing_all}
    for m in unique_all:
        if m['id'] in existing_dates and existing_dates[m['id']]:
            m['added_date'] = existing_dates[m['id']]

    # Issue 5: Strip show_name from combined movies.json
    for m in unique_all:
        m.pop('show_name', None)

    print(f"[all] {len(unique_all)} total movies")
    save_json(unique_all, combined_file)

    # ── 4. Generate changelog ──
    existing_ids = {m['id'] for m in existing_all}
    new_ids = {m['id'] for m in new_movies if m['id'] not in existing_ids}
    generate_changelog(new_ids, OUTPUT_DIR)

    # ── 5. Generate paginated JSON files ──
    save_paginated(unique_all, OUTPUT_DIR)
    for cat in all_cat_keys:
        if cat == "cartoons_auto":
            continue
        cat_dir = os.path.join(OUTPUT_DIR, cat)
        cat_basename = cat.split("/")[-1]
        cat_file = os.path.join(cat_dir, f"{cat_basename}.json")
        if os.path.exists(cat_file):
            with open(cat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items = data.get('episodes', data.get('movies', []))
            if len(items) > 50:
                save_paginated(items, cat_dir)

    # ── 6. Generate trending.json ──
    trending = sorted(unique_all, key=lambda m: m.get('view_count', 0), reverse=True)[:50]
    save_json(trending, os.path.join(OUTPUT_DIR, "trending.json"))


if __name__ == "__main__":
    print(f"Starting YouTube movie discovery at {datetime.now()}...")
    generate_site_config(config)
    movies = scrape_movies()
    save_all(movies)
    print("Done!")
