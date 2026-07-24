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

_FONTS_REGISTERED = False
_FONTS_OK = False


def _register_fonts() -> bool:
    """
    Register the Amharic (Noto Sans Ethiopic) fonts with ReportLab.

    Safe to call multiple times — registration only happens once.
    Returns True if both the regular and bold Amharic fonts are
    registered and available for use, False otherwise.
    """
    global _FONTS_REGISTERED, _FONTS_OK
    if _FONTS_REGISTERED:
        return _FONTS_OK

    settings = get_settings()
    font_dir = os.path.join(settings.static_dir, "fonts")
    regular_path = os.path.join(font_dir, "NotoSansEthiopic-Regular.ttf")
    bold_path = os.path.join(font_dir, "NotoSansEthiopic-Bold.ttf")

    regular_ok = False
    bold_ok = False

    try:
        if os.path.exists(regular_path):
            pdfmetrics.registerFont(TTFont("NotoEthiopic", regular_path))
            regular_ok = True
        else:
            logger.warning("Amharic regular font not found at %s", regular_path)

        if os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont("NotoEthiopic-Bold", bold_path))
            bold_ok = True
        else:
            logger.warning("Amharic bold font not found at %s", bold_path)

    except Exception as e:
        logger.error("Failed to register Amharic fonts: %s", str(e))

    _FONTS_REGISTERED = True
    _FONTS_OK = regular_ok and bold_ok
    return _FONTS_OK


# Font names to use for Amharic text once registered via _register_fonts().
_AMHARIC_FONT = "NotoEthiopic"
_AMHARIC_FONT_BOLD = "NotoEthiopic-Bold"


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
        recipient_name_amharic: str | None = None,
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

        if not _register_fonts():
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
            c.setFillColor(colors.HexColor("#F1EADF"))
            c.rect(0, 0, w, h, fill=True, stroke=False)

            # 2. Border
            PDFService._draw_border(c)

            # 2b. Watermark
            PDFService._draw_watermark(c, w)

            # 3. QR code, top-right corner
            PDFService._draw_qr_code(c, qr_code_path)

            # 4. Centered logo + bilingual org name lockup
            PDFService._draw_header_lockup(c, settings)

            # 5. Bilingual title (recipient name)
            PDFService._draw_title(c, recipient_name)

            # 6. "To ____" / "ለ ____" recipient line
            PDFService._draw_recipient_line(
                c, recipient_name, recipient_name_amharic
            )

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
    def _draw_qr_code(c: canvas.Canvas, qr_code_path: str) -> None:
        """QR code, top-right corner, for certificate verification."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        qr_size = 22 * mm
        qr_x = w - 22 * mm - qr_size
        qr_y = h - 22 * mm - qr_size

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
    def _draw_watermark(c: canvas.Canvas, page_width: float) -> None:
        """Faint gold guilloche seal watermark, cropped at the bottom edge."""
        settings = get_settings()
        seal_path = os.path.join(
            settings.static_dir, "Small_Seal_Guilloche_Gradient_Gold_RGB.png"
        )

        if not os.path.exists(seal_path):
            return

        seal_size = 80 * mm

        c.saveState()
        c.setFillAlpha(0.12)  # lower = more transparent
        c.drawImage(
            seal_path,
            (page_width - seal_size) / 2,
            -42 * mm,  # negative y crops it at the bottom
            width=seal_size,
            height=seal_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        c.restoreState()

    @staticmethod
    def _draw_header_row(
        c: canvas.Canvas,
        logo_path: str,
        qr_code_path: str,
    ) -> None:
        """
        Draw the top header row: an enlarged ECMA logo (which already
        contains the organization's name/title text, so no separate
        "CERTIFICATE OF COMPLETION" text is drawn), left-aligned, with
        the QR code on the far right.
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        header_y = h - 40 * mm  # baseline for the row

        logo_h = 34 * mm
        logo_w = 90 * mm
        logo_x = (w - logo_w) / 2
        logo_y = header_y - 6 * mm

        if os.path.exists(logo_path):
            c.drawImage(
                logo_path,
                logo_x, logo_y,
                width=logo_w, height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            c.setFont("Times-Bold", 12)
            c.setFillColor(PDFService.DARK_COLOR)
            c.drawString(logo_x, logo_y + 14 * mm, "ETHIOPIAN CAPITAL")
            c.drawString(logo_x, logo_y + 8 * mm, "MARKET AUTHORITY")

        # --- QR code (right-aligned) ---
        qr_size = 22 * mm
        qr_x = w - 22 * mm - qr_size - 2 * mm
        qr_y = header_y

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
        Centered header: enlarged ECMA logo only. The logo image already
        contains the organization's name/wordmark, so no separate text
        is drawn beside it.
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        icon_path = os.path.join(
            settings.static_dir,
            "ECMA-Primary_Logo_Full-Colour-Gradient_RGB.png",
        )
        logo_w = 85 * mm
        logo_h = 32 * mm
        logo_x = (w - logo_w) / 2
        top_y = h - 18 * mm


        if os.path.exists(icon_path):
            c.drawImage(
                icon_path,
                logo_x, top_y - logo_h,
                width=logo_w, height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            logger.warning("ECMA logo not found at %s", icon_path)
    @staticmethod
    def _draw_title(c: canvas.Canvas, recipient_name: str) -> None:
        """Bilingual title, centered: recipient name in large bold serif."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        display_name = f"[{recipient_name}]"
        c.setFont("Times-Bold", 25)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 60 * mm, "CERTIFICATE OF PARTICIPATION")

        c.setFont(_AMHARIC_FONT_BOLD, 16)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 68 * mm, "የተሳትፎ የምስክር ወረቀት")

    @staticmethod
    def _split_recipient_names(
        recipient_name: str,
        recipient_name_amharic: str | None = None,
    ) -> tuple[str, str]:
        """
        Extract English and Amharic recipient names.
        
        Supports:
        1. Explicit recipient_name_amharic if provided.
        2. Combined names in recipient_name separated by '/', '|', ',', or parentheses.
        3. Auto-detecting Ethiopic Unicode characters.
        """
        import re

        if recipient_name_amharic and recipient_name_amharic.strip():
            return recipient_name.strip(), recipient_name_amharic.strip()

        name = (recipient_name or "").strip()

        # Check for explicit separators: /, |
        for sep in ['/', '|']:
            if sep in name:
                parts = name.split(sep, 1)
                p1, p2 = parts[0].strip(), parts[1].strip()
                if re.search(r'[\u1200-\u137F]', p2):
                    return p1, p2
                elif re.search(r'[\u1200-\u137F]', p1):
                    return p2, p1
                return p1, p2

        # Check for parentheses: e.g. "Abel Tesfaye (አበበ ተስፋዬ)"
        match = re.search(r'^(.*?)\s*[\(\（](.*?)[\)\）]\s*$', name)
        if match:
            p1, p2 = match.group(1).strip(), match.group(2).strip()
            if re.search(r'[\u1200-\u137F]', p2):
                return p1, p2
            elif re.search(r'[\u1200-\u137F]', p1):
                return p2, p1
            return p1, p2

        # Check for comma separator if scripts differ
        if ',' in name:
            parts = name.split(',', 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            if re.search(r'[\u1200-\u137F]', p2):
                return p1, p2
            elif re.search(r'[\u1200-\u137F]', p1):
                return p2, p1

        # Single string: check if it is Ethiopic or Latin
        if re.search(r'[\u1200-\u137F]', name):
            return "", name
        else:
            return name, ""

    @staticmethod
    def _draw_recipient_line(
        c: canvas.Canvas,
        recipient_name: str,
        recipient_name_amharic: str | None = None,
    ) -> None:
        """Two-column 'To ____' (English) / 'ለ ____' (Amharic) recipient line."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        y = h - 82 * mm

        english_name, amharic_name = PDFService._split_recipient_names(
            recipient_name, recipient_name_amharic
        )

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
        if english_name:
            c.setFont("Times-Bold", 12)
            c.drawCentredString((line_start + line_end) / 2, y + 2 * mm, english_name)

        # Amharic: "ለ ______________"
        c.setFont(_AMHARIC_FONT, 11)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(right_x, y, "ለ")
        label_w_am = c.stringWidth("ለ", _AMHARIC_FONT, 11)
        line_start_am = right_x + label_w_am + 3 * mm
        line_end_am = PDFService.CONTENT_RIGHT_EDGE
        c.line(line_start_am, y - 1 * mm, line_end_am, y - 1 * mm)
        if amharic_name:
            c.setFont(_AMHARIC_FONT_BOLD, 12)
            c.drawCentredString((line_start_am + line_end_am) / 2, y + 2 * mm, amharic_name)

    @staticmethod
    def _draw_body(c: canvas.Canvas, certificate_title: str, organization_name: str) -> None:
        """Draw the completion description in two columns: English (left), Amharic (right)."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        left_x = PDFService.CONTENT_LEFT + 4 * mm
        right_x = w / 2 + PDFService.COLUMN_GAP
        para_top = h - 96 * mm
        line_gap = 7.5 * mm

        # English column (left)
        c.setFont("Times-Roman", 16)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, para_top, "for successfully completing ECMA's twelve week")
        c.drawString(left_x, para_top - line_gap, "online investor education program organized")
        c.drawString(left_x, para_top - 2 * line_gap, f"by {organization_name}")
        # c.drawString(left_x, para_top - 3 * line_gap, "knowledge in capital markets through online")
        # c.drawString(left_x, para_top - 4 * line_gap, "education.")

        # Amharic column (right)
        c.setFont(_AMHARIC_FONT, 15)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(right_x, para_top, "የኢትዮጵያ የካፒታል ገበያ ባለስልጣን የካፒታል ገበያ መሠረታዊ")
        c.drawString(right_x, para_top - line_gap, "እውቀት ማጎልበት ላይ ትኩረት አድርጎ ለአስራ ሁለት ሳምንታት")
        c.drawString(right_x, para_top - 2 * line_gap, "የሰጠው የበይነ መረብ ስልጠና በስኬት ስላጠናቀቁ ይህ የተሳትፎ")
        c.drawString(right_x, para_top - 3 * line_gap, "የምስክር ወረቀት ተበርክቶላቸዋል።")

    @staticmethod
    def _draw_signature(c: canvas.Canvas, settings) -> None:
        """
        Draw the signature section: an optional signature image above a
        centered signing line, with the Director General's name, English
        title, and Amharic title beneath. Falls back to a blank line if
        the signature image is not yet available.

        Expected signature image path: static/signatures/final signature.png
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        box_x = 28 * mm
        box_w = w - 56 * mm
        sig_center_x = box_x + box_w / 2

        line_y = 48 * mm
        line_half_width = 45 * mm

        sig_path = os.path.join(
            settings.static_dir, "final signiture.png"
        )
        if os.path.exists(sig_path):
            sig_w = 150 * mm
            sig_h = 58 * mm
            c.drawImage(
                sig_path,
                sig_center_x - sig_w / 2, line_y - 20 * mm,
                width=sig_w, height=sig_h,
                preserveAspectRatio=True,
                mask="auto",
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

        c.setFont(_AMHARIC_FONT_BOLD, 8)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawCentredString(sig_center_x, line_y - 14 * mm, "ዋና ዳይሬክተር")
    @staticmethod
    def _draw_stamp(c: canvas.Canvas, settings) -> None:
        """
        Official seal/stamp, bottom-right corner. Uses an image if present,
        otherwise draws a simple placeholder circle so the layout holds its
        shape until a real stamp asset is available.

        Expected stamp image path: static/stamp.png
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        stamp_size = 96 * mm
        stamp_x = w - 24 * mm - stamp_size
        stamp_y = -20 * mm - 6

        stamp_path = os.path.join(settings.static_dir, "final stamp.png")

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
        """Draw the footer: issue date (left), certificate ID (right) — English + Amharic."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        formatted_date = issue_date.strftime("%B %d, %Y")

        left_x = 28 * mm

        # # --- Left column: Issued on, then Certificate ID stacked below ---
        # c.setFont("Times-Roman", 9)
        # c.setFillColor(PDFService.LIGHT_TEXT)
        # c.drawString(left_x, 30 * mm, "Issued on:")
        # c.setFont("Times-Bold", 9)
        # c.setFillColor(PDFService.DARK_COLOR)
        # c.drawString(left_x, 25.5 * mm, formatted_date)

        c.setFont("Times-Roman", 9)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawString(left_x, 19 * mm, "Certificate ID:")
        c.setFont("Times-Bold", 9)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, 14.5 * mm, certificate_id)
