"""
backend/main.py - FastAPI application entrypoint with lifespan startup, CORS, and API routing.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import database
from backend.config import (
    CORS_ORIGINS,
    DATABASE_PATH,
    SLM_MODEL_PATH,
    SESSION_IDLE_TIMEOUT_HOURS,
)
from backend.session_manager import session_manager
from backend.routers import auth, profile, domains, interviews, analytics, settings

logger = logging.getLogger("interview_backend")
logging.basicConfig(level=logging.INFO)


async def _periodic_idle_cleanup(interval_seconds: int = 1800):
    """Background task to evict idle interview sessions every 30 minutes."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            evicted = await session_manager.cleanup_idle_sessions(timeout_hours=SESSION_IDLE_TIMEOUT_HOURS)
            if evicted > 0:
                logger.info(f"Idle session cleanup: evicted {evicted} stale sessions from memory.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in idle session cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    target_db = getattr(app.state, "db_path", DATABASE_PATH)
    logger.info(f"Initializing database at: {target_db}")
    database.init_db(target_db)

    # 1. Model runtime: Load llama_cpp model once at startup behind a lock in threadpool
    app.state.shared_slm = None
    app.state.slm_load_error = None
    app.state.model_mode = "groq_fallback"

    skip_slm = os.getenv("TESTING") == "1" or getattr(app.state, "skip_slm_load", False)

    if not skip_slm:
        try:
            from interview import LLAMA_AVAILABLE, Llama
            if LLAMA_AVAILABLE and os.path.exists(SLM_MODEL_PATH):
                logger.info(f"Loading SLM model once at startup from: {SLM_MODEL_PATH}...")
                loop = asyncio.get_running_loop()

                def load_model():
                    return Llama(
                        model_path=SLM_MODEL_PATH,
                        n_gpu_layers=-1,
                        n_ctx=2048,
                        chat_format="chatml",
                        verbose=False
                    )

                start_m_load = asyncio.get_running_loop().time()
                app.state.shared_slm = await loop.run_in_executor(None, load_model)
                app.state.model_load_seconds = asyncio.get_running_loop().time() - start_m_load
                app.state.model_mode = "slm_hybrid"
                logger.info(f"✅ SLM model successfully loaded into memory in {app.state.model_load_seconds:.2f}s.")
            else:
                logger.info("SLM model not found or llama_cpp unavailable. Operating in Groq-only fallback mode.")
        except Exception as e:
            logger.warning(f"Could not load SLM model at startup: {e}. Falling back to Groq.")
            app.state.slm_load_error = str(e)
    else:
        logger.info("Testing mode: skipping SLM model loading.")

    # 2. Start background idle session eviction task
    cleanup_task = asyncio.create_task(_periodic_idle_cleanup())

    yield

    # --- SHUTDOWN ---
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Backend application shutdown complete.")


app = FastAPI(
    title="Interview Framework Backend API",
    version="1.0.0",
    description="FastAPI Backend for Adaptive Technical Interviews",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routers under /api
app.include_router(auth.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(domains.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/api/health")
async def health_check(request: Request):
    """System health check and diagnostic endpoint."""
    target_db = getattr(request.app.state, "db_path", DATABASE_PATH)
    db_ok = False
    try:
        summary = database.get_cohort_summary_stats(db_path=target_db)
        db_ok = True
    except Exception:
        db_ok = False

    from backend.config import GROQ_API_KEY
    groq_configured = bool(GROQ_API_KEY and str(GROQ_API_KEY).strip())
    model_loaded = getattr(request.app.state, "shared_slm", None) is not None
    model_mode = getattr(request.app.state, "model_mode", "groq_fallback")

    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "db_ok": db_ok,
        "model_mode": model_mode,
        "model_loaded": model_loaded,
        "model_load_seconds": round(getattr(request.app.state, "model_load_seconds", 0.0), 2),
        "groq_configured": groq_configured,
        "version": "1.0.0",
        "active_sessions_in_memory": len(session_manager._sessions)
    }
