import os
import io
import math
import hmac
import hashlib
import json
import base64
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

import zlib

# Secret key for signing verification tokens
_SIGN_SECRET = os.environ.get("SECRET_KEY", "hacksphere-super-secure-production-key-2026")

def get_canonical_base_url(base_url=None) -> str:
    """
    Ensure the base URL in QR codes is always reachable by physical mobile phones.
    If the server was called via localhost or a private LAN IP, use the public canonical URL.
    """
    canonical = "https://hackathon-hub-kappa.vercel.app"
    if not base_url:
        return canonical
    base = base_url.strip().rstrip("/")
    low = base.lower()
    if any(local_kw in low for local_kw in ["localhost", "127.0.0.1", "0.0.0.0", "::", "192.168.", "10.", "172."]):
        return canonical
    if base.startswith("http://"):
        base = "https://" + base[7:]
    return base

def generate_certificate_code() -> str:
    """Generate a unique human-friendly certificate verification code."""
    year = datetime.now().year
    random_part = secrets.token_hex(3).upper()
    return f"HS-{year}-{random_part}"

def build_verify_token(certificate_code, participant_name, hackathon_title,
                        project_name, organizer_name, event_dates, issued_at):
    """
    Build a self-contained signed verification token containing all cert data.
    Uses zlib compression + HMAC signature for a compact QR code that scans instantly.
    """
    issued_date = issued_at[:10] if issued_at else datetime.now().strftime("%Y-%m-%d")
    data = {
        "c": certificate_code,
        "n": participant_name,
        "h": hackathon_title,
        "p": project_name or "",
        "o": organizer_name,
        "d": event_dates,
        "i": issued_date,
    }
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    comp = zlib.compress(raw, level=9)
    sig = hmac.new(_SIGN_SECRET.encode(), comp, hashlib.sha256).digest()[:10]
    token = base64.urlsafe_b64encode(comp + sig).decode().rstrip("=")
    return token

def decode_verify_token(token):
    """
    Decode and verify a self-contained certificate token.
    Supports both compact zlib tokens and legacy uncompressed tokens.
    Returns dict with cert data or None if invalid/tampered.
    """
    if not token:
        return None
    # 1. Try compact zlib token format
    try:
        padded = token + "=" * (4 - len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode())
        if len(raw) > 10:
            comp, sig = raw[:-10], raw[-10:]
            exp = hmac.new(_SIGN_SECRET.encode(), comp, hashlib.sha256).digest()[:10]
            if hmac.compare_digest(sig, exp):
                return json.loads(zlib.decompress(comp).decode("utf-8"))
    except Exception:
        pass

    # 2. Try legacy uncompressed base64 format
    try:
        padded = token + "=" * (4 - len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode("utf-8")
        payload, sig = raw.rsplit("|", 1)
        expected = hmac.new(_SIGN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:24]
        if hmac.compare_digest(sig, expected):
            return json.loads(payload)
    except Exception:
        pass

    return None

def build_verify_url(base_url, certificate_code, participant_name, hackathon_title,
                      project_name, organizer_name, event_dates, issued_at=None):
    """
    Build a self-contained verification URL that works on ANY device without requiring
    login or database lookup. Canonical base URL is enforced for mobile compatibility.
    """
    canonical_base = get_canonical_base_url(base_url)
    token = build_verify_token(
        certificate_code, participant_name, hackathon_title,
        project_name, organizer_name, event_dates, issued_at or datetime.now().strftime("%Y-%m-%d")
    )
    return f"{canonical_base}/verify-certificate/{certificate_code}?t={token}"


# ─────────────────────────────────────────────────────────────────────────────
# Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

def draw_sparkle_star(c, cx, cy, radius, color):
    """Draw a classic 4-pointed luxury sparkle star."""
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
    p_inner = c.beginPath()
    p_inner.moveTo(cx - 5.5, cy - 2.5)
    p_inner.lineTo(cx, cy + 4)
    p_inner.lineTo(cx + 5.5, cy - 2.5)
    c.setLineWidth(1.8)
    c.drawPath(p_inner, fill=0, stroke=1)


def draw_organizer_signature(c, cx_center, y_base, name, color):
    """
    Draw the organizer's actual name in elegant cursive handwriting script.
    Uses TrueType cursive script font bundled with the app, with graceful fallback.
    """
    organizer_text = (name or "Oliver Shaw").strip()
    font_path = os.path.join(os.path.dirname(__file__), "static", "fonts", "Signature.ttf")
    used_ttf = False

    if os.path.exists(font_path):
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            if "SignatureFont" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("SignatureFont", font_path))
            c.setFont("SignatureFont", 22)
            c.setFillColor(color)
            c.drawCentredString(cx_center, y_base + 6, organizer_text)
            used_ttf = True
        except Exception:
            used_ttf = False

    if not used_ttf:
        # Graceful fallback: elegant italic serif script
        c.setFont("Times-BoldItalic", 21)
        c.setFillColor(color)
        c.drawCentredString(cx_center, y_base + 8, organizer_text)


def draw_qr_code(c, x, y, size, data):
    """
    Draw a crisp, high-contrast QR code with a clean white quiet-zone background
    so any smartphone camera can scan it instantly in a fraction of a second.
    """
    # 1. Pure white background card with border for clean scanning contrast
    padding = 5
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(0.75)
    c.rect(x - padding, y - padding, size + 2 * padding, size + 2 * padding, fill=1, stroke=1)

    # 2. Render vector QR code with medium error correction
    qr = QrCodeWidget(data)
    qr.barBorder = 3
    qr.barLevel = 'M'
    bounds = qr.getBounds()
    w_qr = bounds[2] - bounds[0]
    h_qr = bounds[3] - bounds[1]
    d = Drawing(size, size, transform=[size / w_qr, 0, 0, size / h_qr, 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, x, y)


# ─────────────────────────────────────────────────────────────────────────────
# Main Certificate Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_certificate_pdf(
    certificate_code: str,
    participant_name: str,
    hackathon_title: str,
    event_dates: str,
    organizer_name: str,
    project_name: str = None,
    output_path: str = None,
    verify_url: str = None,
    issued_at: str = None,
) -> bytes:
    """
    Generate an official luxury PDF certificate matching the HackSphere template design:
    - Pure white background with warm bronze double-border
    - 4 corner accent blocks with 4-pointed sparkle stars
    - Academy geometric crest at top
    - Bold serif 'CERTIFICATE' header + 'OF PARTICIPATION' subtitle
    - Participant name in bold serif with bronze underline
    - 3-line commendation statement
    - Cursive organizer signature (LEFT), large scannable QR code (CENTER), issue date (RIGHT)
    QR code encodes a self-contained signed verification URL that works without DB lookup.
    """
    buffer = io.BytesIO()
    target = output_path if output_path else buffer

    w, h = landscape(A4)   # 841.89 × 595.28 pt
    c = canvas.Canvas(target, pagesize=landscape(A4))

    # ── Color palette ─────────────────────────────────────────────────────
    bronze       = colors.HexColor("#8c7355")
    bronze_light = colors.HexColor("#a38c6d")
    bronze_tint  = colors.HexColor("#fbf9f6")
    charcoal     = colors.HexColor("#18181b")
    body_color   = colors.HexColor("#374151")
    gray_caption = colors.HexColor("#6b7280")

    # 1. White canvas
    c.setFillColor(colors.HexColor("#ffffff"))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # 2. Double bronze border
    outer_m, inner_m = 36, 43
    c.setStrokeColor(bronze)
    c.setLineWidth(1.5)
    c.rect(outer_m, outer_m, w - 2 * outer_m, h - 2 * outer_m, fill=0, stroke=1)
    c.setLineWidth(0.7)
    c.rect(inner_m, inner_m, w - 2 * inner_m, h - 2 * inner_m, fill=0, stroke=1)

    # 3. 4 Corner accent blocks with sparkle stars
    corner_size = 48
    corners = [
        (outer_m,                       h - outer_m - corner_size),
        (w - outer_m - corner_size,     h - outer_m - corner_size),
        (outer_m,                       outer_m),
        (w - outer_m - corner_size,     outer_m),
    ]
    for bx, by in corners:
        c.setFillColor(bronze_tint)
        c.rect(bx, by, corner_size, corner_size, fill=1, stroke=0)
        c.setStrokeColor(bronze)
        c.setLineWidth(0.7)
        c.rect(bx, by, corner_size, corner_size, fill=0, stroke=1)
        draw_sparkle_star(c, bx + corner_size / 2, by + corner_size / 2, 9, bronze)

    # 4. Top crest + brand
    draw_top_crest(c, w / 2, h - 76, bronze)
    c.setFillColor(colors.HexColor("#3f3529"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(w / 2, h - 96, "H A C K S P H E R E")
    c.setFillColor(bronze_light)
    c.setFont("Helvetica", 6.8)
    c.drawCentredString(w / 2, h - 107, "ACADEMY  &  GLOBAL REGISTRY")

    # 5. "CERTIFICATE" bold serif headline
    c.setFillColor(charcoal)
    c.setFont("Times-Bold", 40)
    c.drawCentredString(w / 2, h - 158, "CERTIFICATE")

    # 6. "OF PARTICIPATION" subtitle flanked by horizontal rules
    sub_text = "O F   P A R T I C I P A T I O N"
    c.setFont("Helvetica", 9.5)
    sub_w = c.stringWidth(sub_text, "Helvetica", 9.5)
    c.setFillColor(bronze)
    c.drawCentredString(w / 2, h - 184, sub_text)
    c.setStrokeColor(bronze)
    c.setLineWidth(0.75)
    rule_len, rule_gap = 58, 14
    rule_y = h - 181
    c.line(w/2 - sub_w/2 - rule_gap - rule_len, rule_y, w/2 - sub_w/2 - rule_gap, rule_y)
    c.line(w/2 + sub_w/2 + rule_gap, rule_y, w/2 + sub_w/2 + rule_gap + rule_len, rule_y)

    # 7. "PRESENTED TO" small label
    c.setFillColor(bronze)
    c.setFont("Helvetica-Bold", 7.8)
    c.drawCentredString(w / 2, h - 218, "P R E S E N T E D   T O")

    # 8. Participant name (large serif) + underline
    display_name = participant_name.strip().upper()
    c.setFillColor(charcoal)
    c.setFont("Times-Bold", 29)
    c.drawCentredString(w / 2, h - 260, display_name)
    name_w = c.stringWidth(display_name, "Times-Bold", 29)
    line_w = max(name_w + 70, 330)
    c.setStrokeColor(bronze)
    c.setLineWidth(0.9)
    c.line(w/2 - line_w/2, h - 272, w/2 + line_w/2, h - 272)

    # 9. Commendation body — 3 lines
    c.setFillColor(body_color)
    c.setFont("Helvetica", 9.5)
    c.drawCentredString(w/2, h - 304, "For successfully designing, building, and submitting the accepted project")

    if project_name:
        line2 = f"'{project_name.strip()}'  in  {hackathon_title.strip()}"
    else:
        line2 = f"in  {hackathon_title.strip()}"
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w/2, h - 321, line2)

    c.setFillColor(body_color)
    c.setFont("Helvetica", 9.2)
    c.drawCentredString(
        w/2, h - 338,
        f"conducted on {event_dates}.  Your dedication, innovation, and excellence are highly appreciated."
    )

    # ── 10. Bottom Row: Left=Signature, Center=QR Code, Right=Date ────────────

    bottom_y = 52   # baseline of bottom content area

    # ── LEFT: Cursive organizer signature ──────────────────────────────────
    sig_cx = 165
    sig_line_y = bottom_y + 46

    # Draw the organizer's name in cursive handwriting
    draw_organizer_signature(c, sig_cx, sig_line_y + 5, organizer_name, charcoal)

    # Signature underline rule
    c.setStrokeColor(bronze)
    c.setLineWidth(0.75)
    c.line(sig_cx - 80, sig_line_y, sig_cx + 80, sig_line_y)

    # Printed name below line
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(sig_cx, sig_line_y - 13, (organizer_name or "Organizer").upper())

    c.setFillColor(gray_caption)
    c.setFont("Helvetica", 7.2)
    c.drawCentredString(sig_cx, sig_line_y - 24, "DIRECTOR  &  ORGANIZER")

    # ── CENTER: Large scannable QR Code (enlarged for instant 1-scan detection) ──
    qr_size = 80
    qr_x = w / 2 - qr_size / 2
    qr_y = bottom_y + 10

    # Build self-contained verify URL (works even if DB is empty on this Lambda)
    issued_date = issued_at or datetime.now().strftime("%Y-%m-%d")
    if verify_url:
        qr_data = verify_url
    else:
        # Build signed self-contained token URL
        from certificates import build_verify_url as _bvu
        qr_data = _bvu(
            "https://hackathon-hub-kappa.vercel.app",
            certificate_code, participant_name, hackathon_title,
            project_name, organizer_name, event_dates, issued_date
        )

    draw_qr_code(c, qr_x, qr_y, qr_size, qr_data)

    # "OFFICIAL VERIFICATION" tag above QR
    c.setFillColor(bronze)
    c.setFont("Helvetica-Bold", 7.0)
    c.drawCentredString(w/2, qr_y + qr_size + 8, "OFFICIAL VERIFICATION")

    # Caption and code below QR
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(w/2, qr_y - 11, "SCAN TO VERIFY CREDENTIAL")
    c.setFillColor(bronze)
    c.setFont("Courier-Bold", 7.5)
    c.drawCentredString(w/2, qr_y - 21, certificate_code)

    # ── RIGHT: Issue Date ───────────────────────────────────────────────────
    date_cx = w - 165
    date_line_y = bottom_y + 46
    today_str = datetime.now().strftime("%B %d, %Y").upper()
    c.setFillColor(charcoal)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawCentredString(date_cx, date_line_y + 12, today_str)
    c.setStrokeColor(bronze)
    c.setLineWidth(0.75)
    c.line(date_cx - 80, date_line_y, date_cx + 80, date_line_y)
    c.setFillColor(gray_caption)
    c.setFont("Helvetica", 7.2)
    c.drawCentredString(date_cx, date_line_y - 12, "D A T E")

    c.showPage()
    c.save()

    if output_path:
        return None

    buffer.seek(0)
    return buffer.getvalue()
