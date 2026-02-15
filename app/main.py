"""
Agentic Honey-Pot API
Main FastAPI application entry point.
Deployment Version: 2026.02.15.1630
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.routes import router
from app.services import get_session_manager

# Import benchmark sub-apps
try:
    from benchmark.server import app as arena_app
except ImportError:
    logger.warning("Could not import Benchmark Arena app")
    arena_app = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Honey-Pot API...")
    settings = get_settings()
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize session manager (lazy, but log status)
    session_manager = get_session_manager()
    logger.info("Session manager initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Honey-Pot API...")
    await session_manager.close()
    logger.info("Session manager closed")


# Create FastAPI app
app = FastAPI(
    title="Agentic Honey-Pot API",
    description="AI-powered scam detection and engagement system",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)

# Mount Benchmark Arena
if arena_app:
    app.mount("/arena", arena_app)
    logger.info("Benchmark Arena mounted at /arena")

# Mount Benchmark Results (Static)
from fastapi.staticfiles import StaticFiles
import os
results_path = os.path.join(os.getcwd(), "benchmark", "webui")
if os.path.exists(results_path):
    app.mount("/benchmark", StaticFiles(directory=results_path, html=True), name="benchmark_results")
    logger.info("Benchmark Results mounted at /benchmark")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Return HTTP 400 for malformed or missing required fields."""
    raw_body = ""
    try:
        raw_bytes = await request.body()
        raw_body = raw_bytes.decode("utf-8", errors="ignore") if raw_bytes else ""
    except Exception as e:
        logger.warning(f"Failed to read raw body for validation error: {e}")

    if raw_body:
        max_len = 2000
        if len(raw_body) > max_len:
            raw_body = f"{raw_body[:max_len]}...[truncated]"

    logger.warning(
        "Request validation error: method=%s path=%s content_type=%s content_length=%s body=%s errors=%s",
        request.method,
        request.url.path,
        request.headers.get("content-type"),
        request.headers.get("content-length"),
        raw_body,
        exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Invalid request body.",
            "errors": exc.errors(),
            "hint": "Check if your field names match (e.g., sessionId vs session_id)"
        },
    )


@app.get("/")
async def root():
    """Root endpoint — serves interactive GUI dashboard."""
    from fastapi.responses import HTMLResponse
    from app.core.gui import GUI_HTML
    return HTMLResponse(content=GUI_HTML)
