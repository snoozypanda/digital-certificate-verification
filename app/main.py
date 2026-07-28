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
    
    # Auto-create database tables on startup (useful for SQLite fallback)
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")
    
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


# HTTP CORS Origins contain scheme + domain (+ port) only.
# Browsers send Origin: https://frontend-nu-woad-19.vercel.app for all pages (/admin, /verify).
allowed_origins = [
    "https://frontend-nu-woad-19.vercel.app",
    "https://simpson-median-current-austin.trycloudflare.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://172.10.20.53:8000",
    "http://10.1.10.35:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
            "expected_columns": [
                "recipient_name",
                "certificate_title",
                "issue_date",
                "organization_name",
            ],
            "optional_columns": [
                "recipient_name_amharic",
                "recipient_email",
            ],
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


from fastapi.responses import HTMLResponse


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root():
    """Serve the verification page at the root path."""
    try:
        with open("frontend/verify.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Verification page not found</h1>", status_code=404)


@app.get("/verify.html", response_class=HTMLResponse, include_in_schema=False)
@app.get("/verify", response_class=HTMLResponse, include_in_schema=False)
def get_verify_page():
    """Serve the verification page."""
    try:
        with open("frontend/verify.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Verification page not found</h1>", status_code=404)


@app.get("/admin.html", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def get_admin_page():
    """Serve the admin page."""
    try:
        with open("frontend/admin.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin page not found</h1>", status_code=404)


@app.get("/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
