"""
FastAPI application factory and configuration.

Sets up the application with:
- API metadata for OpenAPI docs
- CORS middleware
- Static file serving
- Global exception handlers
- Startup event for directory creation
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exceptions import (
    CertificateNotFoundError,
    CertificateRevokedError,
    CSVValidationError,
    FileProcessingError,
)
from app.routers.certificates import router as certificates_router
from app.utils.helpers import ensure_directories

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    - On startup: create required directories.
    - On shutdown: cleanup resources (if needed in the future).
    """
    logger.info("Starting up %s...", get_settings().app_name)
    ensure_directories()
    logger.info("All directories verified.")
    yield
    logger.info("Shutting down...")


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A digital certificate verification system that generates "
        "QR-coded PDF certificates from CSV uploads and provides "
        "public verification endpoints."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Static Files
# ---------------------------------------------------------------------------

# Ensure static directory exists before mounting (Starlette validates at mount time)
import os
os.makedirs(settings.static_dir, exist_ok=True)

# Mount static directory for serving generated PDFs and QR codes
app.mount(
    "/static",
    StaticFiles(directory=settings.static_dir),
    name="static",
)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------


@app.exception_handler(CertificateNotFoundError)
async def certificate_not_found_handler(
    request: Request,
    exc: CertificateNotFoundError,
) -> JSONResponse:
    """Handle certificate not found errors → 404."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": exc.message,
            "certificate_id": exc.certificate_id,
        },
    )


@app.exception_handler(CertificateRevokedError)
async def certificate_revoked_handler(
    request: Request,
    exc: CertificateRevokedError,
) -> JSONResponse:
    """Handle revoked certificate errors → 410 Gone."""
    return JSONResponse(
        status_code=410,
        content={
            "detail": exc.message,
            "certificate_id": exc.certificate_id,
            "status": "REVOKED",
        },
    )


@app.exception_handler(CSVValidationError)
async def csv_validation_handler(
    request: Request,
    exc: CSVValidationError,
) -> JSONResponse:
    """Handle CSV validation errors → 422."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.message,
            "errors": exc.errors,
        },
    )


@app.exception_handler(FileProcessingError)
async def file_processing_handler(
    request: Request,
    exc: FileProcessingError,
) -> JSONResponse:
    """Handle file processing errors → 500."""
    logger.error("File processing error: %s", exc.message, exc_info=exc.original_error)
    return JSONResponse(
        status_code=500,
        content={
            "detail": exc.message,
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(certificates_router)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
