#!/usr/bin/env python3
"""Generate RSS 2.0 feeds from movie JSON data."""

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def fmt_duration(seconds):
    s = int(seconds or 0)
    h, m = s // 3600, s % 3600 // 60
    return f"{h}h {m}m" if h else f"{m}m"


def fmt_views(n):
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def infer_source(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    if "dailymotion" in url:
        return "Dailymotion"
    return "Unknown"


def build_feed(title, description, link, movies, last_updated):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    # Parse last_updated for pubDate fallback
    try:
        pub_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
    except Exception:
        pub_dt = datetime.now(timezone.utc)

    for m in movies:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = m.get("title", "")
        ET.SubElement(item, "link").text = m.get("url", "")
        cat = m.get("category", "unknown")
        desc = (
            f"Category: {cat} | Duration: {fmt_duration(m.get('duration'))} | "
            f"Views: {fmt_views(m.get('view_count'))} | "
            f"Source: {infer_source(m.get('url', ''))}"
        )
        ET.SubElement(item, "description").text = desc
        guid = ET.SubElement(item, "guid", isPermaLink="false")
        guid.text = m.get("id", "")
        ET.SubElement(item, "pubDate").text = format_datetime(pub_dt)
        thumb = m.get("thumbnail")
        if thumb:
            ET.SubElement(item, "enclosure", url=thumb, type="image/jpeg", length="0")

    return rss


def write_feed(rss, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=True)


def main():
    cfg = load_config()
    site = cfg.get("site", {})
    site_name = site.get("name", "ContentHub")
    site_desc = site.get("description", "")
    site_link = site.get("github_repo", "")
    output_dir = cfg.get("scraper", {}).get("output_dir", "movies")
    movies_dir = ROOT / output_dir
    feeds_dir = movies_dir / "feeds"

    feeds_generated = 0
    total_items = 0

    # Combined feed
    combined_path = movies_dir / "movies.json"
    if combined_path.exists():
        data = load_json(combined_path)
        last_updated = data.get("last_updated", "")
        movies = data.get("movies", [])
        top50 = sorted(movies, key=lambda m: m.get("view_count", 0), reverse=True)[:50]
        rss = build_feed(site_name, site_desc, site_link, top50, last_updated)
        write_feed(rss, feeds_dir / "all.xml")
        feeds_generated += 1
        total_items += len(top50)

        # Trending feed — top 20 by view_count
        top20 = sorted(movies, key=lambda m: m.get("view_count", 0), reverse=True)[:20]
        rss = build_feed(
            f"{site_name} — Trending", site_desc, site_link, top20, last_updated
        )
        write_feed(rss, feeds_dir / "trending.xml")
        feeds_generated += 1
        total_items += len(top20)

    # Per-category feeds — discover from directory
    for entry in sorted(movies_dir.iterdir()):
        if not entry.is_dir() or entry.name == "feeds":
            continue
        cat_json = entry / f"{entry.name}.json"
        if not cat_json.exists():
            continue
        data = load_json(cat_json)
        last_updated = data.get("last_updated", "")
        cat_movies = data.get("movies", [])[:30]
        rss = build_feed(
            f"{site_name} — {entry.name.replace('_', ' ').title()}",
            site_desc,
            site_link,
            cat_movies,
            last_updated,
        )
        write_feed(rss, feeds_dir / f"{entry.name}.xml")
        feeds_generated += 1
        total_items += len(cat_movies)

    print(f"RSS feeds generated: {feeds_generated}")
    print(f"Total items across all feeds: {total_items}")


if __name__ == "__main__":
    main()
