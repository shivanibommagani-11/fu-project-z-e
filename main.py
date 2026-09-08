"""
Fuze Real Estate Agentic Service - FastAPI Application Entry Point
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.chat import router as chat_router
from app.api.chat_stream import router as chat_stream_router
from app.config.settings import settings
from app.database.session import init_db, engine
from app.services.llm import initialize_llm
from app.core.conversations import ConversationManager
from app.core.checkpoints import CheckpointManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""

    # Startup
    logger.info("🚀 Starting Fuze Real Estate Agentic Service...")

    try:
        # Initialize database tables
        logger.info("Initializing database...")
        init_db()

        # Test database connection directly without inserting data
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM DUAL"))
        logger.info("✓ Database connection successful!")

        # Initialize LLM service
        logger.info("Initializing LLM service...")
        llm_service = await initialize_llm()
        logger.info(f"✓ LLM service ready: {llm_service.model}")

        logger.info("✓ Application startup complete!")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down Fuze Real Estate Agentic Service...")

    try:
        # Cleanup old sessions
        removed_sessions = ConversationManager.cleanup_old_sessions(max_age_hours=24)
        logger.info(f"Cleaned up {removed_sessions} old sessions")

        # Cleanup old checkpoints
        removed_checkpoints = CheckpointManager.cleanup_old_checkpoints(max_age_hours=24)
        logger.info(f"Cleaned up {removed_checkpoints} old checkpoints")

        logger.info("✓ Shutdown complete!")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Agentic AI service for Fuze Real Estate contract management",
    lifespan=lifespan,
    debug=settings.api_debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(chat_stream_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Fuze Real Estate Agentic Service",
        "version": settings.api_version,
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "upload": "/api/chat/upload",
            "health": "/api/health",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting uvicorn server on 0.0.0.0:{settings.api_port}")
    logger.info(f"API docs available at http://localhost:{settings.api_port}/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )