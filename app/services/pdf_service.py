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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.config import get_settings
from app.exceptions import FileProcessingError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Font registration (module-level, runs once on import)
# ---------------------------------------------------------------------------

_FONTS_REGISTERED = False


def _register_fonts() -> None:
    """
    Register the Amharic (Noto Sans Ethiopic) fonts with ReportLab.

    Safe to call multiple times — registration only happens once.
    """
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    settings = get_settings()
    fonts_dir = os.path.join(settings.static_dir, "fonts")
    regular_path = os.path.join(fonts_dir, "NotoSansEthiopic-Regular.ttf")
    bold_path = os.path.join(fonts_dir, "NotoSansEthiopic-Bold.ttf")

    try:
        if os.path.exists(regular_path):
            pdfmetrics.registerFont(TTFont("NotoEthiopic", regular_path))
        else:
            logger.warning("Amharic regular font not found at %s", regular_path)

        if os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont("NotoEthiopic-Bold", bold_path))
        else:
            logger.warning("Amharic bold font not found at %s", bold_path)

        _FONTS_REGISTERED = True
    except Exception as e:
        logger.error("Failed to register Amharic fonts: %s", str(e))


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

    # Amharic translations for standard certificate copy.
    # NOTE: these should be reviewed by a native Amharic speaker on staff
    # before use on real, issued certificates.
    AM_SUBTITLE_LINE1 = "ይህ የሚያረጋግጠው የሚከተለው ግለሰብ ሁሉንም መስፈርቶች"
    AM_SUBTITLE_LINE2 = "በተሳካ ሁኔታ አሟልቶ ይህንን የምስክር ወረቀት ማግኘቱን ነው፦"
    AM_COMPLETION_LINE1 = "የኢትዮጵያ ካፒታል ገበያ ባለስልጣን"
    AM_COMPLETION_LINE2 = "የመስመር ላይ የባለሀብት ትምህርት ስልጠና መርሃ ግብርን በተሳካ ሁኔታ በማጠናቀቅ"
    AM_DEPUTY_DG_TITLE = "ምክትል ዋና ዳይሬክተር"
    AM_DG_TITLE = "ዋና ዳይሬክተር"
    AM_ISSUED_ON = "የተሰጠበት ቀን፦"
    AM_CERT_ID = "የምስክር ወረቀት መለያ፦"
    AM_ADDRESS_LINE1 = "የኢትዮጵያ ካፒታል ገበያ ባለስልጣን፣ ፍላሚንጎ አካባቢ፣ ቂርቆስ ክፍለ ከተማ፣"
    AM_ADDRESS_LINE2 = "አዲስ አበባ፣ ኢትዮጵያ"

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
        _register_fonts()

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

            # 3. Header row: enlarged logo (centered, contains its own text) + QR (right)
            logo_path = os.path.join(
                settings.static_dir,
                "ECMA-Primary_Logo_Full-Colour-Gradient_RGB.png",
            )
            PDFService._draw_header_row(c, logo_path, qr_code_path)

            # 4. Subtitle narrative (English + Amharic)
            PDFService._draw_subtitle(c)

            # 5. Bilingual title
            PDFService._draw_title(c)

            # 6. Completion description + program title (English + Amharic)
            PDFService._draw_program_info(c, certificate_title)

            # 7. Signature box (English + Amharic titles)
            PDFService._draw_signature_box(c)

            # 8. Footer metadata (English + Amharic)
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
    def _draw_subtitle(c: canvas.Canvas) -> None:
        """Draw the main heading above the recipient name, in English then Amharic."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        # English heading
        c.setFont("Times-Bold", 24)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 55 * mm, "CERTIFICATE OF PARTICIPATION")

        # Amharic heading
        c.setFont("NotoEthiopic-Bold", 16)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 63 * mm, "የተሳትፎ የምስክር ወረቀት")

    @staticmethod
    def _draw_title(c: canvas.Canvas) -> None:
        """Bilingual title, centered: English above Amharic."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        # The name in large bold serif with bracket decoration
        # (font size increased from 28 -> 34)
        display_name = f"[{name}]"
        c.setFont("Times-Bold", 34)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(w / 2, h - 86 * mm, display_name)

    @staticmethod
    def _draw_program_info(c: canvas.Canvas, certificate_title: str) -> None:
        """Draw the completion description in two columns: English (left), Amharic (right)."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        y = h - 74 * mm

        left_x = PDFService.CONTENT_LEFT + 4 * mm
        right_x = w / 2 + 6 * mm
        para_top = h - 100 * mm
        line_gap = 6 * mm

        # English column (left)
        c.setFont("Times-Roman", 15)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, para_top, "has successfully completed ECMA's 12 week")
        c.drawString(left_x, para_top - line_gap, "online investor Education program organized")
        c.drawString(left_x, para_top - 2 * line_gap, "by the Ethiopian Capital Market Authority,")
        c.drawString(left_x, para_top - 3 * line_gap, "designed to provide fundaments knowledge")
        c.drawString(left_x, para_top - 4 * line_gap, "in capital market through online education.")

        # Amharic column (right)
        c.setFont("NotoEthiopic", 13.5)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(right_x, para_top, "የኢትዮጵያ የካፒታል ገበያ ባለስልጣን የካፒታል ገበያ መሠረታዊ")
        c.drawString(right_x, para_top - line_gap, "እውቀት ማግኘት ዓላማ ትኩረት አድርጎ ለ12 ሳምንታት በቆየው")
        c.drawString(right_x, para_top - 2 * line_gap, "በድህረ መረብ ስልጠና መርሃ-ግብር ተሳትፎ እና ስልጠናውን በስኬት ስላጠናቀቁ/ቂ")
        c.drawString(right_x, para_top - 3 * line_gap, "ይህ የተሳትፎ የምስክር ወረቀት ተሰጥቷል/ታል።")

        
    @staticmethod
    def _draw_body(c: canvas.Canvas, certificate_title: str, organization_name: str) -> None:
        """
        Draw the signature section inside a subtle rounded-corner box,
        with two columns: left (Deputy DG) and right (DG). Titles are
        shown in English and Amharic.
        """
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT

        # Signature box dimensions
        box_x = 28 * mm
        box_y = 40 * mm
        box_w = w - 56 * mm
        box_h = 32 * mm

        english_lines = [
            f"has successfully completed the {certificate_title}",
            f"program organized by {organization_name}, designed",
            "to provide foundational knowledge through online",
            "education.",
        ]

        # # --- Left signature: Rahel Kassa ---
        # left_x = box_x + 8 * mm
        # name_y = box_y + 22 * mm
        # title_y = box_y + 13 * mm
        # am_title_y = box_y + 7 * mm

        # # Name (font size increased from 10 -> 12)
        # c.setFont("Times-Bold", 12)
        # c.setFillColor(PDFService.DARK_COLOR)
        # c.drawString(left_x, name_y, "Rahel Kassa")

        # # English title (font size increased from 9 -> 11)
        # c.setFont("Times-Bold", 11)
        # c.setFillColor(PDFService.DARK_COLOR)
        # title_text = "Deputy Director General"
        # c.drawString(left_x, title_y, title_text)

        # # Amharic title
        # c.setFont("NotoEthiopic-Bold", 9)
        # c.drawString(left_x, am_title_y, PDFService.AM_DEPUTY_DG_TITLE)

        # # Signature line extending from end of title
        # title_w = c.stringWidth(title_text, "Times-Bold", 11)
        # c.setStrokeColor(PDFService.GRAY_LINE)
        # c.setLineWidth(0.5)
        # line_start = left_x + title_w + 2 * mm
        # line_end = left_x + title_w + 30 * mm
        # c.line(line_start, title_y, line_end, title_y)

# --- Signature: Hana Tehelku, Director General (centered) ---
        name_y = box_y + 22 * mm
        title_y = box_y + 13 * mm
        am_title_y = box_y + 7 * mm

        sig_center_x = box_x + box_w / 2

        c.setFont("Times-Bold", 12)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawCentredString(sig_center_x, name_y, "Hana Tehelku")

        c.setFont("Times-Bold", 11)
        c.setFillColor(PDFService.DARK_COLOR)
        right_title = "Director General"
        c.drawCentredString(sig_center_x, title_y, right_title)

        c.setFont("NotoEthiopic-Bold", 9)
        c.drawCentredString(sig_center_x, am_title_y, PDFService.AM_DG_TITLE)

        # Signature line, centered under the title
        title_w = c.stringWidth(right_title, "Times-Bold", 11)
        c.setStrokeColor(PDFService.GRAY_LINE)
        c.setLineWidth(0.5)
        line_half = max(title_w, 40 * mm) / 2
        c.line(sig_center_x - line_half, title_y, sig_center_x + line_half, title_y)

        # --- Stamp placeholder (to be filled in later), left of the signature ---
        stamp_radius = 11 * mm
        stamp_cx = box_x + 20 * mm
        stamp_cy = box_y + box_h / 2

        c.saveState()
        c.setDash(2, 2)
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.7)
        c.circle(stamp_cx, stamp_cy, stamp_radius, fill=False, stroke=True)
        c.restoreState()

        c.setFont("Times-Italic", 7)
        c.setFillColor(colors.HexColor("#999999"))
        c.drawCentredString(stamp_cx, stamp_cy - 2, "STAMP")

    @staticmethod
    def _draw_footer(
        c: canvas.Canvas,
        issue_date: date,
        certificate_id: str,
    ) -> None:
        """Draw the footer: issue date (left), address (center), certificate ID (right) — English + Amharic."""
        w, h = PDFService.PAGE_WIDTH, PDFService.PAGE_HEIGHT
        formatted_date = issue_date.strftime("%B %d, %Y")
        left_x = PDFService.CONTENT_LEFT

        left_x = 28 * mm
        right_x = w - 28 * mm

        # --- Left: Issued on (English + Amharic) ---
# --- Left: Issued on (English + Amharic) ---
        c.setFont("Times-Roman", 9)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawString(left_x, 36 * mm, "Issued on:")

        c.setFont("NotoEthiopic", 8)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawString(left_x, 30.5 * mm, PDFService.AM_ISSUED_ON)

        c.setFont("Times-Bold", 10)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawString(left_x, 25.5 * mm, formatted_date)
        


# --- Right: Certificate ID (English + Amharic) ---
        c.setFont("Times-Roman", 9)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawRightString(right_x, 36 * mm, "Certificate ID:")

        c.setFont("NotoEthiopic", 8)
        c.setFillColor(PDFService.LIGHT_TEXT)
        c.drawRightString(right_x, 30.5 * mm, PDFService.AM_CERT_ID)

        c.setFont("Times-Bold", 10)
        c.setFillColor(PDFService.DARK_COLOR)
        c.drawRightString(right_x, 25.5 * mm, certificate_id)
