# Frontend

React + TypeScript + Vite frontend for Cashflow Copilot. It never receives a secret; only non-secret `VITE_` values may reach browser code.

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
    ├── App.tsx           # Root component — health on mount, fixture connection check on demand
    ├── App.css           # Global styles
    └── api/
        └── client.ts     # Typed fetch wrappers; interfaces mirror backend response models by hand
```

## API client

`src/api/client.ts` exports typed functions that hit the backend. All requests use the `/api` prefix which Vite proxies during development. In production, the backend must serve the built `dist/` folder or a reverse proxy must route `/api` accordingly.
