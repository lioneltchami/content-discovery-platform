const { addonBuilder, serveHTTP } = require('stremio-addon-sdk');
const fetch = require('node-fetch');

// Configuration — update these for your instance
const ADDON_ID = 'community.contenthub';
const ADDON_NAME = 'ContentHub';
const API_URL = 'https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/movies/movies.json';

const manifest = {
  id: ADDON_ID,
  version: '1.0.0',
  name: ADDON_NAME,
  description: 'Discover free movies and videos from YouTube and Dailymotion',
  resources: ['catalog', 'meta', 'stream'],
  types: ['movie'],
  catalogs: [
    { type: 'movie', id: 'contenthub-all', name: `${ADDON_NAME} - All` },
    { type: 'movie', id: 'contenthub-trending', name: `${ADDON_NAME} - Trending` },
  ],
  idPrefixes: ['ch-'],
};

let cachedMovies = null;
let cacheTime = 0;
const CACHE_TTL = 3600000; // 1 hour

async function getMovies() {
  if (cachedMovies && Date.now() - cacheTime < CACHE_TTL) return cachedMovies;
  const res = await fetch(API_URL);
  const data = await res.json();
  cachedMovies = data.movies || [];
  cacheTime = Date.now();
  return cachedMovies;
}

const builder = new addonBuilder(manifest);

builder.defineCatalogHandler(async ({ type, id, extra }) => {
  const movies = await getMovies();
  let items = movies;
  if (id === 'contenthub-trending') {
    items = [...movies].sort((a, b) => (b.view_count || 0) - (a.view_count || 0));
  }
  if (extra && extra.search) {
    const q = extra.search.toLowerCase();
    items = items.filter(m => m.title && m.title.toLowerCase().includes(q));
  }
  const metas = items.slice(0, 100).map(m => ({
    id: `ch-${m.id}`,
    type: 'movie',
    name: m.title,
    poster: m.thumbnail || `https://i.ytimg.com/vi/${m.id}/hqdefault.jpg`,
    description: `${m.category} | ${m.uploader || 'Unknown'} | ${formatViews(m.view_count)}`,
  }));
  return { metas };
});

builder.defineMetaHandler(async ({ type, id }) => {
  const videoId = id.replace('ch-', '');
  const movies = await getMovies();
  const m = movies.find(mv => mv.id === videoId);
  if (!m) return { meta: null };
  return {
    meta: {
      id: `ch-${m.id}`,
      type: 'movie',
      name: m.title,
      poster: m.thumbnail || `https://i.ytimg.com/vi/${m.id}/hqdefault.jpg`,
      description: `Category: ${m.category}\nUploader: ${m.uploader || 'Unknown'}\nViews: ${formatViews(m.view_count)}`,
      runtime: m.duration ? `${Math.floor(m.duration / 60)} min` : undefined,
    },
  };
});

builder.defineStreamHandler(async ({ type, id }) => {
  const videoId = id.replace('ch-', '');
  const movies = await getMovies();
  const m = movies.find(mv => mv.id === videoId);
  if (!m) return { streams: [] };
  const source = m.source || 'youtube';
  const streams = [];
  if (source === 'youtube') {
    streams.push({ title: 'YouTube', ytId: videoId });
  } else if (source === 'dailymotion') {
    streams.push({ title: 'Dailymotion', externalUrl: `https://www.dailymotion.com/video/${videoId}` });
  }
  return { streams };
});

function formatViews(count) {
  if (!count) return '0 views';
  if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M views';
  if (count >= 1000) return (count / 1000).toFixed(1) + 'K views';
  return count + ' views';
}

serveHTTP(builder.getInterface(), { port: process.env.PORT || 7000 });
console.log(`Stremio addon running on port ${process.env.PORT || 7000}`);
