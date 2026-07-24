"""
Pydantic schemas for certificate API request/response validation.

These schemas define the shape of data flowing through the API,
separate from the database models.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CertificateStatus(str, Enum):
    """Certificate status enum for API responses."""
    VALID = "VALID"
    REVOKED = "REVOKED"


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class CertificateResponse(BaseModel):
    """Full certificate response returned by list/detail endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    certificate_id: str
    recipient_name: str
    recipient_name_amharic: str | None = None
    recipient_email: str | None = None
    certificate_title: str
    issue_date: date
    organization_name: str
    status: CertificateStatus
    qr_code_path: str | None = None
    pdf_path: str | None = None
    created_at: datetime


class CertificateVerifyResponse(BaseModel):
    """
    Public-facing verification response.

    Contains only the information needed to confirm a certificate
    is valid. Excludes internal fields like id and file paths.
    """

    model_config = ConfigDict(from_attributes=True)

    certificate_id: str
    recipient_name: str
    recipient_name_amharic: str | None = None
    certificate_title: str
    issue_date: date
    organization_name: str
    status: CertificateStatus
    is_valid: bool = Field(
        description="True if the certificate status is VALID."
    )


class UploadSummaryResponse(BaseModel):
    """Summary returned after processing a CSV upload."""

    total_processed: int = Field(
        description="Total number of rows in the CSV."
    )
    successful: int = Field(
        description="Number of certificates successfully created."
    )
    failed: int = Field(
        description="Number of rows that failed processing."
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages for failed rows.",
    )


# ---------------------------------------------------------------------------
# Internal Data Transfer Objects
# ---------------------------------------------------------------------------


class CertificateCreateDTO(BaseModel):
    """
    Internal DTO used to pass validated CSV row data between services.

    Not exposed in the API — used by csv_service to hand data to
    certificate_service.
    """

    recipient_name: str
    recipient_name_amharic: str | None = None
    recipient_email: str | None = None
    certificate_title: str
    issue_date: date
    organization_name: str
