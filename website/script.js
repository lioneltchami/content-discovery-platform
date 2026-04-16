// ==============================
// Config-Driven Content Hub – Main Script
// ==============================

// ── Theme Toggle ──
function initTheme() {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  updateThemeIcon(theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

let siteConfig = null;

async function loadSiteConfig() {
  const res = await fetch('site-config.json');
  if (!res.ok) throw new Error('Failed to load site-config.json');
  siteConfig = await res.json();
}

function getApiUrl() {
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    || window.location.protocol === 'file:';
  if (isLocal) {
    return '../' + siteConfig.api_base_url + '/movies.json';
  }
  // For GitHub Pages or similar: use raw GitHub URL
  if (siteConfig.site.github_repo) {
    return siteConfig.site.github_repo.replace('github.com', 'raw.githubusercontent.com') + '/main/' + siteConfig.api_base_url + '/movies.json';
  }
  return siteConfig.api_base_url + '/movies.json';
}

const PAGE_SIZE = 48;
let currentPage = 1;
let allMovies = [];
let currentFilter = 'all';
let placeholderColors = {};

// ── Format duration (seconds → h:mm:ss) ──
function formatDuration(seconds) {
  if (!seconds) return '--:--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

// ── Format view count ──
function formatViews(count) {
  if (!count) return '0 views';
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M views`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K views`;
  return `${count} views`;
}

// ── Create movie card HTML ──
function createMovieCard(movie) {
  const card = document.createElement('a');
  card.className = 'movie-card';
  card.href = `player.html?v=${movie.id}&source=${movie.source || 'youtube'}`;
  card.dataset.category = (movie.category || '').toLowerCase();

  const thumbnailUrl = movie.thumbnail || `https://i.ytimg.com/vi/${movie.id}/hqdefault.jpg`;
  const sourceBadge = movie.source === 'dailymotion' ? 'DM' : 'YT';
  const placeholderColor = placeholderColors[movie.id] || '#1a1a2e';

  card.innerHTML = `
    <div class="card-thumbnail" style="background:${placeholderColor}">
      <img src="${thumbnailUrl}" alt="${escapeHtml(movie.title)}" loading="lazy" />
      <span class="card-duration">${formatDuration(movie.duration)}</span>
      <span class="card-category-badge">${escapeHtml(movie.category || 'Unknown')}</span>
      <span class="card-source-badge">${sourceBadge}</span>
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
        <span class="card-uploader" title="${escapeHtml(movie.uploader || '')}">${escapeHtml(movie.uploader || 'Unknown')}</span>
      </div>
    </div>
  `;

  // Watchlist button
  const bookmarkBtn = document.createElement('button');
  bookmarkBtn.className = 'watchlist-btn' + (isInWatchlist(movie.id) ? ' saved' : '');
  bookmarkBtn.innerHTML = isInWatchlist(movie.id) ? '🔖' : '🏷️';
  bookmarkBtn.title = 'Add to watchlist';
  bookmarkBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleWatchlist(movie.id);
    bookmarkBtn.classList.toggle('saved');
    bookmarkBtn.innerHTML = bookmarkBtn.classList.contains('saved') ? '🔖' : '🏷️';
  });
  card.appendChild(bookmarkBtn);

  // Hover detail
  const hoverDetail = document.createElement('div');
  hoverDetail.className = 'card-hover-detail';
  hoverDetail.innerHTML = `
    <span>${escapeHtml(movie.uploader || 'Unknown uploader')}</span>
    <span>${formatDuration(movie.duration)}</span>
    <span>${formatViews(movie.view_count)}</span>
    ${movie.source === 'dailymotion' ? '<span>Dailymotion</span>' : ''}
  `;
  card.querySelector('.card-body').appendChild(hoverDetail);

  // Recently watched tracking
  card.addEventListener('click', () => addToRecentlyWatched(movie.id));

  return card;
}

// ── Escape HTML to prevent XSS ──
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Show loading skeletons ──
function showSkeletons(container, count = 12) {
  container.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const skeleton = document.createElement('div');
    skeleton.className = 'skeleton-card';
    skeleton.innerHTML = `
      <div class="skeleton-thumb"></div>
      <div class="skeleton-body">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    `;
    container.appendChild(skeleton);
  }
}

// ── Render movies ──
function renderMovies(movies) {
  const grid = document.getElementById('moviesGrid');
  grid.innerHTML = '';

  const label = siteConfig ? siteConfig.site.content_label_plural : 'movies';

  if (movies.length === 0) {
    grid.innerHTML = `
      <div class="no-results">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="M21 21l-4.35-4.35"></path>
        </svg>
        <h3>No ${escapeHtml(label)} found</h3>
        <p>Try selecting a different category</p>
      </div>
    `;
    return;
  }

  const visible = movies.slice(0, currentPage * PAGE_SIZE);
  visible.forEach(movie => grid.appendChild(createMovieCard(movie)));

  if (visible.length < movies.length) {
    const loadMoreBtn = document.createElement('button');
    loadMoreBtn.className = 'load-more-btn';
    loadMoreBtn.textContent = `Load More (${movies.length - visible.length} remaining)`;
    loadMoreBtn.addEventListener('click', () => {
      currentPage++;
      renderMovies(movies);
    });
    grid.appendChild(loadMoreBtn);
  }
}

// ── Filter movies ──
function filterMovies(category) {
  currentFilter = category;
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.category === category);
  });
  applyFilters();
}

// ── Fuzzy Search ──
function fuzzyMatch(text, query) {
  if (!text || !query) return false;
  const t = text.toLowerCase();
  const q = query.toLowerCase().trim();
  if (t.includes(q)) return true;
  const words = q.split(/\s+/);
  const textWords = t.split(/\s+/);
  return words.every(w => textWords.some(tw => tw.startsWith(w) || tw.includes(w)));
}

// ── Search & Filter Logic ──
let searchQuery = '';

function applyFilters() {
  currentPage = 1;
  let filtered = allMovies;

  if (currentFilter === '_watchlist') {
    const wl = getWatchlist();
    filtered = filtered.filter(m => wl.includes(m.id));
  } else if (currentFilter === '_recent') {
    const recent = getRecentlyWatched();
    filtered = recent.map(id => allMovies.find(m => m.id === id)).filter(Boolean);
  } else if (currentFilter !== 'all') {
    filtered = filtered.filter(m => (m.category || '').toLowerCase() === currentFilter);
  }

  if (searchQuery.trim() !== '') {
    filtered = filtered.filter(m =>
      fuzzyMatch(m.title, searchQuery) ||
      fuzzyMatch(m.uploader, searchQuery) ||
      fuzzyMatch(m.category, searchQuery)
    );
  }

  const countEl = document.getElementById('searchResultCount');
  if (countEl) {
    countEl.textContent = searchQuery.trim() !== ''
      ? `Found ${filtered.length} result${filtered.length !== 1 ? 's' : ''}`
      : '';
  }

  renderMovies(filtered);
}

// ── Search Suggestions ──
let suggestionsEl = null;

function initSuggestions() {
  if (suggestionsEl) return;
  const wrapper = document.querySelector('.search-wrapper');
  if (!wrapper) return;
  wrapper.style.position = 'relative';
  suggestionsEl = document.createElement('div');
  suggestionsEl.id = 'searchSuggestions';
  suggestionsEl.className = 'search-suggestions';
  suggestionsEl.style.cssText = 'position:absolute;top:100%;left:0;right:0;z-index:100;background:var(--bg-secondary,#1a1a2e);border:1px solid var(--border-color,#333);border-radius:8px;margin-top:4px;display:none;max-height:240px;overflow:auto;box-shadow:0 8px 24px rgba(0,0,0,.4)';
  wrapper.appendChild(suggestionsEl);
}

function showSuggestions(query) {
  if (!suggestionsEl || !query.trim()) { hideSuggestions(); return; }
  const matches = allMovies.filter(m => fuzzyMatch(m.title, query)).slice(0, 5);
  if (!matches.length) { hideSuggestions(); return; }
  suggestionsEl.innerHTML = matches.map(m =>
    `<div class="suggestion-item" style="padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--border-color,#333);color:var(--text-primary,#eee);font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(m.title)}</div>`
  ).join('');
  suggestionsEl.querySelectorAll('.suggestion-item').forEach((el, i) => {
    el.addEventListener('mousedown', (e) => {
      e.preventDefault();
      searchInput.value = matches[i].title;
      searchQuery = matches[i].title;
      hideSuggestions();
      applyFilters();
    });
  });
  suggestionsEl.style.display = 'block';
}

function hideSuggestions() {
  if (suggestionsEl) suggestionsEl.style.display = 'none';
}

// ── Search Events ──
const searchInput = document.getElementById('searchInput');
const searchClear = document.getElementById('searchClear');
let searchTimeout;

if (searchInput) {
  initSuggestions();
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    if (searchClear) searchClear.classList.toggle('visible', searchQuery.trim() !== '');
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { applyFilters(); showSuggestions(searchQuery); }, 250);
  });
  searchInput.addEventListener('blur', () => setTimeout(hideSuggestions, 150));
  searchInput.addEventListener('focus', () => { if (searchQuery.trim()) showSuggestions(searchQuery); });
}

function clearSearch() {
  if (searchInput) {
    searchInput.value = '';
    searchQuery = '';
    if (searchClear) searchClear.classList.remove('visible');
    hideSuggestions();
    applyFilters();
    searchInput.focus();
  }
}

// ── Keyboard Shortcuts ──
let shortcutsModal = null;

function showShortcutsHelp() {
  if (shortcutsModal) { shortcutsModal.remove(); shortcutsModal = null; return; }
  shortcutsModal = document.createElement('div');
  shortcutsModal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center';
  const shortcuts = [
    ['/', 'Focus search'],
    ['Ctrl+K', 'Focus search'],
    ['Esc', 'Clear search / close modal'],
    ['?', 'Show this help'],
    ['j', 'Next movie card'],
    ['k', 'Previous movie card'],
    ['Enter', 'Open focused card'],
  ];
  const box = document.createElement('div');
  box.style.cssText = 'background:var(--bg-secondary,#1a1a2e);border:1px solid var(--border-color,#333);border-radius:12px;padding:24px;max-width:400px;width:90%;color:var(--text-primary,#eee)';
  box.innerHTML = '<h3 style="margin:0 0 16px;font-size:1.1rem">⌨️ Keyboard Shortcuts</h3>' +
    shortcuts.map(([k, d]) => `<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border-color,#222)"><kbd style="background:var(--bg-primary,#0a0a1a);padding:2px 8px;border-radius:4px;font-size:0.85rem">${k}</kbd><span style="font-size:0.9rem">${d}</span></div>`).join('');
  shortcutsModal.appendChild(box);
  shortcutsModal.addEventListener('click', (e) => { if (e.target === shortcutsModal) dismissShortcutsHelp(); });
  document.body.appendChild(shortcutsModal);
}

function dismissShortcutsHelp() {
  if (shortcutsModal) { shortcutsModal.remove(); shortcutsModal = null; }
}

document.addEventListener('keydown', (e) => {
  const inInput = document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA' || document.activeElement.isContentEditable);

  // Escape: dismiss modal, or clear search
  if (e.key === 'Escape') {
    if (shortcutsModal) { dismissShortcutsHelp(); return; }
    if (searchInput) { searchInput.value = ''; searchQuery = ''; hideSuggestions(); if (searchClear) searchClear.classList.remove('visible'); applyFilters(); searchInput.blur(); }
    return;
  }

  // Ctrl+K: focus search (works even in input)
  if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    if (searchInput) searchInput.focus();
    return;
  }

  if (inInput) return;

  // / : focus search
  if (e.key === '/') {
    e.preventDefault();
    if (searchInput) searchInput.focus();
    return;
  }

  // ? : show shortcuts help
  if (e.key === '?') {
    e.preventDefault();
    showShortcutsHelp();
    return;
  }

  // j/k: navigate movie cards
  if (e.key === 'j' || e.key === 'k') {
    const cards = Array.from(document.querySelectorAll('.movie-card'));
    if (!cards.length) return;
    const idx = cards.indexOf(document.activeElement);
    const next = e.key === 'j' ? Math.min(idx + 1, cards.length - 1) : Math.max(idx - 1, 0);
    cards[next].focus();
    cards[next].scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
});

// ── Update stats ──
function updateStats(movies) {
  const label = siteConfig ? siteConfig.site.content_label_plural : 'Movies';
  const capitalLabel = label.charAt(0).toUpperCase() + label.slice(1);

  const totalEl = document.getElementById('totalMovies');
  const categoriesEl = document.getElementById('totalCategories');
  const viewsEl = document.getElementById('totalViews');
  const totalLabel = document.getElementById('totalMoviesLabel');

  if (totalEl) totalEl.textContent = movies.length;
  if (totalLabel) totalLabel.textContent = capitalLabel;

  if (categoriesEl) {
    const uniqueCategories = new Set(movies.map(m => m.category));
    categoriesEl.textContent = uniqueCategories.size;
  }

  if (viewsEl) {
    const total = movies.reduce((sum, m) => sum + (m.view_count || 0), 0);
    if (total >= 1_000_000_000) viewsEl.textContent = (total / 1_000_000_000).toFixed(1) + 'B';
    else if (total >= 1_000_000) viewsEl.textContent = (total / 1_000_000).toFixed(0) + 'M';
    else viewsEl.textContent = (total / 1_000).toFixed(0) + 'K';
  }
}

// ── Render filter buttons from config ──
function renderFilterButtons() {
  const bar = document.getElementById('filterBar');
  if (!bar || !siteConfig) return;
  bar.innerHTML = '';

  // "All" button
  const allBtn = document.createElement('button');
  allBtn.className = 'filter-btn active';
  allBtn.dataset.category = 'all';
  allBtn.textContent = '🎞️ All';
  allBtn.addEventListener('click', () => filterMovies('all'));
  bar.appendChild(allBtn);

  // Watchlist button
  const watchlistBtn = document.createElement('button');
  watchlistBtn.className = 'filter-btn';
  watchlistBtn.dataset.category = '_watchlist';
  watchlistBtn.innerHTML = '🔖 My Watchlist';
  watchlistBtn.addEventListener('click', () => filterMovies('_watchlist'));
  bar.appendChild(watchlistBtn);

  // Recently Watched button
  const recentBtn = document.createElement('button');
  recentBtn.className = 'filter-btn';
  recentBtn.dataset.category = '_recent';
  recentBtn.innerHTML = '🕐 Recently Watched';
  recentBtn.addEventListener('click', () => filterMovies('_recent'));
  bar.appendChild(recentBtn);

  // Category buttons
  for (const [key, cat] of Object.entries(siteConfig.categories)) {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.category = key;
    btn.textContent = `${cat.icon} ${cat.display_name}`;
    btn.addEventListener('click', () => filterMovies(key));
    bar.appendChild(btn);
  }

  // Cartoon shows dropdown
  if (siteConfig.cartoon_shows && Object.keys(siteConfig.cartoon_shows).length > 0) {
    const dropdownWrapper = document.createElement('div');
    dropdownWrapper.className = 'filter-dropdown';

    const dropdownBtn = document.createElement('button');
    dropdownBtn.className = 'filter-btn filter-dropdown-toggle';
    dropdownBtn.innerHTML = '📺 Shows ▾';
    dropdownBtn.addEventListener('click', () => {
      dropdownWrapper.classList.toggle('open');
      dropdownBtn.innerHTML = dropdownWrapper.classList.contains('open') ? '📺 Shows ▴' : '📺 Shows ▾';
    });
    dropdownWrapper.appendChild(dropdownBtn);

    const dropdownContent = document.createElement('div');
    dropdownContent.className = 'filter-dropdown-content';

    for (const [key, show] of Object.entries(siteConfig.cartoon_shows)) {
      const btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.dataset.category = `cartoons/${key}`;
      btn.textContent = `${show.icon} ${show.display_name}`;
      btn.addEventListener('click', () => filterMovies(`cartoons/${key}`));
      dropdownContent.appendChild(btn);
    }

    dropdownWrapper.appendChild(dropdownContent);
    bar.appendChild(dropdownWrapper);
  }

  // Surprise Me button
  const surpriseBtn = document.createElement('button');
  surpriseBtn.className = 'filter-btn surprise-btn';
  surpriseBtn.innerHTML = '🎲 Surprise Me';
  surpriseBtn.addEventListener('click', () => {
    const filtered = currentFilter === 'all' ? allMovies : allMovies.filter(m => (m.category || '').toLowerCase() === currentFilter);
    if (filtered.length === 0) return;
    const random = filtered[Math.floor(Math.random() * filtered.length)];
    window.location.href = `player.html?v=${random.id}&source=${random.source || 'youtube'}`;
  });
  bar.appendChild(surpriseBtn);
}

// ── Apply theme from config ──
function applyTheme() {
  if (!siteConfig) return;
  const s = siteConfig.site;
  const root = document.documentElement.style;
  if (s.theme_color) root.setProperty('--accent-1', s.theme_color);
  if (s.accent_color) root.setProperty('--accent-2', s.accent_color);
  if (s.background_color) root.setProperty('--bg-primary', s.background_color);

  // Update meta theme-color
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta && s.theme_color) meta.setAttribute('content', s.theme_color);
}

// ── Apply site identity to the page ──
function applySiteIdentity() {
  if (!siteConfig) return;
  const s = siteConfig.site;

  const siteName = document.getElementById('siteName');
  if (siteName) siteName.textContent = s.name;

  const siteTagline = document.getElementById('siteTagline');
  if (siteTagline) siteTagline.textContent = s.tagline;

  // Logo
  const logoIcon = document.querySelector('.logo-icon');
  if (logoIcon) logoIcon.textContent = s.logo_emoji;

  const logoText = document.querySelector('.logo-text');
  if (logoText) {
    // Split name into two parts for the <span> styling
    const parts = s.name.split(' ');
    if (parts.length > 1) {
      logoText.innerHTML = escapeHtml(parts[0]) + '<span>' + escapeHtml(parts.slice(1).join(' ')) + '</span>';
    } else {
      logoText.textContent = s.name;
    }
  }

  // Footer brand
  const footerBrand = document.querySelector('.footer-brand h3');
  if (footerBrand && logoText) footerBrand.innerHTML = logoText.innerHTML;

  const footerDesc = document.querySelector('.footer-brand p');
  if (footerDesc) footerDesc.textContent = s.footer_text;

  // Footer categories
  const footerCats = document.getElementById('footerCategories');
  if (footerCats) {
    footerCats.innerHTML = '';
    for (const [key, cat] of Object.entries(siteConfig.categories)) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#';
      a.textContent = cat.display_name;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        filterMovies(key);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      li.appendChild(a);
      footerCats.appendChild(li);
    }
  }

  // GitHub links
  const navGithub = document.getElementById('navGithubLink');
  if (navGithub && s.github_repo) navGithub.href = s.github_repo;

  const footerGithub = document.getElementById('footerGithubLink');
  if (footerGithub && s.github_repo) footerGithub.href = s.github_repo;

  // Footer bottom
  const footerSiteName = document.getElementById('footerSiteName');
  if (footerSiteName) footerSiteName.textContent = s.name;

  const footerYear = document.getElementById('footerYear');
  if (footerYear) footerYear.textContent = new Date().getFullYear();

  // Page title
  document.title = `${s.name} – ${s.tagline || 'Free Content'}`;
}

// ── Toast ──
function showToast(msg) {
  let t = document.querySelector('.toast') || document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => { t.classList.add('visible'); });
  setTimeout(() => { t.classList.remove('visible'); }, 3000);
}

// ── Voice Search ──
function startVoiceSearch() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    showToast('Voice search is not supported in this browser');
    return;
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SR();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  const btn = document.getElementById('voiceSearchBtn');
  btn.classList.add('listening');
  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    const input = document.getElementById('searchInput');
    if (input) { input.value = text; searchQuery = text; applyFilters(); }
    btn.classList.remove('listening');
  };
  recognition.onerror = () => btn.classList.remove('listening');
  recognition.onend = () => btn.classList.remove('listening');
  recognition.start();
}

// ── Watchlist ──
function getWatchlist() {
  return JSON.parse(localStorage.getItem('watchlist') || '[]');
}
function toggleWatchlist(movieId) {
  let list = getWatchlist();
  if (list.includes(movieId)) {
    list = list.filter(id => id !== movieId);
    showToast('Removed from watchlist');
  } else {
    list.push(movieId);
    showToast('Added to watchlist');
  }
  localStorage.setItem('watchlist', JSON.stringify(list));
}
function isInWatchlist(movieId) {
  return getWatchlist().includes(movieId);
}

// ── Recently Watched ──
function addToRecentlyWatched(movieId) {
  let recent = JSON.parse(localStorage.getItem('recentlyWatched') || '[]');
  recent = recent.filter(id => id !== movieId);
  recent.unshift(movieId);
  recent = recent.slice(0, 20);
  localStorage.setItem('recentlyWatched', JSON.stringify(recent));
}
function getRecentlyWatched() {
  return JSON.parse(localStorage.getItem('recentlyWatched') || '[]');
}

// ── Featured Video ──
function renderFeatured() {
  if (!allMovies.length) return;
  const top = allMovies.reduce((a, b) => (b.view_count || 0) > (a.view_count || 0) ? b : a);
  const card = document.getElementById('featuredCard');
  const section = document.getElementById('featuredSection');
  if (!card || !section) return;
  const thumb = top.thumbnail || `https://i.ytimg.com/vi/${top.id}/hqdefault.jpg`;
  card.innerHTML = `
    <img src="${thumb}" alt="${escapeHtml(top.title)}" />
    <div class="featured-overlay">
      <div class="featured-title">${escapeHtml(top.title)}</div>
      <div class="featured-meta">
        <span class="featured-badge">${escapeHtml(top.category || 'Unknown')}</span>
        <span>${formatViews(top.view_count)}</span>
        <span>${escapeHtml(top.uploader || '')}</span>
      </div>
    </div>
  `;
  card.addEventListener('click', () => {
    window.location.href = `player.html?v=${top.id}&source=${top.source || 'youtube'}`;
  });
  section.style.display = '';
}

// ── Initialize ──
async function init() {
  initTheme();
  const grid = document.getElementById('moviesGrid');
  if (!grid) return;

  grid.setAttribute('aria-live', 'polite');
  showSkeletons(grid);

  try {
    await loadSiteConfig();
    applyTheme();
    applySiteIdentity();
    if (typeof renderNavbar === 'function') { renderNavbar('home'); renderFooter(); }
    renderFilterButtons();

    const res = await fetch(getApiUrl());
    if (!res.ok) throw new Error('Failed to fetch content');
    const data = await res.json();
    allMovies = data.movies || [];

    // Load placeholder colors (non-blocking)
    try {
      const pUrl = getApiUrl().replace('movies.json', 'placeholders.json');
      const pRes = await fetch(pUrl);
      if (pRes.ok) placeholderColors = await pRes.json();
    } catch (e) { /* placeholders are optional */ }

    updateStats(allMovies);
    renderFeatured();
    renderMovies(allMovies);
  } catch (error) {
    console.error('Error loading content:', error);
    grid.innerHTML = `
      <div class="no-results">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
        </svg>
        <h3>Could not load content</h3>
        <p>Please check your internet connection and try again</p>
        <button class="retry-btn" onclick="init()">Retry</button>
      </div>
    `;
  }
}

// ── Copy code block to clipboard (for docs page) ──
function copyCode(button) {
  const codeBlock = button.closest('.code-block').querySelector('pre');
  const text = codeBlock.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const original = button.textContent;
    button.textContent = 'Copied!';
    setTimeout(() => { button.textContent = original; }, 2000);
  });
}

// ── Sync: Save/Restore via short code ──
function showSyncModal() {
  const existing = document.querySelector('.sync-modal');
  if (existing) { existing.remove(); return; }

  const modal = document.createElement('div');
  modal.className = 'sync-modal';
  modal.innerHTML = `
    <div class="sync-modal-content">
      <h3>🔄 Sync Your Data</h3>
      <p>Save your watchlist and history to access on any device.</p>
      <div class="sync-tabs">
        <button class="sync-tab active" onclick="showSyncTab('save')">Save</button>
        <button class="sync-tab" onclick="showSyncTab('restore')">Restore</button>
      </div>
      <div id="syncSaveTab" class="sync-tab-content">
        <p>Get a 6-character code to restore your data on another device.</p>
        <button class="sync-action-btn" onclick="doSyncSave()" id="syncSaveBtn">Save My Stuff</button>
        <div id="syncSaveResult" class="sync-result"></div>
      </div>
      <div id="syncRestoreTab" class="sync-tab-content" style="display:none">
        <p>Enter your 6-character code to restore your watchlist and history.</p>
        <input type="text" id="syncCodeInput" class="sync-code-input" maxlength="6" placeholder="e.g. K7X2M9" autocomplete="off" />
        <button class="sync-action-btn" onclick="doSyncRestore()" id="syncRestoreBtn">Restore My Stuff</button>
        <div id="syncRestoreResult" class="sync-result"></div>
      </div>
      <a href="/sync-help" class="sync-help-link">How does this work?</a>
    </div>
  `;
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
  document.body.appendChild(modal);
}

function showSyncTab(tab) {
  document.getElementById('syncSaveTab').style.display = tab === 'save' ? 'block' : 'none';
  document.getElementById('syncRestoreTab').style.display = tab === 'restore' ? 'block' : 'none';
  document.querySelectorAll('.sync-tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0 && tab === 'save') || (i === 1 && tab === 'restore'));
  });
}

async function doSyncSave() {
  const btn = document.getElementById('syncSaveBtn');
  const result = document.getElementById('syncSaveResult');
  btn.disabled = true;
  btn.textContent = 'Saving...';
  try {
    const data = {
      watchlist: JSON.parse(localStorage.getItem('watchlist') || '[]'),
      recentlyWatched: JSON.parse(localStorage.getItem('recentlyWatched') || '[]'),
    };
    const res = await fetch('/api/sync-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const json = await res.json();
    if (res.ok) {
      result.innerHTML = `<div class="sync-success">
        <div class="sync-code">${json.code}</div>
        <p>Write this code down! It expires in ${json.expiresIn}.</p>
      </div>`;
    } else {
      result.innerHTML = `<div class="sync-error">${json.error}</div>`;
    }
  } catch (e) {
    result.innerHTML = '<div class="sync-error">Could not connect. Try again later.</div>';
  }
  btn.disabled = false;
  btn.textContent = 'Save My Stuff';
}

async function doSyncRestore() {
  const btn = document.getElementById('syncRestoreBtn');
  const result = document.getElementById('syncRestoreResult');
  const code = document.getElementById('syncCodeInput').value.trim().toUpperCase();
  if (code.length !== 6) {
    result.innerHTML = '<div class="sync-error">Please enter a 6-character code.</div>';
    return;
  }
  btn.disabled = true;
  btn.textContent = 'Restoring...';
  try {
    const res = await fetch('/api/sync-restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    const json = await res.json();
    if (res.ok) {
      if (json.watchlist) localStorage.setItem('watchlist', JSON.stringify(json.watchlist));
      if (json.recentlyWatched) localStorage.setItem('recentlyWatched', JSON.stringify(json.recentlyWatched));
      result.innerHTML = `<div class="sync-success">
        <p>✅ Restored! ${(json.watchlist || []).length} watchlist items and ${(json.recentlyWatched || []).length} recently watched.</p>
        <p>Refreshing page...</p>
      </div>`;
      setTimeout(() => location.reload(), 1500);
    } else {
      result.innerHTML = `<div class="sync-error">${json.error}</div>`;
    }
  } catch (e) {
    result.innerHTML = '<div class="sync-error">Could not connect. Try again later.</div>';
  }
  btn.disabled = false;
  btn.textContent = 'Restore My Stuff';
}

// Run on page load
document.addEventListener('DOMContentLoaded', init);
