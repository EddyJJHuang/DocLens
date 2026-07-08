from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager, suppress
import asyncio
import logging

from app.config import settings
from app.database.engine import DB_PATH
from app.database.seed import seed_database
from app.api.routes import api_router
from app.session_store import session_store

logger = logging.getLogger(__name__)


async def cleanup_sessions_periodically():
    while True:
        await asyncio.sleep(60)
        removed = session_store.cleanup_expired()
        if removed:
            logger.info("Cleaned up %s expired DocLens session cache(s).", removed)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Surface key configuration state prominently at startup (do not crash the
    # process — /health and the frontend should still come up; the API endpoints
    # fail fast with a 503 when a query/upload is attempted without a key).
    if settings.openai_configured:
        logger.info("OpenAI key detected — RAG upload/query paths enabled.")
    else:
        logger.warning(
            "OPENAI_API_KEY is not configured. The app will boot, but /api/upload "
            "and /api/query will return 503 until a key is set in .env."
        )

    # Ensure the synthetic demand-planning database exists (zero-setup demo).
    if not DB_PATH.exists():
        logger.info("Seeding synthetic demand-planning database...")
        seed_database()

    # Uploaded documents are session-scoped runtime cache, not product memory.
    # A restart should not resurrect previous users' files or indexes.
    session_store.clear_all()
    cleanup_task = asyncio.create_task(cleanup_sessions_periodically())
    yield
    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    session_store.clear_all()
    # Execution here handles elegant resource shutdown / destruction behaviors

app = FastAPI(title="DocLens API", version="1.0.0", lifespan=lifespan)

# Restrict Origin headers globally depending on environment contexts
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", settings.frontend_origin],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
