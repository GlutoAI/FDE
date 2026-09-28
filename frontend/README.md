# Frontend

React + TypeScript + Vite frontend for the FDE Interview App.

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Starts the Vite dev server on `http://localhost:5173`. API calls to `/api/*` are proxied to the backend at `http://localhost:8000` (configured in `vite.config.ts`).

## Build

```bash
npm run build
```

Output is written to `dist/`.

## Project structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── src/
    ├── main.tsx          # React entry point
    ├── App.tsx           # Root component — fetches /api/health on mount
    ├── App.css           # Global styles
    └── api/
        └── client.ts     # Typed fetch wrapper for backend API
```

## API client

`src/api/client.ts` exports typed functions that hit the backend. All requests use the `/api` prefix which Vite proxies during development. In production, the backend must serve the built `dist/` folder or a reverse proxy must route `/api` accordingly.
