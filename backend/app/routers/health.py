from fastapi import APIRouter, HTTPException
from app.database import get_db_connection

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "db": "disconnected", "detail": str(e)},
        )
