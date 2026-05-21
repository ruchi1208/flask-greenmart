from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_file,
)

from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required,
)
from .models import Testimonial, RewardWallet, RewardTransaction, TestimonialRewardConfig
from werkzeug.security import generate_password_hash
from functools import wraps
import io
import os
import base64
import qrcode
from datetime import datetime
from .models import BundleGroup, BundleItem
# Models
from .models import (
    db,
    User,
    Product,
    ContactMessage,
    Wishlist,
    Cart,
    Order,
    OrderItem,
    Category,
    Address,
    generate_tracking_id,
    ProductVariant
)
from .models import ProductSale
from datetime import datetime
from . import mail
from flask_mail import Message
from . import csrf
from .models import Review
from .models import User, Product, Order, Coupon, DeliveryZone 
# Forms & Products
from .forms import SignupForm, LoginForm
from .products import all_products
from .models import FlashSale, FlashSaleItem
# ✅ EMAIL FUNCTIONS
from .emails import (
    send_order_confirmed,
    send_order_cancelled,
    send_payment_confirmed,
    send_welcome_email,
)
from .models import NewsletterSubscriber
import csv
import io


# ReportLab (PDF / POS / Invoice)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib import colors


views = Blueprint("views", __name__)

YOUR_UPI_ID = "ronipatel3105-1@oksbi"
YOUR_NAME   = "GreenMart"
UPLOAD_FOLDER = "website/static/payment_screenshots"


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required!")
            return redirect(url_for("views.home"))
        return f(*args, **kwargs)
    return decorated_function


def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("views.home"))
        if current_user.role != "customer":
            return redirect(url_for("views.home"))
        return f(*args, **kwargs)
    return decorated_function


@views.route("/search")
def search():
    q = request.args.get("q", "").strip()

    # AJAX / live suggestion call mate JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not q:
            return jsonify([])
        products = Product.query.filter(Product.name.ilike(f"%{q}%")).limit(8).all()
        return jsonify([{
            "id":    p.id,
            "name":  p.name,
            "price": p.price,
            "image": p.image,
            "stock": p.stock,
        } for p in products])

    # Normal page load mate template
    products = Product.query.filter(Product.name.ilike(f"%{q}%")).all() if q else []
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template("search.html",
                           products=products,
                           query=q,
                           login_form=login_form,
                           signup_form=signup_form)


# 404 fix — /api/search_suggestions route add karo
@views.route("/api/search_suggestions")
def search_suggestions():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    products = Product.query.filter(Product.name.ilike(f"%{q}%")).limit(8).all()
    return jsonify([{
        "id":    p.id,
        "name":  p.name,
        "price": p.price,
        "image": "/" + p.image if not p.image.startswith("/") else p.image,
        "stock": p.stock,
    } for p in products])


@views.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    email = request.form.get('email', '').strip().lower()

    if not email:
        return jsonify({'success': False, 'message': 'Email દાખલ કરો!'})

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            return jsonify({'success': False, 'message': '⚠️ આ email already subscribed છે!'})
        existing.is_active = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Welcome back! Re-subscribed ✅'})

    subscriber = NewsletterSubscriber(email=email)
    db.session.add(subscriber)
    db.session.commit()

    try:
        msg = Message(subject="Welcome to GreenMart Newsletter! 🌿", recipients=[email])
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;
                    border-radius:12px;overflow:hidden;border:1px solid #e0e0e0;">
            <div style="background:linear-gradient(135deg,#1a4a22,#2e7d32);
                        padding:32px;text-align:center;">
                <h1 style="color:white;margin:0;font-size:26px;">🌿 GreenMart</h1>
                <p style="color:#a5d6a7;margin:6px 0 0;">Fresh & Organic</p>
            </div>
            <div style="padding:32px;background:#fff;">
                <h2 style="color:#2e7d32;">You're subscribed! 🎉</h2>
                <p style="color:#555;line-height:1.7;">
                    Thank you for subscribing. You'll be the first to know about:</p>
                <ul style="color:#555;line-height:2;">
                    <li>🛒 Exclusive deals & discounts</li>
                    <li>🥦 Fresh arrivals & seasonal produce</li>
                    <li>🎁 Special offers & coupons</li>
                </ul>
            </div>
            <div style="background:#f5f5f5;padding:16px;text-align:center;">
                <p style="color:#888;font-size:12px;margin:0;">© 2026 GreenMart</p>
            </div>
        </div>"""
        mail.send(msg)
    except Exception as e:
        print(f"Newsletter Email Error: {e}")

    return jsonify({'success': True, 'message': '🎉 Subscribed! Check your email.'})



@views.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name")
    if name:
        current_user.name = name
        db.session.commit()
        flash("Profile updated successfully!", "success")
    else:
        flash("Name cannot be empty.", "danger")
    return redirect(url_for("views.profile"))


@views.route("/change_password", methods=["POST"])
@login_required
def change_password():
    old_password     = request.form.get("old_password")
    new_password     = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if not current_user.check_password(old_password):
        flash("Old password is incorrect!", "danger")
        return redirect(url_for("views.profile"))

    if new_password != confirm_password:
        flash("New password and confirmation do not match!", "danger")
        return redirect(url_for("views.profile"))

    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash("Password changed successfully!", "success")
    return redirect(url_for("views.profile"))


# ------------------------------------------------
# HOME
# ------------------------------------------------
# ─────────────────────────────────────────────────────────────────────
# REPLACE your existing home() function in views.py with this version
# ─────────────────────────────────────────────────────────────────────

@views.route("/", methods=["GET", "POST"])
def home():
    categories = Category.query.all()

    if current_user.is_authenticated and current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    signup_form = SignupForm()
    login_form  = LoginForm()

    # ✅ Recently Viewed — server side
    rv_products = []
    if current_user.is_authenticated:
        from .models import RecentlyViewed
        rv_items = RecentlyViewed.query.filter_by(user_id=current_user.id)\
                    .order_by(RecentlyViewed.viewed_at.desc()).limit(8).all()
        rv_products = [item.product for item in rv_items if item.product]
    else:
        rv_ids = session.get("recently_viewed", [])
        for pid in rv_ids:
            p = Product.query.get(pid)
            if p:
                rv_products.append(p)

    if login_form.validate_on_submit() and login_form.submit.data:
        user = User.query.filter_by(email=login_form.email.data).first()
        if user and user.check_password(login_form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            else:
                return redirect(url_for("views.home"))
        flash("Invalid email or password", "danger")

    if signup_form.validate_on_submit() and signup_form.submit.data:
        existing_user = User.query.filter_by(email=signup_form.email.data).first()
        if existing_user:
            flash("Email already registered", "danger")
        else:
            user = User(
                name=signup_form.name.data,
                email=signup_form.email.data,
                role="customer",
            )
            user.set_password(signup_form.password.data)
            db.session.add(user)
            db.session.commit()
            try:
                send_welcome_email(user)
            except Exception as e:
                print("Welcome Email Error:", e)
            flash("Account created! Please login.", "success")
            return redirect(url_for("views.home"))

    best_sellers = Product.query.filter(Product.id <= 10).all()
    trending     = Product.query.filter(Product.id > 10, Product.id <= 18).all()
    tab_best     = Product.query.filter(Product.id <= 10).all()
    tab_bread    = Product.query.join(Category).filter(Category.name == "Bakery").limit(4).all()
    tab_juices   = Product.query.join(Category).filter(Category.name == "Juices").limit(4).all()
    tab_organic  = Product.query.join(Category).filter(
        Category.name.in_(["Grains", "Nuts & Seeds"])
    ).limit(5).all()
    tab_fruits   = Product.query.join(Category).filter(
        Category.name.in_(["Fruits", "Vegetables"])
    ).limit(6).all()

    return render_template(
        "home.html",
        testimonials=Testimonial.query.filter_by(status='approved')
            .order_by(Testimonial.is_featured.desc(), Testimonial.moderated_at.desc())
            .limit(6).all(),

        signup_form  = signup_form,
        login_form   = login_form,
        user         = current_user,
        categories   = categories,
        best_sellers = best_sellers,
        trending     = trending,
        tab_best     = tab_best,
        tab_bread    = tab_bread,
        tab_juices   = tab_juices,
        tab_organic  = tab_organic,
        tab_fruits   = tab_fruits,
        rv_products  = rv_products,

        title       = "Farm Fresh",
        subtitle    = "Organic & Healthy",
        description = "Donec sed mauris non quam molestie imperdiet.<br>Integer ullamcorper, purus sit amet hendrerit tincidunt",
        image1  = "/static/images/1.jpg",
        image2  = "/static/images/2.jpg",
        image3  = "/static/images/3.jpg",
        image4  = "/static/images/4.jpg",
        image5  = "/static/images/5.jpg",
        image16 = "/static/images/dailyuse.jpg",
        image17 = "/static/images/bread.jpg",
        image18 = "/static/images/org-juice.jpg",
        image19 = "/static/images/discount.png",
        image20 = "/static/images/orgjuice.jpg",
        image21 = "/static/images/orgfruit.jpg",
        image35 = "/static/images/testimonial.jpg",
    )


# ------------------------------------------------
# LOGOUT
# ------------------------------------------------
@views.route("/logout")
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("views.home"))


# ------------------------------------------------
# PROFILE
# ------------------------------------------------
@views.route("/profile")
@login_required
def profile():
    login_form  = LoginForm()
    signup_form = SignupForm()
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    wallet = RewardWallet.query.filter_by(user_id=current_user.id).first()
    txns   = (RewardTransaction.query
              .filter_by(user_id=current_user.id)
              .order_by(RewardTransaction.created_at.desc())
              .limit(30).all())
    return render_template(
        "profile.html",
        user=current_user,
        orders=orders,
        login_form=login_form,
        signup_form=signup_form,
        wallet=wallet,
        txns=txns,
    )


@views.route("/orders")
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    order_list = []
    for order in orders:
        items = []
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                items.append({
                    "name":     product.name,        
                    "quantity": item.quantity,
                    "price":    item.price,
                    "subtotal": item.price * item.quantity,
                })
        order_list.append({
            "id":           f"ORD{order.id}",
            "total_amount": order.total_amount,
            "status":       order.status,
            "tracking_id":  order.tracking_id or "N/A",
            "created_at":   order.created_at.strftime("%d-%m-%Y %H:%M"),
            "items":        items,
        })
    return render_template("orders.html", orders=order_list)

# ------------------------------------------------
# PRODUCT DETAIL
# ------------------------------------------------
@views.route("/product/<int:product_id>")
def product_detail(product_id):
    product  = Product.query.get_or_404(product_id)
    reviews  = Review.query.filter_by(product_id=product_id)\
                           .order_by(Review.created_at.desc()).all()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0

    similar_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product_id
    ).limit(4).all()

    # ✅ DB ma recently viewed save karo (only logged in users)
    if current_user.is_authenticated:
        from .models import RecentlyViewed
        existing = RecentlyViewed.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first()
        if existing:
            existing.viewed_at = datetime.utcnow()  # timestamp refresh
        else:
            # Max 8 items rakho — oldest delete karo
            count = RecentlyViewed.query.filter_by(user_id=current_user.id).count()
            if count >= 8:
                oldest = RecentlyViewed.query.filter_by(user_id=current_user.id)\
                            .order_by(RecentlyViewed.viewed_at.asc()).first()
                if oldest:
                    db.session.delete(oldest)
            rv = RecentlyViewed(user_id=current_user.id, product_id=product_id)
            db.session.add(rv)
        db.session.commit()

    # Session fallback for guests
    else:
        viewed = session.get("recently_viewed", [])
        if product_id in viewed:
            viewed.remove(product_id)
        viewed.insert(0, product_id)
        session["recently_viewed"] = viewed[:8]
        session.modified = True

    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template("quick_view.html",
        product=product,
        reviews=reviews,
        avg_rating=avg_rating,
        similar_products=similar_products,
        login_form=login_form,
        signup_form=signup_form,
    )
        
# ================================================
# RECENTLY VIEWED
# ================================================
@views.route("/api/recently-viewed")
def recently_viewed_api():
    ids = session.get("recently_viewed", [])
    products = []
    for pid in ids:
        p = Product.query.get(pid)
        if p:
            products.append({
                "id":    p.id,
                "name":  p.name,
                "price": p.price,
                "image": p.image,
                "stock": p.stock,
                "category": p.category.name if p.category else "",
            })
    return jsonify(products)


@views.route("/api/clear-recently-viewed", methods=["POST"])
@login_required
def clear_recently_viewed():
    from .models import RecentlyViewed
    if current_user.is_authenticated:
        RecentlyViewed.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    session.pop("recently_viewed", None)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})
    return redirect(url_for("views.home"))
    
@views.route("/product/<int:product_id>/review", methods=["POST"])
@login_required
def add_review(product_id):
    from flask_login import current_user
    rating  = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "").strip()

    # Already reviewed check
    existing = Review.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    if existing:
        flash("You have already given a review!", "warning")
        return redirect(url_for("views.product_detail", product_id=product_id))

    review = Review(
        user_id=current_user.id,
        product_id=product_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()
    flash("Review submit successfully, THANK YOU 🙏", "success")
    return redirect(url_for("views.product_detail", product_id=product_id))


@views.route("/best-deals")
def best_deals():
    signup_form = SignupForm()
    login_form  = LoginForm()
    return render_template(
        "best_deals.html",
        signup_form=signup_form,
        login_form=login_form,
        user=current_user,
        products=all_products,
        image6="/static/images/tomato.jpg",
        image7="/static/images/juice.jpg",
        image8="/static/images/brocoli.jpg",
        image9="/static/images/quinoa.jpg",
        image10="/static/images/grapes.jpg",
        image11="/static/images/oats.jpg",
        image12="/static/images/milk.jpg",
        image13="/static/images/spice.jpg",
        image14="/static/images/avocado.jpg",
        image15="/static/images/nuts.jpg",
        image27="/static/images/b2.jpg",
        image28="/static/images/green.jpg",
    )


@views.route("/about")
def about():
    signup_form = SignupForm()
    login_form  = LoginForm()
    return render_template(
        "about.html",
        signup_form=signup_form,
        login_form=login_form,
        user=current_user,
        products=all_products,
        image1="/static/images/about.jpg",
        image6="/static/images/tomato.jpg",
        image7="/static/images/juice.jpg",
        image2="/static/images/granola-jar.jpg",
        image3="/static/images/peas.jpg",
        image4="/static/images/corn.jpg",
        image5="/static/images/peanut-butter.jpg",
        image8="/static/images/j.jpg",
        image9="static/images/brown-rice.jpg",
        image10="/static/images/bread.jpg",
        image11="/static/images/almonds.jpg",
    )


@views.route('/contact', methods=['GET', 'POST'])
def contact():
    signup_form = SignupForm()
    login_form  = LoginForm()
    if request.method == 'POST':
        name    = request.form.get('name')
        email   = request.form.get('email')
        phone   = request.form.get('phone')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # DB માં save કરો
        new_msg = ContactMessage(
            name=name, email=email,
            phone=phone, subject=subject, message=message
        )
        db.session.add(new_msg)
        db.session.commit()

        # ── Email 1: User ને Confirmation ──────────────────
        try:
            user_mail = Message(
                subject="Thank you for contacting GreenMart! 🌿",
                recipients=[email]
            )
            user_mail.html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2e7d32, #66bb6a); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">🌿 GreenMart</h1>
                    <p style="color: #c8e6c9; margin: 5px 0 0;">Fresh & Organic</p>
                </div>

                <!-- Body -->
                <div style="padding: 30px; background: #ffffff;">
                    <h2 style="color: #2e7d32;">Hello {name}! 👋</h2>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">
                        Thank you for reaching out to us. We have received your message and our team will get back to you within <strong>24-48 hours</strong>.
                    </p>

                    <!-- Message Summary Box -->
                    <div style="background: #f1f8e9; border-left: 4px solid #66bb6a; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2e7d32; margin: 0 0 10px;">Your Message Summary</h3>
                        <p style="margin: 5px 0; color: #555;"><strong>Subject:</strong> {subject}</p>
                        <p style="margin: 5px 0; color: #555;"><strong>Message:</strong> {message}</p>
                    </div>

                    <p style="color: #555; font-size: 14px;">
                        If you have any urgent queries, feel free to reply to this email.
                    </p>
                </div>

                <!-- Footer -->
                <div style="background: #f5f5f5; padding: 20px; text-align: center; border-top: 1px solid #e0e0e0;">
                    <p style="color: #888; font-size: 13px; margin: 0;">
                        © 2026 GreenMart | Fresh & Organic Products
                    </p>
                    <p style="color: #888; font-size: 12px; margin: 5px 0 0;">
                        This is an automated email. Please do not reply directly.
                    </p>
                </div>
            </div>
            """
            mail.send(user_mail)

            # ── Email 2: Admin ને Notification ─────────────
            admin_mail = Message(
                subject=f"📬 New Contact: {subject}",
                recipients=['your@gmail.com']  # Admin email
            )
            admin_mail.html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
                
                <div style="background: #2e7d32; padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">📬 New Contact Message</h2>
                </div>

                <div style="padding: 25px; background: #ffffff;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; color: #888; width: 30%;"><strong>Name</strong></td>
                            <td style="padding: 10px; color: #333;">{name}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; color: #888;"><strong>Email</strong></td>
                            <td style="padding: 10px; color: #333;">{email}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; color: #888;"><strong>Phone</strong></td>
                            <td style="padding: 10px; color: #333;">{phone}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; color: #888;"><strong>Subject</strong></td>
                            <td style="padding: 10px; color: #333;">{subject}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; color: #888;"><strong>Message</strong></td>
                            <td style="padding: 10px; color: #333;">{message}</td>
                        </tr>
                    </table>
                </div>

                <div style="background: #f5f5f5; padding: 15px; text-align: center;">
                    <p style="color: #888; font-size: 12px; margin: 0;">GreenMart Admin Panel Notification</p>
                </div>
            </div>
            """
            mail.send(admin_mail)

            flash('Message sent successfully! We will contact you soon. ✅', 'success')

        except Exception as e:
            print(f"Email Error: {e}")
            flash('Message saved! (Email notification pending)', 'warning')

        return redirect(url_for('views.contact'))

    return render_template('contact.html', 
                           signup_form=signup_form,
                           login_form=login_form,)

# ------------------------------------------------
# WISHLIST
# ------------------------------------------------
@views.route("/add_to_wishlist/<int:product_id>")
@login_required
def add_to_wishlist(product_id):
    exists = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not exists:
        wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        flash("Item added to Wishlist!", "success")
    else:
        flash("Item already in Wishlist!", "info")
    return redirect(request.referrer or url_for("views.home"))


@views.route("/remove_wishlist_item/<int:product_id>", methods=["POST"])
@login_required
def remove_wishlist_item(product_id):
    item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed!", "danger")
    return redirect(url_for("views.wishlist"))


@views.route("/clear_wishlist", methods=["POST"])
@login_required
def clear_wishlist():
    Wishlist.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Wishlist cleared!", "danger")
    return redirect(url_for("views.wishlist"))


# ------------------------------------------------
# CART
# ------------------------------------------------
@views.route("/add_to_cart/<int:product_id>", methods=["POST", "GET"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)

    variant_id = request.form.get('variant_id') or None
    variant_id = int(variant_id) if variant_id else None

    if variant_id:
        variant = ProductVariant.query.get_or_404(variant_id)
        price = variant.price
    else:
        price = product.price

    cart_item = Cart.query.filter_by(
        user_id=current_user.id,
        product_id=product_id,
        variant_id=variant_id
    ).first()

    if cart_item:
        cart_item.quantity += 1
        # ✅ Variant price update karo, but custom_price sirf variant mate
        if variant_id:
            cart_item.custom_price = price
        flash("Quantity updated in Cart!", "info")
    else:
        cart_item = Cart(
            user_id=current_user.id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=1,
            # ✅ Variant hoy to custom_price = variant price, nahitar None
            custom_price=price if variant_id else None,
        )
        db.session.add(cart_item)
        flash("Item added to Cart!", "success")

    wishlist_item = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    if wishlist_item:
        db.session.delete(wishlist_item)

    db.session.commit()
    return redirect(request.referrer or url_for("views.shop"))


@views.route("/wishlist")
@login_required
def wishlist():
    login_form     = LoginForm()
    signup_form    = SignupForm()
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
 
    products = []
    for item in wishlist_items:
        product = Product.query.get(item.product_id)   # ✅ fetch from DB, not static list
        if product:
            products.append(product)
 
    return render_template(
        "wishlist.html",
        wishlist    = products,
        login_form  = login_form,
        signup_form = signup_form,
    )
 

@views.route("/cart")
@login_required
def cart():
    login_form  = LoginForm()
    signup_form = SignupForm()
    cart_items  = Cart.query.filter_by(user_id=current_user.id).all()
    products    = []
    total_price = 0
    now         = datetime.utcnow()

    for item in cart_items:
        product = Product.query.get(item.product_id)
        if not product:
            continue

        # ✅ Variant label
        variant_label = None
        if item.variant_id:
            variant = ProductVariant.query.get(item.variant_id)
            if variant:
                variant_label = variant.label

        effective_price = product.price
        discount_pct    = 0
        sale_label      = None

        # ── Priority 1: custom_price (bundle deal only — no variant) ────────
        if item.custom_price and item.custom_price < product.price and not item.variant_id:
            effective_price = item.custom_price
            discount_pct    = round((1 - item.custom_price / product.price) * 100, 1)
            sale_label      = "Bundle Deal"

        # ── Priority 2: Variant custom price (no discount badge) ────────────
        elif item.custom_price and item.variant_id:
            effective_price = item.custom_price

        # ── Priority 3: ProductSale ──────────────────────────────────────────
        else:
            sale = ProductSale.query.filter_by(
                product_id=product.id,
                is_active=True
            ).first()
            if sale and sale.is_live:
                effective_price = round(product.price * (1 - sale.discount_pct / 100), 2)
                discount_pct    = sale.discount_pct
                sale_label      = sale.label or "Sale"

        subtotal = round(effective_price * item.quantity, 2)

        products.append({
            "id":             product.id,
            "name":           product.name,
            "variant_label":  variant_label,  # ✅ NEW
            "price":          effective_price,
            "original_price": product.price,
            "discount_pct":   discount_pct,
            "sale_label":     sale_label,
            "image":          product.image,
            "quantity":       item.quantity,
            "subtotal":       subtotal,
            "stock":          product.stock,
        })
        total_price += subtotal

    total_price = round(total_price, 2)

    return render_template(
        "cart.html",
        cart=products,
        total_price=total_price,
        login_form=login_form,
        signup_form=signup_form,
    )

@views.route("/update_cart/<int:product_id>/<string:action>", methods=["POST"])
@login_required
def update_cart(product_id, action):
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        if action == "increase":
            cart_item.quantity += 1
        elif action == "decrease":
            cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                db.session.delete(cart_item)
        db.session.commit()
    return redirect(url_for("views.cart"))


@views.route("/clear_cart", methods=["POST"])
@login_required
def clear_cart():
    Cart.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Cart cleared!", "danger")
    return redirect(url_for("views.cart"))


@views.route("/remove_cart_item/<int:product_id>", methods=["POST"])
@login_required
def remove_cart_item(product_id):
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed from Cart!", "danger")
    return redirect(url_for("views.cart"))


# ------------------------------------------------
# SHOP
# ------------------------------------------------
@views.route("/shop")
@login_required
@customer_required
def shop():
    signup_form = SignupForm()
    login_form  = LoginForm()

    fruits_veg    = Product.query.join(Category).filter(Category.name.in_(["Fruits", "Vegetables"])).all()
    dairy_bev     = Product.query.join(Category).filter(Category.name.in_(["Dairy", "Juices", "Beverages"])).all()
    grains_nuts   = Product.query.join(Category).filter(Category.name.in_(["Grains", "Nuts & Seeds"])).all()
    spices_snacks = Product.query.join(Category).filter(Category.name.in_(["Spices", "Snacks"])).all()
    frozen        = Product.query.join(Category).filter(Category.name == "Frozen").all()
    personal      = Product.query.join(Category).filter(Category.name == "Personal Care").all()
    new_arrivals  = Product.query.order_by(Product.id.desc()).limit(10).all()

    return render_template(
        "shop.html",
        signup_form   = signup_form,
        login_form    = login_form,
        user          = current_user,
        fruits_veg    = fruits_veg,
        dairy_bev     = dairy_bev,
        grains_nuts   = grains_nuts,
        spices_snacks = spices_snacks,
        frozen        = frozen,
        personal      = personal,
        new_arrivals  = new_arrivals,
    )
    
# ================================================
# CHECKOUT  (COD)
# ================================================
# @views.route("/checkout", methods=["GET", "POST"])
# @login_required
# def checkout():
#     login_form  = LoginForm()
#     signup_form = SignupForm()

#     user_addresses  = Address.query.filter_by(user_id=current_user.id).all()
#     default_address = Address.query.filter_by(user_id=current_user.id, is_default=True).first()

#     cart_items_db  = Cart.query.filter_by(user_id=current_user.id).all()
#     subtotal       = 0
#     checkout_items = []

#     for item in cart_items_db:
#         product = Product.query.get(item.product_id)
#         if product:
#             total = product.price * item.quantity
#             subtotal += total
#             checkout_items.append({
#                 "id":       product.id,
#                 "name":     product.name,
#                 "price":    product.price,
#                 "quantity": item.quantity,
#                 "subtotal": total,
#                 "stock":    product.stock,
#             })

#     if request.method == "POST":
#         if not checkout_items:
#             return jsonify({"success": False, "message": "Cart is empty"})

#         address_id = request.form.get("address_id")
#         if address_id:
#             addr = Address.query.get(address_id)
#         else:
#             addr = Address(
#                 user_id=current_user.id,
#                 full_name=request.form.get("full_name"),
#                 phone=request.form.get("phone"),
#                 street=request.form.get("street"),
#                 city=request.form.get("city"),
#                 state=request.form.get("state"),
#                 pin=request.form.get("pin"),
#             )
#             db.session.add(addr)
#             db.session.flush()

#         try:
#             order = Order(
#                 user_id        = current_user.id,
#                 total_amount   = subtotal,
#                 status         = "Pending",
#                 payment_method = "cod",
#                 payment_status = "Unpaid",
#                 tracking_id    = generate_tracking_id(),  # ✅ AUTO TRACKING ID
#                 shipping_name  = addr.full_name,
#                 shipping_phone = addr.phone,
#                 shipping_street= addr.street,
#                 shipping_city  = addr.city,
#                 shipping_state = addr.state,
#                 shipping_pin   = addr.pin,
#             )
#             db.session.add(order)
#             db.session.flush()

#             for item in checkout_items:
#                 product = Product.query.get(item["id"])
#                 if product.stock < item["quantity"]:
#                     return jsonify({
#                         "success": False,
#                         "message": f"Only {product.stock} left for {product.name}"
#                     })
#                 product.stock -= item["quantity"]
#                 db.session.add(OrderItem(
#                     order_id   = order.id,
#                     product_id = product.id,
#                     quantity   = item["quantity"],
#                     price      = product.price,
#                 ))

#             Cart.query.filter_by(user_id=current_user.id).delete()
#             db.session.commit()

#             # ✅ ORDER CONFIRMED EMAIL
#             try:
#                 send_order_confirmed(order)
#             except Exception as e:
#                 print("Order Confirmed Email Error:", e)

#             return jsonify({"success": True, "order_id": f"ORD{order.id}"})

#         except Exception as e:
#             db.session.rollback()
#             print("Checkout Error:", e)
#             return jsonify({"success": False, "message": "Checkout failed"})

#     return render_template(
#         "checkout.html",
#         cart_items=checkout_items,
#         subtotal=subtotal,
#         user_addresses=user_addresses,
#         default_address=default_address,
#         login_form=login_form,
#         signup_form=signup_form,
#     )


# ─────────────────────────────────────────────────────────────
# આ routes views.py માં ઉમેરો (cancel_reasons route પછી)
# models import માં Coupon અને DeliveryZone ઉમેરો
# ─────────────────────────────────────────────────────────────

# models import line માં આ ઉમેરો:
# from .models import (db, User, Product, ContactMessage, Wishlist,
#     Cart, Order, OrderItem, Category, Address, generate_tracking_id,
#     Coupon, DeliveryZone)


# ═══════════════════════════════════════════════════════════
# COUPON APPLY — AJAX call
# POST /apply_coupon  →  {code, subtotal}
# ═══════════════════════════════════════════════════════════
@views.route("/apply_coupon", methods=["POST"])
@login_required
def apply_coupon():
    data     = request.get_json()
    code     = (data.get("code") or "").strip().upper()
    subtotal = float(data.get("subtotal", 0))

    if not code:
        return jsonify({"success": False, "message": "Coupon code દાખલ કરો!"})

    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        return jsonify({"success": False, "message": "Invalid coupon code!"})

    valid, msg = coupon.is_valid()
    if not valid:
        return jsonify({"success": False, "message": msg})

    discount, msg2 = coupon.calculate_discount(subtotal)
    if discount == 0:
        return jsonify({"success": False, "message": msg2})

    return jsonify({
        "success":  True,
        "discount": discount,
        "message":  f"🎉 Coupon applied! Rs.{discount:.0f} off!",
        "type":     coupon.coupon_type,
        "value":    coupon.discount_value,
    })


# ═══════════════════════════════════════════════════════════
# DELIVERY CHARGE — AJAX call
# GET /get_delivery_charge?city=Ahmedabad
# ═══════════════════════════════════════════════════════════
@views.route("/get_delivery_charge")
@login_required
def get_delivery_charge():
    city   = request.args.get("city", "").strip()
    charge = DeliveryZone.get_charge(city)
    return jsonify({
        "charge":  charge,
        "is_free": charge == 0,
        "message": "Free Delivery! 🎉" if charge == 0 else f"Delivery charge: Rs.{charge:.0f}",
    })


# ═══════════════════════════════════════════════════════════
# CHECKOUT (COD) — coupon + delivery charge support
# views.py માં હાલના checkout function ને replace કરો
# ═══════════════════════════════════════════════════════════
@views.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    login_form  = LoginForm()
    signup_form = SignupForm()
 
    user_addresses  = Address.query.filter_by(user_id=current_user.id).all()
    default_address = Address.query.filter_by(user_id=current_user.id, is_default=True).first()
 
    cart_items_db  = Cart.query.filter_by(user_id=current_user.id).all()
    subtotal       = 0
    checkout_items = []
 
    for item in cart_items_db:                                   # ✅ correct indent
        product = Product.query.get(item.product_id)            # ✅ indented inside for loop
        if product:
            unit_price = item.custom_price if item.custom_price else product.price
            total      = unit_price * item.quantity
            subtotal  += total
            checkout_items.append({
                "id":       product.id,
                "name":     product.name,
                "price":    unit_price,
                "quantity": item.quantity,
                "subtotal": total,
                "stock":    product.stock,
            })
 
    if request.method == "POST":
        if not checkout_items:
            return jsonify({"success": False, "message": "Cart is empty"})
 
        # ── Address ───────────────────────────────────────────────
        address_id = request.form.get("address_id")
        if address_id:
            addr = Address.query.get(address_id)
            if not addr:
                return jsonify({"success": False, "message": "Address not found!"})
        else:
            addr = Address(
                user_id   = current_user.id,
                full_name = request.form.get("full_name", ""),
                phone     = request.form.get("phone", ""),
                street    = request.form.get("street", ""),
                city      = request.form.get("city", ""),
                state     = request.form.get("state", ""),
                pin       = request.form.get("pin", ""),
            )
            db.session.add(addr)
            db.session.flush()
 
        # ── Delivery Charge ───────────────────────────────────────
        delivery_charge = DeliveryZone.get_charge(addr.city)
 
        # ── Coupon ────────────────────────────────────────────────
        coupon_code     = request.form.get("coupon_code", "").strip().upper()
        discount_amount = 0
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code).first()
            if coupon:
                valid, _ = coupon.is_valid()
                if valid:
                    discount_amount, _ = coupon.calculate_discount(subtotal)
                    coupon.used_count += 1
 
        # ── Reward Points Redemption ──────────────────────────────
        REDEEM_POINTS   = 50
        REDEEM_VALUE    = 50    # ₹50 discount for 50 points
        redeem_points   = request.form.get("redeem_points") == "on"
        points_discount = 0
 
        # ✅ get_or_create so it never crashes on None wallet
        wallet = RewardWallet.query.filter_by(user_id=current_user.id).first()
        if redeem_points and wallet and wallet.points >= REDEEM_POINTS:
            points_discount = REDEEM_VALUE
 
        # ── Final Total ───────────────────────────────────────────
        final_total = subtotal + delivery_charge - discount_amount - points_discount
        final_total = max(final_total, 0)
 
        try:
            order = Order(
                user_id         = current_user.id,
                total_amount    = final_total,
                status          = "Pending",
                payment_method  = "cod",
                payment_status  = "Unpaid",
                tracking_id     = generate_tracking_id(),
                coupon_code     = coupon_code or None,
                discount_amount = discount_amount,
                delivery_charge = delivery_charge,
                shipping_name   = addr.full_name,
                shipping_phone  = addr.phone,
                shipping_street = addr.street,
                shipping_city   = addr.city,
                shipping_state  = addr.state,
                shipping_pin    = addr.pin,
            )
            db.session.add(order)
            db.session.flush()
 
            for item in checkout_items:
                product = Product.query.get(item["id"])
                if product.stock < item["quantity"]:
                    db.session.rollback()
                    return jsonify({
                        "success": False,
                        "message": f"Only {product.stock} left for {product.name}"
                    })
                product.stock -= item["quantity"]
                db.session.add(OrderItem(
                    order_id   = order.id,
                    product_id = product.id,
                    quantity   = item["quantity"],
                    price      = item["price"],   # ✅ use unit_price, not product.price
                ))
 
            # ── Deduct reward points if redeemed ──────────────────
            if points_discount > 0 and wallet:
                wallet.points -= REDEEM_POINTS
                db.session.add(RewardTransaction(
                    user_id = current_user.id,
                    points  = -REDEEM_POINTS,
                    reason  = f"Redeemed for Order #ORD{order.id} (₹{REDEEM_VALUE} off)",
                ))
 
            Cart.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
 
            try:
                send_order_confirmed(order)
            except Exception as e:
                print("Order Confirmed Email Error:", e)
 
            return jsonify({"success": True, "order_id": f"ORD{order.id}"})
 
        except Exception as e:
            db.session.rollback()
            print("Checkout Error:", e)
            return jsonify({"success": False, "message": "Checkout failed. Please try again."})
 
    # ── GET request ───────────────────────────────────────────────
    wallet = RewardWallet.query.filter_by(user_id=current_user.id).first()
    return render_template(
        "checkout.html",
        cart_items       = checkout_items,
        subtotal         = subtotal,
        user_addresses   = user_addresses,
        default_address  = default_address,
        login_form       = login_form,
        signup_form      = signup_form,
        wallet           = wallet,
        available_points = wallet.points if wallet else 0,
    )
# ------------------------------------------------
# INVOICE
# ------------------------------------------------
@views.route("/invoice/<order_code>")
@login_required
def invoice(order_code):
    order_id = int(order_code.replace("ORD", ""))
    order    = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    items    = []
    subtotal = 0

    for item in order.items:
        product    = Product.query.get(item.product_id)
        line_total = item.price * item.quantity
        subtotal  += line_total
        items.append({
            "name":     product.name if product else "Product",
            "quantity": item.quantity,
            "price":    item.price,
            "total":    line_total
        })

    tax         = round(subtotal * 0.05, 2)
    grand_total = subtotal + tax

    return render_template(
        "invoice.html",
        order=order,
        items=items,
        subtotal=subtotal,
        tax=tax,
        grand_total=grand_total,
        user=current_user
    )


# @views.route("/invoice/pos/<order_code>")
# @login_required
# def pos_invoice(order_code):
#     order_id = int(order_code.replace("ORD", ""))
#     order    = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
#     buffer   = io.BytesIO()

#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=(80 * mm, 200 * mm),
#         rightMargin=10, leftMargin=10,
#         topMargin=10,  bottomMargin=10
#     )
#     styles   = getSampleStyleSheet()
#     elements = []

#     elements.append(Paragraph(
#         "<b>GREENMART</b><br/>Fresh & Organic Store<br/>----------------------",
#         styles["Title"]
#     ))
#     elements.append(Spacer(1, 6))
#     elements.append(Paragraph(
#         f"Invoice: ORD{order.id}<br/>Date: {order.created_at.strftime('%d-%m-%Y %H:%M')}<br/>Customer: {current_user.name}<br/>Tracking: {order.tracking_id or 'N/A'}<br/>----------------------",
#         styles["Normal"]
#     ))

#     data     = [["Item", "Qty", "Amt"]]
#     subtotal = 0
#     for item in order.items:
#         total    = item.price * item.quantity
#         subtotal += total
#         data.append([item.product.name[:12], str(item.quantity), f"{total:.2f}"])

#     table = Table(data, colWidths=[35*mm, 10*mm, 15*mm])
#     table.setStyle(TableStyle([
#         ("GRID",  (0,0), (-1,-1), 0.5, colors.black),
#         ("FONT",  (0,0), (-1, 0), "Helvetica-Bold"),
#         ("ALIGN", (1,1), (-1,-1), "CENTER"),
#     ]))
#     elements.append(table)
#     elements.append(Spacer(1, 6))

#     tax   = round(subtotal * 0.05, 2)
#     grand = subtotal + tax
#     elements.append(Paragraph(
#         f"----------------------<br/>Subtotal: ₹{subtotal:.2f}<br/>GST (5%): ₹{tax:.2f}<br/><b>Total: ₹{grand:.2f}</b><br/>----------------------<br/>Thank you....!!<br/>Visit Again!",
#         styles["Normal"]
#     ))

#     doc.build(elements)
#     buffer.seek(0)
#     return send_file(buffer, as_attachment=True, download_name=f"POS_ORD{order.id}.pdf", mimetype="application/pdf")

@views.route("/invoice/pos/<order_code>")
@login_required
def pos_invoice(order_code):
    from .pos_receipt import generate_pos_receipt
 
    order_id = int(order_code.replace("ORD", ""))
    order    = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
 
    buffer = generate_pos_receipt(order, current_user.name)
 
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"GreenMart_Receipt_ORD{order.id}.pdf",
        mimetype="application/pdf"
    )


# ------------------------------------------------
# ADDRESSES
# ------------------------------------------------
@views.route("/addresses", methods=["GET", "POST"])
@login_required
def addresses():
    if request.method == "POST":
        if request.form.get("is_default"):
            Address.query.filter_by(user_id=current_user.id, is_default=True).update({"is_default": False})
        new_addr = Address(
            user_id=current_user.id,
            full_name=request.form.get("full_name"),
            phone=request.form.get("phone"),
            street=request.form.get("street"),
            city=request.form.get("city"),
            state=request.form.get("state"),
            pin=request.form.get("pin"),
            is_default=bool(request.form.get("is_default"))
        )
        db.session.add(new_addr)
        db.session.commit()
        flash("Address saved!", "success")
        return redirect(url_for("views.addresses"))
    all_addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template("addresses.html", addresses=all_addresses)


@views.route("/delete_address/<int:addr_id>", methods=["POST"])
@login_required
def delete_address(addr_id):
    addr = Address.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    db.session.delete(addr)
    db.session.commit()
    flash("Address deleted!", "danger")
    return redirect(url_for("views.addresses"))


@views.route("/set_default_address/<int:addr_id>", methods=["POST"])
@login_required
def set_default_address(addr_id):
    Address.query.filter_by(user_id=current_user.id).update({"is_default": False})
    addr = Address.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    addr.is_default = True
    db.session.commit()
    flash("Default address set!", "success")
    return redirect(url_for("views.addresses"))


# ================================================
# UPI — QR Generate
# ================================================
@views.route("/generate_upi_qr/<int:amount>")
@login_required
def generate_upi_qr(amount):
    upi_url = (
        f"upi://pay?pa={YOUR_UPI_ID}"
        f"&pn={YOUR_NAME}"
        f"&am={amount}"
        f"&cu=INR"
        f"&tn=GreenMart-Order"
    )
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=4)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img    = qr.make_image(fill_color="#2d6a4f", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return jsonify({"qr": img_base64, "upi_url": upi_url, "upi_id": YOUR_UPI_ID})


# ================================================
# UPI — Payment Submit
# ================================================
@views.route("/submit_upi_payment", methods=["POST"])
@login_required
def submit_upi_payment():
    utr        = request.form.get("utr_number", "").strip()
    screenshot = request.files.get("payment_screenshot")
    address_id = request.form.get("address_id")

    if not utr and (not screenshot or not screenshot.filename):
        return jsonify({"success": False, "message": "UTR number અથવા Screenshot જરૂરી છે!"})

    if address_id:
        addr = Address.query.get(address_id)
        if not addr:
            return jsonify({"success": False, "message": "Address not found!"})
    else:
        class TempAddr:
            full_name = request.form.get("full_name", "")
            phone     = request.form.get("phone", "")
            street    = request.form.get("street", "")
            city      = request.form.get("city", "")
            state     = request.form.get("state", "")
            pin       = request.form.get("pin", "")
        addr = TempAddr()

        if request.form.get("save_address"):
            new_addr = Address(
                user_id=current_user.id,
                full_name=addr.full_name,
                phone=addr.phone,
                street=addr.street,
                city=addr.city,
                state=addr.state,
                pin=addr.pin,
            )
            db.session.add(new_addr)

    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({"success": False, "message": "Cart empty છે!"})

    subtotal       = 0
    checkout_items = []
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            subtotal += product.price * item.quantity
            checkout_items.append({"product": product, "qty": item.quantity})

    screenshot_path = None
    if screenshot and screenshot.filename:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        ts       = int(datetime.utcnow().timestamp())
        filename = f"pay_{current_user.id}_{ts}.jpg"
        screenshot.save(os.path.join(UPLOAD_FOLDER, filename))
        screenshot_path = f"payment_screenshots/{filename}"

    try:
        order = Order(
            user_id            = current_user.id,
            total_amount       = subtotal,
            status             = "Processing",
            payment_method     = "upi",
            payment_status     = "Pending Verification",
            tracking_id        = generate_tracking_id(),  # ✅ AUTO TRACKING ID
            utr_number         = utr or None,
            payment_screenshot = screenshot_path,
            shipping_name      = addr.full_name,
            shipping_phone     = addr.phone,
            shipping_street    = addr.street,
            shipping_city      = addr.city,
            shipping_state     = addr.state,
            shipping_pin       = addr.pin,
        )
        db.session.add(order)
        db.session.flush()

        for ci in checkout_items:
            product = ci["product"]
            if product.stock < ci["qty"]:
                db.session.rollback()
                return jsonify({
                    "success": False,
                    "message": f"'{product.name}' નો stock ઓછો છે! (Available: {product.stock})"
                })
            product.stock -= ci["qty"]
            db.session.add(OrderItem(
                order_id   = order.id,
                product_id = product.id,
                quantity   = ci["qty"],
                price      = product.price,
            ))

        Cart.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        # ✅ ORDER CONFIRMED EMAIL
        try:
            send_order_confirmed(order)
        except Exception as e:
            print("UPI Order Email Error:", e)

        return jsonify({"success": True, "order_id": f"ORD{order.id}"})

    except Exception as e:
        db.session.rollback()
        print("UPI Error:", e)
        return jsonify({"success": False, "message": "Order save failed."})


# ================================================
# ADMIN — Pending Payments List
# ================================================
@views.route("/admin/pending-payments")
@admin_required
def pending_payments():
    orders      = (Order.query.filter_by(payment_method="upi", payment_status="Pending Verification").order_by(Order.created_at.desc()).all())
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "admin/pending_payments.html",
        orders=orders,
        login_form=login_form,
        signup_form=signup_form,
    )


# ================================================
# ADMIN — Approve / Reject UPI Payment
# ================================================
@views.route("/admin/verify-payment/<int:order_id>", methods=["POST"])
@admin_required
def admin_verify_payment(order_id):
    action = request.form.get("action")
    order  = Order.query.get_or_404(order_id)

    if action == "approve":
        order.payment_status = "Paid"
        order.status         = "Confirmed"
        db.session.commit()

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

    return redirect(url_for("views.pending_payments"))


# ================================================
# CANCEL ORDER
# ================================================
CANCEL_REASONS = [
    "Changed my mind",
    "Ordered by mistake",
    "Found better price elsewhere",
    "Delivery time too long",
    "Duplicate order",
    "Payment issue",
    "Other",
]

@views.route("/cancel_order/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status not in ["Pending", "Processing"]:
        return jsonify({
            "success": False,
            "message": f"'{order.status}' order cancel nahi thay. Fakt Pending/Processing orders cancel thay."
        })

    reason = request.form.get("cancel_reason", "").strip()
    note   = request.form.get("cancel_note",   "").strip()

    if not reason:
        return jsonify({"success": False, "message": "Cancel reason select karo!"})

    try:
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity

        order.status         = "Cancelled"
        order.cancel_reason  = reason
        order.cancel_note    = note or None
        order.cancelled_at   = datetime.utcnow()
        order.cancel_flagged = True

        db.session.commit()

        try:
            send_order_cancelled(order)
        except Exception as e:
            print("Cancel Email Error:", e)

        return jsonify({
            "success":  True,
            "message":  "Order successfully cancelled!",
            "order_id": f"ORD{order.id}"
        })

    except Exception as e:
        db.session.rollback()
        print("Cancel Error:", e)
        return jsonify({"success": False, "message": "Cancel failed. Please try again."})


@views.route("/cancel_reasons")
@login_required
def cancel_reasons():
    return jsonify(CANCEL_REASONS)


# ================================================
# ADMIN — Cancelled Orders
# ================================================
@views.route("/admin/cancelled-orders")
@admin_required
def admin_cancelled_orders():
    orders      = Order.query.filter_by(status="Cancelled").order_by(Order.cancelled_at.desc()).all()
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "admin/cancelled_orders.html",
        orders=orders,
        login_form=login_form,
        signup_form=signup_form,
    )


@views.route("/admin/clear-cancel-flag/<int:order_id>", methods=["POST"])
@admin_required
def clear_cancel_flag(order_id):
    order = Order.query.get_or_404(order_id)
    order.cancel_flagged = False
    db.session.commit()
    flash(f"ORD{order.id} reviewed!", "success")
    return redirect(url_for("views.admin_cancelled_orders"))


# ------------------------------------------------
# CATEGORY PAGES
# ------------------------------------------------
@views.route("/dairy-beverages")
def dairy_beverages():
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "dairy_beverages.html",
        login_form=login_form,
        signup_form=signup_form,
        image17="/static/images/milk.jpg",
        image18="/static/images/buffelo.jpg",
        image19="/static/images/cheese.jpg",
        image20="/static/images/paneer.jpg",
        image21="/static/images/butter.jpg",
        image22="/static/images/ghee.jpg",
        image23="/static/images/curd.jpg",
        image24="/static/images/egg.jpg"
    )


@views.route("/grains-nuts")
def grains_nuts():
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "grains_nuts.html",
        login_form=login_form,
        signup_form=signup_form,
        image33="/static/images/almonds.jpg",
        image34="/static/images/cashew.jpg",
        image35="/static/images/nuts.jpg",
        image36="/static/images/peanut.jpg",
        image37="/static/images/pistachios.jpg",
        image38="/static/images/raisins.jpg",
        image39="/static/images/chia.jpg",
        image40="/static/images/flax.jpg",
        image41="/static/images/oats.jpg",
        image42="/static/images/quinoa.jpg"
    )


@views.route("/spices-snacks")
def spices_snacks():
    login_form  = LoginForm()
    signup_form = SignupForm()
    return render_template(
        "spices_snacks.html",
        login_form=login_form,
        signup_form=signup_form,
        image43="/static/images/redchilli.jpg",
        image44="/static/images/termeric.jpg",
        image45="/static/images/cumin.jpg",
        image46="/static/images/black-pepper.jpg",
        image47="/static/images/potato-chips.jpg",
        image48="/static/images/cookies.jpg",
    )
    
# ═══════════════════════════════════════════════════════════════════════
#  TESTIMONIAL ROUTES  — paste into views.py
#  Also add these imports at top of views.py:
#    from .models import Testimonial, RewardWallet, RewardTransaction, TestimonialRewardConfig
# ═══════════════════════════════════════════════════════════════════════

# ── Customer: Submit / Edit testimonial ─────────────────────────────
@views.route("/testimonial/submit", methods=["GET", "POST"])
@login_required
def submit_testimonial():
    login_form  = LoginForm()
    signup_form = SignupForm()

    # Already has one?
    existing = Testimonial.query.filter_by(user_id=current_user.id).first()

    # Collect only DELIVERED orders of this user for the "verified purchase" dropdown
    delivered_orders = Order.query.filter_by(
        user_id=current_user.id, status="Delivered"
    ).order_by(Order.created_at.desc()).all()

    if request.method == "POST":
        rating   = int(request.form.get("rating", 5))
        headline = request.form.get("headline", "").strip()
        body     = request.form.get("body", "").strip()
        order_id = request.form.get("order_id") or None
        product_id = request.form.get("product_id") or None

        if not headline or not body:
            flash("Please fill in the title and your review.", "danger")
            return redirect(url_for("views.submit_testimonial"))

        if len(body) < 30:
            flash("Your review is too short (min 30 characters).", "warning")
            return redirect(url_for("views.submit_testimonial"))

        if existing:
            # Allow resubmit only if previously rejected
            if existing.status == "approved":
                flash("Your testimonial is already approved and published! 🎉", "info")
                return redirect(url_for("views.profile"))
            # Update
            existing.rating     = rating
            existing.headline   = headline
            existing.body       = body
            existing.order_id   = int(order_id) if order_id else None
            existing.product_id = int(product_id) if product_id else None
            existing.status     = Testimonial.STATUS_PENDING
            existing.reward_given = False
            existing.admin_note = None
            existing.moderated_at = None
            db.session.commit()
            flash("✅ Testimonial updated & re-submitted for review!", "success")
        else:
            t = Testimonial(
                user_id    = current_user.id,
                rating     = rating,
                headline   = headline,
                body       = body,
                order_id   = int(order_id) if order_id else None,
                product_id = int(product_id) if product_id else None,
                status     = Testimonial.STATUS_PENDING,
            )
            db.session.add(t)
            db.session.commit()
            flash("✅ Testimonial submitted! You'll earn reward points once approved.", "success")

        return redirect(url_for("views.profile"))

    products = Product.query.order_by(Product.name).all()
    wallet   = RewardWallet.query.filter_by(user_id=current_user.id).first()

    return render_template(
        "submit_testimonial.html",
        login_form=login_form,
        signup_form=signup_form,
        existing=existing,
        delivered_orders=delivered_orders,
        products=products,
        reward_points=TestimonialRewardConfig.get_points(),
        wallet=wallet,
    )


# ── Public: Testimonials page (all approved) ────────────────────────
@views.route("/testimonials")
def testimonials_page():
    login_form  = LoginForm()
    signup_form = SignupForm()
    testimonials = (
        Testimonial.query
        .filter_by(status="approved")
        .order_by(Testimonial.is_featured.desc(), Testimonial.moderated_at.desc())
        .all()
    )
    return render_template(
        "testimonials.html",
        login_form=login_form,
        signup_form=signup_form,
        testimonials=testimonials,
    )


# ── Customer: Reward wallet page ────────────────────────────────────
@views.route("/my-rewards")
@login_required
def my_rewards():
    login_form  = LoginForm()
    signup_form = SignupForm()
    wallet = RewardWallet.query.filter_by(user_id=current_user.id).first()
    txns   = (RewardTransaction.query
              .filter_by(user_id=current_user.id)
              .order_by(RewardTransaction.created_at.desc())
              .limit(30).all())
    return render_template(
        "my_rewards.html",
        login_form=login_form,
        signup_form=signup_form,
        wallet=wallet,
        txns=txns,
    )


@views.route("/api/flash-sale")
def api_flash_sale():
    from datetime import datetime
    sale = FlashSale.query.filter_by(is_active=True).first()
 
    if not sale or not sale.is_live:
        return jsonify({"active": False})
 
    items = []
    for item in sale.items:
        p = item.product
        items.append({
            "product_id":     p.id,
            "name":           p.name,
            "image":          p.image,
            "original_price": float(p.price),
            "sale_price":     float(item.sale_price),
            "discount_pct":   float(item.discount_pct),
            "stock":          p.stock,
        })
 
    # ends_at UTC ISO — JS side 'Z' append karke correct parse karse
    ends_at_iso = sale.ends_at.strftime("%Y-%m-%dT%H:%M:%S")
 
    return jsonify({
        "active":            True,
        "sale_name":         sale.name,
        "seconds_remaining": sale.seconds_remaining,
        "ends_at":           ends_at_iso,   # UTC, no tz suffix — JS adds 'Z'
        "items":             items,
    })
 


# ── Check if a single product is on flash sale ───────────────
# Product detail page par badge dikhavva
@views.route("/api/flash-sale/product/<int:product_id>")
def api_flash_sale_product(product_id):
    from datetime import datetime
    sale = FlashSale.query.filter_by(is_active=True).first()

    if not sale or not sale.is_live:
        return jsonify({"on_sale": False})

    item = FlashSaleItem.query.filter_by(
        flash_sale_id=sale.id, product_id=product_id
    ).first()

    if not item:
        return jsonify({"on_sale": False})

    return jsonify({
        "on_sale":          True,
        "sale_name":        sale.name,
        "discount_pct":     item.discount_pct,
        "sale_price":       item.sale_price,
        "original_price":   item.product.price,
        "seconds_remaining": sale.seconds_remaining,
    })

# ── Public: Bundles listing page ────────────────────────────────────
@views.route("/bundles")
def bundles_page():
    login_form  = LoginForm()
    signup_form = SignupForm()
 
    bundles = (
        BundleGroup.query
        .filter_by(is_active=True)
        .order_by(BundleGroup.created_at.desc())
        .all()
    )
    # Only live bundles
    live_bundles = [b for b in bundles if b.is_live]
 
    return render_template(
        "bundles.html",
        bundles=live_bundles,
        login_form=login_form,
        signup_form=signup_form,
    )
 
 
# ── API: Add entire bundle to cart ──────────────────────────────────
@views.route("/api/bundle/<int:bundle_id>/add-to-cart", methods=["POST"])
@login_required
@csrf.exempt
def add_bundle_to_cart(bundle_id):
    bundle = BundleGroup.query.get_or_404(bundle_id)

    if not bundle.is_live:
        return jsonify({"success": False, "message": "Aa bundle currently available nathi!"})

    mrp_total       = bundle.mrp_total
    effective_price = bundle.effective_price

    # ✅ Safety check
    if not mrp_total or mrp_total == 0:
        return jsonify({"success": False, "message": "Bundle items not found!"})

    discount_ratio = effective_price / mrp_total  # e.g. 0.80 for 20% off

    added   = []
    skipped = []

    for item in bundle.items:
        product = item.product
        if not product or product.stock < item.quantity:
            skipped.append(product.name if product else "Unknown")
            continue

        # ✅ Per-product discounted price
        bundle_unit_price = round(product.price * discount_ratio, 2)

        cart_item = Cart.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first()

        if cart_item:
            # ✅ Existing item — quantity + custom_price dono update karo
            cart_item.quantity    += item.quantity
            cart_item.custom_price = bundle_unit_price
        else:
            cart_item = Cart(
                user_id      = current_user.id,
                product_id   = product.id,
                quantity     = item.quantity,
                custom_price = bundle_unit_price,  # ✅ discounted price
            )
            db.session.add(cart_item)

        added.append(product.name)

    db.session.commit()

    msg = f"✅ {len(added)} products cart ma add thaya! Bundle discount apply thayo."
    if skipped:
        msg += f" ⚠️ {len(skipped)} out of stock: {', '.join(skipped)}"

    return jsonify({
        "success":     True,
        "message":     msg,
        "added_count": len(added),
        "skipped":     skipped,
    })
 
 
# ── API: Bundle list for home/shop section (JSON) ───────────────────
@views.route("/api/bundles")
def api_bundles():
    bundles = BundleGroup.query.filter_by(is_active=True).all()
    live = [b for b in bundles if b.is_live]
 
    result = []
    for b in live:
        result.append({
            "id":           b.id,
            "name":         b.name,
            "description":  b.description,
            "deal_type":    b.deal_type,
            "badge_label":  b.badge_label,
            "mrp_total":    b.mrp_total,
            "effective_price": b.effective_price,
            "savings":      b.savings,
            "savings_pct":  b.savings_pct,
            "image":        b.image,
            "items": [{
                "product_id":   i.product_id,
                "name":         i.product.name,
                "image":        i.product.image,
                "price":        i.product.price,
                "quantity":     i.quantity,
            } for i in b.items if i.product],
        })
 
    return jsonify(result)

