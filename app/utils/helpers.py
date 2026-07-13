"""
Shared utility functions.

General-purpose helpers that don't belong to any specific service.
"""

import os
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def ensure_directories() -> None:
    """
    Create all required directories for the application.

    Called during application startup to ensure the filesystem
    is ready for file generation.
    """
    settings = get_settings()
    directories = [
        settings.static_dir,
        settings.certificates_dir,
        settings.qr_codes_dir,
        settings.upload_dir,
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info("Ensured directory exists: %s", directory)


def format_file_size(size_bytes: int) -> str:
    """Format a file size in bytes to a human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
