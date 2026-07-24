"""
CSV parsing and validation service.

Handles reading uploaded CSV files, validating their structure,
and extracting certificate data rows.

Supports CSV files exported from Excel, Google Sheets, LibreOffice,
and macOS Numbers by handling UTF-8 BOM and normalizing headers.
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
    "recipient_name_amharic",
    "amharic_name",
}

# All known columns (for warning about unexpected ones)
ALL_KNOWN_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


class CSVService:
    """Service for parsing and validating CSV certificate data."""

    @staticmethod
    def _normalize_header(name: str) -> str:
        """
        Normalize a single CSV column header.

        Removes UTF-8 BOM characters, strips whitespace, and lowercases.
        This handles headers from Excel (\ufeff prefix), Google Sheets,
        LibreOffice, and macOS Numbers.
        """
        # Remove BOM character (U+FEFF) that Excel prepends to UTF-8 files
        name = name.replace("\ufeff", "")
        # Remove zero-width characters that some editors insert
        name = name.replace("\u200b", "")  # zero-width space
        name = name.replace("\u200c", "")  # zero-width non-joiner
        name = name.replace("\ufffe", "")  # reversed BOM
        # Strip whitespace and lowercase
        return name.strip().lower()

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
        # Decode with utf-8-sig to automatically strip the UTF-8 BOM.
        # This is the key fix: 'utf-8' preserves the BOM as \ufeff in front
        # of the first column name, causing header validation to fail.
        try:
            text = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = file_content.decode("latin-1")
                logger.warning("CSV file was not UTF-8; fell back to Latin-1 decoding.")
            except UnicodeDecodeError:
                raise CSVValidationError(
                    "Unable to read the CSV file. Ensure it is UTF-8 encoded."
                )

        reader = csv.DictReader(io.StringIO(text))

        # Validate header
        if reader.fieldnames is None:
            raise CSVValidationError("CSV file is empty or has no header row.")

        # Normalize all headers: strip BOM remnants, whitespace, and lowercase
        raw_headers = list(reader.fieldnames)
        normalized_headers = [CSVService._normalize_header(h) for h in raw_headers]

        # Build a mapping from normalized name -> original name for diagnostics
        header_set = set(normalized_headers)

        # Check for required columns
        missing = REQUIRED_COLUMNS - header_set
        if missing:
            raise CSVValidationError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}. "
                f"Found columns: {normalized_headers}",
                errors=[
                    f"Missing column: {col}" for col in sorted(missing)
                ] + [
                    f"Columns found in file: {', '.join(normalized_headers)}"
                ],
            )

        # Warn about unexpected columns (non-fatal)
        unexpected = header_set - ALL_KNOWN_COLUMNS
        if unexpected:
            logger.warning(
                "CSV contains unrecognized columns (ignored): %s",
                ", ".join(sorted(unexpected)),
            )

        # Re-create the reader with normalized headers so that row dicts
        # use clean keys regardless of what the original file contained.
        text_io = io.StringIO(text)
        reader = csv.DictReader(text_io)
        # Override fieldnames with normalized versions.
        # When fieldnames is set manually, DictReader does NOT consume the
        # first line as a header — it treats it as data. We must skip it.
        reader.fieldnames = normalized_headers
        next(text_io)  # skip the original header line

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
        # Normalize values (keys are already normalized from the reader)
        normalized = {k: (v.strip() if v is not None else "") for k, v in row.items() if k}

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
        # Keys are already normalized from the reader
        normalized = {k: (v.strip() if v is not None else "") for k, v in row.items() if k}

        recipient_name_amharic = (
            normalized.get("recipient_name_amharic")
            or normalized.get("amharic_name")
            or None
        )

        return CertificateCreateDTO(
            recipient_name=normalized["recipient_name"],
            recipient_name_amharic=recipient_name_amharic,
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

