# 🎬 YouTube Content Discovery Platform

[![GitHub stars](https://img.shields.io/github/stars/samyak2403/daily-movies-api?style=flat-square)](https://github.com/samyak2403/daily-movies-api/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/samyak2403/daily-movies-api?style=flat-square)](https://github.com/samyak2403/daily-movies-api/commits/main)

A **config-driven, white-label platform** for curating YouTube content into niche discovery sites. Define your categories in a single `config.yaml`, and the pipeline handles scraping, JSON API generation, and a ready-to-deploy static website.

**Fork → Edit config → Push → You have a content platform.**

---

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ config.yaml │────▶│  yt-dlp      │────▶│  JSON API    │────▶│  Static Site  │
│ (categories)│     │  scraper     │     │  (per-category│     │  (index.html) │
└─────────────┘     └──────────────┘     │   + combined) │     └──────────────┘
                                         └──────────────┘
```

1. **Config** — You define categories, search queries, and site branding in `config.yaml`.
2. **Scraper** — A GitHub Actions cron job runs every 6 hours, using `yt-dlp` to search YouTube for each category.
3. **JSON API** — Results are saved as structured JSON files (per-category and combined), committed back to the repo.
4. **Website** — A static site reads the JSON files directly from the repo via raw GitHub URLs. Deploy anywhere.

---

## Quick Start

```bash
# 1. Fork this repository

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/daily-movies-api.git
cd daily-movies-api

# 3. Edit config.yaml — change site name, categories, branding
#    (see Config Reference below)

# 4. Push to main — GitHub Actions will scrape and populate JSON files
git add config.yaml
git commit -m "Configure my platform"
git push

# 5. Deploy the website/ folder to Vercel, GitHub Pages, or any static host
```

### Local Development

```bash
pip install -r requirements.txt
python scripts/scraper.py          # Run the scraper locally
python scripts/generate_search_index.py  # Build search index
```

Requires **Python 3.10+** and [Deno](https://deno.com/) v2.0+ (for yt-dlp YouTube JS challenge support).

---

## Config Reference

All platform behavior is controlled by `config.yaml`:

```yaml
# ── Site Identity ──
site:
  name: "My Platform"                # Site title
  tagline: "Short tagline"           # Shown below the title
  description: "SEO description"     # Meta description
  theme_color: "#7c3aed"             # Primary color
  accent_color: "#ec4899"            # Accent/highlight color
  background_color: "#0a0a1a"        # Page background
  logo_emoji: "🎬"                   # Emoji used as logo
  footer_text: "Footer message"      # Footer text
  github_repo: "https://github.com/you/repo"
  content_label: "movies"            # Singular label ("movies", "videos", "tracks")
  content_label_plural: "movies"     # Plural label

# ── Scraper Settings ──
scraper:
  results_per_category: 15           # Max results per search query
  schedule_cron: "0 */6 * * *"       # Cron expression for GitHub Actions
  output_dir: "movies"               # Output directory for JSON files

# ── Content Categories ──
categories:
  category_key:                      # Lowercase, underscore-separated
    query: "youtube search string"   # The YouTube search query
    type: movie                      # movie | show | cartoon | music | tutorial | sermon
    min_duration: 2400               # Minimum duration in seconds
    icon: "🎬"                       # Emoji for filter buttons

# ── Subcategories (optional) ──
cartoon_shows:                       # Nested under cartoons/ folder
  show_key:
    query: "search query"
    icon: "🤖"
    display_name: "Human-Readable Name"

# ── Sponsorship (optional) ──
sponsorship:
  enabled: true
  github_sponsors: ""
  buy_me_a_coffee: ""
  ko_fi: ""
  custom_url: ""
  message: "Support message"
```

---

## Example Platforms

### NollyHub — Nollywood Movie Discovery

```yaml
site:
  name: "NollyHub"
  tagline: "Free Nollywood movies on YouTube"
  logo_emoji: "🇳🇬"
  content_label: "movies"

categories:
  nollywood:
    query: "full nollywood movie"
    type: movie
    min_duration: 3600
    icon: "🎬"
  yoruba:
    query: "full yoruba movie"
    type: movie
    min_duration: 3600
    icon: "🗣️"
  igbo:
    query: "full igbo movie"
    type: movie
    min_duration: 3600
    icon: "🎭"
```

### AI Hub — AI Tutorial Aggregator

```yaml
site:
  name: "AI Hub"
  tagline: "Curated AI & ML tutorials from YouTube"
  logo_emoji: "🤖"
  content_label: "tutorials"

categories:
  machine_learning:
    query: "machine learning full course"
    type: tutorial
    min_duration: 1800
    icon: "🧠"
  deep_learning:
    query: "deep learning tutorial"
    type: tutorial
    min_duration: 1800
    icon: "🔬"
  llm:
    query: "large language model tutorial"
    type: tutorial
    min_duration: 900
    icon: "💬"
```

### GospelStream — Gospel Music & Sermons

```yaml
site:
  name: "GospelStream"
  tagline: "Gospel music and sermons, updated daily"
  logo_emoji: "✝️"
  content_label: "videos"

categories:
  gospel_music:
    query: "gospel worship music"
    type: music
    min_duration: 300
    icon: "🎵"
  sermons:
    query: "full sermon"
    type: sermon
    min_duration: 1800
    icon: "📖"
  choir:
    query: "gospel choir performance"
    type: music
    min_duration: 300
    icon: "🎶"
```

---

## API Endpoints

JSON files are served as raw GitHub URLs. Replace `YOUR_USERNAME` and `YOUR_REPO` with your fork details.

| Endpoint | URL |
|----------|-----|
| All content (combined) | `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/movies/movies.json` |
| Single category | `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/movies/{category}/{category}.json` |
| Subcategory | `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/movies/cartoons/{show}/{show}.json` |
| Search index | `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/movies/search_index.json` |

### JSON Schema

```json
{
  "last_updated": "2026-04-16T05:00:00Z",
  "total_movies": 557,
  "movies": [
    {
      "id": "abc123",
      "title": "Video Title",
      "url": "https://www.youtube.com/watch?v=abc123",
      "duration": 7200,
      "view_count": 1500000,
      "uploader": "Channel Name",
      "category": "hindi",
      "thumbnail": "https://i.ytimg.com/vi/abc123/hq720.jpg"
    }
  ]
}
```

---

## Android Integration

### Data Model (Kotlin)

```kotlin
data class ContentResponse(
    val last_updated: String,
    val total_movies: Int,
    val movies: List<ContentItem>
)

data class ContentItem(
    val id: String,
    val title: String,
    val url: String,
    val duration: Int,
    val view_count: Int,
    val uploader: String?,
    val category: String,
    val thumbnail: String?
)
```

### Retrofit Interface

```kotlin
interface ContentApiService {
    @GET("{user}/{repo}/main/movies/movies.json")
    suspend fun getAllContent(
        @Path("user") user: String,
        @Path("repo") repo: String
    ): ContentResponse

    @GET("{user}/{repo}/main/movies/{category}/{category}.json")
    suspend fun getCategory(
        @Path("user") user: String,
        @Path("repo") repo: String,
        @Path("category") category: String
    ): ContentResponse
}
```

### Retrofit Instance

```kotlin
val retrofit = Retrofit.Builder()
    .baseUrl("https://raw.githubusercontent.com/")
    .addConverterFactory(GsonConverterFactory.create())
    .build()

val apiService = retrofit.create(ContentApiService::class.java)
```

### Fetch Data

```kotlin
class ContentViewModel : ViewModel() {
    fun fetchContent() {
        viewModelScope.launch {
            try {
                val response = apiService.getAllContent("YOUR_USERNAME", "YOUR_REPO")
                val items = response.movies
                // Update your UI
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
```

---

## Deployment

### GitHub Pages

1. Go to **Settings → Pages** in your repo.
2. Set source to **Deploy from a branch**, select `main`, folder `/website`.
3. Your site will be live at `https://YOUR_USERNAME.github.io/YOUR_REPO/`.

### Vercel

1. Import your repo on [vercel.com](https://vercel.com).
2. Set **Root Directory** to `website`.
3. Set **Framework Preset** to `Other`.
4. Deploy — Vercel will auto-deploy on every push.

---

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/scraper.py` | Main scraper — searches YouTube via yt-dlp for each category in `config.yaml`, outputs per-category and combined JSON files. |
| `scripts/check_availability.py` | Checks if YouTube videos in the database are still available (not deleted/private). Removes dead entries. |
| `scripts/youtube_api_enrichment.py` | Enriches entries with YouTube Data API v3 metadata (view count, duration, likes, description). Requires `YOUTUBE_API_KEY`. |
| `scripts/tmdb_enrichment.py` | Enriches movie entries with TMDB metadata (poster, rating, overview). Requires `TMDB_API_KEY`. |
| `scripts/generate_search_index.py` | Pre-generates a tokenized search index from `movies.json` for fast client-side search. |
| `scripts/cleanup_data.py` | One-time data cleanup — normalizes schema, fixes casing, strips thumbnail query strings, defaults null values. |

---

## Folder Structure

```
├── config.yaml              ← Platform configuration (edit this!)
├── scripts/                 ← Scraper and utility scripts
├── website/                 ← Static site (index.html, player, docs)
├── movies/                  ← Generated JSON data (auto-updated)
│   ├── movies.json          ← All content combined
│   ├── search_index.json    ← Pre-built search index
│   ├── {category}/          ← Per-category JSON
│   └── cartoons/{show}/     ← Per-show JSON
└── .github/
    └── workflows/           ← GitHub Actions (cron scraper)
```

---

## Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository.
2. **Create a branch** for your feature: `git checkout -b feature/my-feature`.
3. **Make your changes** and test locally with `python scripts/scraper.py`.
4. **Submit a pull request** with a clear description of what you changed and why.

To request a new content category, use the [New Category Request](../../issues/new?template=new-category.yml) issue template.

---

## Sponsorship

If you find this project useful, consider supporting its development:

- ⭐ **Star this repo** — it helps with visibility
- 🐛 **Report bugs** and suggest features via [Issues](../../issues)
- 💖 **Sponsor** — see [FUNDING.yml](.github/FUNDING.yml) for options

---

## License

This project is licensed under the [MIT License](LICENSE).
