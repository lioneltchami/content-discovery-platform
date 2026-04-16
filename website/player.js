// ── Player State ──
let siteConfig = null;

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
}
let API_URL = '';
let currentMovie = null;
let allMovies = [];
let recommendations = {};
let isLoop = false;
let isTheater = false;

async function loadSiteConfig() {
    const res = await fetch('site-config.json');
    if (!res.ok) throw new Error('Failed to load site-config.json');
    siteConfig = await res.json();
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        || window.location.protocol === 'file:';
    if (isLocal) {
        API_URL = '../' + siteConfig.api_base_url + '/movies.json';
    } else if (siteConfig.site.github_repo) {
        API_URL = siteConfig.site.github_repo.replace('github.com', 'raw.githubusercontent.com') + '/main/' + siteConfig.api_base_url + '/movies.json';
    } else {
        API_URL = siteConfig.api_base_url + '/movies.json';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function applyPlayerConfig() {
    if (!siteConfig) return;
    const s = siteConfig.site;

    // Logo
    const logoIcon = document.querySelector('.logo-icon');
    if (logoIcon) logoIcon.textContent = s.logo_emoji;

    const logoText = document.getElementById('playerLogoText');
    if (logoText) {
        const parts = s.name.split(' ');
        if (parts.length > 1) {
            logoText.innerHTML = escapeHtml(parts[0]) + '<span>' + escapeHtml(parts.slice(1).join(' ')) + '</span>';
        } else {
            logoText.textContent = s.name;
        }
    }

    // GitHub link
    const ghLink = document.getElementById('playerGithubLink');
    if (ghLink && s.github_repo) ghLink.href = s.github_repo;

    // Theme
    const root = document.documentElement.style;
    if (s.theme_color) root.setProperty('--accent-1', s.theme_color);
    if (s.accent_color) root.setProperty('--accent-2', s.accent_color);
    if (s.background_color) root.setProperty('--bg-primary', s.background_color);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta && s.theme_color) meta.setAttribute('content', s.theme_color);

    // Footer
    const footerBrand = document.getElementById('playerFooterBrand');
    if (footerBrand && logoText) footerBrand.innerHTML = logoText.innerHTML;

    const footerDesc = document.getElementById('playerFooterDesc');
    if (footerDesc) footerDesc.textContent = s.footer_text;

    const footerGithub = document.getElementById('playerFooterGithub');
    if (footerGithub && s.github_repo) footerGithub.href = s.github_repo;

    const footerName = document.getElementById('playerFooterName');
    if (footerName) footerName.textContent = s.name;

    const footerYear = document.getElementById('playerFooterYear');
    if (footerYear) footerYear.textContent = new Date().getFullYear();

    // Footer categories
    const footerCats = document.getElementById('playerFooterCategories');
    if (footerCats && siteConfig.categories) {
        footerCats.innerHTML = '';
        for (const [key, cat] of Object.entries(siteConfig.categories)) {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = '/';
            a.textContent = cat.display_name;
            li.appendChild(a);
            footerCats.appendChild(li);
        }
    }
}

// ── Get video ID and source from URL params ──
function getVideoId() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('v');
    const source = params.get('source') || 'youtube';
    if (!id) return null;
    // Validate video ID format to prevent XSS via iframe src injection
    if (source === 'dailymotion' && !/^[a-zA-Z0-9]+$/.test(id)) return null;
    if (source !== 'dailymotion' && !/^[a-zA-Z0-9_-]{11}$/.test(id)) return null;
    return { id, source };
}

// ── Format helpers ──
function formatDuration(seconds) {
    if (!seconds) return '--:--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m ${s}s`;
}

function formatViews(count) {
    if (!count) return '0 views';
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M views`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K views`;
    return `${count} views`;
}

// ── Load and embed video player ──
function loadPlayer(videoId, source) {
    const container = document.getElementById('videoContainer');
    const loading = document.getElementById('videoLoading');

    const iframe = document.createElement('iframe');
    iframe.id = 'ytPlayer';
    if (source === 'dailymotion') {
        iframe.src = `https://www.dailymotion.com/embed/video/${videoId}?autoplay=1&quality=1080&sharing-enable=false`;
    } else {
        iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1&iv_load_policy=3&enablejsapi=1`;
    }
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    iframe.allowFullscreen = true;
    iframe.title = 'Video Player';

    iframe.onload = () => {
        loading.classList.add('hidden');
    };

    container.appendChild(iframe);
}

// ── Populate movie info ──
function setMovieInfo(movie, source) {
    document.getElementById('videoTitle').textContent = movie.title;
    document.getElementById('videoCategory').textContent = movie.category || 'Unknown';
    document.getElementById('videoViews').textContent = formatViews(movie.view_count);
    document.getElementById('videoDuration').textContent = formatDuration(movie.duration);
    document.getElementById('videoUploader').textContent = movie.uploader || 'Unknown';
    document.title = `${movie.title} – ${siteConfig ? siteConfig.site.name : 'Player'}`;

    const ytLink = document.getElementById('youtubeLink');
    if (source === 'dailymotion') {
        ytLink.href = `https://www.dailymotion.com/video/${movie.id}`;
        ytLink.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5,3 19,12 5,21"></polygon>
            </svg>
            Watch on Dailymotion`;
    } else {
        ytLink.href = movie.url || `https://www.youtube.com/watch?v=${movie.id}`;
        ytLink.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z"/>
                <path fill="#fff" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
            </svg>
            Watch on YouTube`;
    }

    // Update iframe title with actual movie title for accessibility
    const iframe = document.getElementById('ytPlayer');
    if (iframe) iframe.title = `${movie.title} - ${source === 'dailymotion' ? 'Dailymotion' : 'YouTube'} Player`;
}

// ── Player Controls ──
function toggleLoop() {
    isLoop = !isLoop;
    const btn = document.getElementById('loopBtn');
    btn.classList.toggle('active', isLoop);
    // TODO: Loop requires YouTube IFrame API (postMessage) for proper implementation.
    // Toggling iframe.src restarts the video, so we only toggle the visual state here.
}

function toggleTheater() {
    isTheater = !isTheater;
    const btn = document.getElementById('theaterBtn');
    btn.classList.toggle('active', isTheater);
    const container = document.getElementById('videoContainer');
    const wrapper = document.getElementById('playerWrapper');
    if (isTheater) {
        wrapper.style.maxWidth = '100%';
        wrapper.style.padding = '0 0 3rem';
        container.style.borderRadius = '0';
        container.style.aspectRatio = '21/9';
    } else {
        wrapper.style.maxWidth = '1100px';
        wrapper.style.padding = '1.5rem 2rem 3rem';
        container.style.borderRadius = 'var(--radius-lg)';
        container.style.aspectRatio = '16/9';
    }
}

function toggleAutoplay(btn) {
    // UI-only toggle — autoplay-next requires tracking video end events via YouTube IFrame API
    btn.classList.toggle('active');
}

function goFullscreen() {
    const iframe = document.getElementById('ytPlayer');
    if (iframe) {
        if (iframe.requestFullscreen) iframe.requestFullscreen();
        else if (iframe.webkitRequestFullscreen) iframe.webkitRequestFullscreen();
        else if (iframe.msRequestFullscreen) iframe.msRequestFullscreen();
    }
}

function showToast(message) {
    const existing = document.querySelector('.toast-msg');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast-msg';
    toast.textContent = message;
    toast.style.cssText = 'position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);background:var(--bg-card);color:var(--text-primary);padding:0.75rem 1.5rem;border-radius:var(--radius-sm);border:1px solid var(--border-color);font-size:0.9rem;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,0.3);';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function openPiP() {
    // PiP works on video elements, not iframes directly
    // Show a hint to the user
    showToast('Tip: Right-click the video twice while playing and select "Picture in Picture" from the YouTube player menu.');
}

function shareVideo() {
    const url = window.location.href;
    if (navigator.share) {
        navigator.share({ title: currentMovie?.title || 'Movie', url });
    } else {
        navigator.clipboard.writeText(url).then(() => showToast('Link copied to clipboard!'));
    }
}

function copyLink() {
    navigator.clipboard.writeText(window.location.href).then(() => {
        showToast('Player link copied!');
    });
}

function showQRCode() {
    const url = window.location.href;
    const title = currentMovie?.title || 'Video';
    const modal = document.createElement('div');
    modal.className = 'qr-modal';
    modal.innerHTML = `<div class="qr-modal-content">
        <h3>${escapeHtml(title)}</h3>
        <img src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&amp;data=${encodeURIComponent(url)}" alt="QR Code" width="250" height="250" />
        <p>Scan to watch</p>
    </div>`;
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    document.addEventListener('keydown', function handler(e) {
        if (e.key === 'Escape') { modal.remove(); document.removeEventListener('keydown', handler); }
    });
    document.body.appendChild(modal);
}

// ── Create related movie card ──
function createRelatedCard(movie) {
    const card = document.createElement('a');
    card.className = 'movie-card';
    card.href = `/player?v=${movie.id}&source=${movie.source || 'youtube'}`;
    card.dataset.category = (movie.category || '').toLowerCase();

    const thumb = movie.thumbnail || `https://i.ytimg.com/vi/${movie.id}/hqdefault.jpg`;

    card.innerHTML = `
<div class="card-thumbnail">
  <img src="${thumb}" alt="${escapeHtml(movie.title)}" loading="lazy" />
  <span class="card-duration">${formatDurationShort(movie.duration)}</span>
  <span class="card-category-badge">${escapeHtml(movie.category || '')}</span>
  <div class="play-overlay">
    <svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"></polygon></svg>
  </div>
</div>
<div class="card-body">
  <h3 class="card-title">${escapeHtml(movie.title)}</h3>
  <div class="card-meta">
    <span class="card-views">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
        <circle cx="12" cy="12" r="3"></circle>
      </svg>
      ${formatViews(movie.view_count)}
    </span>
    <span class="card-uploader">${escapeHtml(movie.uploader || '')}</span>
  </div>
</div>
  `;
    return card;
}

function formatDurationShort(seconds) {
    if (!seconds) return '--:--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
}

// ── Show related movies ──
function showRelated(movies, currentId) {
    const grid = document.getElementById('relatedGrid');
    const heading = document.getElementById('relatedHeading');
    if (heading && siteConfig) {
        const label = siteConfig.site.content_label_plural || 'Videos';
        heading.textContent = `${siteConfig.site.logo_emoji || '🎬'} More ${label.charAt(0).toUpperCase() + label.slice(1)}`;
    }

    let related = [];

    // Use pre-computed recommendations if available
    const recIds = recommendations[currentId];
    if (recIds && recIds.length > 0) {
        related = recIds.map(id => movies.find(m => m.id === id)).filter(Boolean).slice(0, 8);
    }

    // Fallback: category-based + view count sorting
    if (related.length < 4) {
        const currentCat = currentMovie ? currentMovie.category : '';
        const fallback = movies
            .filter(m => m.id !== currentId && !related.find(r => r.id === m.id))
            .sort((a, b) => {
                if (a.category === currentCat && b.category !== currentCat) return -1;
                if (a.category !== currentCat && b.category === currentCat) return 1;
                return (b.view_count || 0) - (a.view_count || 0);
            });
        related = [...related, ...fallback].slice(0, 8);
    }

    grid.innerHTML = '';
    related.forEach(m => grid.appendChild(createRelatedCard(m)));
}

// ── Show error ──
function showError(msg) {
    const wrapper = document.getElementById('playerWrapper');
    wrapper.innerHTML = `
<div class="player-error">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="12" r="10"/>
    <line x1="15" y1="9" x2="9" y2="15"/>
    <line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
  <h2>Video Not Found</h2>
  <p id="errorMsg"></p>
  <a href="/" class="action-btn primary" style="display: inline-flex; text-decoration: none;">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12l9-9 9 9"/><path d="M9 21V12h6v9"/></svg>
    Back to Home
  </a>
</div>
  `;
    // Set message via textContent to prevent XSS
    document.getElementById('errorMsg').textContent = msg;
}

function updateOGTags(movie, source) {
    const title = movie.title || 'Video';
    const desc = `Watch ${title} - ${movie.category || ''} | ${(movie.uploader || 'Unknown')}`;
    const thumb = movie.thumbnail || `https://i.ytimg.com/vi/${movie.id}/hqdefault.jpg`;
    const name = (siteConfig && siteConfig.site && siteConfig.site.name) || 'ContentHub';
    const ogImageUrl = `/api/og-image?title=${encodeURIComponent(title)}&thumbnail=${encodeURIComponent(thumb)}&category=${encodeURIComponent(movie.category || '')}&source=${source}&siteName=${encodeURIComponent(name)}`;

    const tags = {
        'meta[property="og:title"]': title,
        'meta[property="og:description"]': desc,
        'meta[property="og:image"]': ogImageUrl,
        'meta[name="twitter:title"]': title,
        'meta[name="twitter:description"]': desc,
        'meta[name="twitter:image"]': ogImageUrl
    };
    for (const [sel, val] of Object.entries(tags)) {
        const el = document.querySelector(sel);
        if (el) el.content = val;
    }
}

// ── Initialize ──
async function init() {
    // Set theme icon
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        const theme = document.documentElement.getAttribute('data-theme') || 'dark';
        themeBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
    }

    try {
        await loadSiteConfig();
        applyPlayerConfig();
        renderNavbar('player');
        renderFooter();
    } catch (e) {
        console.warn('Could not load site config:', e);
        renderNavbar('player');
        renderFooter();
    }

    const video = getVideoId();
    if (!video) {
        showError('No video ID provided. Please select a movie from the home page.');
        return;
    }

    const { id: videoId, source } = video;

    // Load player immediately
    loadPlayer(videoId, source);

    // Fetch movie data
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        allMovies = data.movies || [];

        // Fetch recommendations
        try {
            const apiBase = API_URL.replace(/\/movies\.json$/, '');
            const recRes = await fetch(apiBase + '/recommendations.json');
            if (recRes.ok) {
                const recData = await recRes.json();
                recommendations = recData.recommendations || {};
            }
        } catch(e) { /* graceful fallback */ }

        currentMovie = allMovies.find(m => m.id === videoId);

        if (currentMovie) {
            setMovieInfo(currentMovie, source);
            updateOGTags(currentMovie, source);
        } else {
            // Still play the video even if not in our DB
            document.getElementById('videoTitle').textContent = source === 'dailymotion' ? 'Dailymotion Video' : 'YouTube Video';
            const ytLink = document.getElementById('youtubeLink');
            if (source === 'dailymotion') {
                ytLink.href = `https://www.dailymotion.com/video/${videoId}`;
                ytLink.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="5,3 19,12 5,21"></polygon>
                    </svg>
                    Watch on Dailymotion`;
            } else {
                ytLink.href = `https://www.youtube.com/watch?v=${videoId}`;
            }
        }

        showRelated(allMovies, videoId);

    } catch (err) {
        console.error('Error fetching movie data:', err);
    }
}

document.addEventListener('DOMContentLoaded', init);
