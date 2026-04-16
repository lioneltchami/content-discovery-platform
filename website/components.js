// ── Shared Components ──
// Renders navbar and footer from siteConfig (or sensible defaults).

function renderNavbar(activePage) {
  const nav = document.getElementById('navbar');
  if (!nav) return;
  const s = (window.siteConfig && window.siteConfig.site) || {};
  const name = s.name || 'ContentHub';
  const emoji = s.logo_emoji || '🎬';
  const ghRepo = s.github_repo || '#';
  const parts = name.split(' ');
  const logoHtml = parts.length > 1
    ? _esc(parts[0]) + '<span>' + _esc(parts.slice(1).join(' ')) + '</span>'
    : _esc(name);
  const isHome = activePage === 'home';
  const isDocs = activePage === 'docs';
  const showSync = isHome && typeof showSyncModal === 'function';
  const theme = document.documentElement.getAttribute('data-theme') || 'dark';

  nav.innerHTML = `<div class="navbar-inner">
    <a href="/" class="logo">
      <div class="logo-icon">${emoji}</div>
      <div class="logo-text">${logoHtml}</div>
    </a>
    <ul class="nav-links">
      <li><a href="/"${isHome ? ' class="active"' : ''}>Home</a></li>
      <li><a href="/docs"${isDocs ? ' class="active"' : ''}>Docs</a></li>
      <li><a href="${_esc(ghRepo)}" target="_blank" rel="noopener">GitHub</a></li>
    </ul>
    ${showSync ? '<button class="sync-btn" onclick="showSyncModal()" aria-label="Sync data" title="Save or restore your watchlist">🔄</button>' : ''}
    <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" aria-label="Toggle dark/light mode">${theme === 'dark' ? '☀️' : '🌙'}</button>
  </div>`;
}

function renderFooter() {
  const el = document.getElementById('footer');
  if (!el) return;
  const s = (window.siteConfig && window.siteConfig.site) || {};
  const cats = (window.siteConfig && window.siteConfig.categories) || {};
  const name = s.name || 'ContentHub';
  const emoji = s.logo_emoji || '🎬';
  const ghRepo = s.github_repo || '#';
  const footerText = s.footer_text || 'A free, open-source content discovery platform powered by YouTube.';
  const parts = name.split(' ');
  const brandHtml = parts.length > 1
    ? _esc(parts[0]) + '<span>' + _esc(parts.slice(1).join(' ')) + '</span>'
    : _esc(name);

  const catItems = Object.entries(cats).map(([, c]) =>
    `<li><a href="/">${_esc(c.display_name || '')}</a></li>`
  ).join('');

  el.innerHTML = `<div class="footer-inner">
    <div class="footer-brand">
      <h3>${brandHtml}</h3>
      <p>${_esc(footerText)}</p>
    </div>
    <div class="footer-col">
      <h4>Categories</h4>
      <ul>${catItems}</ul>
    </div>
    <div class="footer-col">
      <h4>Resources</h4>
      <ul>
        <li><a href="/docs">API Documentation</a></li>
        <li><a href="${_esc(ghRepo)}" target="_blank" rel="noopener">GitHub Repo</a></li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <span>&copy; ${new Date().getFullYear()} ${_esc(name)}.</span>
    <span>Updated daily via GitHub Actions</span>
  </div>`;
}

function _esc(t) {
  if (!t) return '';
  var d = document.createElement('div');
  d.textContent = t;
  return d.innerHTML;
}
