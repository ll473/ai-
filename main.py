"""Local development entrypoint for the AI commerce backend."""

import uvicorn

from backend.scripts.migrate import migrate

if __name__ == "__main__":
    # Keep a locally started project in sync with the checked-in database schema.
    # Alembic migrations are idempotent, so this is safe on subsequent starts.
    migrate()
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
