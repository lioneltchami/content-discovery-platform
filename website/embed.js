(function() {
  'use strict';
  const script = document.currentScript;
  const baseUrl = script.src.replace('/embed.js', '');
  const category = script.getAttribute('data-category') || '';
  const count = parseInt(script.getAttribute('data-count') || '6', 10);
  const theme = script.getAttribute('data-theme') || 'dark';

  const colors = theme === 'light'
    ? { bg: '#f5f5f7', card: '#fff', text: '#1a1a2e', muted: '#6a6a8a', border: '#e0e0e0', accent: '#7c3aed' }
    : { bg: '#0a0a1a', card: '#1a1a2e', text: '#f0f0ff', muted: '#8b8bab', border: '#2a2a4a', accent: '#7c3aed' };

  // Create container
  const container = document.createElement('div');
  container.id = 'contenthub-embed-' + Math.random().toString(36).substr(2, 6);
  container.style.cssText = `font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:${colors.bg};border-radius:12px;padding:16px;border:1px solid ${colors.border};overflow:hidden;`;
  container.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <span style="font-weight:700;font-size:14px;color:${colors.text};">Powered by ContentHub</span>
    <a href="${baseUrl}/" target="_blank" rel="noopener" style="font-size:12px;color:${colors.accent};text-decoration:none;">View all →</a>
  </div>
  <div id="${container.id}-grid" style="display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none;"></div>`;
  script.parentNode.insertBefore(container, script);

  // Fetch and render
  fetch(baseUrl + '/site-config.json').then(r => r.json()).then(config => {
    const apiBase = config.site.github_repo
      ? config.site.github_repo.replace('github.com', 'raw.githubusercontent.com') + '/main/' + config.api_base_url
      : baseUrl + '/../' + config.api_base_url;
    return fetch(apiBase + '/movies.json');
  }).then(r => r.json()).then(data => {
    let movies = data.movies || [];
    if (category) {
      movies = movies.filter(m => (m.category || '').toLowerCase().includes(category.toLowerCase()));
    }
    movies = movies.sort((a, b) => (b.view_count || 0) - (a.view_count || 0)).slice(0, count);

    const grid = document.getElementById(container.id + '-grid');
    movies.forEach(m => {
      const thumb = m.thumbnail || `https://i.ytimg.com/vi/${m.id}/hqdefault.jpg`;
      const dur = m.duration ? `${Math.floor(m.duration/3600)}:${String(Math.floor((m.duration%3600)/60)).padStart(2,'0')}:${String(Math.floor(m.duration%60)).padStart(2,'0')}` : '';
      const card = document.createElement('a');
      card.href = `${baseUrl}/player?v=${m.id}&source=${m.source||'youtube'}`;
      card.target = '_blank';
      card.rel = 'noopener';
      card.style.cssText = `flex:0 0 200px;scroll-snap-align:start;text-decoration:none;color:${colors.text};background:${colors.card};border-radius:10px;overflow:hidden;border:1px solid ${colors.border};transition:transform 0.2s;`;
      card.onmouseenter = function(){this.style.transform='translateY(-3px)'};
      card.onmouseleave = function(){this.style.transform='none'};
      card.innerHTML = `<div style="position:relative;aspect-ratio:16/9;background:#121228;overflow:hidden;">
        <img src="${thumb}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;"/>
        ${dur ? `<span style="position:absolute;bottom:4px;right:4px;background:rgba(0,0,0,0.8);color:#fff;font-size:11px;padding:1px 6px;border-radius:3px;font-weight:600;">${dur}</span>` : ''}
      </div>
      <div style="padding:8px 10px;">
        <div style="font-size:12px;font-weight:600;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${escapeHtml(m.title)}</div>
        <div style="font-size:11px;color:${colors.muted};margin-top:4px;">${escapeHtml(m.uploader||'')}</div>
      </div>`;
      grid.appendChild(card);
    });
  }).catch(err => {
    container.querySelector('[id$=-grid]').innerHTML = `<p style="color:${colors.muted};font-size:13px;">Could not load content.</p>`;
  });

  function escapeHtml(t) {
    if (!t) return '';
    var d = document.createElement('div'); d.textContent = t; return d.innerHTML;
  }
})();
