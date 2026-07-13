"""
Custom exception classes for the certificate verification system.

These exceptions are caught by global exception handlers in main.py
and converted to appropriate HTTP responses.
"""


class CertificateNotFoundError(Exception):
    """Raised when a certificate with the given ID does not exist."""

    def __init__(self, certificate_id: str):
        self.certificate_id = certificate_id
        self.message = f"Certificate with ID '{certificate_id}' not found."
        super().__init__(self.message)


class CertificateRevokedError(Exception):
    """Raised when attempting to verify a revoked certificate."""

    def __init__(self, certificate_id: str):
        self.certificate_id = certificate_id
        self.message = f"Certificate with ID '{certificate_id}' has been revoked."
        super().__init__(self.message)


class CSVValidationError(Exception):
    """Raised when the uploaded CSV file has structural issues."""

    def __init__(self, message: str, errors: list[str] | None = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


class FileProcessingError(Exception):
    """Raised when file processing (QR/PDF generation, file I/O) fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
