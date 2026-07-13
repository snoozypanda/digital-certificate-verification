"""
Certificate repository — data access layer.

Encapsulates all database queries for the Certificate model.
Business logic should NOT live here; this layer only handles CRUD.
"""

import logging
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus

logger = logging.getLogger(__name__)


class CertificateRepository:
    """Thin data-access layer for Certificate records."""

    @staticmethod
    def create(db: Session, certificate: Certificate) -> Certificate:
        """Insert a single certificate record."""
        db.add(certificate)
        db.commit()
        db.refresh(certificate)
        logger.info("Created certificate: %s", certificate.certificate_id)
        return certificate

    @staticmethod
    def get_by_certificate_id(db: Session, certificate_id: str) -> Certificate | None:
        """Find a certificate by its public-facing unique ID."""
        return (
            db.query(Certificate)
            .filter(Certificate.certificate_id == certificate_id)
            .first()
        )

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Certificate]:
        """Return a paginated list of all certificates."""
        return (
            db.query(Certificate)
            .order_by(Certificate.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_status(
        db: Session,
        certificate_id: str,
        status: CertificateStatus,
    ) -> Certificate | None:
        """Update the status of a certificate (e.g., VALID → REVOKED)."""
        certificate = CertificateRepository.get_by_certificate_id(db, certificate_id)
        if certificate is None:
            return None
        certificate.status = status
        db.commit()
        db.refresh(certificate)
        logger.info(
            "Updated certificate %s status to %s",
            certificate_id,
            status.value,
        )
        return certificate

    @staticmethod
    def update_paths(
        db: Session,
        certificate_id: str,
        qr_code_path: str,
        pdf_path: str,
    ) -> Certificate | None:
        """Update the generated file paths for a certificate."""
        certificate = CertificateRepository.get_by_certificate_id(db, certificate_id)
        if certificate is None:
            return None
        certificate.qr_code_path = qr_code_path
        certificate.pdf_path = pdf_path
        db.commit()
        db.refresh(certificate)
        return certificate
