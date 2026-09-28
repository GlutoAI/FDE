# Environment Setup

Verified working on macOS (darwin 25.3.0, Apple Silicon) on 2026-09-19.

## Quick start

Two terminals, one per service.

**Backend** (http://localhost:8000):

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173):

```bash
cd frontend
npm run dev
```

Confirm the stack is healthy:

```bash
curl http://localhost:8000/health        # direct
curl http://localhost:5173/api/health    # through the Vite proxy
```

Both return `{"status":"ok","db":"connected"}`.

## The virtual environment

The env is a plain Python `venv` named `venv`, at `backend/venv`. There is no conda environment for this project. The `(base)` that appears in the shell prompt is Anaconda's base environment and is unrelated — after activating, the prompt shows `(venv) (base)`, which is expected. `venv` takes precedence on `PATH`, so `which python` should resolve to `backend/venv/bin/python`.

### Python version — do not use bare `python3`

`python3` on this machine is `/usr/bin/python3`, which is **3.9.6**. The backend requires 3.11+, so creating the venv the way `backend/README.md` describes produces an env that cannot install FastAPI.

Use the Homebrew 3.13 interpreter explicitly:

```bash
cd backend
/opt/homebrew/bin/python3.13 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

The current venv runs Python 3.13.9.

### The venv is not portable

`backend/venv/pyvenv.cfg` hardcodes the Homebrew path `/opt/homebrew/opt/python@3.13`, and the absolute project path is baked into `venv/bin/activate`. If the project directory is moved or renamed, delete `backend/venv` and recreate it with the command above.

## npm and the Intuit registry

`npm install` in `frontend/` originally failed with:

```
npm error Exit handler never called!
```

That message is misleading. The real cause was in the npm debug log: every tarball fetch returned `ENOTFOUND` for `registry.npmjs.intuit.com`. `package-lock.json` had been generated inside Intuit's network, so all 115 `resolved` URLs pointed at their internal Artifactory:

```
https://registry.npmjs.intuit.com:443/artifactory/api/npm/npm-intuit/<pkg>/-/<pkg>-<version>.tgz
```

npm honors the lockfile's `resolved` URLs even when `npm config get registry` is the public registry, so the host override alone does not help.

**Fix applied:** those URLs were rewritten to `https://registry.npmjs.org/`. Versions and integrity hashes are untouched, so the installed dependency tree is identical. The original lockfile is preserved at `frontend/package-lock.json.intuit-bak` for use on the Intuit network.

If you are on the Intuit VPN and want the internal registry back:

```bash
cd frontend
cp package-lock.json.intuit-bak package-lock.json
```

### Cursor's terminal breaks npm

Cursor's sandboxed terminal sets `NPM_CONFIG_CACHE` and `npm_config_devdir` to a temporary sandbox directory, which produces the same opaque `Exit handler never called!` failure. When running npm from inside Cursor:

```bash
unset NPM_CONFIG_CACHE npm_config_devdir
npm install
```

This does not affect a normal Terminal.app session.

## Toolchain versions

| Tool | Version | Path |
|------|---------|------|
| Python (project) | 3.13.9 | `/opt/homebrew/bin/python3.13` |
| Python (system, too old) | 3.9.6 | `/usr/bin/python3` |
| Node | 25.6.1 | `/opt/homebrew/bin/node` |
| npm | 11.9.0 | `/opt/homebrew/bin/npm` |

Backend dependencies resolve to FastAPI 0.141.1, Starlette 1.6.0, Pydantic 2.13.5, and Uvicorn 0.53.0. `requirements.txt` uses floors (`>=`) rather than pins, so these versions will drift on a fresh install.

## Database

SQLite lives at `backend/data/app.db`, created automatically on first startup by `init_db()`. The path in `app/database.py` is **relative** (`./data/app.db`), so the server must be started from the `backend/` directory or the database will be created somewhere unexpected.

`backend/data/` is gitignored, so the database is never committed. Deleting the file is a safe reset.

## Repository state

Git is initialized locally on `main`, with `origin` configured as `https://github.com/GlutoAI/FDE.git` for fetch and push.

At connection time, the remote had no branches and the local files had not yet been committed or pushed. Use `git status` to check the current local state.
