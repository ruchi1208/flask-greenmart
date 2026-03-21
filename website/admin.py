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
    login_form = LoginForm()
    signup_form = SignupForm()
    form = ShopItemsForm()

    if form.validate_on_submit():
        image_file = form.product_picture.data
        filename = secure_filename(image_file.filename)

        upload_folder = os.path.join("website", "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        image_path = os.path.join(upload_folder, filename)
        image_file.save(image_path)

        product = Product(
            name=form.product_name.data,
            price=form.current_price.data,
            description=str(form.previous_price.data),
            image="uploads/" + filename,
            stock=form.stock.data,
        )

        db.session.add(product)
        db.session.commit()

        flash("Product added successfully!")
        return redirect(url_for("admin.manage_products"))

    return render_template(
        "admin/add_product.html",
        login_form=login_form,
        signup_form=signup_form,
        form=form,
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
    form = ShopItemsForm(obj=product)

    login_form = LoginForm()
    signup_form = SignupForm()

    if form.validate_on_submit():
        product.name = form.product_name.data
        product.price = form.current_price.data
        product.description = str(form.previous_price.data)
        product.stock = int(form.stock.data)

        if form.product_picture.data:
            image_file = form.product_picture.data
            filename = secure_filename(image_file.filename)
            upload_folder = os.path.join("website", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            image_file.save(image_path)
            product.image = "uploads/" + filename

        db.session.commit()
        flash("Product updated successfully!")
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
    order.status = new_status
    db.session.commit()

    # ✅ Email send karo based on new status
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

    flash("Order status updated!")
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