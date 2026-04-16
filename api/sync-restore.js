const { kv } = require('@vercel/kv');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { code } = req.body;
    if (!code || code.length !== 6) {
      return res.status(400).json({ error: 'Invalid code' });
    }

    const raw = await kv.get(`sync:${code.toUpperCase()}`);
    if (!raw) {
      return res.status(404).json({ error: 'Code not found or expired' });
    }

    const data = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return res.status(200).json(data);
  } catch (err) {
    console.error('Sync restore error:', err);
    return res.status(500).json({ error: 'Failed to restore' });
  }
};
