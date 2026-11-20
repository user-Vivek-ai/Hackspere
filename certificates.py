import os
import io
import secrets
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, Circle, String, Group, Polygon
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF

IS_VERCEL = os.environ.get("VERCEL") == "1" or "VERCEL" in os.environ

if IS_VERCEL:
    CERT_DIR = os.path.join(tempfile.gettempdir(), "certificates")
else:
    CERT_DIR = os.path.join(os.path.dirname(__file__), "static", "certificates")

os.makedirs(CERT_DIR, exist_ok=True)

def generate_certificate_code() -> str:
    """Generate a unique human-friendly certificate verification code."""
    # Format: HS-2026-X7K9M2
    year = datetime.now().year
    random_part = secrets.token_hex(3).upper()
    return f"HS-{year}-{random_part}"

def draw_decorative_corners(c, w, h, margin, color):
    """Draw stylish geometric corner accents."""
    c.setStrokeColor(color)
    c.setFillColor(color)
    size = 28
    
    # Top-Left
    c.lines([
        (margin - 4, h - margin + 4, margin + size, h - margin + 4),
        (margin - 4, h - margin + 4, margin - 4, h - margin - size)
    ])
    # Top-Right
    c.lines([
        (w - margin + 4, h - margin + 4, w - margin - size, h - margin + 4),
        (w - margin + 4, h - margin + 4, w - margin + 4, h - margin - size)
    ])
    # Bottom-Left
    c.lines([
        (margin - 4, margin - 4, margin + size, margin - 4),
        (margin - 4, margin - 4, margin - 4, margin + size)
    ])
    # Bottom-Right
    c.lines([
        (w - margin + 4, margin - 4, w - margin - size, margin - 4),
        (w - margin + 4, margin - 4, w - margin + 4, margin + size)
    ])

def draw_official_seal(c, x, y):
    """Draw a vector seal badge with star emblem."""
    # Outer gold rim
    c.setFillColor(colors.HexColor("#fef3c7"))
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(2.5)
    c.circle(x, y, 34, fill=1, stroke=1)
    
    # Inner navy ring
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(1)
    c.circle(x, y, 27, fill=1, stroke=1)
    
    # Center text
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x, y + 4, "VERIFIED")
    c.setFont("Helvetica", 7)
    c.drawCentredString(x, y - 6, "EXCELLENCE")
    
    # Ribbon tail
    c.setFillColor(colors.HexColor("#d97706"))
    p = c.beginPath()
    p.moveTo(x - 18, y - 30)
    p.lineTo(x - 28, y - 56)
    p.lineTo(x - 16, y - 48)
    p.lineTo(x - 4, y - 56)
    p.lineTo(x - 10, y - 30)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    p2 = c.beginPath()
    p2.moveTo(x + 10, y - 30)
    p2.lineTo(x + 4, y - 56)
    p2.lineTo(x + 16, y - 48)
    p2.lineTo(x + 28, y - 56)
    p2.lineTo(x + 18, y - 30)
    p2.close()
    c.drawPath(p2, fill=1, stroke=0)

def draw_qr_code(c, x, y, size, data):
    """Draw a vector QR code with white backing and border."""
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(1)
    c.roundRect(x - 4, y - 4, size + 8, size + 8, 4, fill=1, stroke=1)

    qr = QrCodeWidget(data)
    bounds = qr.getBounds()
    w_qr = bounds[2] - bounds[0]
    h_qr = bounds[3] - bounds[1]
    d = Drawing(size, size, transform=[size / w_qr, 0, 0, size / h_qr, 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, x, y)

def generate_certificate_pdf(
    certificate_code: str,
    participant_name: str,
    hackathon_title: str,
    event_dates: str,
    organizer_name: str,
    project_name: str = None,
    output_path: str = None,
    verify_url: str = None
) -> bytes:
    """Generate a high-resolution vector PDF certificate."""
    buffer = io.BytesIO()
    target = output_path if output_path else buffer

    w, h = landscape(A4)
    c = canvas.Canvas(target, pagesize=landscape(A4))
    
    # 1. Subtle warm background tint
    c.setFillColor(colors.HexColor("#fafafa"))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # 2. Outer decorative border (Dark Slate Navy)
    c.setStrokeColor(colors.HexColor("#0f172a"))
    c.setLineWidth(3.5)
    c.rect(26, 26, w - 52, h - 52, fill=0, stroke=1)

    # 3. Inner accent border (Royal Indigo / Gold)
    c.setStrokeColor(colors.HexColor("#3b82f6"))
    c.setLineWidth(1.2)
    c.rect(34, 34, w - 68, h - 68, fill=0, stroke=1)

    # 4. Corner accents
    draw_decorative_corners(c, w, h, 34, colors.HexColor("#d97706"))

    # 5. Top Brand Mark & Title
    c.setFillColor(colors.HexColor("#3b82f6"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 75, "H A C K S P H E R E   P L A T F O R M")

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(w / 2, h - 110, "CERTIFICATE OF PARTICIPATION")

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, h - 132, "THIS CERTIFICATE IS OFFICIALLY PRESENTED AND CONFERRED UPON")

    # 6. Participant Name (Highlight)
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w / 2, h - 180, participant_name.strip())

    # Underline accent below name
    c.setStrokeColor(colors.HexColor("#f59e0b"))
    c.setLineWidth(2)
    c.line(w / 2 - 140, h - 192, w / 2 + 140, h - 192)

    # 7. Achievement Statement
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 12)
    if project_name:
        stmt1 = f"for successfully designing, engineering, and submitting the accepted project"
        stmt2 = f"'{project_name}'"
        c.drawCentredString(w / 2, h - 224, stmt1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(w / 2, h - 244, stmt2)
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica", 12)
        c.drawCentredString(w / 2, h - 264, f"in the world-class competitive hackathon")
    else:
        c.drawCentredString(w / 2, h - 232, "for successfully building and submitting an accepted project to")

    # 8. Hackathon Title
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 18)
    hackathon_y = h - 296 if project_name else h - 265
    c.drawCentredString(w / 2, hackathon_y, hackathon_title.strip())

    # 9. Official Seal
    draw_official_seal(c, w / 2, 130)

    # 10. Left Column Details (Dates & Organizer)
    left_x = 90
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_x, 155, "EVENT DURATION:")
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica", 10)
    c.drawString(left_x, 138, event_dates)

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_x, 115, "HOSTED & ORGANIZED BY:")
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, 98, organizer_name)

    # Organizer Signature Line
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.line(left_x, 78, left_x + 180, 78)
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(left_x, 65, "Authorized Event Lead Signature")

    # 11. Right Column Details (Certificate ID & Registry)
    right_x = w - 340
    issue_date = datetime.now().strftime("%B %d, %Y")
    
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(right_x, 155, "DATE OF ISSUANCE:")
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica", 10)
    c.drawString(right_x, 138, issue_date)

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(right_x, 115, "VERIFIED CERTIFICATE ID:")
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.setFont("Courier-Bold", 11)
    c.drawString(right_x, 98, certificate_code)

    # Validation Stamp line
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.line(right_x, 78, right_x + 160, 78)
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(right_x, 65, "HackSphere Academic & Dev Registry")

    # 12. QR Code (Scan to Verify Name & Credentials)
    qr_x = w - 145
    qr_y = 65
    qr_size = 68
    qr_data = verify_url or f"https://hackspere.vercel.app/verify-certificate/{certificate_code}"
    draw_qr_code(c, qr_x, qr_y, qr_size, qr_data)

    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 14, "SCAN TO VERIFY")
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 23, "Recipient & Project")

    # 13. Bottom Security & Verification Footer
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        w / 2, 40,
        f"Scan QR code or visit https://hackspere.vercel.app/verify-certificate/{certificate_code} to verify authenticity • Issued for Accepted Project"
    )

    c.showPage()
    c.save()

    if output_path:
        return None
    
    buffer.seek(0)
    return buffer.getvalue()
