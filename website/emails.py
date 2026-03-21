from flask_mail import Message
from . import mail


# ─────────────────────────────────────────────
#  INTERNAL SENDER
# ─────────────────────────────────────────────
def _send(subject, to_email, html_body):
    msg = Message(subject=subject, recipients=[to_email], html=html_body)
    mail.send(msg)


# ─────────────────────────────────────────────
#  BASE HTML TEMPLATE
# ─────────────────────────────────────────────
def _base_email(subtitle, header_color, icon, body_html):
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f0;margin:0;padding:0;}}
.wrap{{max-width:600px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);}}
.hdr{{background:{header_color};padding:30px 40px;text-align:center;}}
.hdr .ic{{font-size:42px;}}
.hdr h1{{color:#fff;margin:10px 0 0;font-size:21px;font-weight:700;}}
.hdr p{{color:rgba(255,255,255,0.85);margin:5px 0 0;font-size:13px;}}
.body{{padding:30px 40px;color:#2d3a2e;}}
.box{{background:#f8faf6;border:1px solid #d4e8d0;border-radius:8px;padding:16px 20px;margin:16px 0;}}
.box h3{{margin:0 0 11px;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#6b8f6e;}}
.row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #e8f0e6;font-size:14px;}}
.row:last-child{{border-bottom:none;}}
.row.tot{{font-weight:700;font-size:15px;color:#1a5c2a;}}
.lbl{{color:#5a7a5d;}}
.badge{{display:inline-block;padding:4px 13px;border-radius:20px;font-size:12px;font-weight:600;letter-spacing:0.4px;margin-bottom:13px;}}
.tracking-box{{background:#e8f4fd;border:2px solid #3b82f6;border-radius:10px;padding:18px 24px;margin:16px 0;text-align:center;}}
.tracking-box h3{{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#1e40af;}}
.tracking-id{{font-size:26px;font-weight:800;color:#1e40af;letter-spacing:3px;font-family:monospace;}}
.note{{background:#fffbeb;border-left:4px solid #f59e0b;padding:11px 15px;border-radius:0 6px 6px 0;font-size:13px;color:#92400e;margin-top:14px;}}
.note-g{{background:#f0faf4;border-left:4px solid #2db96a;padding:11px 15px;border-radius:0 6px 6px 0;font-size:13px;color:#1a5c2a;margin-top:14px;}}
.ftr{{background:#f8faf6;padding:20px 40px;text-align:center;font-size:12px;color:#8fa890;border-top:1px solid #e8f0e6;}}
.ftr strong{{color:#4a7a50;}}
p{{line-height:1.7;font-size:15px;color:#3a4a3b;margin:0 0 10px;}}
</style></head>
<body><div class="wrap">
  <div class="hdr"><div class="ic">{icon}</div><h1>GreenMart</h1><p>{subtitle}</p></div>
  <div class="body">{body_html}</div>
  <div class="ftr">
    <strong>GreenMart</strong> — Fresh Groceries Delivered<br>
    Help? <a href="mailto:greenmartatshopping@gmail.com" style="color:#2db96a;">greenmartatshopping@gmail.com</a><br><br>
    © 2025 GreenMart. All rights reserved.
  </div>
</div></body></html>"""


# ─────────────────────────────────────────────
#  ORDER ITEMS
# ─────────────────────────────────────────────
def _items_rows(order_items):
    rows = ""
    for item in order_items:
        name  = item.product.name if item.product else f"Product #{item.product_id}"
        rows += f'<div class="row"><span class="lbl">{name} × {item.quantity}</span><span>₹{item.price * item.quantity:.2f}</span></div>'
    return rows


# ─────────────────────────────────────────────
#  SHIPPING ADDRESS
# ─────────────────────────────────────────────
def _address_block(order):
    return f"""<div class="box"><h3>Delivery Address</h3>
    <div class="row"><span class="lbl">Name</span><span>{order.shipping_name}</span></div>
    <div class="row"><span class="lbl">Phone</span><span>{order.shipping_phone}</span></div>
    <div class="row"><span class="lbl">Address</span><span style="text-align:right">{order.shipping_street}, {order.shipping_city}, {order.shipping_state} — {order.shipping_pin}</span></div>
    </div>"""


# ═══════════════════════════════════════════════════════════
#  1. ORDER CONFIRMED
# ═══════════════════════════════════════════════════════════
def send_order_confirmed(order):
    pay = "Cash on Delivery" if order.payment_method == "cod" else "UPI"
    tracking_html = f'<div class="tracking-box"><h3>🔍 Your Tracking ID</h3><div class="tracking-id">{order.tracking_id}</div><p style="margin:8px 0 0;font-size:12px;color:#1e40af;">Use this ID to track your order status</p></div>' if order.tracking_id else ""
    body = f"""
    <span class="badge" style="background:#d4f0df;color:#1a5c2a;">✅ Order Confirmed</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your order has been <strong>confirmed</strong> and is being prepared. 🌿</p>
    {tracking_html}
    <div class="box">
      <h3>Order #{order.id} — {order.created_at.strftime('%d %b %Y, %I:%M %p')}</h3>
      {_items_rows(order.items)}
      <div class="row tot"><span>Total</span><span>₹{order.total_amount:.2f}</span></div>
    </div>
    <div class="row" style="padding:6px 0;font-size:14px;"><span class="lbl">Payment</span><span><strong>{pay}</strong></span></div>
    {_address_block(order)}
    <div class="note-g">We'll notify you when your order is out for delivery!</div>
    """
    _send(f"GreenMart Order #{order.id} Confirmed! 🎉", order.user.email,
          _base_email("Order Confirmed!", "#2db96a", "🛒", body))


# ═══════════════════════════════════════════════════════════
#  2. ORDER CANCELLED
# ═══════════════════════════════════════════════════════════
def send_order_cancelled(order):
    reason_html = f'<div class="row"><span class="lbl">Reason</span><span>{order.cancel_reason}</span></div>' if order.cancel_reason else ""
    note_html   = f'<div class="row"><span class="lbl">Note</span><span>{order.cancel_note}</span></div>'   if order.cancel_note   else ""
    time_html   = f'<div class="row"><span class="lbl">Cancelled At</span><span>{order.cancelled_at.strftime("%d %b %Y, %I:%M %p")}</span></div>' if order.cancelled_at else ""
    refund_html = '<div class="note">Since you paid online, your <strong>refund will be processed within 5–7 business days</strong>.</div>' if order.payment_status == "Paid" else ""
    body = f"""
    <span class="badge" style="background:#fee2e2;color:#991b1b;">❌ Order Cancelled</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your order <strong>#{order.id}</strong> has been <strong>cancelled</strong>.</p>
    <div class="box">
      <h3>Cancellation Details</h3>
      {reason_html}{note_html}{time_html}
    </div>
    <div class="box">
      <h3>Order Summary</h3>
      {_items_rows(order.items)}
      <div class="row tot"><span>Total</span><span>₹{order.total_amount:.2f}</span></div>
    </div>
    {refund_html}
    <p>We'd love to serve you again — shop anytime. 💚</p>
    """
    _send(f"GreenMart Order #{order.id} Cancelled", order.user.email,
          _base_email("Order Cancelled", "#ef4444", "❌", body))


# ═══════════════════════════════════════════════════════════
#  3. OUT FOR DELIVERY  ✅ Tracking ID included
# ═══════════════════════════════════════════════════════════
def send_order_shipped(order):
    tracking_id = order.tracking_id or "N/A"
    body = f"""
    <span class="badge" style="background:#dbeafe;color:#1e40af;">🚚 Out for Delivery</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your GreenMart order is <strong>on its way</strong> to you! 🛵</p>

    <div class="tracking-box">
      <h3>🔍 Your Tracking ID</h3>
      <div class="tracking-id">{tracking_id}</div>
      <p style="margin:8px 0 0;font-size:12px;color:#1e40af;">Use this ID if you need to contact support about your delivery</p>
    </div>

    <div class="box">
      <h3>Delivery Details</h3>
      <div class="row"><span class="lbl">Order ID</span><span>ORD{order.id}</span></div>
      <div class="row"><span class="lbl">Tracking ID</span><span><strong>{tracking_id}</strong></span></div>
      <div class="row"><span class="lbl">Estimated Arrival</span><span>Today</span></div>
    </div>
    {_address_block(order)}
    <div class="note">Keep your phone handy — agent may call on <strong>{order.shipping_phone}</strong>.</div>
    """
    _send(f"GreenMart Order #{order.id} is Out for Delivery! 🚚", order.user.email,
          _base_email("Your Order is On the Way!", "#3b82f6", "🚚", body))


# ═══════════════════════════════════════════════════════════
#  4. ORDER DELIVERED
# ═══════════════════════════════════════════════════════════
def send_order_delivered(order):
    body = f"""
    <span class="badge" style="background:#d4f0df;color:#1a5c2a;">🎉 Delivered!</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your order has been <strong>delivered successfully</strong>. Enjoy your fresh groceries! 🥦🍅🥕</p>
    <div class="box">
      <h3>Order #{order.id} — Delivered</h3>
      {_items_rows(order.items)}
      <div class="row tot"><span>Total Paid</span><span>₹{order.total_amount:.2f}</span></div>
    </div>
    <div class="note">Issue with your order? Contact us within <strong>24 hours</strong> for hassle-free support.</div>
    <p style="margin-top:14px;">Loved shopping with us? See you again! 💚</p>
    """
    _send(f"GreenMart Order #{order.id} Delivered! 🎉", order.user.email,
          _base_email("Order Delivered!", "#16a34a", "🎉", body))


# ═══════════════════════════════════════════════════════════
#  5. REFUND INITIATED
# ═══════════════════════════════════════════════════════════
def send_refund_initiated(order, refund_amount=None, refund_method="Original Payment Source"):
    amount = refund_amount if refund_amount is not None else order.total_amount
    body = f"""
    <span class="badge" style="background:#fef3c7;color:#92400e;">💰 Refund Initiated</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your refund for Order <strong>#{order.id}</strong> has been <strong>initiated</strong>.</p>
    <div class="box">
      <h3>Refund Details</h3>
      <div class="row"><span class="lbl">Order ID</span><span>#{order.id}</span></div>
      <div class="row"><span class="lbl">Refund Amount</span><span>₹{amount:.2f}</span></div>
      <div class="row"><span class="lbl">Refund To</span><span>{refund_method}</span></div>
      <div class="row tot"><span>Processing Time</span><span>5–7 Business Days</span></div>
    </div>
    <div class="note">Timeline may vary slightly by your bank or payment provider.</div>
    """
    _send(f"GreenMart Refund of ₹{amount:.2f} Initiated — Order #{order.id}", order.user.email,
          _base_email("Refund Initiated", "#f59e0b", "💰", body))


# ═══════════════════════════════════════════════════════════
#  6. REFUND COMPLETED
# ═══════════════════════════════════════════════════════════
def send_refund_completed(order, refund_amount=None, refund_method="Original Payment Source"):
    amount = refund_amount if refund_amount is not None else order.total_amount
    body = f"""
    <span class="badge" style="background:#d4f0df;color:#1a5c2a;">✅ Refund Completed</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your refund of <strong>₹{amount:.2f}</strong> has been <strong>successfully credited</strong>. 🎉</p>
    <div class="box">
      <h3>Refund Summary</h3>
      <div class="row"><span class="lbl">Order ID</span><span>#{order.id}</span></div>
      <div class="row"><span class="lbl">Amount Credited</span><span>₹{amount:.2f}</span></div>
      <div class="row tot"><span>Credited To</span><span>{refund_method}</span></div>
    </div>
    <p style="margin-top:14px;">We hope to see you back on GreenMart soon. 🌿</p>
    """
    _send(f"GreenMart: ₹{amount:.2f} Refunded — Order #{order.id}", order.user.email,
          _base_email("Refund Completed!", "#2db96a", "✅", body))


# ═══════════════════════════════════════════════════════════
#  7. UPI PAYMENT CONFIRMED
# ═══════════════════════════════════════════════════════════
def send_payment_confirmed(order):
    utr_html = f'<div class="row"><span class="lbl">UTR Number</span><span>{order.utr_number}</span></div>' if order.utr_number else ""
    tracking_html = f'<div class="row"><span class="lbl">Tracking ID</span><span><strong>{order.tracking_id}</strong></span></div>' if order.tracking_id else ""
    body = f"""
    <span class="badge" style="background:#d4f0df;color:#1a5c2a;">💳 Payment Verified</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your UPI payment for Order <strong>#{order.id}</strong> has been <strong>verified by our team</strong>.</p>
    <div class="box">
      <h3>Payment Details</h3>
      <div class="row"><span class="lbl">Order ID</span><span>#{order.id}</span></div>
      <div class="row"><span class="lbl">Amount Paid</span><span>₹{order.total_amount:.2f}</span></div>
      <div class="row"><span class="lbl">Method</span><span>UPI</span></div>
      {utr_html}
      {tracking_html}
      <div class="row tot"><span>Status</span><span>✅ Paid</span></div>
    </div>
    <div class="note-g">Your order is now confirmed and being prepared!</div>
    """
    _send(f"GreenMart Payment Verified — Order #{order.id} 💳", order.user.email,
          _base_email("Payment Confirmed!", "#2db96a", "💳", body))


# ═══════════════════════════════════════════════════════════
#  8. ORDER ON HOLD
# ═══════════════════════════════════════════════════════════
def send_order_on_hold(order, reason="Pending payment verification"):
    body = f"""
    <span class="badge" style="background:#fef3c7;color:#92400e;">⏸ Order On Hold</span>
    <p>Hi <strong>{order.shipping_name}</strong>,</p>
    <p>Your order <strong>#{order.id}</strong> has been placed <strong>on hold</strong>.</p>
    <div class="box">
      <h3>Hold Details</h3>
      <div class="row"><span class="lbl">Order ID</span><span>#{order.id}</span></div>
      <div class="row"><span class="lbl">Reason</span><span>{reason}</span></div>
      <div class="row tot"><span>Amount</span><span>₹{order.total_amount:.2f}</span></div>
    </div>
    <div class="note">Your items are reserved. Please <a href="mailto:greenmartatshopping@gmail.com" style="color:#b45309;">contact support</a> to resolve quickly.</div>
    """
    _send(f"GreenMart Order #{order.id} On Hold — Action Needed", order.user.email,
          _base_email("Order On Hold", "#f59e0b", "⏸", body))


# ═══════════════════════════════════════════════════════════
#  9. WELCOME EMAIL
# ═══════════════════════════════════════════════════════════
def send_welcome_email(user):
    body = f"""
    <span class="badge" style="background:#d4f0df;color:#1a5c2a;">🌿 Welcome!</span>
    <p>Hi <strong>{user.name}</strong>,</p>
    <p>Welcome to <strong>GreenMart</strong> — fresh, quality groceries delivered to your door! 🥕🥦🍋</p>
    <div class="box">
      <h3>What Awaits You</h3>
      <div class="row"><span class="lbl">🛒 Fresh Products</span><span>1000+ items</span></div>
      <div class="row"><span class="lbl">🚚 Fast Delivery</span><span>Same-day available</span></div>
      <div class="row"><span class="lbl">💳 Easy Payments</span><span>COD &amp; UPI</span></div>
      <div class="row"><span class="lbl">🔄 Easy Returns</span><span>Hassle-free</span></div>
    </div>
    <p>Start filling your cart with freshness! 💚</p>
    """
    _send("Welcome to GreenMart — Let's Get Fresh! 🌿", user.email,
          _base_email("Welcome to GreenMart!", "#2db96a", "🌿", body))