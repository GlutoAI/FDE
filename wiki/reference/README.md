# Reference

Facts about *this* project and machine, as opposed to transferable method. Verified, not assumed.

Transferable decisions live in [catalog/](../catalog/README.md). Method lives in the phase folders. Nothing in `reference/` is a catalog card.

| Page | Covers |
|---|---|
| [environment-setup.md](environment-setup.md) | Verified local setup and the exact Python and npm gotchas on this machine |
| [architecture.md](architecture.md) | How the scaffold fits together, the `/api` proxy, current surface area |
| [coding-standards.md](coding-standards.md) | Rationale and worked examples behind the enforced standards |
| [troubleshooting.md](troubleshooting.md) | Errors already hit, the real root cause, the fix |

## Scaffold baseline

Recorded here because it determines what has to be installed before anything can be built:

**Backend** — `fastapi`, `uvicorn[standard]`. That is all. No AI SDK, no `pytest`, no `httpx`, no `pydantic-settings`, no migration tool. `requirements.txt` has two lines.

**Frontend** — React 18, `react-dom`, Vite 5, TypeScript 5. No router, no state library, no component library, no test runner.

**Data** — SQLite at `backend/data/app.db`. `init_db()` creates no tables.

Anything beyond a health check requires adding dependencies first, and [troubleshooting.md](troubleshooting.md) records that npm installs have failed on this machine for two distinct reasons. Verify installs before you need them under time pressure.
