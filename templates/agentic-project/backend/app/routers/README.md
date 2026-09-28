# `routers/` — HTTP endpoints

FastAPI routers that `main.py` includes. Each route declares its response model (a `Contract`), so the OpenAPI schema at `/docs` is exact. Routes carry **no `/api` prefix**: the Vite dev server and the Compose UI proxy `/api/*` to the backend and strip the prefix.

Rule for every route: **no HTTP route makes a paid model request.** Live model calls are only possible from the CLI with an explicit `--live`.

## Files

### `health.py` — `GET /health`

`check_health` checks the database with `is_database_reachable(engine)`, with the engine injected by `Depends(get_engine)` from `app/database.py`:

| Database | Status | Body |
|---|---|---|
| answers `SELECT 1` | 200 | `{"status": "ok", "db": "connected"}` |
| fails | 503 | `{"status": "error", "db": "disconnected", "detail": "database_unavailable"}` |

`HealthResponse.detail` is a safe code, never exception text. `response_model_exclude_none=True` leaves `detail` out of healthy responses.

### `diagnostics.py` — `POST /diagnostics/connection`

`run_connection_check` runs the connection agent once. It copies the app's settings with `model_mode="fixture"` **whatever the configuration says**, so the button in the UI can never spend money. It returns `AgentResult[ConnectionOutput]`: the validated output and its provenance. An `AppError` becomes a 502 whose `detail` is the error's safe code.

It reads `location` and `settings` from `request.app.state`, which the lifespan in `main.py` set at startup.

## How to use

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/diagnostics/connection
```

Through the frontend proxy, the same routes are at `/api/health` and `/api/diagnostics/connection`. `frontend/src/api/client.ts` calls them.

An HTTP 200 from `/diagnostics/connection` shows the fixture path works. It says nothing about a hosted model; for that, run `template-cli smoke --live`.

## How to add a route

1. Create `routers/<name>.py` with `router = APIRouter(prefix="/<name>")`.
2. Declare a `Contract` response model and pass it as `response_model`. Document error statuses in `responses=`.
3. Get shared resources from dependencies (`Depends(get_engine)`) or `request.app.state`; never open engines or model clients per request.
4. Catch `AppError` only at the route, and return `str(error)` as the detail, never the exception's cause.
5. Include the router in `create_app` in `main.py`, and add tests in `tests/test_api.py` with FastAPI's `TestClient` over `create_app(<temporary project>)`.

## Tests

`tests/test_api.py`: the health shape, the 503 with a safe code, the diagnostic staying on the fixture model even when live mode is configured, and CORS for the local frontend origin.
