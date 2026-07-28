"""
QR code generation service.

Generates QR code PNG images that link to the certificate
verification URL.
"""

import logging
import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H

from app.config import get_settings
from app.exceptions import FileProcessingError

logger = logging.getLogger(__name__)


class QRService:
    """Service for generating QR code images."""

    @staticmethod
    def generate_qr_code(certificate_id: str) -> str:
        """
        Generate a QR code image for a certificate.

        The QR code encodes the verification URL:
            {BASE_URL}/verify/{certificate_id}

        Args:
            certificate_id: The unique certificate identifier.

        Returns:
            The file path to the saved QR code image.

        Raises:
            FileProcessingError: If QR code generation or saving fails.
        """
        settings = get_settings()
        verification_url = f"{settings.base_url}/verify.html?id={certificate_id}"
        output_dir = settings.qr_codes_dir
        output_path = os.path.join(output_dir, f"{certificate_id}.png")

        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Generate QR code with high error correction
            qr = qrcode.QRCode(
                version=1,
                error_correction=ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(verification_url)
            qr.make(fit=True)

            # Create image with a white background and dark modules
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(output_path)

            logger.info("QR code generated: %s", output_path)
            return output_path

        except Exception as e:
            logger.error(
                "Failed to generate QR code for %s: %s",
                certificate_id,
                str(e),
            )
            raise FileProcessingError(
                f"Failed to generate QR code for certificate '{certificate_id}'.",
                original_error=e,
            )
