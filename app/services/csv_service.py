"""
CSV parsing and validation service.

Handles reading uploaded CSV files, validating their structure,
and extracting certificate data rows.
"""

import csv
import io
import logging
from datetime import date, datetime

from app.exceptions import CSVValidationError
from app.schemas.certificate import CertificateCreateDTO

logger = logging.getLogger(__name__)

# Required columns that must be present in the CSV header
REQUIRED_COLUMNS = {
    "recipient_name",
    "certificate_title",
    "issue_date",
    "organization_name",
}

# Optional columns that are recognized but not required
OPTIONAL_COLUMNS = {
    "recipient_email",
}


class CSVService:
    """Service for parsing and validating CSV certificate data."""

    @staticmethod
    def parse_and_validate(
        file_content: bytes,
    ) -> tuple[list[CertificateCreateDTO], list[str]]:
        """
        Parse a CSV file and validate its contents.

        Args:
            file_content: Raw bytes of the uploaded CSV file.

        Returns:
            A tuple of (valid_records, errors) where:
              - valid_records is a list of CertificateCreateDTO objects
              - errors is a list of human-readable error messages

        Raises:
            CSVValidationError: If the CSV has no valid header or is empty.
        """
        try:
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            raise CSVValidationError(
                "Unable to read the CSV file. Ensure it is UTF-8 encoded."
            )

        reader = csv.DictReader(io.StringIO(text))

        # Validate header
        if reader.fieldnames is None:
            raise CSVValidationError("CSV file is empty or has no header row.")

        headers = {h.strip().lower() for h in reader.fieldnames}
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise CSVValidationError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}",
                errors=[f"Missing column: {col}" for col in sorted(missing)],
            )

        valid_records: list[CertificateCreateDTO] = []
        errors: list[str] = []

        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            row_errors = CSVService._validate_row(row, row_num)
            if row_errors:
                errors.extend(row_errors)
                continue

            try:
                dto = CSVService._row_to_dto(row)
                valid_records.append(dto)
            except Exception as e:
                errors.append(f"Row {row_num}: Unexpected error — {str(e)}")

        if not valid_records and not errors:
            raise CSVValidationError("CSV file contains no data rows.")

        logger.info(
            "CSV parsed: %d valid records, %d errors",
            len(valid_records),
            len(errors),
        )
        return valid_records, errors

    @staticmethod
    def _validate_row(row: dict, row_num: int) -> list[str]:
        """
        Validate a single CSV row.

        Returns a list of error messages (empty if valid).
        """
        errors: list[str] = []
        # Normalize keys
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}

        # Check required fields are non-empty
        for field in REQUIRED_COLUMNS:
            value = normalized.get(field, "").strip()
            if not value:
                errors.append(f"Row {row_num}: '{field}' is required but empty.")

        # Validate date format
        issue_date = normalized.get("issue_date", "").strip()
        if issue_date:
            if not CSVService._parse_date(issue_date):
                errors.append(
                    f"Row {row_num}: 'issue_date' must be in YYYY-MM-DD format, "
                    f"got '{issue_date}'."
                )

        return errors

    @staticmethod
    def _row_to_dto(row: dict) -> CertificateCreateDTO:
        """Convert a validated CSV row dict into a CertificateCreateDTO."""
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}

        return CertificateCreateDTO(
            recipient_name=normalized["recipient_name"],
            recipient_email=normalized.get("recipient_email") or None,
            certificate_title=normalized["certificate_title"],
            issue_date=CSVService._parse_date(normalized["issue_date"]),
            organization_name=normalized["organization_name"],
        )

    @staticmethod
    def _parse_date(date_str: str) -> date | None:
        """
        Attempt to parse a date string in multiple common formats.

        Returns a date object on success, None on failure.
        """
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
