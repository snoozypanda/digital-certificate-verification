"""
Certificate service — core business logic orchestrator.

Coordinates the full certificate lifecycle:
CSV upload → DB insert → QR generation → PDF generation → path update.
"""

import logging
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.exceptions import (
    CertificateNotFoundError,
    CertificateRevokedError,
    CSVValidationError,
)
from app.models.certificate import Certificate, CertificateStatus
from app.repositories.certificate_repo import CertificateRepository
from app.schemas.certificate import (
    CertificateCreateDTO,
    CertificateVerifyResponse,
    UploadSummaryResponse,
)
from app.services.csv_service import CSVService
from app.services.qr_service import QRService
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Orchestrates certificate operations.

    This service layer sits between the API routes and the
    repository/utility services. All business logic lives here.
    """

    @staticmethod
    def _generate_certificate_id() -> str:
        """Generate a unique, URL-safe certificate ID."""
        return f"IED-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    async def process_csv_upload(
        db: Session,
        file: UploadFile,
    ) -> UploadSummaryResponse:
        """
        Process a CSV file upload end-to-end.

        Steps:
        1. Validate the file type.
        2. Parse and validate CSV contents.
        3. For each valid record: create DB entry → generate QR → generate PDF → update paths.
        4. Return an upload summary.

        Args:
            db: Database session.
            file: The uploaded CSV file.

        Returns:
            UploadSummaryResponse with counts and error details.
        """
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise CSVValidationError(
                "Invalid file type. Please upload a CSV file."
            )

        # Read file content
        content = await file.read()
        if not content:
            raise CSVValidationError("The uploaded file is empty.")

        # Parse and validate CSV
        valid_records, errors = CSVService.parse_and_validate(content)

        total = len(valid_records) + len(errors)
        successful = 0

        # Process each valid record
        for dto in valid_records:
            try:
                CertificateService._process_single_certificate(db, dto)
                successful += 1
            except Exception as e:
                error_msg = (
                    f"Failed to process certificate for "
                    f"'{dto.recipient_name}': {str(e)}"
                )
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

        logger.info(
            "CSV upload complete: %d total, %d successful, %d failed",
            total,
            successful,
            len(errors),
        )

        return UploadSummaryResponse(
            total_processed=total,
            successful=successful,
            failed=total - successful,
            errors=errors,
        )

    @staticmethod
    def _process_single_certificate(
        db: Session,
        dto: CertificateCreateDTO,
    ) -> Certificate:
        """
        Process a single certificate record through the full pipeline.

        1. Generate unique certificate ID.
        2. Create database record.
        3. Generate QR code.
        4. Generate PDF.
        5. Update DB with file paths.

        Args:
            db: Database session.
            dto: Validated certificate data.

        Returns:
            The created Certificate model instance.
        """
        cert_id = CertificateService._generate_certificate_id()

        # Create the certificate record in the database
        certificate = Certificate(
            certificate_id=cert_id,
            recipient_name=dto.recipient_name,
            recipient_name_amharic=dto.recipient_name_amharic,
            recipient_email=dto.recipient_email,
            certificate_title=dto.certificate_title,
            issue_date=dto.issue_date,
            organization_name=dto.organization_name,
            status=CertificateStatus.VALID,
        )
        certificate = CertificateRepository.create(db, certificate)

        # Generate QR code
        qr_path = QRService.generate_qr_code(cert_id)

        # Generate PDF certificate
        pdf_path = PDFService.generate_pdf(
            certificate_id=cert_id,
            recipient_name=dto.recipient_name,
            recipient_name_amharic=dto.recipient_name_amharic,
            certificate_title=dto.certificate_title,
            issue_date=dto.issue_date,
            organization_name=dto.organization_name,
            qr_code_path=qr_path,
        )

        # Update the certificate record with file paths
        CertificateRepository.update_paths(db, cert_id, qr_path, pdf_path)

        logger.info(
            "Certificate processed successfully: %s for %s",
            cert_id,
            dto.recipient_name,
        )
        return certificate

    @staticmethod
    def verify_certificate(
        db: Session,
        certificate_id: str,
    ) -> CertificateVerifyResponse:
        """
        Verify a certificate by its ID.

        Returns certificate info if valid, raises if not found or revoked.

        Args:
            db: Database session.
            certificate_id: The public certificate identifier.

        Returns:
            CertificateVerifyResponse with certificate details.

        Raises:
            CertificateNotFoundError: If no certificate exists with this ID.
            CertificateRevokedError: If the certificate has been revoked.
        """
        certificate = CertificateRepository.get_by_certificate_id(
            db, certificate_id
        )

        if certificate is None:
            raise CertificateNotFoundError(certificate_id)

        if certificate.status == CertificateStatus.REVOKED:
            raise CertificateRevokedError(certificate_id)

        return CertificateVerifyResponse(
            certificate_id=certificate.certificate_id,
            recipient_name=certificate.recipient_name,
            recipient_name_amharic=certificate.recipient_name_amharic,
            certificate_title=certificate.certificate_title,
            issue_date=certificate.issue_date,
            organization_name=certificate.organization_name,
            status=certificate.status,
            is_valid=True,
        )

    @staticmethod
    def get_all_certificates(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Certificate]:
        """Return a paginated list of all certificates."""
        return CertificateRepository.get_all(db, skip=skip, limit=limit)

    @staticmethod
    def get_certificate(
        db: Session,
        certificate_id: str,
    ) -> Certificate:
        """
        Get a single certificate by ID.

        Raises:
            CertificateNotFoundError: If the certificate does not exist.
        """
        certificate = CertificateRepository.get_by_certificate_id(
            db, certificate_id
        )
        if certificate is None:
            raise CertificateNotFoundError(certificate_id)
        return certificate

    @staticmethod
    def revoke_certificate(
        db: Session,
        certificate_id: str,
    ) -> Certificate:
        """
        Revoke a certificate (soft delete).

        Sets the certificate status to REVOKED.

        Raises:
            CertificateNotFoundError: If the certificate does not exist.
        """
        certificate = CertificateRepository.update_status(
            db, certificate_id, CertificateStatus.REVOKED
        )
        if certificate is None:
            raise CertificateNotFoundError(certificate_id)

        logger.info("Certificate revoked: %s", certificate_id)
        return certificate
