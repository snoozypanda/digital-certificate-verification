"""
PDF certificate generation service.

Uses ReportLab to create bilingual (English / Amharic) PDF certificates
matching the official Ethiopian Capital Market Authority (ECMA) certificate
of participation format.
"""

import logging
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.exceptions import FileProcessingError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Amharic font registration
# ---------------------------------------------------------------------------
# ReportLab's built-in fonts (Times-Roman, Helvetica, etc.) cannot render
# Ethiopic script. We embed Noto Sans Ethiopic (SIL Open Font License) to
# support the Amharic text on the certificate.
#
# Expected location (relative to the static directory configured in
# app/config.py):
#   static/fonts/NotoSansEthiopic-Regular.ttf
#   static/fonts/NotoSansEthiopic-Bold.ttf
#
# If these files are missing, Amharic text will fail to render and a clear
# error is logged rather than silently producing blank/garbled output.

_AMHARIC_FONT_REGULAR = "NotoEthiopic"
_AMHARIC_FONT_BOLD = "NotoEthiopic-Bold"
_fonts_registered = False


def _register_amharic_fonts() -> bool:
    """Register the Amharic-capable fonts with ReportLab, once per process."""
    global _fonts_registered
    if _fonts_registered:
        return True

    settings = get_settings()
    font_dir = os.path.join(settings.static_dir, "fonts")
    regular_path = os.path.join(font_dir, "NotoSansEthiopic-Regular.ttf")
    bold_path = os.path.join(font_dir, "NotoSansEthiopic-Bold.ttf")

    if not (os.path.exists(regular_path) and os.path.exists(bold_path)):
        logger.error(
            "Amharic font files not found at %s. Bilingual certificate text "
            "requires NotoSansEthiopic-Regular.ttf and NotoSansEthiopic-Bold.ttf "
            "in that folder.",
            font_dir,
        )
        return False

    pdfmetrics.registerFont(TTFont(_AMHARIC_FONT_REGULAR, regular_path))
    pdfmetrics.registerFont(TTFont(_AMHARIC_FONT_BOLD, bold_path))
    _fonts_registered = True
    return True


class PDFService:
    """Service for generating bilingual PDF certificate documents."""

    # Page dimensions (A4 Landscape)
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

    # Color palette matching the new template
    GOLD_COLOR = colors.HexColor("#B8935A")     # Border hairlines
    ECMA_GREEN = colors.HexColor("#1B5E3A")     # Org name / brand green
    DARK_COLOR = colors.HexColor("#3a3a3a")     # Titles / body text
    LIGHT_TEXT = colors.HexColor("#6b6b6b")     # Muted footer text
    GRAY_LINE = colors.HexColor("#999999")      # Signature / signing line

    # Content column split for the bilingual body text
    CONTENT_LEFT = 30 * mm
    CONTENT_RIGHT_EDGE = PAGE_WIDTH - 30 * mm
    COLUMN_GAP = 10 * mm

    @staticmethod
    def generate_pdf(
        certificate_id: str,
        recipient_name: str,
        certificate_title: str,
        issue_date: date,
        organization_name: str,
        qr_code_path: str,
    ) -> str:
        """
        Generate a bilingual (English/Amharic) PDF certificate matching the
        ECMA certificate-of-participation template.

        Args:
            certificate_id: Unique certificate identifier.
            recipient_name: Full name of the recipient.
            certificate_title: Title/course name on the certificate.
            issue_date: Date the certificate was issued.
            organization_name: Issuing organization name.
            qr_code_path: Path to the QR code image to embed.

        Returns:
            The file path to the saved PDF.

        Raises:
            FileProcessingError: If PDF generation fails.
        """
        settings = get_settings()
        output_dir = settings.certificates_dir
        output_path = os.path.join(output_dir, f"{certificate_id}.pdf")

        if not _register_amharic_fonts():
            raise FileProcessingError(
                "Cannot generate certificate: Amharic font files are missing. "
                "Add NotoSansEthiopic-Regular.ttf and NotoSansEthiopic-Bold.ttf "
                "to static/fonts/."
            )

        try:
            os.makedirs(output_dir, exist_ok=True)

            c = canvas.Canvas(output_path, pagesize=landscape(A4))
            c.setTitle(f"Certificate - {recipient_name}")

            w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

            # 1. Plain white background
            c.setFillColor(colors.white)
            c.rect(0, 0, w, h, fill=True, stroke=False)

            # 2. Border
            PDFService._draw_border(c)

            # 3. QR code, top-right corner
            PDFService._draw_qr_code(c, qr_code_path)

            # 4. Centered logo + bilingual org name lockup
            PDFService._draw_header_lockup(c, settings)

            # 5. Bilingual title
            PDFService._draw_title(c)

            # 6. "To ____" / "ለ ____" recipient line
            PDFService._draw_recipient_line(c, recipient_name)

            # 7. Bilingual body paragraph + course title
            PDFService._draw_body(c, certificate_title, organization_name)

            # 8. Signature block (centered)
            PDFService._draw_signature(c, settings)

            # 9. Stamp / seal, bottom-right corner
            PDFService._draw_stamp(c, settings)

            # 10. Footer: issue date + certificate ID, bottom-left
            PDFService._draw_footer(c, issue_date, certificate_id)

            c.save()
            logger.info("PDF certificate generated: %s", output_path)
            return output_path

        except FileProcessingError:
            raise
        except Exception as e:
            logger.error(
                "Failed to generate PDF for %s: %s",
                certificate_id,
                str(e),
            )
            raise FileProcessingError(
                f"Failed to generate PDF for certificate '{certificate_id}'.",
                original_error=e,
            )

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_border(c: canvas.Canvas) -> None:
        """Simple double hairline border with a gold accent line, rounded corners."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        c.setStrokeColor(PDFService.GOLD_COLOR)
        c.setLineWidth(1.4)
        c.roundRect(9 * mm, 9 * mm, w - 18 * mm, h - 18 * mm, 4 * mm, fill=False)

        c.setStrokeColor(PDFService.GOLD_COLOR)
        c.setLineWidth(0.5)
        c.roundRect(12 * mm, 12 * mm, w - 24 * mm, h - 24 * mm, 3 * mm, fill=False)

    @staticmethod
    def _draw_qr_code(c: canvas.Canvas, qr_code_path: str) -> None:
        """QR code in the top-right corner, linking to the verification page."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        qr_size = 20 * mm
        qr_x = w - 20 * mm - qr_size
        qr_y = h - 20 * mm - qr_size

        if os.path.exists(qr_code_path):
            c.drawImage(
                qr_code_path,
                qr_x, qr_y,
                width=qr_size, height=qr_size,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            logger.warning("QR code not found at %s", qr_code_path)

    @staticmethod
    def _draw_header_lockup(c: canvas.Canvas, settings) -> None:
        """
        Centered header: ECMA icon on the left of a text block containing
        the Amharic org name (bold, green) above the English org name
        (bold, green), the whole unit centered as a group.
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        icon_path = os.path.join(
            settings.static_dir,
            "ECMA-Primary_Logo_Full-Colour-Gradient_RGB.png",
        )
        icon_size = 20 * mm
        text_block_width = 78 * mm
        gap = 4 * mm
        total_width = icon_size + gap + text_block_width
        start_x = (w - total_width) / 2
        top_y = h - 18 * mm

        if os.path.exists(icon_path):
            c.drawImage(
                icon_path,
                start_x, top_y - icon_size,
                width=icon_size, height=icon_size,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            logger.warning("ECMA icon not found at %s", icon_path)

        text_x = start_x + icon_size + gap

        c.setFont(_AMHARIC_FONT_BOLD, 11)
        c.setFillColor(PDFService.ECMA_GREEN)
        c.drawString(text_x, top_y - 6 * mm, "የኢትዮጵያ የካፒታል ገበያ")
        c.drawString(text_x, top_y - 11 * mm, "ባለስልጣን")

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(PDFService.ECMA_GREEN)
        c.drawString(text_x, top_y - 16.5 * mm, "ETHIOPIAN CAPITAL")
        c.drawString(text_x, top_y - 20.5 * mm, "MARKET AUTHORITY")

    @staticmethod
    def _draw_title(c: canvas.Canvas) -> None:
        """Bilingual title, centered: English above Amharic."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        c.setFont("Times-Bold", 24)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 52 * mm, "CERTIFICATE OF PARTICIPATION")

        c.setFont(_AMHARIC_FONT_BOLD, 16)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 60 * mm, "የተሳትፎ የምስክር ወረቀት")

    @staticmethod
    def _draw_recipient_line(c: canvas.Canvas, recipient_name: str) -> None:
        """Two-column 'To ____' (English) / 'ለ ____' (Amharic) recipient line."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        y = h - 74 * mm

        left_x = PDFService.CONTENT_LEFT
        right_x = w / 2 + PDFService.COLUMN_GAP

        # English: "To ______________"
        c.setFont("Times-Roman", 11)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, y, "To")
        label_w = c.stringWidth("To", "Times-Roman", 11)
        line_start = left_x + label_w + 3 * mm
        line_end = w / 2 - PDFService.COLUMN_GAP
        c.setStrokeColor(PDFService.GRAY_LINE)
        c.setLineWidth(0.6)
        c.line(line_start, y - 1 * mm, line_end, y - 1 * mm)
        c.setFont("Times-Bold", 12)
        c.drawCentredString((line_start + line_end) / 2, y + 2 * mm, recipient_name)

        # Amharic: "ለ ______________"
        c.setFont(_AMHARIC_FONT_REGULAR, 11)
        c.drawString(right_x, y, "ለ")
        a_label_w = c.stringWidth("ለ", _AMHARIC_FONT_REGULAR, 11)
        a_line_start = right_x + a_label_w + 3 * mm
        a_line_end = PDFService.CONTENT_RIGHT_EDGE
        c.line(a_line_start, y - 1 * mm, a_line_end, y - 1 * mm)
        c.setFont("Times-Bold", 12)
        c.drawCentredString((a_line_start + a_line_end) / 2, y + 2 * mm, recipient_name)

    @staticmethod
    def _draw_body(c: canvas.Canvas, certificate_title: str, organization_name: str) -> None:
        """
        Bilingual body paragraph in two columns, plus the program/course
        title centered below.

        NOTE: The Amharic column below is static boilerplate text (dynamic
        translation of certificate_title isn't available). Only the English
        column substitutes the actual program name. If certificates are
        issued for programs other than the standard investor-education
        course, the Amharic wording should be reviewed for accuracy.
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        left_x = PDFService.CONTENT_LEFT
        right_x = w / 2 + PDFService.COLUMN_GAP
        col_width_left = (w / 2 - PDFService.COLUMN_GAP) - left_x
        col_width_right = PDFService.CONTENT_RIGHT_EDGE - right_x

        english_lines = [
            f"has successfully completed the {certificate_title}",
            f"program organized by {organization_name}, designed",
            "to provide foundational knowledge through online",
            "education.",
        ]

        amharic_lines = [
            "የኢትዮጵያ የካፒታል ገበያ ባለስልጣን የካፒታል ገበያ መሰረታዊ",
            "እውቀት ማጎልበት ላይ ትኩረት አድርጎ በሰጠው የበይነ መረብ",
            "ስልጠና መርሃ-ግብር በተሳካ ሁኔታ ስለአጠናቀቀ/ች ይህ የተሳትፎ",
            "የምስክር ወረቀት ተሰጥቶታል/ቷታል።",
        ]

        c.setFont("Times-Roman", 10.5)
        c.setFillColor(PDFService.DARK_COLOR)
        y = h - 84 * mm
        for line in english_lines:
            c.drawString(left_x, y, line)
            y -= 5 * mm

        c.setFont(_AMHARIC_FONT_REGULAR, 10)
        y = h - 84 * mm
        for line in amharic_lines:
            c.drawString(right_x, y, line)
            y -= 5 * mm

    @staticmethod
    def _draw_signature(c: canvas.Canvas, settings) -> None:
        """
        Centered signature block. Uses a scanned signature image if present,
        otherwise falls back to a plain signing line.

        Expected signature image path: static/signatures/director_signature.png
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        sig_center_x = w / 2
        line_y = 38 * mm
        line_half_width = 32 * mm

        signature_path = os.path.join(
            settings.static_dir, "signatures", "director_signature.png"
        )

        if os.path.exists(signature_path):
            sig_w = 45 * mm
            sig_h = 16 * mm
            c.drawImage(
                signature_path,
                sig_center_x - sig_w / 2, line_y + 2 * mm,
                width=sig_w, height=sig_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            logger.info(
                "No signature image found at %s; drawing blank signing line.",
                signature_path,
            )

        c.setStrokeColor(PDFService.GRAY_LINE)
        c.setLineWidth(0.6)
        c.line(sig_center_x - line_half_width, line_y, sig_center_x + line_half_width, line_y)

        c.setFont("Times-Bold", 10)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(sig_center_x, line_y - 5 * mm, "Hana Tehelku")

        c.setFont("Times-Roman", 8.5)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawCentredString(
            sig_center_x, line_y - 9.5 * mm,
            "Director General, Ethiopian Capital Market Authority",
        )

    @staticmethod
    def _draw_stamp(c: canvas.Canvas, settings) -> None:
        """
        Official seal/stamp, bottom-right corner. Uses an image if present,
        otherwise draws a simple placeholder circle so the layout holds its
        shape until a real stamp asset is available.

        Expected stamp image path: static/stamp.png
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        stamp_size = 26 * mm
        stamp_x = w - 24 * mm - stamp_size
        stamp_y = 22 * mm

        stamp_path = os.path.join(settings.static_dir, "stamp.png")

        if os.path.exists(stamp_path):
            c.drawImage(
                stamp_path,
                stamp_x, stamp_y,
                width=stamp_size, height=stamp_size,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            # Placeholder seal: dashed circle with small label, so the
            # layout is easy to preview before the real stamp asset lands.
            cx = stamp_x + stamp_size / 2
            cy = stamp_y + stamp_size / 2
            radius = stamp_size / 2

            c.saveState()
            c.setStrokeColor(PDFService.GOLD_COLOR)
            c.setLineWidth(1)
            c.setDash(2, 2)
            c.circle(cx, cy, radius, fill=False)
            c.setDash([], 0)

            c.setFont("Helvetica", 6.5)
            c.setFillColor(PDFService.LIGHT_TEXT)
            c.drawCentredString(cx, cy + 2, "OFFICIAL")
            c.drawCentredString(cx, cy - 5, "SEAL")
            c.restoreState()

            logger.info(
                "No stamp image found at %s; drawing placeholder seal.",
                stamp_path,
            )

    @staticmethod
    def _draw_footer(
        c: canvas.Canvas,
        issue_date: date,
        certificate_id: str,
    ) -> None:
        """Footer: issue date and certificate ID, stacked bottom-left."""
        formatted_date = issue_date.strftime("%B %d, %Y")
        left_x = PDFService.CONTENT_LEFT

        c.setFont("Times-Roman", 8)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawString(left_x, 30 * mm, "Issued on:")
        c.setFont("Times-Bold", 9)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, 25.5 * mm, formatted_date)

        c.setFont("Times-Roman", 8)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawString(left_x, 19 * mm, "Certificate ID:")
        c.setFont("Times-Bold", 9)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, 14.5 * mm, certificate_id)














# """
# PDF certificate generation service.

# Uses ReportLab to create professional-looking PDF certificates matching
# the official Ethiopian Capital Market Authority (ECMA) certificate format.
# """

# import logging
# import os
# from datetime import date

# from reportlab.lib import colors
# from reportlab.lib.pagesizes import landscape, A4
# from reportlab.lib.units import mm
# from reportlab.pdfgen import canvas

# from app.config import get_settings
# from app.exceptions import FileProcessingError

# logger = logging.getLogger(__name__)


# class PDFService:
#     """Service for generating PDF certificate documents."""

#     # Page dimensions (A4 Landscape)
#     PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

#     # Color palette matching the template design
#     GOLD_COLOR = colors.HexColor("#8B6914")    # Dark gold for the thick border
#     DARK_COLOR = colors.HexColor("#2a2a2a")    # Dark charcoal for text
#     BORDER_DARK = colors.HexColor("#3a3a3a")   # Border outline color
#     LIGHT_TEXT = colors.HexColor("#444444")     # Slightly muted text
#     GRAY_LINE = colors.HexColor("#888888")     # Signature lines

#     # Content area insets (inside the innermost border)
#     CONTENT_LEFT = 28 * mm
#     CONTENT_RIGHT_EDGE = PAGE_WIDTH - 28 * mm

#     @staticmethod
#     def generate_pdf(
#         certificate_id: str,
#         recipient_name: str,
#         certificate_title: str,
#         issue_date: date,
#         organization_name: str,
#         qr_code_path: str,
#     ) -> str:
#         """
#         Generate a professional PDF certificate matching the ECMA template.

#         Args:
#             certificate_id: Unique certificate identifier.
#             recipient_name: Full name of the recipient.
#             certificate_title: Title/course name on the certificate.
#             issue_date: Date the certificate was issued.
#             organization_name: Issuing organization name.
#             qr_code_path: Path to the QR code image to embed.

#         Returns:
#             The file path to the saved PDF.

#         Raises:
#             FileProcessingError: If PDF generation fails.
#         """
#         settings = get_settings()
#         output_dir = settings.certificates_dir
#         output_path = os.path.join(output_dir, f"{certificate_id}.pdf")

#         try:
#             os.makedirs(output_dir, exist_ok=True)

#             c = canvas.Canvas(output_path, pagesize=landscape(A4))
#             c.setTitle(f"Certificate - {recipient_name}")

#             w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

#             # 1. Plain white background
#             c.setFillColor(colors.white)
#             c.rect(0, 0, w, h, fill=True, stroke=False)

#             # 2. Borders
#             PDFService._draw_borders(c)

#             # 3. Header row: Logo (left) + "CERTIFICATE OF COMPLETION" (center-right) + QR (right)
#             logo_path = os.path.join(
#                 settings.static_dir,
#                 "ECMA-Primary_Logo_Full-Colour-Gradient_RGB.png",
#             )
#             PDFService._draw_header_row(c, logo_path, qr_code_path)

#             # 4. Subtitle narrative
#             PDFService._draw_subtitle(c)

#             # 5. Recipient name
#             PDFService._draw_recipient_name(c, recipient_name)

#             # 6. Completion description + program title
#             PDFService._draw_program_info(c, certificate_title)

#             # 7. Signature box
#             PDFService._draw_signature_box(c)

#             # 8. Footer metadata
#             PDFService._draw_footer(c, issue_date, certificate_id)

#             c.save()
#             logger.info("PDF certificate generated: %s", output_path)
#             return output_path

#         except Exception as e:
#             logger.error(
#                 "Failed to generate PDF for %s: %s",
#                 certificate_id,
#                 str(e),
#             )
#             raise FileProcessingError(
#                 f"Failed to generate PDF for certificate '{certificate_id}'.",
#                 original_error=e,
#             )

#     # ------------------------------------------------------------------
#     # Drawing helpers
#     # ------------------------------------------------------------------

#     @staticmethod
#     def _draw_borders(c: canvas.Canvas) -> None:
#         """
#         Draw the multi-layered border matching the template:
#         outer thin dark → thick gold → inner thin dark → content thin dark.
#         """
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

#         # Layer 1: Outermost thin dark border
#         c.setStrokeColor(PDFService.BORDER_DARK)
#         c.setLineWidth(1.2)
#         c.rect(6 * mm, 6 * mm, w - 12 * mm, h - 12 * mm, fill=False)

#         # Layer 2: Thick gold border
#         c.setStrokeColor(PDFService.GOLD_COLOR)
#         c.setLineWidth(4 * mm)
#         c.rect(10 * mm, 10 * mm, w - 20 * mm, h - 20 * mm, fill=False)

#         # Layer 3: Thin dark line right inside gold
#         c.setStrokeColor(PDFService.BORDER_DARK)
#         c.setLineWidth(0.6)
#         c.rect(13.5 * mm, 13.5 * mm, w - 27 * mm, h - 27 * mm, fill=False)

#         # Layer 4: Inner content border (with a small gap)
#         c.setStrokeColor(PDFService.BORDER_DARK)
#         c.setLineWidth(0.8)
#         c.rect(16 * mm, 16 * mm, w - 32 * mm, h - 32 * mm, fill=False)

#     @staticmethod
#     def _draw_header_row(
#         c: canvas.Canvas,
#         logo_path: str,
#         qr_code_path: str,
#     ) -> None:
#         """
#         Draw the top header row: ECMA logo on the left, the
#         'CERTIFICATE OF COMPLETION' title to its right, and
#         the QR code on the far right — all on the same line.
#         """
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
#         header_y = h - 40 * mm  # baseline for the row

#         # --- Logo (left-aligned) ---
#         logo_h = 18 * mm
#         logo_w = 48 * mm
#         logo_x = 22 * mm
#         logo_y = header_y - 2 * mm

#         if os.path.exists(logo_path):
#             c.drawImage(
#                 logo_path,
#                 logo_x, logo_y,
#                 width=logo_w, height=logo_h,
#                 preserveAspectRatio=True,
#                 mask="auto",
#             )
#         else:
#             c.setFont("Times-Bold", 9)
#             c.setFillColor(PDFService.DARK_COLOR)
#             c.drawString(logo_x, logo_y + 10 * mm, "ETHIOPIAN CAPITAL")
#             c.drawString(logo_x, logo_y + 6 * mm, "MARKET AUTHORITY")

#         # --- "CERTIFICATE OF COMPLETION" (positioned to the right of the logo) ---
#         # The title sits between the logo and QR code, visually centered in that span
#         title_center_x = (logo_x + logo_w + (w - 22 * mm - 22 * mm)) / 2
#         c.setFont("Times-Bold", 22)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawCentredString(title_center_x, header_y + 6 * mm, "CERTIFICATE OF COMPLETION")

#         # --- QR code (right-aligned) ---
#         qr_size = 20 * mm
#         qr_x = w - 22 * mm - qr_size - 2 * mm
#         qr_y = header_y - 2 * mm

#         if os.path.exists(qr_code_path):
#             c.drawImage(
#                 qr_code_path,
#                 qr_x, qr_y,
#                 width=qr_size, height=qr_size,
#                 preserveAspectRatio=True,
#                 mask="auto",
#             )
#         else:
#             logger.warning("QR code not found at %s", qr_code_path)

#     @staticmethod
#     def _draw_subtitle(c: canvas.Canvas) -> None:
#         """Draw the italic narrative text below the title."""
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

#         c.setFont("Times-Italic", 12)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawCentredString(
#             w / 2,
#             h - 50 * mm,
#             "This is to certify that the following individual has successfully fulfilled all",
#         )
#         c.drawCentredString(
#             w / 2,
#             h - 56 * mm,
#             "requirements and is hereby awarded this certificate:",
#         )

#     @staticmethod
#     def _draw_recipient_name(c: canvas.Canvas, name: str) -> None:
#         """Draw the recipient name prominently with bracket decoration."""
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

#         # The name in large bold serif with bracket decoration
#         display_name = f"[{name}]"
#         c.setFont("Times-Bold", 28)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawCentredString(w / 2, h - 76 * mm, display_name)

#     @staticmethod
#     def _draw_program_info(c: canvas.Canvas, certificate_title: str) -> None:
#         """Draw the completion description and program/course title."""
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

#         # Completion text
#         c.setFont("Times-Roman", 11)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawCentredString(
#             w / 2,
#             h - 92 * mm,
#             "Upon successful completion of the Ethiopian Capital Market Authority",
#         )
#         c.drawCentredString(
#             w / 2,
#             h - 98 * mm,
#             "Online Investor Education Training Program.",
#         )

#         # Course / program title (bold)
#         c.setFont("Times-Bold", 13)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawCentredString(w / 2, h - 110 * mm, certificate_title)

#     @staticmethod
#     def _draw_signature_box(c: canvas.Canvas) -> None:
#         """
#         Draw the signature section inside a subtle rounded-corner box,
#         with two columns: left (Deputy DG) and right (DG).
#         """
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

#         # Signature box dimensions
#         box_x = 28 * mm
#         box_y = 44 * mm
#         box_w = w - 56 * mm
#         box_h = 28 * mm

#         # Subtle border for the signature box
#         c.setStrokeColor(colors.HexColor("#cccccc"))
#         c.setLineWidth(0.5)
#         c.roundRect(box_x, box_y, box_w, box_h, 2 * mm, fill=False)

#         # --- Left signature: Rahel Kassa ---
#         left_x = box_x + 8 * mm
#         name_y = box_y + 17 * mm
#         title_y = box_y + 9 * mm

#         c.setFont("Times-Bold", 10)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawString(left_x, name_y, "Rahel Kassa")

#         c.setFont("Times-Bold", 9)
#         c.setFillColor(PDFService.DARK_COLOR)
#         title_text = "Deputy Director General"
#         c.drawString(left_x, title_y, title_text)

#         # Signature line extending from end of title
#         title_w = c.stringWidth(title_text, "Times-Bold", 9)
#         c.setStrokeColor(PDFService.GRAY_LINE)
#         c.setLineWidth(0.5)
#         line_start = left_x + title_w + 2 * mm
#         line_end = left_x + title_w + 30 * mm
#         c.line(line_start, title_y, line_end, title_y)

#         # --- Right signature: Hana Tehelku ---
#         right_x = w / 2 + 15 * mm
#         c.setFont("Times-Bold", 10)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawString(right_x, name_y, "Hana Tehelku")

#         c.setFont("Times-Bold", 9)
#         c.setFillColor(PDFService.DARK_COLOR)
#         right_title = "Director General"
#         c.drawString(right_x, title_y, right_title)

#         right_title_w = c.stringWidth(right_title, "Times-Bold", 9)
#         r_line_start = right_x + right_title_w + 2 * mm
#         r_line_end = right_x + right_title_w + 30 * mm
#         c.line(r_line_start, title_y, r_line_end, title_y)

#     @staticmethod
#     def _draw_footer(
#         c: canvas.Canvas,
#         issue_date: date,
#         certificate_id: str,
#     ) -> None:
#         """Draw the footer: issue date (left), address (center), certificate ID (right)."""
#         w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
#         formatted_date = issue_date.strftime("%B %d, %Y")

#         left_x = 28 * mm
#         right_x = w - 28 * mm

#         # --- Left: Issued on ---
#         c.setFont("Times-Roman", 8)
#         c.setFillColor(PDFService.LIGHT_TEXT)
#         c.drawString(left_x, 35 * mm, "Issued on:")
#         c.setFont("Times-Bold", 9)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawString(left_x, 29 * mm, formatted_date)

#         # --- Center: Address ---
#         c.setFont("Times-Roman", 7.5)
#         c.setFillColor(PDFService.LIGHT_TEXT)
#         c.drawCentredString(
#             w / 2,
#             32 * mm,
#             "Ethiopian Capital Market Authority, Flamingo Area, Kirkos Sub-",
#         )
#         c.drawCentredString(w / 2, 27 * mm, "City, Addis Ababa, Ethiopia")

#         # --- Right: Certificate ID ---
#         c.setFont("Times-Roman", 8)
#         c.setFillColor(PDFService.LIGHT_TEXT)
#         c.drawRightString(right_x, 35 * mm, "Certificate ID:")
#         c.setFont("Times-Bold", 9)
#         c.setFillColor(PDFService.DARK_COLOR)
#         c.drawRightString(right_x, 29 * mm, certificate_id)
