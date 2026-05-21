from flask import Blueprint, render_template, redirect, url_for, flash, request
from functools import wraps
from werkzeug.utils import secure_filename
import os
from .forms import CategoryForm
from .models import Category, Product
from flask_login import login_user, logout_user, login_required, current_user
from .forms import SettingsForm
from .models import db, User, Product, Order
from .forms import ShopItemsForm, LoginForm, SignupForm
from .models import Category
from datetime import datetime
from .models import db, User, Product, Order, Coupon, DeliveryZone
from .models import ContactMessage
from .models import NewsletterSubscriber
from flask_mail import Message
from . import mail
import csv, io
from flask import make_response
from .models import Testimonial, RewardWallet, RewardTransaction, TestimonialRewardConfig, FlashSale, FlashSaleItem
from . import csrf
from .models import ProductSale
from .models import BundleGroup, BundleItem, ProductVariant
# ✅ EMAIL IMPORTS
from .emails import (
    send_order_confirmed,
    send_order_cancelled,
    send_payment_confirmed,
    send_order_shipped,
    send_order_delivered,
)

admin = Blueprint("admin", __name__)


# ---------------- Admin access decorator ----------------
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required!")
            return redirect(url_for("views.home"))
        return f(*args, **kwargs)

    return decorated_function


# ---------------- Admin Login ----------------
@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            else:
                flash("You are not an admin!")
                return redirect(url_for("views.home"))

        flash("Invalid credentials!")

    return render_template("login.html")


# ---------------- Admin Logout ----------------
@admin.route("/logout")
@login_required
def logout():
    login_form = LoginForm()
    signup_form = SignupForm()
    logout_user()
    flash("Logged out successfully!")
    return redirect(url_for("admin.login"))

# ── Subscribers List ──────────────────────────────────────────────
@admin.route('/newsletter')
@admin_required
def newsletter():
    subscribers = NewsletterSubscriber.query\
                    .order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    total       = len(subscribers)
    active      = sum(1 for s in subscribers if s.is_active)
    unique      = len(set(s.email for s in subscribers))  # always == total (unique constraint)
    return render_template('admin/newsletter.html',
                           subscribers=subscribers,
                           total=total, active=active, unique=unique)

# ── Delete Subscriber ─────────────────────────────────────────────
@admin.route('/newsletter/delete/<int:sub_id>', methods=['POST'])
@admin_required
def delete_subscriber(sub_id):
    sub = NewsletterSubscriber.query.get_or_404(sub_id)
    db.session.delete(sub)
    db.session.commit()
    flash('Subscriber deleted!', 'danger')
    return redirect(url_for('admin.newsletter'))

# ── Export CSV ────────────────────────────────────────────────────
@admin.route('/newsletter/export')
@admin_required
def export_subscribers():
    subscribers = NewsletterSubscriber.query.filter_by(is_active=True)\
                    .order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['#', 'Email', 'Status', 'Subscribed At'])
    for i, s in enumerate(subscribers, 1):
        writer.writerow([
            i, s.email,
            'Active' if s.is_active else 'Inactive',
            s.subscribed_at.strftime('%d-%m-%Y %H:%M')
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=greenmart_subscribers.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

# ── Bulk Email Send ───────────────────────────────────────────────
@admin.route('/newsletter/send', methods=['POST'])
@admin_required
def send_newsletter():
    subject = request.form.get('subject', '').strip()
    content = request.form.get('content', '').strip()

    if not subject or not content:
        flash('Subject અને Content જરૂરી છે!', 'danger')
        return redirect(url_for('admin.newsletter'))

    # ✅ Unique emails only
    subscribers = NewsletterSubscriber.query.filter_by(is_active=True).all()
    unique_emails = list({s.email for s in subscribers})  # set removes duplicates

    if not unique_emails:
        flash('કોઈ active subscribers નથી!', 'warning')
        return redirect(url_for('admin.newsletter'))

    success_count = 0
    fail_count    = 0

    for email in unique_emails:
        try:
            msg = Message(subject=subject, recipients=[email])
            msg.html = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;
                        border-radius:12px;overflow:hidden;border:1px solid #e0e0e0;">
                <div style="background:linear-gradient(135deg,#1a4a22,#2e7d32);
                            padding:28px;text-align:center;">
                    <h1 style="color:white;margin:0;font-size:24px;">🌿 GreenMart</h1>
                    <p style="color:#a5d6a7;margin:4px 0 0;">Fresh & Organic Newsletter</p>
                </div>
                <div style="padding:32px;background:#fff;">
                    <h2 style="color:#2e7d32;">{subject}</h2>
                    <div style="color:#555;line-height:1.8;">{content}</div>
                </div>
                <div style="background:#f5f5f5;padding:16px;text-align:center;">
                    <p style="color:#888;font-size:12px;margin:0;">
                        © 2026 GreenMart &nbsp;|&nbsp;
                        <a href="#" style="color:#2e7d32;">Unsubscribe</a>
                    </p>
                </div>
            </div>"""
            mail.send(msg)
            success_count += 1
        except Exception as e:
            print(f"Send Error ({email}): {e}")
            fail_count += 1

    flash(f'✅ Sent: {success_count} | ❌ Failed: {fail_count} | Total unique: {len(unique_emails)}', 'success')
    return redirect(url_for('admin.newsletter'))


# ---------------- Admin Dashboard ----------------
@admin.route("/dashboard")
@admin_required
def dashboard():
    users = User.query.count()
    products = Product.query.count()
    orders = Order.query.count()
    categories = Category.query.all()

    login_form = LoginForm()
    signup_form = SignupForm()

    return render_template(
        "dashboard.html",
        users=users,
        products=products,
        orders=orders,
        login_form=login_form,
        signup_form=signup_form,
    )


# ---------------- Manage Users ----------------
@admin.route("/admin/users")
@admin_required
def manage_users():
    users = User.query.all()

    login_form = LoginForm()
    signup_form = SignupForm()

    return render_template(
        "admin/users.html", users=users, login_form=login_form, signup_form=signup_form
    )


# ---------------- Manage Products ----------------
@admin.route("/admin/products")
@admin_required
def manage_products():
    login_form = LoginForm()
    signup_form = SignupForm()

    products = Product.query.all()

    return render_template(
        "admin/products.html",
        login_form=login_form,
        signup_form=signup_form,
        products=products,
    )


@admin.route("/admin/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    login_form  = LoginForm()
    signup_form = SignupForm()
    form        = ShopItemsForm()

    # ✅ Category choices dynamically load કરો
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]

    if form.validate_on_submit():
        image_file = form.product_picture.data
        filename   = secure_filename(image_file.filename)

        upload_folder = os.path.join("website", "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        image_file.save(os.path.join(upload_folder, filename))

        product = Product(
            name        = form.product_name.data,
            price       = form.current_price.data,
            description = form.description.data,
            image       = "/static/uploads/" + filename,
            stock       = form.stock.data,
            category_id = form.category_id.data,  # ✅
        )
        db.session.add(product)
        db.session.commit()

        flash("✅ Product added successfully!", "success")
        return redirect(url_for("admin.manage_products"))

    return render_template(
        "admin/add_product.html",
        form=form,
        login_form=login_form,
        signup_form=signup_form,
    )

# ---------------- View Order ----------------
@admin.route("/admin/orders/view/<int:id>")
@admin_required
def view_order(id):
    order = Order.query.get_or_404(id)
    login_form = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "admin/view_order.html",
        order=order,
        login_form=login_form,
        signup_form=signup_form,
    )


# ---------------- Edit Product ----------------
@admin.route("/admin/products/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form    = ShopItemsForm(obj=product)

    # ✅ Choices load કરો
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]

    login_form  = LoginForm()
    signup_form = SignupForm()

    if form.validate_on_submit():
        product.name        = form.product_name.data
        product.price       = form.current_price.data
        product.description = form.description.data
        product.stock       = form.stock.data
        product.category_id = form.category_id.data  # ✅

        if form.product_picture.data:
            image_file = form.product_picture.data
            filename   = secure_filename(image_file.filename)
            upload_folder = os.path.join("website", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            image_file.save(os.path.join(upload_folder, filename))
            product.image = "/static/uploads/" + filename

        db.session.commit()
        flash("✅ Product updated!", "success")
        return redirect(url_for("admin.manage_products"))

    return render_template(
        "admin/edit_product.html",
        form=form,
        product=product,
        login_form=login_form,
        signup_form=signup_form,
    )

# ---------------- Delete Product ----------------
@admin.route("/admin/products/delete/<int:id>", methods=["POST"])
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!")
    return redirect(url_for("admin.manage_products"))


# ---------------- Update Order Status ----------------
@admin.route("/admin/orders/update/<int:id>", methods=["POST"])
@admin_required
def admin_update_order_status(id):
    order = Order.query.get_or_404(id)
    new_status = request.form.get("status")
    old_status = order.status

    order.status = new_status

    # ── Cancellation logic ───────────────────────────────────────────
    if new_status == "Cancelled" and old_status != "Cancelled":

        # 1. Stock restore
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity

        # 2. Reward points refund (je order ma redeem karyeli hoy)
        if order.discount_amount and order.discount_amount > 0:
            # Check karo ke discount reward points thi aavyo hato ke coupon thi
            # Reward redemption RewardTransaction ma negative entry hoy che
            from .models import RewardTransaction, RewardWallet
            redeem_txn = RewardTransaction.query.filter_by(
                user_id=order.user_id
            ).filter(
                RewardTransaction.reason.like(f"%Order #ORD{order.id}%")
            ).filter(
                RewardTransaction.points < 0
            ).first()

            if redeem_txn:
                # Points refund karo
                wallet = RewardWallet.query.filter_by(user_id=order.user_id).first()
                if wallet:
                    refund_pts = abs(redeem_txn.points)
                    wallet.points += refund_pts
                    refund_txn = RewardTransaction(
                        user_id = order.user_id,
                        points  = refund_pts,
                        reason  = f"Points refund — Order #ORD{order.id} cancelled by admin",
                    )
                    db.session.add(refund_txn)

        # 3. Cancel metadata set karo
        order.cancel_reason  = request.form.get("cancel_reason", "Cancelled by admin")
        order.cancelled_at   = datetime.utcnow()
        order.cancel_flagged = True

    db.session.commit()

    # ── Email ────────────────────────────────────────────────────────
    try:
        if new_status == "Confirmed":
            send_order_confirmed(order)
        elif new_status == "Cancelled":
            send_order_cancelled(order)
        elif new_status in ["Shipped", "out_for_delivery"]:
            send_order_shipped(order)
        elif new_status == "Delivered":
            send_order_delivered(order)
    except Exception as e:
        print("Email Error:", e)

    flash(f"✅ Order #ORD{order.id} status updated to '{new_status}'!", "success")
    return redirect(url_for("admin.manage_orders"))


# ---------------- Manage Orders ----------------
@admin.route("/manage-orders")
@login_required
@admin_required
def manage_orders():
    login_form = LoginForm()
    signup_form = SignupForm()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template(
        "admin/manage_orders.html",
        login_form=login_form,
        signup_form=signup_form,
        orders=orders,
    )

# Messages list
@admin.route('/messages')
@login_required
def messages():
    filter_by = request.args.get('filter')
    if filter_by == 'unread':
        msgs = ContactMessage.query.filter_by(is_read=False).order_by(ContactMessage.created_at.desc()).all()
    else:
        msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/admin_messages.html', messages=msgs)

# Mark as read
@admin.route('/messages/read/<int:id>')
@login_required
def mark_read(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('admin.messages'))

# Delete message
@admin.route('/messages/delete/<int:id>')
@login_required
def delete_message(id):
    msg = ContactMessage.query.get_or_404(id)
    db.session.delete(msg)
    db.session.commit()
    flash('Message deleted.', 'success')
    return redirect(url_for('admin.messages'))

@admin.context_processor
def inject_unread_count():
    count = ContactMessage.query.filter_by(is_read=False).count()
    return dict(unread_messages_count=count)




# ---------------- Reports ----------------
@admin.route("/admin/reports")
@admin_required
def reports():
    login_form = LoginForm()
    signup_form = SignupForm()
    total_orders = Order.query.count()
    total_products = Product.query.count()
    low_stock_products = Product.query.filter(Product.stock < 5).all()

    return render_template(
        "admin/reports.html",
        total_orders=total_orders,
        total_products=total_products,
        login_form=login_form,
        signup_form=signup_form,
        low_stock_products=low_stock_products,
    )


# ---------------- Manage Categories ----------------
@admin.route("/admin/categories", methods=["GET", "POST"])
@admin_required
def manage_categories():
    login_form = LoginForm()
    signup_form = SignupForm()
    form = CategoryForm()
    categories = Category.query.all()

    if form.validate_on_submit():
        new_category = Category(name=form.name.data)
        db.session.add(new_category)
        db.session.commit()
        flash("Category added successfully!")
        return redirect(url_for("admin.manage_categories"))

    return render_template(
        "admin/Manage_Categories.html",
        form=form,
        login_form=login_form,
        signup_form=signup_form,
        categories=categories,
    )


# ---------------- Settings ----------------
@admin.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def settings():
    login_form = LoginForm()
    signup_form = SignupForm()
    form = SettingsForm()
    if form.validate_on_submit():
        flash("Settings updated successfully!")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings.html", login_form=login_form, signup_form=signup_form, form=form
    )


# ---------------- Add / Edit / Delete Category ----------------
@admin.route("/add-category", methods=["POST"])
def add_category():
    name = request.form.get("name")
    if name:
        new_cat = Category(name=name)
        db.session.add(new_cat)
        db.session.commit()
    return redirect(url_for("admin.manage_categories"))


@admin.route("/category/edit/<int:id>", methods=["POST"])
def edit_category(id):
    category = Category.query.get_or_404(id)
    category.name = request.form.get("name")
    db.session.commit()
    return redirect(url_for("admin.manage_categories"))


@admin.route("/category/delete/<int:id>")
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for("admin.manage_categories"))


# ============================================================
# Pending UPI Payments
# ============================================================
@admin.route("/pending-payments")
@admin_required
def pending_payments():
    orders = (
        Order.query
        .filter_by(payment_method="upi", payment_status="Pending Verification")
        .order_by(Order.created_at.desc())
        .all()
    )
    login_form = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "admin/pending_payments.html",
        orders=orders,
        login_form=login_form,
        signup_form=signup_form,
    )


# ============================================================
# Verify UPI Payment — ✅ Email included
# ============================================================
@admin.route("/verify-payment/<int:order_id>", methods=["POST"])
@admin_required
def admin_verify_payment(order_id):
    action = request.form.get("action")
    order  = Order.query.get_or_404(order_id)

    if action == "approve":
        order.payment_status = "Paid"
        order.status         = "Confirmed"
        db.session.commit()

        # ✅ Payment confirmed email
        try:
            send_payment_confirmed(order)
        except Exception as e:
            print("Payment Confirmed Email Error:", e)

        flash(f"✅ ORD{order.id} approved!", "success")

    elif action == "reject":
        order.payment_status = "Failed"
        order.status         = "Payment Failed"
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity
        db.session.commit()
        flash(f"❌ ORD{order.id} rejected. Stock restored.", "danger")

    return redirect(url_for("admin.pending_payments"))


# ─────────────────────────────────────────────────────────────
# admin.py માં ઉમેરો — Coupon & Delivery Zone Management
# Import line માં Coupon, DeliveryZone ઉમેરો:
# from .models import db, User, Product, Order, Coupon, DeliveryZone
# ─────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════
# MANAGE COUPONS
# ═══════════════════════════════════════════════════════════
@admin.route("/view-store")
@admin_required
def view_store():
    login_form = LoginForm()
    signup_form = SignupForm()
    return render_template("admin/view_store.html", login_form=login_form, signup_form=signup_form)

@admin.route("/admin/coupons")
@admin_required
def manage_coupons():
    coupons     = Coupon.query.order_by(Coupon.created_at.desc()).all()
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template("admin/coupons.html",
                           coupons=coupons,
                            now=datetime.utcnow(),
                           login_form=login_form,
                           signup_form=signup_form)


@admin.route("/admin/coupons/add", methods=["POST"])
@admin_required
def add_coupon():
    from datetime import datetime
    code           = request.form.get("code", "").strip().upper()
    coupon_type    = request.form.get("coupon_type", "flat")
    discount_value = float(request.form.get("discount_value", 0))
    min_order      = float(request.form.get("min_order", 0))
    max_discount   = request.form.get("max_discount")
    usage_limit    = request.form.get("usage_limit")
    expires_at     = request.form.get("expires_at")

    if not code or discount_value <= 0:
        flash("Code અને Discount value જરૂરી છે!", "danger")
        return redirect(url_for("admin.manage_coupons"))

    if Coupon.query.filter_by(code=code).first():
        flash(f"'{code}' already exists!", "danger")
        return redirect(url_for("admin.manage_coupons"))

    coupon = Coupon(
        code           = code,
        coupon_type    = coupon_type,
        discount_value = discount_value,
        min_order      = min_order,
        max_discount   = float(max_discount) if max_discount else None,
        usage_limit    = int(usage_limit) if usage_limit else None,
        expires_at     = datetime.strptime(expires_at, "%Y-%m-%d") if expires_at else None,
    )
    db.session.add(coupon)
    db.session.commit()
    flash(f"✅ Coupon '{code}' added!", "success")
    return redirect(url_for("admin.manage_coupons"))


@admin.route("/admin/coupons/toggle/<int:id>", methods=["POST"])
@admin_required
def toggle_coupon(id):
    coupon           = Coupon.query.get_or_404(id)
    coupon.is_active = not coupon.is_active
    db.session.commit()
    status = "activated" if coupon.is_active else "deactivated"
    flash(f"Coupon '{coupon.code}' {status}!", "success")
    return redirect(url_for("admin.manage_coupons"))


@admin.route("/admin/coupons/delete/<int:id>", methods=["POST"])
@admin_required
def delete_coupon(id):
    coupon = Coupon.query.get_or_404(id)
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted!", "danger")
    return redirect(url_for("admin.manage_coupons"))


# ═══════════════════════════════════════════════════════════
# MANAGE DELIVERY ZONES
# ═══════════════════════════════════════════════════════════
@admin.route("/admin/delivery-zones")
@admin_required
def manage_delivery_zones():
    zones       = DeliveryZone.query.order_by(DeliveryZone.city).all()
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template("admin/delivery_zones.html",
                           zones=zones,
                           login_form=login_form,
                           signup_form=signup_form)


@admin.route("/admin/delivery-zones/add", methods=["POST"])
@admin_required
def add_delivery_zone():
    city   = request.form.get("city", "").strip().title()
    charge = float(request.form.get("charge", 50))

    if not city:
        flash("City name જરૂરી છે!", "danger")
        return redirect(url_for("admin.manage_delivery_zones"))

    if DeliveryZone.query.filter(
        db.func.lower(DeliveryZone.city) == city.lower()
    ).first():
        flash(f"'{city}' already exists!", "danger")
        return redirect(url_for("admin.manage_delivery_zones"))

    zone = DeliveryZone(city=city, charge=charge)
    db.session.add(zone)
    db.session.commit()
    flash(f"✅ '{city}' zone added! Charge: Rs.{charge:.0f}", "success")
    return redirect(url_for("admin.manage_delivery_zones"))


@admin.route("/admin/delivery-zones/edit/<int:id>", methods=["POST"])
@admin_required
def edit_delivery_zone(id):
    zone        = DeliveryZone.query.get_or_404(id)
    zone.city   = request.form.get("city", zone.city).strip().title()
    zone.charge = float(request.form.get("charge", zone.charge))
    db.session.commit()
    flash(f"✅ '{zone.city}' updated!", "success")
    return redirect(url_for("admin.manage_delivery_zones"))


@admin.route("/admin/delivery-zones/delete/<int:id>", methods=["POST"])
@admin_required
def delete_delivery_zone(id):
    zone = DeliveryZone.query.get_or_404(id)
    db.session.delete(zone)
    db.session.commit()
    flash("Zone deleted!", "danger")
    return redirect(url_for("admin.manage_delivery_zones"))

# ══════════════════════════════════════════════════════════════
#  ADD THESE ROUTES to your admin.py (or views.py — wherever
#  your @admin blueprint routes live)
#
#  These power the View Store page's live data sections.
# ══════════════════════════════════════════════════════════════

from flask import Blueprint, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from sqlalchemy import func
from .models import (
    db, Product, Order, OrderItem, User,
    ContactMessage, Coupon, DeliveryZone, ChatSession
)


# ── 1. Store stats dashboard + sparklines + health ───────────

@admin.route('/admin/api/store-stats')
@login_required
def api_store_stats():
    today   = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Today's revenue & orders
    today_orders = Order.query.filter(
        func.date(Order.created_at) == today
    ).all()
    revenue_today = sum(o.total_amount or 0 for o in today_orders)
    orders_today  = len(today_orders)

    # Pending orders
    pending_orders = Order.query.filter_by(status='Pending').count()

    # Total users & new this week
    total_users    = User.query.count()
    new_users_week = User.query.filter(User.id > 0,
        Order.created_at >= week_ago
    ).count() if False else \
        db.session.query(func.count(User.id)).filter(
            User.id.in_(
                db.session.query(Order.user_id).filter(Order.created_at >= week_ago)
            )
        ).scalar() or 0

    # Total products & out of stock
    total_products = Product.query.count()
    out_of_stock   = Product.query.filter(Product.stock <= 0).count()

    # Revenue last 7 days (sparkline)
    rev_7d = []
    ord_7d = []
    usr_7d = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_orders = Order.query.filter(func.date(Order.created_at) == day).all()
        rev_7d.append(round(sum(o.total_amount or 0 for o in day_orders), 2))
        ord_7d.append(len(day_orders))
        usr_7d.append(User.query.filter(func.date(User.id) == day).count() if False else
                      db.session.query(func.count(Order.user_id.distinct())).filter(
                          func.date(Order.created_at) == day).scalar() or 0)

    # Week totals
    revenue_week = sum(rev_7d)
    orders_week  = sum(ord_7d)

    # Health extras
    unread_messages  = ContactMessage.query.filter_by(is_read=False).count()
    pending_upi      = Order.query.filter_by(payment_method='upi', payment_status='Unpaid').count()
    expiring_coupons = Coupon.query.filter(
        Coupon.is_active == True,
        Coupon.expires_at != None,
        Coupon.expires_at <= datetime.utcnow() + timedelta(days=3)
    ).count()

    return jsonify({
        'revenue_today':    round(revenue_today, 2),
        'orders_today':     orders_today,
        'pending_orders':   pending_orders,
        'total_users':      total_users,
        'total_products':   total_products,
        'out_of_stock':     out_of_stock,
        'revenue_week':     round(revenue_week, 2),
        'orders_week':      orders_week,
        'new_users_week':   new_users_week,
        'rev_7d':           rev_7d,
        'ord_7d':           ord_7d,
        'usr_7d':           usr_7d,
        'unread_messages':  unread_messages,
        'pending_upi':      pending_upi,
        'expiring_coupons': expiring_coupons,
    })


# ── 2. Product Spotlight ──────────────────────────────────────

@admin.route('/admin/api/products-spotlight')
@login_required
def api_products_spotlight():
    from .models import Review, Category
    products = Product.query.order_by(Product.stock.desc()).limit(10).all()
    result = []
    for p in products:
        avg = db.session.query(func.avg(Review.rating)) \
                .filter_by(product_id=p.id).scalar()
        count = Review.query.filter_by(product_id=p.id).count()
        cat_name = p.category.name if p.category else None
        result.append({
            'id':           p.id,
            'name':         p.name,
            'price':        p.price,
            'stock':        p.stock,
            'image':        p.image or '',
            'category':     cat_name,
            'avg_rating':   round(float(avg), 1) if avg else 0,
            'review_count': count,
        })
    return jsonify(result)


# ── 3. Activity Feed ──────────────────────────────────────────

@admin.route('/admin/api/activity-feed')
@login_required
def api_activity_feed():
    items = []

    # Recent orders
    orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    for o in orders:
        items.append({
            'type': 'order',
            'text': f'New order #{o.tracking_id or o.id}',
            'sub':  f'₹{o.total_amount:.0f} · {o.status}',
            'time': o.created_at.isoformat(),
        })

    # Recent users
    users = User.query.order_by(User.id.desc()).limit(3).all()
    for u in users:
        items.append({
            'type': 'user',
            'text': f'{u.name} signed up',
            'sub':  u.email,
            'time': datetime.utcnow().isoformat(),  # fallback if no created_at
        })

    # Recent messages
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(3).all()
    for m in msgs:
        items.append({
            'type': 'message',
            'text': f'New message from {m.name}',
            'sub':  m.subject or 'Contact enquiry',
            'time': m.created_at.isoformat(),
        })

    # Recent chat sessions
    chats = ChatSession.query.order_by(ChatSession.created_at.desc()).limit(3).all()
    for c in chats:
        items.append({
            'type': 'chat',
            'text': f'{c.user_name} started a chat',
            'sub':  f'Status: {c.status}',
            'time': c.created_at.isoformat(),
        })

    # Sort by time desc, return top 15
    items.sort(key=lambda x: x['time'], reverse=True)
    return jsonify(items[:15])


# ── 4. Low Stock ──────────────────────────────────────────────

@admin.route('/admin/api/low-stock')
@login_required
def api_low_stock():
    products = Product.query.filter(Product.stock <= 10) \
                .order_by(Product.stock.asc()).limit(10).all()
    result = []
    for p in products:
        result.append({
            'id':       p.id,
            'name':     p.name,
            'price':    p.price,
            'stock':    p.stock,
            'category': p.category.name if p.category else None,
        })
    return jsonify(result)


# ── 5. Coupon Performance ─────────────────────────────────────

@admin.route('/admin/api/coupons-performance')
@login_required
def api_coupons_performance():
    coupons = Coupon.query.order_by(Coupon.used_count.desc()).limit(10).all()
    result = []
    for c in coupons:
        result.append({
            'code':           c.code,
            'coupon_type':    c.coupon_type,
            'discount_value': c.discount_value,
            'used_count':     c.used_count,
            'usage_limit':    c.usage_limit,
            'is_active':      c.is_active,
            'expires_at':     c.expires_at.strftime('%d %b %Y') if c.expires_at else None,
        })
    return jsonify(result)


# ── 6. Delivery Zones ─────────────────────────────────────────

@admin.route('/admin/api/delivery-zones')
@login_required
def api_delivery_zones():
    zones = DeliveryZone.query.order_by(DeliveryZone.city).all()
    return jsonify([{
        'id':        z.id,
        'city':      z.city,
        'charge':    z.charge,
        'is_active': z.is_active,
    } for z in zones])

# ═══════════════════════════════════════════════════════════════════════
#  ADMIN TESTIMONIAL ROUTES  — paste into admin.py
#  Also add these imports at top of admin.py:
#    from .models import (Testimonial, RewardWallet, RewardTransaction,
#                         TestimonialRewardConfig)
# ═══════════════════════════════════════════════════════════════════════


# ── Admin: List all testimonials ─────────────────────────────────────
@admin.route("/admin/testimonials")
@admin_required
def manage_testimonials():
    login_form  = LoginForm()
    signup_form = SignupForm()

    status_filter = request.args.get("status", "all")

    q = Testimonial.query.order_by(
        Testimonial.is_featured.desc(),
        Testimonial.created_at.desc()
    )
    if status_filter != "all":
        q = q.filter_by(status=status_filter)

    testimonials = q.all()
    config       = TestimonialRewardConfig.query.first()

    counts = {
        "all":      Testimonial.query.count(),
        "pending":  Testimonial.query.filter_by(status="pending").count(),
        "approved": Testimonial.query.filter_by(status="approved").count(),
        "rejected": Testimonial.query.filter_by(status="rejected").count(),
    }

    return render_template(
        "admin/testimonials.html",
        login_form=login_form,
        signup_form=signup_form,
        testimonials=testimonials,
        status_filter=status_filter,
        counts=counts,
        config=config,
    )


# ── Admin: Approve testimonial ───────────────────────────────────────
@admin.route("/admin/testimonials/<int:tid>/approve", methods=["POST"])
@admin_required
def approve_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)

    t.status        = Testimonial.STATUS_APPROVED
    t.moderated_at  = datetime.utcnow()
    t.moderated_by_id = current_user.id
    t.admin_note    = request.form.get("admin_note", "").strip() or None

    # Override display name (optional)
    override_name = request.form.get("display_name", "").strip()
    if override_name:
        t.display_name = override_name

    # Credit reward points (only once)
    if not t.reward_given:
        pts    = TestimonialRewardConfig.get_points()
        wallet = RewardWallet.get_or_create(t.user_id)
        wallet.points += pts
        txn = RewardTransaction(
            user_id = t.user_id,
            points  = pts,
            reason  = f"Testimonial approved — earned {pts} reward points 🎉",
        )
        db.session.add(txn)
        t.reward_given = True

    db.session.commit()
    flash(f"✅ Testimonial approved! Reward points credited.", "success")
    return redirect(url_for("admin.manage_testimonials"))


# ── Admin: Reject testimonial ────────────────────────────────────────
@admin.route("/admin/testimonials/<int:tid>/reject", methods=["POST"])
@admin_required
def reject_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    t.status          = Testimonial.STATUS_REJECTED
    t.moderated_at    = datetime.utcnow()
    t.moderated_by_id = current_user.id
    t.admin_note      = request.form.get("admin_note", "").strip() or None
    db.session.commit()
    flash("❌ Testimonial rejected.", "warning")
    return redirect(url_for("admin.manage_testimonials"))


# ── Admin: Delete testimonial ────────────────────────────────────────
@admin.route("/admin/testimonials/<int:tid>/delete", methods=["POST"])
@admin_required
def delete_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    flash("🗑️ Testimonial deleted.", "danger")
    return redirect(url_for("admin.manage_testimonials"))


# ── Admin: Toggle featured ───────────────────────────────────────────
@admin.route("/admin/testimonials/<int:tid>/feature", methods=["POST"])
@admin_required
def feature_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    t.is_featured = not t.is_featured
    db.session.commit()
    state = "⭐ Featured" if t.is_featured else "Unfeatured"
    flash(f"{state}: '{t.headline}'", "success")
    return redirect(url_for("admin.manage_testimonials"))


# ── Admin: Update reward points config ──────────────────────────────
@admin.route("/admin/testimonials/config", methods=["POST"])
@admin_required
def update_testimonial_config():
    pts = request.form.get("reward_points", 50)
    try:
        pts = max(0, int(pts))
    except ValueError:
        flash("Invalid points value.", "danger")
        return redirect(url_for("admin.manage_testimonials"))

    config = TestimonialRewardConfig.query.first()
    if not config:
        config = TestimonialRewardConfig(reward_points=pts)
        db.session.add(config)
    else:
        config.reward_points = pts

    db.session.commit()
    flash(f"✅ Reward updated to {pts} points per testimonial.", "success")
    return redirect(url_for("admin.manage_testimonials"))


# ── Admin: Reward wallet overview ────────────────────────────────────
@admin.route("/admin/rewards")
@admin_required
def admin_rewards():
    login_form  = LoginForm()
    signup_form = SignupForm()
    wallets = (
        RewardWallet.query
        .join(User, RewardWallet.user_id == User.id)
        .order_by(RewardWallet.points.desc())
        .all()
    )
    total_points_issued = db.session.query(
        db.func.sum(RewardTransaction.points)
    ).filter(RewardTransaction.points > 0).scalar() or 0

    return render_template(
        "admin/rewards.html",
        login_form=login_form,
        signup_form=signup_form,
        wallets=wallets,
        total_points_issued=total_points_issued,
    )
    
# ══════════════════════════════════════════════════════════════
# FLASH SALE — ADMIN ROUTES
# admin.py ma aa routes paste karo
# Import line ma FlashSale, FlashSaleItem ઉમેરો:
#   from .models import FlashSale, FlashSaleItem
# ══════════════════════════════════════════════════════════════

from datetime import datetime, timedelta


# ── List all flash sales ──────────────────────────────────────
@admin.route("/admin/flash-sales")
@admin_required
def manage_flash_sales():
    login_form  = LoginForm()
    signup_form = SignupForm()
    sales    = FlashSale.query.order_by(FlashSale.created_at.desc()).all()
    products = Product.query.order_by(Product.name).all()
    return render_template(
        "admin/flash_sales.html",
        sales=sales,
        products=products,
        login_form=login_form,
        signup_form=signup_form,
        now=datetime.utcnow(),
    )


# ── Create new flash sale ─────────────────────────────────────
@admin.route("/admin/flash-sales/create", methods=["POST"])
@csrf.exempt 
@admin_required
def create_flash_sale():
    name       = request.form.get("name", "").strip()
    duration_h = float(request.form.get("duration_hours", 1))

    if not name:
        flash("Sale name જરૂરી છે!", "danger")
        return redirect(url_for("admin.manage_flash_sales"))

    starts_at = datetime.utcnow()
    ends_at   = starts_at + timedelta(hours=duration_h)

    sale = FlashSale(
        name       = name,
        is_active  = False,
        starts_at  = starts_at,
        ends_at    = ends_at,
        created_by = current_user.id,
    )
    db.session.add(sale)
    db.session.commit()
    flash(f"✅ Flash Sale '{name}' created! Haju products add karo.", "success")
    return redirect(url_for("admin.edit_flash_sale", sale_id=sale.id))


# ── Edit flash sale — add/remove products & discounts ────────
@admin.route("/admin/flash-sales/<int:sale_id>", methods=["GET", "POST"])
@admin_required
def edit_flash_sale(sale_id):
    login_form  = LoginForm()
    signup_form = SignupForm()
    sale     = FlashSale.query.get_or_404(sale_id)
    products = Product.query.order_by(Product.name).all()

    # IDs already in this sale
    existing_ids = {item.product_id for item in sale.items}

    return render_template(
        "admin/edit_flash_sale.html",
        sale=sale,
        products=products,
        existing_ids=existing_ids,
        login_form=login_form,
        signup_form=signup_form,
    )


# ── Add / update product discount in a sale ───────────────────
@admin.route("/admin/flash-sales/<int:sale_id>/add-item", methods=["POST"])
@admin_required
def add_flash_sale_item(sale_id):
    sale       = FlashSale.query.get_or_404(sale_id)
    product_id = int(request.form.get("product_id", 0))
    disc_pct   = float(request.form.get("discount_pct", 10))

    if not product_id:
        flash("Product select karo!", "danger")
        return redirect(url_for("admin.edit_flash_sale", sale_id=sale_id))

    # Already exists? Update discount
    existing = FlashSaleItem.query.filter_by(
        flash_sale_id=sale_id, product_id=product_id
    ).first()
    if existing:
        existing.discount_pct = disc_pct
        flash("✅ Discount updated!", "success")
    else:
        item = FlashSaleItem(
            flash_sale_id=sale_id,
            product_id=product_id,
            discount_pct=disc_pct,
        )
        db.session.add(item)
        flash("✅ Product added to sale!", "success")

    db.session.commit()
    return redirect(url_for("admin.edit_flash_sale", sale_id=sale_id))


# ── Remove product from sale ──────────────────────────────────
@admin.route("/admin/flash-sales/<int:sale_id>/remove-item/<int:item_id>", methods=["POST"])
@admin_required
def remove_flash_sale_item(sale_id, item_id):
    item = FlashSaleItem.query.filter_by(id=item_id, flash_sale_id=sale_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Product removed!", "warning")
    return redirect(url_for("admin.edit_flash_sale", sale_id=sale_id))


# ── Apply bulk discount to ALL products in sale ───────────────
@admin.route("/admin/flash-sales/<int:sale_id>/bulk-discount", methods=["POST"])
@admin_required
def bulk_flash_discount(sale_id):
    sale     = FlashSale.query.get_or_404(sale_id)
    disc_pct = float(request.form.get("bulk_pct", 10))

    for item in sale.items:
        item.discount_pct = disc_pct

    db.session.commit()
    flash(f"✅ Badha products par {disc_pct:.0f}% discount set karyun!", "success")
    return redirect(url_for("admin.edit_flash_sale", sale_id=sale_id))


# ── Start / Stop sale ─────────────────────────────────────────
@admin.route("/admin/flash-sales/<int:sale_id>/toggle", methods=["POST"])
@csrf.exempt
@admin_required
def toggle_flash_sale(sale_id):
    sale = FlashSale.query.get_or_404(sale_id)

    if sale.is_active:
        # Stop
        sale.is_active = False
        flash(f"⏹️ '{sale.name}' band karyo!", "warning")
    else:
        # Deactivate any other running sale first
        FlashSale.query.filter_by(is_active=True).update({"is_active": False})

        # Reset timer from now
        duration = sale.ends_at - sale.starts_at   # preserve original duration
        sale.starts_at = datetime.utcnow()
        sale.ends_at   = sale.starts_at + duration
        sale.is_active = True
        flash(f"⚡ '{sale.name}' shuru thai! Timer reset.", "success")

    db.session.commit()
    return redirect(url_for("admin.manage_flash_sales"))


# ── Delete sale ───────────────────────────────────────────────
@admin.route("/admin/flash-sales/<int:sale_id>/delete", methods=["POST"])
@csrf.exempt
@admin_required
def delete_flash_sale(sale_id):
    sale = FlashSale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    flash("Flash Sale deleted!", "danger")
    return redirect(url_for("admin.manage_flash_sales"))

# ══════════════════════════════════════════════════════════
# PER-PRODUCT SALE — ADMIN ROUTES
# ══════════════════════════════════════════════════════════

@admin.route("/admin/product-sales")
@admin_required
def manage_product_sales():
    login_form  = LoginForm()
    signup_form = SignupForm()
    sales    = ProductSale.query.order_by(ProductSale.created_at.desc()).all()
    products = Product.query.order_by(Product.name).all()

    # Products without any sale set
    sale_product_ids = {s.product_id for s in sales}
    available_products = [p for p in products if p.id not in sale_product_ids]

    return render_template(
        "admin/product_sales.html",
        sales=sales,
        available_products=available_products,
        login_form=login_form,
        signup_form=signup_form,
        now=datetime.utcnow(),
    )


@admin.route("/admin/product-sales/add", methods=["POST"])
@csrf.exempt
@admin_required
def add_product_sale():
    IST_OFFSET = timedelta(hours=5, minutes=30)
    product_id   = int(request.form.get("product_id", 0))
    discount_pct = float(request.form.get("discount_pct", 10))
    label        = request.form.get("label", "").strip() or None
    starts_at_str = request.form.get("starts_at", "").strip()
    ends_at_str   = request.form.get("ends_at", "").strip()

    if not product_id:
        flash("Product select karo!", "danger")
        return redirect(url_for("admin.manage_product_sales"))

    if ProductSale.query.filter_by(product_id=product_id).first():
        flash("Aa product par already sale chhe! Pehla edit karo.", "warning")
        return redirect(url_for("admin.manage_product_sales"))

    try:
        starts_at = (datetime.strptime(starts_at_str, "%Y-%m-%dT%H:%M") - IST_OFFSET) if starts_at_str else None
        ends_at   = (datetime.strptime(ends_at_str,   "%Y-%m-%dT%H:%M") - IST_OFFSET) if ends_at_str   else None
    except ValueError:
        flash("Date format incorrect chhe.", "danger")
        return redirect(url_for("admin.manage_product_sales"))

    sale = ProductSale(
        product_id   = product_id,
        discount_pct = discount_pct,
        label        = label,
        is_active    = True,
        starts_at    = starts_at,
        ends_at      = ends_at,
    )
    db.session.add(sale)
    db.session.commit()

    product = Product.query.get(product_id)
    flash(f"✅ '{product.name}' par {discount_pct:.0f}% sale set karyo!", "success")
    return redirect(url_for("admin.manage_product_sales"))


@admin.route("/admin/product-sales/edit/<int:sale_id>", methods=["POST"])
@csrf.exempt
@admin_required
def edit_product_sale(sale_id):
    IST_OFFSET = timedelta(hours=5, minutes=30)
    sale = ProductSale.query.get_or_404(sale_id)
 
    sale.discount_pct = float(request.form.get("discount_pct", sale.discount_pct))
    sale.label        = request.form.get("label", "").strip() or None
 
    starts_at_str = request.form.get("starts_at", "").strip()
    ends_at_str   = request.form.get("ends_at",   "").strip()
 
    try:
        # ✅ Now actually assigned to the model object
        sale.starts_at = (
            datetime.strptime(starts_at_str, "%Y-%m-%dT%H:%M") - IST_OFFSET
        ) if starts_at_str else None
 
        sale.ends_at = (
            datetime.strptime(ends_at_str, "%Y-%m-%dT%H:%M") - IST_OFFSET
        ) if ends_at_str else None
 
    except ValueError:
        flash("Date format incorrect chhe.", "danger")
        return redirect(url_for("admin.manage_product_sales"))
 
    db.session.commit()   # ✅ commit after assignment
    flash(f"✅ '{sale.product.name}' sale updated!", "success")
    return redirect(url_for("admin.manage_product_sales"))

@admin.route("/admin/product-sales/toggle/<int:sale_id>", methods=["POST"])
@csrf.exempt
@admin_required
def toggle_product_sale(sale_id):
    sale           = ProductSale.query.get_or_404(sale_id)
    sale.is_active = not sale.is_active
    db.session.commit()
    state = "activated" if sale.is_active else "deactivated"
    flash(f"Sale {state}: '{sale.product.name}'", "success")
    return redirect(url_for("admin.manage_product_sales"))


@admin.route("/admin/product-sales/delete/<int:sale_id>", methods=["POST"])
@csrf.exempt
@admin_required
def delete_product_sale(sale_id):
    sale = ProductSale.query.get_or_404(sale_id)
    name = sale.product.name
    db.session.delete(sale)
    db.session.commit()
    flash(f"🗑 '{name}' sale removed!", "danger")
    return redirect(url_for("admin.manage_product_sales"))

# ── List all bundles ─────────────────────────────────────────────────
@admin.route("/admin/bundles")
@admin_required
def manage_bundles():
    login_form  = LoginForm()
    signup_form = SignupForm()
    bundles  = BundleGroup.query.order_by(BundleGroup.created_at.desc()).all()
    products = Product.query.order_by(Product.name).all()
    return render_template(
        "admin/bundles.html",
        bundles=bundles,
        products=products,
        login_form=login_form,
        signup_form=signup_form,
        now=datetime.utcnow(),
    )
 
 
# ── Create bundle ────────────────────────────────────────────────────
@admin.route("/admin/bundles/create", methods=["POST"])
@csrf.exempt
@admin_required
def create_bundle():
    name         = request.form.get("name", "").strip()
    description  = request.form.get("description", "").strip()
    deal_type    = request.form.get("deal_type", "percent")
    badge_label  = request.form.get("badge_label", "").strip()
    fixed_price  = request.form.get("fixed_price")
    discount_pct = request.form.get("discount_pct")
    buy_qty      = request.form.get("buy_qty")
    free_qty     = request.form.get("free_qty")
    starts_at    = request.form.get("starts_at")
    ends_at      = request.form.get("ends_at")
    IST          = timedelta(hours=5, minutes=30)
 
    if not name:
        flash("Bundle name જરૂરી છે!", "danger")
        return redirect(url_for("admin.manage_bundles"))
 
    bundle = BundleGroup(
        name         = name,
        description  = description,
        deal_type    = deal_type,
        badge_label  = badge_label,
        fixed_price  = float(fixed_price)  if fixed_price  else None,
        discount_pct = float(discount_pct) if discount_pct else None,
        buy_qty      = int(buy_qty)        if buy_qty      else None,
        free_qty     = int(free_qty)       if free_qty     else None,
        starts_at    = (datetime.strptime(starts_at, "%Y-%m-%dT%H:%M") - IST) if starts_at else None,
        ends_at      = (datetime.strptime(ends_at,   "%Y-%m-%dT%H:%M") - IST) if ends_at   else None,
        created_by   = current_user.id,
        is_active    = True,
    )
    db.session.add(bundle)
    db.session.commit()
    flash(f"✅ Bundle '{name}' created! Products add karo.", "success")
    return redirect(url_for("admin.edit_bundle", bundle_id=bundle.id))
 
 
# ── Edit bundle — add/remove products ───────────────────────────────
@admin.route("/admin/bundles/<int:bundle_id>", methods=["GET", "POST"])
@csrf.exempt
@admin_required
def edit_bundle(bundle_id):
    login_form  = LoginForm()
    signup_form = SignupForm()
    bundle   = BundleGroup.query.get_or_404(bundle_id)
    products = Product.query.order_by(Product.name).all()
    existing_ids = {item.product_id for item in bundle.items}
 
    return render_template(
        "admin/edit_bundle.html",
        bundle=bundle,
        products=products,
        existing_ids=existing_ids,
        login_form=login_form,
        signup_form=signup_form,
    )
 
 
# ── Add product to bundle ────────────────────────────────────────────
@admin.route("/admin/bundles/<int:bundle_id>/add-item", methods=["POST"])
@csrf.exempt
@admin_required
def add_bundle_item(bundle_id):
    bundle     = BundleGroup.query.get_or_404(bundle_id)
    product_id = int(request.form.get("product_id", 0))
    quantity   = int(request.form.get("quantity", 1))
 
    if not product_id:
        flash("Product select karo!", "danger")
        return redirect(url_for("admin.edit_bundle", bundle_id=bundle_id))
 
    existing = BundleItem.query.filter_by(
        bundle_id=bundle_id, product_id=product_id
    ).first()
 
    if existing:
        existing.quantity = quantity
        flash("✅ Quantity updated!", "success")
    else:
        item = BundleItem(
            bundle_id=bundle_id,
            product_id=product_id,
            quantity=quantity,
        )
        db.session.add(item)
        flash("✅ Product bundle ma add thayo!", "success")
 
    db.session.commit()
    return redirect(url_for("admin.edit_bundle", bundle_id=bundle_id))
 
 
# ── Remove product from bundle ───────────────────────────────────────
@admin.route("/admin/bundles/<int:bundle_id>/remove-item/<int:item_id>", methods=["POST"])
@csrf.exempt
@admin_required
def remove_bundle_item(bundle_id, item_id):
    item = BundleItem.query.filter_by(id=item_id, bundle_id=bundle_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Product removed!", "warning")
    return redirect(url_for("admin.edit_bundle", bundle_id=bundle_id))
 
 
# ── Toggle active/inactive ───────────────────────────────────────────
@admin.route("/admin/bundles/<int:bundle_id>/toggle", methods=["POST"])
@csrf.exempt
@admin_required
def toggle_bundle(bundle_id):
    bundle           = BundleGroup.query.get_or_404(bundle_id)
    bundle.is_active = not bundle.is_active
    db.session.commit()
    state = "activated ✅" if bundle.is_active else "deactivated ⏸"
    flash(f"Bundle '{bundle.name}' {state}!", "success")
    return redirect(url_for("admin.manage_bundles"))
 
 
# ── Delete bundle ────────────────────────────────────────────────────
@admin.route("/admin/bundles/<int:bundle_id>/delete", methods=["POST"])
@csrf.exempt
@admin_required
def delete_bundle(bundle_id):
    bundle = BundleGroup.query.get_or_404(bundle_id)
    db.session.delete(bundle)
    db.session.commit()
    flash("Bundle deleted!", "danger")
    return redirect(url_for("admin.manage_bundles"))
 
 
# ── Update bundle settings ───────────────────────────────────────────
@admin.route("/admin/bundles/<int:bundle_id>/update", methods=["POST"])
@csrf.exempt
@admin_required
def update_bundle(bundle_id):
    bundle       = BundleGroup.query.get_or_404(bundle_id)
    IST          = timedelta(hours=5, minutes=30)
    fixed_price  = request.form.get("fixed_price")
    discount_pct = request.form.get("discount_pct")
    buy_qty      = request.form.get("buy_qty")
    free_qty     = request.form.get("free_qty")
    starts_at    = request.form.get("starts_at")
    ends_at      = request.form.get("ends_at")
 
    bundle.name         = request.form.get("name", bundle.name).strip()
    bundle.description  = request.form.get("description", "").strip()
    bundle.deal_type    = request.form.get("deal_type", bundle.deal_type)
    bundle.badge_label  = request.form.get("badge_label", "").strip()
    bundle.fixed_price  = float(fixed_price)  if fixed_price  else None
    bundle.discount_pct = float(discount_pct) if discount_pct else None
    bundle.buy_qty      = int(buy_qty)        if buy_qty      else None
    bundle.free_qty     = int(free_qty)       if free_qty     else None
    bundle.starts_at    = (datetime.strptime(starts_at, "%Y-%m-%dT%H:%M") - IST) if starts_at else None
    bundle.ends_at      = (datetime.strptime(ends_at,   "%Y-%m-%dT%H:%M") - IST) if ends_at   else None
 
    db.session.commit()
    flash(f"✅ Bundle '{bundle.name}' updated!", "success")
    return redirect(url_for("admin.edit_bundle", bundle_id=bundle_id))

@admin.route('/product/<int:product_id>/variants', methods=['GET', 'POST'])
@admin_required   # ✅ missing હતો
def manage_variants(product_id):
    product  = Product.query.get_or_404(product_id)
    variants = ProductVariant.query.filter_by(product_id=product_id)\
                             .order_by(ProductVariant.sort_order).all()

    if request.method == 'POST':
        label      = request.form.get('label', '').strip()
        price      = request.form.get('price')
        stock      = request.form.get('stock', 0)
        sort_order = request.form.get('sort_order', 0)

        if not label or not price:
            flash('Label અને Price જરૂરી છે!', 'danger')
            return redirect(url_for('admin.manage_variants', product_id=product_id))

        v = ProductVariant(
            product_id = product_id,
            label      = label,          # e.g. "250gm", "500gm", "1kg"
            price      = float(price),
            stock      = int(stock),
            sort_order = int(sort_order),
        )
        db.session.add(v)
        db.session.commit()
        flash(f'✅ Variant "{label}" added!', 'success')
        return redirect(url_for('admin.manage_variants', product_id=product_id))

    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template(
        'admin/variants.html',
        product=product,
        variants=variants,
        login_form=login_form,
        signup_form=signup_form,
    )


@admin.route('/variant/<int:variant_id>/edit', methods=['POST'])
@admin_required
def edit_variant(variant_id):
    v          = ProductVariant.query.get_or_404(variant_id)
    v.label    = request.form.get('label', v.label).strip()
    v.price    = float(request.form.get('price', v.price))
    v.stock    = int(request.form.get('stock', v.stock))
    v.sort_order = int(request.form.get('sort_order', v.sort_order))
    db.session.commit()
    flash('✅ Variant updated!', 'success')
    return redirect(url_for('admin.manage_variants', product_id=v.product_id))


@admin.route('/variant/<int:variant_id>/toggle', methods=['POST'])
@admin_required
def toggle_variant(variant_id):
    v           = ProductVariant.query.get_or_404(variant_id)
    v.is_active = not v.is_active
    db.session.commit()
    state = "activated ✅" if v.is_active else "deactivated ⏸"
    flash(f'Variant "{v.label}" {state}!', 'info')
    return redirect(url_for('admin.manage_variants', product_id=v.product_id))


@admin.route('/variant/<int:variant_id>/delete', methods=['POST'])
@admin_required
def delete_variant(variant_id):
    v   = ProductVariant.query.get_or_404(variant_id)
    pid = v.product_id
    lbl = v.label
    db.session.delete(v)
    db.session.commit()
    flash(f'🗑 Variant "{lbl}" deleted!', 'danger')
    return redirect(url_for('admin.manage_variants', product_id=pid))