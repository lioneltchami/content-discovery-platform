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

# Settings from config
RESULTS_PER_CATEGORY = config['scraper']['results_per_category']
OUTPUT_DIR = config['scraper']['output_dir']


def generate_site_config(config):
    """Write website/site-config.json from the config for the frontend."""
    categories_list = []
    for name, cat in config.get('categories', {}).items():
        categories_list.append({
            "key": name,
            "display_name": cat.get('display_name', name.replace('_', ' ').title()),
            "icon": cat.get('icon', '📁'),
            "type": cat.get('type', 'movie'),
        })

    site_config = {
        "site": config.get('site', {}),
        "categories": categories_list,
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


def scrape_from_channels():
    """Scrape movies from trusted YouTube channels."""
    all_movies = []
    channels = config.get('trusted_channels', [])
    results_per = config['scraper']['results_per_category']

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': results_per,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for ch in channels:
            name = ch['name']
            url = ch['url'] + '/videos'
            tags = ch.get('tags', [])
            primary_tag = tags[0] if tags else 'uncategorized'
            min_dur = ch.get('min_duration', 1200)

            print(f"Scraping channel: {name}...")
            try:
                result = ydl.extract_info(url, download=False)
            except Exception as e:
                print(f"  Error: {e}")
                continue

            entries = result.get('entries', []) if result else []
            for video in entries:
                try:
                    if not video:
                        continue
                    duration = video.get('duration', 0) or 0
                    if duration < min_dur:
                        continue

                    video_id = video.get('id', '')
                    title = video.get('title', '')
                    if not video_id or not title:
                        continue

                    movie_data = {
                        'id': video_id,
                        'title': title,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'duration': duration,
                        'view_count': video.get('view_count') or 0,
                        'uploader': video.get('uploader') or name,
                        'category': primary_tag,
                        'channel_tags': tags,
                        'channel_name': name,
                        'thumbnail': video.get('thumbnails', [{}])[-1].get('url', '') if video.get('thumbnails') else f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
                        'source': 'youtube',
                        'added_date': datetime.utcnow().isoformat() + 'Z',
                    }

                    lang_tags = detect_language_tags(title)
                    if lang_tags:
                        movie_data.update(lang_tags)

                    all_movies.append(movie_data)
                    print(f"  [{time.strftime('%X')}] {title}")
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  Error processing video: {e}")

            time.sleep(2)

    # Deduplicate by video ID
    unique = list({m['id']: m for m in all_movies}.values())
    return unique


def scrape_from_search():
    """Fallback: scrape movies using search queries from categories config (old approach)."""
    all_movies = []
    default_sources = config['scraper'].get('default_sources', ['youtube'])

    # Build search categories from config (old-style categories with 'query' field)
    search_categories = {}
    for name, cat in config.get('categories', {}).items():
        if 'query' in cat:
            search_categories[name] = cat['query']

    if not search_categories:
        print("No search queries found in categories config.")
        return []

    SEARCH_PREFIXES = {
        'youtube': 'ytsearch',
        'dailymotion': 'dmsearch',
    }

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for category, query in search_categories.items():
            cat_config = config['categories'].get(category, {})
            sources = cat_config.get('sources', default_sources)
            min_duration = cat_config.get('min_duration', 2400)

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
                            all_movies.append(movie_data)
                            print(f"[{time.strftime('%X')}] Added ({source}): {movie_data['title']}")
                            time.sleep(0.2)
                    except Exception as e:
                        print(f"Error processing video in {category} ({source}): {e}")

                time.sleep(2)

    unique = list({m['id']: m for m in all_movies}.values())
    return unique


def scrape_movies():
    """Scrape movies — uses channel-based scraping if trusted_channels exists, else falls back to search."""
    if config.get('trusted_channels'):
        print("Using channel-based scraping (trusted_channels)...")
        return scrape_from_channels()
    else:
        print("No trusted_channels found, falling back to search-based scraping...")
        return scrape_from_search()


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
        by_category.setdefault(cat, []).append(movie)

    # ── 2. Save per-category files ──
    all_cat_keys = set(config.get('categories', {}).keys()) | set(by_category.keys())

    for cat in all_cat_keys:
        cat_dir = os.path.join(OUTPUT_DIR, cat)
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

        print(f"[{cat}] {len(unique)} total movies")
        save_json(unique, cat_file)

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

    print(f"[all] {len(unique_all)} total movies")
    save_json(unique_all, combined_file)

    # ── 4. Generate changelog ──
    existing_ids = {m['id'] for m in existing_all}
    new_ids = {m['id'] for m in new_movies if m['id'] not in existing_ids}
    generate_changelog(new_ids, OUTPUT_DIR)

    # ── 5. Generate paginated JSON files ──
    save_paginated(unique_all, OUTPUT_DIR)
    for cat in all_cat_keys:
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

    # ── Save versioned API copy ──
    v1_dir = os.path.join(OUTPUT_DIR, 'v1')
    os.makedirs(v1_dir, exist_ok=True)
    import shutil
    shutil.copy2(combined_file, os.path.join(v1_dir, 'movies.json'))
    trending_src = os.path.join(OUTPUT_DIR, 'trending.json')
    if os.path.exists(trending_src):
        shutil.copy2(trending_src, os.path.join(v1_dir, 'trending.json'))
    print(f'  Saved versioned API at {v1_dir}/')


if __name__ == "__main__":
    print(f"Starting YouTube movie discovery at {datetime.now()}...")
    generate_site_config(config)
    movies = scrape_movies()
    save_all(movies)
    print("Done!")
