const { kv } = require('@vercel/kv');

function generateCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // no 0/O/1/I to avoid confusion
  let code = '';
  for (let i = 0; i < 6; i++) code += chars[Math.floor(Math.random() * chars.length)];
  return code;
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { watchlist, recentlyWatched } = req.body;
    if (!watchlist && !recentlyWatched) {
      return res.status(400).json({ error: 'No data to save' });
    }

    // Generate unique code (retry if collision)
    let code, attempts = 0;
    do {
      code = generateCode();
      const existing = await kv.get(`sync:${code}`);
      if (!existing) break;
      attempts++;
    } while (attempts < 5);

    const data = {
      watchlist: watchlist || [],
      recentlyWatched: recentlyWatched || [],
      savedAt: new Date().toISOString(),
    };

    // Store with 30-day expiry (2592000 seconds)
    await kv.set(`sync:${code}`, JSON.stringify(data), { ex: 2592000 });

    return res.status(200).json({ code, expiresIn: '30 days' });
  } catch (err) {
    console.error('Sync save error:', err);
    return res.status(500).json({ error: 'Failed to save' });
  }
};
