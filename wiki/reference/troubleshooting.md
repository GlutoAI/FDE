# Troubleshooting

Problems already hit on this project, with the actual root cause. Search this page by error text before debugging.

## `npm error Exit handler never called!`

A generic npm crash message that hides the real failure. Read the debug log path it prints and look for the actual errors:

```bash
tail -60 ~/.npm/_logs/<timestamp>-debug-0.log
```

Two distinct causes have produced this exact message here:

**Unreachable registry.** The log shows repeated `ENOTFOUND registry.npmjs.intuit.com`. The lockfile pins tarball URLs to Intuit's internal Artifactory, which only resolves on their network. See [environment-setup.md](environment-setup.md) for the rewrite that fixed it.

**Cursor's sandbox cache.** The log path points somewhere under `cursor-sandbox-cache`. Cursor sets `NPM_CONFIG_CACHE` and `npm_config_devdir` into a sandbox temp directory that npm cannot use properly:

```bash
unset NPM_CONFIG_CACHE npm_config_devdir
npm install
```

## `Operation not permitted` creating the venv

```
Error: [Errno 1] Operation not permitted: '.../backend/venv/include'
```

The project lives under `~/Downloads`, which macOS restricts, and Cursor's terminal sandbox further limits writes. Create the venv from a normal Terminal.app session, or grant the terminal full disk access.

## FastAPI will not install / syntax errors on install

The venv was built with the system Python 3.9.6 instead of 3.11+. Check with `python --version` after activating. Delete `backend/venv` and recreate it with `/opt/homebrew/bin/python3.13 -m venv venv`.

## Frontend loads but shows "Failed to reach API"

The backend is not running, or is not on port 8000. `vite.config.ts` proxies to `http://127.0.0.1:8000` — a hardcoded target, so a backend started on another port will not be found.

Isolate which half is broken:

```bash
curl http://localhost:8000/health        # backend itself
curl http://localhost:5173/api/health    # backend through the proxy
```

If the first works and the second does not, the proxy or the Vite server is the problem. If neither works, the backend is down.

Restart the Vite dev server after editing `vite.config.ts` — proxy configuration is not hot-reloaded.

## Health check returns 503

The response `detail` contains the underlying SQLite error. The usual cause is the server being started from the wrong directory: `DB_PATH` in `app/database.py` is the relative path `./data/app.db`, so `uvicorn` must run from `backend/`.

A corrupt database is safe to delete — it is recreated on the next startup:

```bash
rm backend/data/app.db
```

## Port already in use

```bash
lsof -i :8000    # backend
lsof -i :5173    # frontend
kill <pid>
```

An orphaned `uvicorn --reload` from a previous session is the common culprit, since the reloader spawns a child process that can outlive the parent.
