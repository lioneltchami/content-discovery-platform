# ContentHub Stremio Addon

Stremio addon that serves the YouTube Content Discovery Platform catalog directly into Stremio. Browse and stream content from your platform's JSON API inside the Stremio app.

## Configuration

Edit `index.js` and update these constants:

```javascript
const ADDON_ID = 'community.contenthub';   // Unique addon identifier
const ADDON_NAME = 'ContentHub';            // Display name in Stremio
const API_URL = 'https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/movies/movies.json';
```

## Run Locally

```bash
npm install
npm start
```

The addon serves on `http://localhost:7000` by default. Set the `PORT` environment variable to change it.

## Install in Stremio

1. Start the addon (`npm start`)
2. Open Stremio
3. Go to the addon catalog (puzzle icon)
4. Enter `http://localhost:7000/manifest.json` in the addon URL field
5. Click Install

## Deploy

**Vercel** — Add a `vercel.json` with the Node.js runtime pointing to `index.js`, then `vercel deploy`.

**Railway** — Connect your repo, set root directory to `stremio-addon/`, Railway auto-detects the start script.

**BeamUp** (Stremio community hosting) — Run `npx stremio-beamup` from this directory to deploy for free.

After deploying, replace `localhost:7000` with your deployed URL when installing in Stremio.
