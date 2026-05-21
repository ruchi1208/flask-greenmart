"""
GreenMart — Unique Thermal POS Receipt
Replace the pos_invoice route in views.py with this function
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode
import io
from datetime import datetime


def generate_pos_receipt(order, customer_name):
    """
    Generate a unique attractive thermal POS receipt.
    Returns a BytesIO buffer containing the PDF.
    """

    # ── Page setup ──────────────────────────────────────────
    PAGE_W   = 80 * mm
    MARGIN   = 6 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN

    # Calculate dynamic height
    base_height  = 180 * mm
    per_item     = 7 * mm
    item_count   = len(order.items)
    PAGE_H       = base_height + (item_count * per_item)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))

    # Colors
    GREEN_DARK   = colors.HexColor("#1a5c2a")
    GREEN_MID    = colors.HexColor("#2db96a")
    GREEN_LIGHT  = colors.HexColor("#d4f0df")
    GRAY_DARK    = colors.HexColor("#333333")
    GRAY_MID     = colors.HexColor("#666666")
    GRAY_LIGHT   = colors.HexColor("#f5f5f5")
    WHITE        = colors.white

    y = PAGE_H  # Start from top

    # ── 1. GREEN HEADER BANNER ───────────────────────────────
    c.setFillColor(GREEN_DARK)
    c.rect(0, y - 28*mm, PAGE_W, 28*mm, fill=1, stroke=0)

    # Leaf emoji row
    c.setFillColor(GREEN_MID)
    c.setFont("Helvetica-Bold", 8)
    leaves = "🌿  🌿  🌿  🌿  🌿  🌿  🌿"
    c.drawCentredString(PAGE_W/2, y - 6*mm, leaves)

    # GreenMart title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W/2, y - 13*mm, "GreenMart")

    # Tagline
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(GREEN_LIGHT)
    c.drawCentredString(PAGE_W/2, y - 18*mm, "Fresh. Organic. Delivered.")

    # Website
    c.setFont("Helvetica", 6)
    c.setFillColor(GREEN_LIGHT)
    c.drawCentredString(PAGE_W/2, y - 23*mm, "greenmartatshopping@gmail.com")

    y -= 30*mm

    # ── 2. DOTTED SEPARATOR ─────────────────────────────────
    c.setStrokeColor(GREEN_MID)
    c.setLineWidth(0.5)
    c.setDash(2, 2)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setDash()
    y -= 6*mm

    # ── 3. ORDER INFO BOX ───────────────────────────────────
    c.setFillColor(GRAY_LIGHT)
    c.roundRect(MARGIN, y - 22*mm, CONTENT_W, 22*mm, 2*mm, fill=1, stroke=0)

    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 3*mm, y - 5*mm, f"ORDER  #ORD{order.id}")

    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_MID)
    c.drawString(MARGIN + 3*mm, y - 9*mm,
                 f"Date: {order.created_at.strftime('%d %b %Y  %I:%M %p')}")
    c.drawString(MARGIN + 3*mm, y - 13*mm,
                 f"Tracking: {order.tracking_id or 'N/A'}")
    c.drawString(MARGIN + 3*mm, y - 17*mm,
                 f"Payment: {'Cash on Delivery' if order.payment_method == 'cod' else 'UPI'}")
    c.drawString(MARGIN + 3*mm, y - 21*mm,
                 f"Status: {order.status}")

    y -= 25*mm

    # ── 4. CUSTOMER INFO ────────────────────────────────────
    c.setFillColor(GREEN_DARK)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN, y, "CUSTOMER")
    y -= 4*mm

    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGIN, y, customer_name)
    y -= 4*mm

    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAY_MID)

    # Street — 38 chars per line
    street   = order.shipping_street
    max_ch   = 38
    if len(street) > max_ch:
        c.drawString(MARGIN, y, street[:max_ch])
        y -= 4*mm
        c.drawString(MARGIN, y, street[max_ch:max_ch*2])
    else:
        c.drawString(MARGIN, y, street)
    y -= 4*mm

    # City — અલગ line
    c.drawString(MARGIN, y, order.shipping_city)
    y -= 4*mm

    # State + Pin — અલગ line
    c.drawString(MARGIN, y, f"{order.shipping_state} — {order.shipping_pin}")
    y -= 4*mm

    # Phone
    c.drawString(MARGIN, y, f"Ph: {order.shipping_phone}")
    y -= 6*mm

    # ── 5. ITEMS HEADER ─────────────────────────────────────
    c.setFillColor(GREEN_DARK)
    c.rect(MARGIN, y - 5*mm, CONTENT_W, 5*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MARGIN + 2*mm, y - 3.5*mm, "ITEM")
    c.drawRightString(PAGE_W - MARGIN - 2*mm, y - 3.5*mm, "AMOUNT")
    c.drawCentredString(PAGE_W/2, y - 3.5*mm, "QTY")
    y -= 6*mm

    # ── 6. ITEMS LIST ───────────────────────────────────────
    subtotal = 0
    for i, item in enumerate(order.items):
        name  = item.product.name if item.product else f"Product #{item.product_id}"
        total = item.price * item.quantity
        subtotal += total

        # Alternate row shading
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#f9fdf9"))
            c.rect(MARGIN, y - 6*mm, CONTENT_W, 6*mm, fill=1, stroke=0)

        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica", 7)
        # Truncate long names
        display_name = name[:22] + ".." if len(name) > 22 else name
        c.drawString(MARGIN + 2*mm, y - 4*mm, display_name)

        c.setFont("Helvetica", 7)
        c.drawCentredString(PAGE_W/2, y - 4*mm, f"x{item.quantity}")

        c.setFont("Helvetica-Bold", 7)
        c.drawRightString(PAGE_W - MARGIN - 2*mm, y - 4*mm, f"Rs.{total:.2f}")

        # Unit price below
        c.setFont("Helvetica", 6)
        c.setFillColor(GRAY_MID)
        c.drawString(MARGIN + 2*mm, y - 7.5*mm, f"  Rs.{item.price:.2f} each")

        y -= 8*mm

    y -= 2*mm

    # ── 7. DOTTED LINE ──────────────────────────────────────
    c.setStrokeColor(GRAY_MID)
    c.setDash(1, 2)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setDash()
    y -= 4*mm

    # ── 8. TOTALS ───────────────────────────────────────────
    tax       = round(subtotal * 0.05, 2)
    grand     = subtotal + tax

    # Subtotal
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY_MID)
    c.drawString(MARGIN, y, "Subtotal")
    c.drawRightString(PAGE_W - MARGIN, y, f"Rs.{subtotal:.2f}")
    y -= 5*mm

    # GST
    c.drawString(MARGIN, y, "GST (5%)")
    c.drawRightString(PAGE_W - MARGIN, y, f"Rs.{tax:.2f}")
    y -= 5*mm

    # TOTAL — highlighted
    c.setFillColor(GREEN_DARK)
    c.rect(MARGIN, y - 7*mm, CONTENT_W, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 3*mm, y - 4.5*mm, "TOTAL")
    c.drawRightString(PAGE_W - MARGIN - 3*mm, y - 4.5*mm, f"Rs.{grand:.2f}")
    y -= 10*mm

    # # ── 9. QR CODE ──────────────────────────────────────────
    # y -= 2*mm
    # tracking = order.tracking_id or f"ORD{order.id}"
    # qr = qrcode.QRCode(version=1,
    #                    error_correction=qrcode.constants.ERROR_CORRECT_H,
    #                    box_size=4, border=2)
    # qr.add_data(f"GreenMart Order: {tracking}")
    # qr.make(fit=True)
    # qr_img    = qr.make_image(fill_color="#1a5c2a", back_color="white")
    # qr_buffer = io.BytesIO()
    # qr_img.save(qr_buffer, format="PNG")
    # qr_buffer.seek(0)

    # qr_size = 18*mm
    # qr_x    = (PAGE_W - qr_size) / 2
    # c.drawImage(ImageReader(qr_buffer), qr_x, y - qr_size,
    #             width=qr_size, height=qr_size)

    # c.setFont("Helvetica", 6)
    # c.setFillColor(GRAY_MID)
    # c.drawCentredString(PAGE_W/2, y - qr_size - 3*mm, "Scan to track your order")
    # y -= qr_size + 6*mm

    # # ── 10. SAVINGS BADGE ───────────────────────────────────
    # c.setFillColor(colors.HexColor("#fff9e6"))
    # c.roundRect(MARGIN, y - 8*mm, CONTENT_W, 8*mm, 2*mm, fill=1, stroke=0)
    # c.setStrokeColor(colors.HexColor("#f59e0b"))
    # c.roundRect(MARGIN, y - 8*mm, CONTENT_W, 8*mm, 2*mm, fill=0, stroke=1)
    # c.setFillColor(colors.HexColor("#92400e"))
    # c.setFont("Helvetica-Bold", 7)
    # c.drawCentredString(PAGE_W/2, y - 5*mm,
    #                     f"You saved Rs.{tax:.2f} with GreenMart today!")
    # y -= 11*mm

    # # ── 11. OFFER STRIP ─────────────────────────────────────
    # c.setFillColor(GREEN_MID)
    # c.rect(0, y - 8*mm, PAGE_W, 8*mm, fill=1, stroke=0)
    # c.setFillColor(WHITE)
    # c.setFont("Helvetica-Bold", 7)
    # c.drawCentredString(PAGE_W/2, y - 5*mm,
    #                     "Next Order: Use code FRESH10 for 10% off!")
    # y -= 11*mm

    # ── 12. THANK YOU MESSAGE ───────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GREEN_DARK)
    c.drawCentredString(PAGE_W/2, y, "Thank You for Shopping!")
    y -= 5*mm

    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(PAGE_W/2, y, "Your freshness matters to us 💚")
    y -= 5*mm

    c.setFont("Helvetica", 6.5)
    c.drawCentredString(PAGE_W/2, y, "Mon-Sun: 8:00 AM - 10:00 PM")
    y -= 4*mm
    c.drawCentredString(PAGE_W/2, y, "+1800090098")
    y -= 6*mm

    # ── 13. BOTTOM WAVE DESIGN ──────────────────────────────
    c.setFillColor(GREEN_DARK)
    c.rect(0, 0, PAGE_W, 6*mm, fill=1, stroke=0)
    c.setFillColor(GREEN_MID)
    c.setFont("Helvetica", 7)
    c.setFillColor(WHITE)
    c.drawCentredString(PAGE_W/2, 2*mm, "🌿 GreenMart — Fresh & Organic 🌿")

    c.save()
    buffer.seek(0)
    return buffer