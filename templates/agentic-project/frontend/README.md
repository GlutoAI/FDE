# Frontend

React + TypeScript + Vite frontend for the Agentic Project Template.

## Setup

```bash
npm ci
```

`npm ci` installs exactly what `package-lock.json` pins. Use `npm install <package>` only to add or upgrade a dependency, then commit the updated lock file; `scripts/check.sh` runs `npm audit` against it.

## Development

```bash
npm run dev
```

Starts the Vite dev server on `http://localhost:5173`. API calls to `/api/*` are proxied to the backend at `http://localhost:8000` with the `/api` prefix removed (configured in `vite.config.ts`).

## Build

```bash
npm run build
```

Type-checks with `tsc`, then writes the bundle to `dist/`.

## Project structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── src/
    ├── main.tsx                  # React entry point and global styles
    ├── App.tsx                   # Root page: composes hooks and cards, fetches nothing itself
    ├── App.css                   # Global styles
    ├── api/
    │   └── client.ts             # Typed fetch calls and the interfaces mirroring backend models
    ├── hooks/
    │   ├── useHealthStatus.ts    # GET /health on mount and on retry
    │   └── useConnectionCheck.ts # POST /diagnostics/connection on demand
    └── components/
        ├── HealthCard.tsx        # Presentational: renders health state from props
        └── ConnectionCard.tsx    # Presentational: renders the probe result from props
```

## How data flows

Components never call `fetch`. A hook calls a function in `api/client.ts`, holds the loading, result, and error state, and returns them with an action (`refreshHealth`, `startConnectionCheck`). `App.tsx` passes that state to presentational components, which report clicks through `onX` props. A new feature follows the same three steps: an interface and a call in `client.ts`, a hook, and a component.

The interfaces in `client.ts` mirror the backend's Pydantic models by hand. When a backend response model changes, change its interface in the same commit.

## API client

All requests use the `/api` prefix, which Vite proxies during development. In production, the backend must serve the built `dist/` folder or a reverse proxy must route `/api` accordingly; the Docker `ui` service does the latter with nginx (`docker/nginx.conf`).
