"""
Certificate SQLAlchemy model.

Represents a certificate record in the database, including metadata
about the recipient, organization, and paths to generated artifacts.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Integer,
    String,
    func,
)

from app.database import Base


class CertificateStatus(str, enum.Enum):
    """Possible states for a certificate."""
    VALID = "VALID"
    REVOKED = "REVOKED"


class Certificate(Base):
    """
    Certificate database model.

    Each row represents a single certificate issued to a recipient.
    Soft deletion is implemented via the `status` field (REVOKED).
    """

    __tablename__ = "certificates"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    certificate_id: str = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique public-facing certificate identifier (UUID-based)",
    )
    recipient_name: str = Column(String(255), nullable=False)
    recipient_name_amharic: str | None = Column(String(255), nullable=True)
    recipient_email: str | None = Column(String(255), nullable=True)
    certificate_title: str = Column(String(500), nullable=False)
    issue_date: date = Column(Date, nullable=False)
    organization_name: str = Column(String(255), nullable=False)
    status: CertificateStatus = Column(
        Enum(CertificateStatus),
        nullable=False,
        default=CertificateStatus.VALID,
        server_default=CertificateStatus.VALID.value,
    )
    qr_code_path: str | None = Column(String(500), nullable=True)
    pdf_path: str | None = Column(String(500), nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Certificate(id={self.id}, certificate_id='{self.certificate_id}', "
            f"recipient='{self.recipient_name}', status='{self.status}')>"
        )
