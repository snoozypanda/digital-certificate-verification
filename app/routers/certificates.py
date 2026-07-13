"""
Certificate API routes.

Handles HTTP request/response for certificate operations.
Business logic is delegated to CertificateService.
"""

import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.certificate import (
    CertificateResponse,
    CertificateVerifyResponse,
    UploadSummaryResponse,
)
from app.services.certificate_service import CertificateService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Certificates"])


@router.post(
    "/certificates/upload",
    response_model=UploadSummaryResponse,
    summary="Upload CSV and generate certificates",
    description=(
        "Upload a CSV file containing certificate recipients. "
        "The system will validate the data, create certificate records, "
        "generate QR codes, and produce PDF certificates."
    ),
)
async def upload_certificates(
    file: UploadFile = File(
        ...,
        description="CSV file with columns: recipient_name, certificate_title, "
        "issue_date, organization_name. Optional: recipient_email.",
    ),
    db: Session = Depends(get_db),
) -> UploadSummaryResponse:
    """Process a CSV upload and generate certificates."""
    logger.info("Received CSV upload: %s", file.filename)
    return await CertificateService.process_csv_upload(db, file)


@router.get(
    "/verify/{certificate_id}",
    response_model=CertificateVerifyResponse,
    summary="Verify a certificate",
    description=(
        "Public endpoint to verify the authenticity of a certificate. "
        "Returns certificate details if valid, or an error if not found "
        "or revoked."
    ),
)
def verify_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> CertificateVerifyResponse:
    """Verify a certificate by its unique ID."""
    logger.info("Verification request for: %s", certificate_id)
    return CertificateService.verify_certificate(db, certificate_id)


@router.get(
    "/certificates",
    response_model=list[CertificateResponse],
    summary="List all certificates",
    description="Retrieve a paginated list of all certificates.",
)
def list_certificates(
    skip: int = Query(0, ge=0, description="Number of records to skip."),
    limit: int = Query(100, ge=1, le=500, description="Max records to return."),
    db: Session = Depends(get_db),
) -> list[CertificateResponse]:
    """Return all certificates with optional pagination."""
    return CertificateService.get_all_certificates(db, skip=skip, limit=limit)


@router.get(
    "/certificates/{certificate_id}",
    response_model=CertificateResponse,
    summary="Get a specific certificate",
    description="Retrieve a single certificate by its unique ID.",
)
def get_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> CertificateResponse:
    """Return a single certificate by ID."""
    return CertificateService.get_certificate(db, certificate_id)


@router.delete(
    "/certificates/{certificate_id}",
    response_model=CertificateResponse,
    summary="Revoke a certificate",
    description=(
        "Soft-delete a certificate by changing its status to REVOKED. "
        "The certificate record is preserved for audit purposes."
    ),
)
def revoke_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> CertificateResponse:
    """Revoke (soft-delete) a certificate."""
    logger.info("Revocation request for: %s", certificate_id)
    return CertificateService.revoke_certificate(db, certificate_id)
