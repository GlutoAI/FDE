# Interview API — Backend

FastAPI backend with SQLite database.

## Prerequisites

- Python 3.11+

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 2. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Run the server

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

The server will be available at **http://localhost:8000**.

## Endpoints

### GET /health

Returns the application and database status.

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "db": "connected"}
```

## Database

SQLite database is stored at `data/app.db` relative to where the server runs (i.e., `backend/data/app.db`). The file and directory are created automatically on first run.
