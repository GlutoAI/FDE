# Repo Map

Observed facts about this scaffold, recorded by reading and running it — not inferred. Update when something is verified, and mark anything still assumed.

Method pages live in `wiki/`; this file is only what is true of *this* repository.

## Stack

| Layer | What is actually here |
|---|---|
| Backend | FastAPI + `uvicorn[standard]`. **Two lines in `requirements.txt` — that is the whole dependency list.** |
| Database | SQLite via the stdlib `sqlite3` module. No ORM, no migration tool. |
| Frontend | React 18, Vite 5, TypeScript 5. No router, no state library, no component library. |
| Tests | **None.** No `pytest`, no test runner on either side, no test directory. |
| AI | **None.** No `anthropic` SDK, no HTTP client (`httpx`/`requests`) installed. |

Anything beyond the health check needs dependencies added first. See [`wiki/reference/troubleshooting.md`](../wiki/reference/troubleshooting.md) — npm installs have failed on this machine for two distinct causes already.

## Commands

```bash
# Backend — MUST be run from backend/ (see trap below)
cd backend
python3 -m venv venv && source venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev                             # http://localhost:5173
npm run build                           # tsc && vite build — a type error fails the build
```

There is no `npm test` and no `pytest` target. Adding one is a setup step, not a given.

## Entry points

| Path | Role |
|---|---|
| `backend/app/main.py` | FastAPI app, CORS, `lifespan` calling `init_db()`, router registration |
| `backend/app/database.py` | `get_db_connection()` contextmanager + `init_db()` |
| `backend/app/routers/health.py` | The only route: `GET /health` |
| `frontend/src/App.tsx` | Root component; fetches health on mount |
| `frontend/src/api/client.ts` | Typed fetch wrapper, `BASE_URL = '/api'` |
| `frontend/vite.config.ts` | Dev server and the `/api` proxy |

## Verified traps

**`DB_PATH = "./data/app.db"` is relative to the working directory.** Starting uvicorn from the repo root instead of `backend/` silently creates a *second*, empty database at `./data/app.db`. Symptom: tables that "disappear". Always start from `backend/`.

**`get_db_connection()` does not commit.** It closes the connection on exit and nothing else. Every write needs an explicit `conn.commit()` or it is silently discarded.

**`init_db()` creates no tables.** It runs `os.makedirs` and `SELECT 1`. New schema goes there, or into a real migration step.

**The `/api` prefix is stripped by the Vite proxy.** Browser calls `/api/health`; the backend sees `/health`. Backend route paths must **not** include `/api`.

**Each request opens a fresh connection.** No pooling, no FastAPI dependency wiring — routes use the contextmanager directly.

**`npm run build` runs `tsc` first**, so a type error fails the build even when the dev server was happy.

## Not yet verified

- Whether the interview environment is this scaffold or a larger app built on it.
- Whether a scheduler, queue, or job runner exists anywhere (none in this scaffold).
- Whether `pip install` succeeds on this machine — the recorded failures are npm-side only.

Replace each line above with an observation as soon as one exists.
