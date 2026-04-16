module.exports = async (req, res) => {
  const { title, thumbnail, category, source, siteName } = req.query;

  const displayTitle = decodeURIComponent(title || 'Untitled Video');
  const displayCategory = decodeURIComponent(category || '');
  const displaySource = (source || 'youtube').toUpperCase();
  const displaySiteName = decodeURIComponent(siteName || 'ContentHub');
  const thumbUrl = decodeURIComponent(thumbnail || '');

  const truncTitle = displayTitle.length > 60 ? displayTitle.substring(0, 57) + '...' : displayTitle;
  const line1 = truncTitle.substring(0, 35);
  const line2 = truncTitle.length > 35 ? truncTitle.substring(35) : '';

  const svg = `
<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0a1a"/>
      <stop offset="100%" style="stop-color:#1a1a3e"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#7c3aed"/>
      <stop offset="100%" style="stop-color:#ec4899"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="0" y="0" width="1200" height="6" fill="url(#accent)"/>
  <rect x="60" y="80" width="480" height="270" rx="16" fill="#121228"/>
  ${thumbUrl ? `<image href="${thumbUrl}" x="60" y="80" width="480" height="270" preserveAspectRatio="xMidYMid slice" clip-path="inset(0 round 16px)"/>` : ''}
  <rect x="60" y="370" width="50" height="24" rx="12" fill="#7c3aed"/>
  <text x="85" y="387" font-family="Arial,sans-serif" font-size="13" font-weight="bold" fill="white" text-anchor="middle">${displaySource}</text>
  ${displayCategory ? `<text x="120" y="387" font-family="Arial,sans-serif" font-size="14" fill="#a0a0c0">${displayCategory}</text>` : ''}
  <text x="60" y="440" font-family="Arial,sans-serif" font-size="36" font-weight="bold" fill="#f0f0ff">${escapeXml(line1)}</text>
  ${line2 ? `<text x="60" y="485" font-family="Arial,sans-serif" font-size="36" font-weight="bold" fill="#f0f0ff">${escapeXml(line2)}</text>` : ''}
  <text x="60" y="570" font-family="Arial,sans-serif" font-size="22" font-weight="bold" fill="#7c3aed">${escapeXml(displaySiteName)}</text>
  <text x="1140" y="570" font-family="Arial,sans-serif" font-size="16" fill="#6a6a8a" text-anchor="end">Free videos from YouTube &amp; Dailymotion</text>
  <rect x="0" y="624" width="1200" height="6" fill="url(#accent)"/>
</svg>`;

  res.setHeader('Content-Type', 'image/svg+xml');
  res.setHeader('Cache-Control', 'public, max-age=86400, s-maxage=86400');
  res.status(200).send(svg);
};

function escapeXml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
