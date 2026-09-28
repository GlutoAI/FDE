# Architecture

A deliberately small full-stack scaffold: a FastAPI service over SQLite, and a React single-page app that calls it. The only feature implemented end to end is a health check, which exists to prove the wiring works.

## Layout

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, lifespan, router registration
│   ├── database.py        # SQLite connection contextmanager + init_db()
│   └── routers/
│       └── health.py      # GET /health
├── requirements.txt
└── venv/                  # local only, gitignored

frontend/
├── src/
│   ├── main.tsx           # React entry point
│   ├── App.tsx            # Root component, fetches health on mount
│   ├── App.css
│   └── api/client.ts      # Typed fetch wrapper
├── vite.config.ts         # Dev server + /api proxy
└── package.json
```

## How the two halves connect

The frontend never calls `http://localhost:8000` directly. `src/api/client.ts` sets `BASE_URL = '/api'` and Vite's dev server proxies that prefix to the backend, stripping it on the way through:

```ts
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```

So a browser request to `/api/health` arrives at the backend as `/health`. This matters when adding routes: the backend router paths must **not** include an `/api` prefix, because the proxy removes it.

The proxy only exists in development. In production the backend has to serve the built `dist/` folder, or a reverse proxy has to route `/api` — neither is set up yet.

### CORS is configured but unused in practice

`main.py` allows origins `http://localhost:5173` and `http://localhost:3000`. Because the proxy makes requests same-origin from the browser's perspective, CORS is not exercised during normal dev. It becomes relevant only if the frontend is pointed straight at port 8000.

## Backend details

`init_db()` runs once at startup via FastAPI's `lifespan` context manager. It creates `data/` if missing and opens a connection — it does **not** create any tables, so adding a schema means extending that function.

`get_db_connection()` is a `@contextmanager` yielding a `sqlite3.Connection` with `row_factory = sqlite3.Row`, so rows support mapping access. It closes the connection on exit but does **not** commit; any write will need an explicit `conn.commit()`.

Each call opens a fresh connection. There is no pooling and no FastAPI dependency-injection wiring, so routes use the context manager directly.

`GET /health` runs `SELECT 1` and returns `{"status": "ok", "db": "connected"}`. On failure it raises a 503 whose `detail` carries the error string.

## Frontend details

`App.tsx` holds three pieces of state — `health`, `loading`, `error` — and calls `fetchHealth()` on mount, with a Retry button that re-runs it. There is no router, no state management library, and no component library; styling is plain CSS in `App.css`.

Note the error handling split in `client.ts`: a non-OK HTTP response is **not** thrown. It is converted into a `HealthResponse` with `status: 'error'` and merged with the response body. Only a network-level failure rejects the promise and reaches the `.catch()` in `App.tsx`. That is why the UI distinguishes "API reported unhealthy" from "could not reach API at all".

`npm run build` runs `tsc` before `vite build`, so a type error fails the build.

## Adding a feature

The health check is the template. To add an endpoint end to end:

1. Create a router in `backend/app/routers/`, using path `/thing` (no `/api` prefix).
2. Register it in `main.py` with `app.include_router(...)`.
3. If it needs tables, extend `init_db()` in `database.py`.
4. Add a typed function and response interface to `frontend/src/api/client.ts`, calling `${BASE_URL}/thing`.
5. Consume it from a component.

Both dev servers hot-reload — `uvicorn --reload` for Python, Vite HMR for the frontend — so no restart is needed for either side.
