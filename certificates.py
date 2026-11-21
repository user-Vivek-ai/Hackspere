import os
import io
import math
import secrets
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
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

def draw_sparkle_star(c, cx, cy, radius, color):
    """Draw a classic 4-pointed luxury sparkle star at (cx, cy)."""
    c.setFillColor(color)
    c.setStrokeColor(color)
    p = c.beginPath()
    inner = radius * 0.22
    p.moveTo(cx, cy + radius)
    p.curveTo(cx, cy + inner, cx + inner, cy, cx + radius, cy)
    p.curveTo(cx + inner, cy, cx, cy - inner, cx, cy - radius)
    p.curveTo(cx - inner, cy, cx, cy - inner, cx - radius, cy)
    p.curveTo(cx - inner, cy, cx, cy + inner, cx, cy + radius)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

def draw_top_crest(c, cx, cy, color):
    """Draw a geometric luxury academy crest with hexagon and inner chevron."""
    c.setStrokeColor(color)
    c.setLineWidth(2.0)
    r = 13
    pts = []
    for i in range(6):
        angle = math.pi / 6 + i * (math.pi / 3)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        p.lineTo(pt[0], pt[1])
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    # Inner geometric chevron/peak
    p_inner = c.beginPath()
    p_inner.moveTo(cx - 5.5, cy - 2.5)
    p_inner.lineTo(cx, cy + 4)
    p_inner.lineTo(cx + 5.5, cy - 2.5)
    c.setLineWidth(1.8)
    c.drawPath(p_inner, fill=0, stroke=1)

def draw_signature(c, x, y, color):
    """Draw an authentic, flowing cursive vector signature (Oliver Shaw)."""
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.5)
    c.setLineCap(1)  # Round cap
    c.setLineJoin(1) # Round join

    # Capital 'O' and looping body
    p = c.beginPath()
    p.moveTo(x + 12, y + 26)
    p.curveTo(x - 2, y + 24, x - 4, y + 6, x + 8, y + 2)
    p.curveTo(x + 22, y - 2, x + 24, y + 22, x + 14, y + 26)
    p.curveTo(x + 8, y + 28, x + 16, y + 15, x + 28, y + 9)
    # 'l' loop
    p.curveTo(x + 32, y + 24, x + 35, y + 26, x + 35, y + 15)
    p.curveTo(x + 35, y + 2, x + 38, y + 2, x + 42, y + 8)
    # 'i' 'v' 'e' 'r'
    p.curveTo(x + 46, y + 14, x + 50, y + 2, x + 55, y + 8)
    p.curveTo(x + 60, y + 14, x + 64, y + 4, x + 70, y + 7)
    p.curveTo(x + 75, y + 10, x + 80, y + 3, x + 85, y + 6)
    c.drawPath(p, fill=0, stroke=1)

    # Dot on 'i'
    c.circle(x + 44, y + 16, 1.2, fill=1, stroke=0)

    # Capital 'S' and 'haw' flourish
    p2 = c.beginPath()
    p2.moveTo(x + 95, y + 24)
    p2.curveTo(x + 102, y + 28, x + 106, y + 20, x + 98, y + 15)
    p2.curveTo(x + 90, y + 9, x + 94, y + 2, x + 105, y + 3)
    p2.curveTo(x + 112, y + 4, x + 118, y + 18, x + 122, y + 24)
    p2.lineTo(x + 123, y + 2)
    p2.curveTo(x + 124, y + 12, x + 130, y + 14, x + 134, y + 4)
    p2.curveTo(x + 138, y + 10, x + 144, y + 4, x + 148, y + 7)
    p2.curveTo(x + 154, y + 12, x + 160, y + 3, x + 168, y + 14)
    p2.curveTo(x + 172, y + 10, x + 176, y + 3, x + 195, y + 1)
    c.drawPath(p2, fill=0, stroke=1)

def draw_qr_code(c, x, y, size, data):
    """Draw a vector QR code with crisp border."""
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
    """
    Generate an official high-resolution vector PDF certificate
    matching the luxury Brookstone / HackSphere certificate template design:
    - Pure white/ivory background
    - Warm bronze/taupe double border with 4 corner star accents
    - Academy geometric crest & typography
    - Bold serif 'CERTIFICATE' and flanked '— OF PARTICIPATION —'
    - Participant name in bold serif with underline
    - Clean 3-line commendation statement
    - Authentic cursive signature, scannable QR verification code, and issue date
    """
    buffer = io.BytesIO()
    target = output_path if output_path else buffer

    w, h = landscape(A4) # 841.89 x 595.28 pt
    c = canvas.Canvas(target, pagesize=landscape(A4))

    # Color palette matching template image
    bronze = colors.HexColor("#8c7355")
    bronze_light = colors.HexColor("#a38c6d")
    bronze_tint = colors.HexColor("#fbf9f6")
    charcoal = colors.HexColor("#18181b")
    body_color = colors.HexColor("#374151")
    gray_caption = colors.HexColor("#6b7280")

    # 1. Clean off-white canvas
    c.setFillColor(colors.HexColor("#ffffff"))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # 2. Outer & Inner Double Borders
    outer_m = 36
    inner_m = 42

    # Draw outer bronze border line
    c.setStrokeColor(bronze)
    c.setLineWidth(1.4)
    c.rect(outer_m, outer_m, w - 2 * outer_m, h - 2 * outer_m, fill=0, stroke=1)

    # Draw inner bronze border line
    c.setStrokeColor(bronze)
    c.setLineWidth(0.7)
    c.rect(inner_m, inner_m, w - 2 * inner_m, h - 2 * inner_m, fill=0, stroke=1)

    # 3. 4 Corner Accent Blocks with Sparkle Stars
    corner_size = 46
    corners = [
        (outer_m, h - outer_m - corner_size),       # Top-Left
        (w - outer_m - corner_size, h - outer_m - corner_size), # Top-Right
        (outer_m, outer_m),                         # Bottom-Left
        (w - outer_m - corner_size, outer_m)        # Bottom-Right
    ]

    for cx, cy in corners:
        # Subtle warm tinted background box
        c.setFillColor(bronze_tint)
        c.rect(cx, cy, corner_size, corner_size, fill=1, stroke=0)
        # Re-stroke border around corner block
        c.setStrokeColor(bronze)
        c.setLineWidth(0.7)
        c.rect(cx, cy, corner_size, corner_size, fill=0, stroke=1)
        # Center 4-pointed sparkle star
        star_x = cx + corner_size / 2
        star_y = cy + corner_size / 2
        draw_sparkle_star(c, star_x, star_y, 8.5, bronze)

    # 4. Top Crest & Institution Brand
    crest_y = h - 74
    draw_top_crest(c, w / 2, crest_y, bronze)

    c.setFillColor(colors.HexColor("#3f3529"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(w / 2, h - 94, "H A C K S P H E R E")

    c.setFillColor(bronze_light)
    c.setFont("Helvetica", 6.8)
    c.drawCentredString(w / 2, h - 105, "ACADEMY & GLOBAL REGISTRY")

    # 5. Header Title: "CERTIFICATE"
    c.setFillColor(charcoal)
    c.setFont("Times-Bold", 40)
    c.drawCentredString(w / 2, h - 156, "CERTIFICATE")

    # 6. Subtitle with Flanked Divider Rules: "— OF PARTICIPATION —"
    sub_text = "O F   P A R T I C I P A T I O N"
    c.setFont("Helvetica", 9.5)
    sub_width = c.stringWidth(sub_text, "Helvetica", 9.5)

    c.setFillColor(bronze)
    c.drawCentredString(w / 2, h - 182, sub_text)

    # Left and right horizontal divider rules
    c.setStrokeColor(bronze)
    c.setLineWidth(0.75)
    rule_len = 55
    rule_gap = 14
    c.line(w / 2 - sub_width / 2 - rule_gap - rule_len, h - 179, w / 2 - sub_width / 2 - rule_gap, h - 179)
    c.line(w / 2 + sub_width / 2 + rule_gap, h - 179, w / 2 + sub_width / 2 + rule_gap + rule_len, h - 179)

    # 7. "PRESENTED TO"
    c.setFillColor(bronze)
    c.setFont("Helvetica-Bold", 7.8)
    c.drawCentredString(w / 2, h - 216, "P R E S E N T E D   T O")

    # 8. Participant Name (Large Serif with Underline)
    display_name = participant_name.strip().upper()
    c.setFillColor(charcoal)
    c.setFont("Times-Bold", 28)
    c.drawCentredString(w / 2, h - 258, display_name)

    # Dynamic underline
    name_w = c.stringWidth(display_name, "Times-Bold", 28)
    line_w = max(name_w + 60, 320)
    c.setStrokeColor(bronze)
    c.setLineWidth(0.85)
    c.line(w / 2 - line_w / 2, h - 270, w / 2 + line_w / 2, h - 270)

    # 9. Commendation / Achievement Statement (3 Elegant Lines)
    c.setFillColor(body_color)
    c.setFont("Helvetica", 9.5)

    stmt_line1 = "For successfully designing, building, and submitting the accepted project"
    c.drawCentredString(w / 2, h - 302, stmt_line1)

    if project_name:
        stmt_line2 = f"'{project_name.strip()}' in {hackathon_title.strip()}"
    else:
        stmt_line2 = f"in {hackathon_title.strip()}"
    
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 319, stmt_line2)

    c.setFillColor(body_color)
    c.setFont("Helvetica", 9.2)
    stmt_line3 = f"conducted on {event_dates}. Your dedication, innovation, and technical excellence are highly appreciated."
    c.drawCentredString(w / 2, h - 336, stmt_line3)

    # 10. Bottom Section: Left (Signature), Center (Scannable QR Code), Right (Date)
    
    # --- Left Column: Organizer Signature ---
    sig_center_x = 165
    sig_line_y = 96
    
    # Vector Cursive Autograph
    draw_signature(c, sig_center_x - 95, sig_line_y + 6, charcoal)
    
    # Divider Rule
    c.setStrokeColor(bronze)
    c.setLineWidth(0.75)
    c.line(sig_center_x - 75, sig_line_y, sig_center_x + 75, sig_line_y)
    
    # Printed Name & Title
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(sig_center_x, sig_line_y - 12, (organizer_name or "Oliver Shaw").upper())
    
    c.setFillColor(gray_caption)
    c.setFont("Helvetica", 7.2)
    c.drawCentredString(sig_center_x, sig_line_y - 23, "DIRECTOR & ORGANIZER")

    # --- Center Column: Vector QR Code for Instant Verification ---
    qr_size = 52
    qr_x = w / 2 - qr_size / 2
    qr_y = 70
    qr_data = verify_url or f"https://hackathon-hub-kappa.vercel.app/verify-certificate/{certificate_code}"

    # Draw QR code
    draw_qr_code(c, qr_x, qr_y, qr_size, qr_data)

    # Top Verification Tag
    c.setFillColor(bronze)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(w / 2, qr_y + qr_size + 7, "OFFICIAL VERIFICATION")

    # Bottom Verification Caption & Certificate ID
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(w / 2, qr_y - 10, "SCAN TO VERIFY CREDENTIAL")

    c.setFillColor(bronze)
    c.setFont("Courier-Bold", 7.2)
    c.drawCentredString(w / 2, qr_y - 20, certificate_code)

    # --- Right Column: Issuance Date ---
    date_center_x = w - 165
    date_line_y = 96

    # Formatted Date
    today_str = datetime.now().strftime("%B %d, %Y").upper()
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawCentredString(date_center_x, date_line_y + 12, today_str)

    # Divider Rule
    c.setStrokeColor(bronze)
    c.setLineWidth(0.75)
    c.line(date_center_x - 75, date_line_y, date_center_x + 75, date_line_y)

    # Date Label
    c.setFillColor(gray_caption)
    c.setFont("Helvetica", 7.2)
    c.drawCentredString(date_center_x, date_line_y - 12, "D A T E")

    c.showPage()
    c.save()

    if output_path:
        return None

    buffer.seek(0)
    return buffer.getvalue()
