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

from werkzeug.security import generate_password_hash
from functools import wraps
import io

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
)

# Forms & Products
from .forms import SignupForm, LoginForm
from .products import all_products

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
            return redirect(url_for("views.home"))  # ✅ HOME PAGE
        if current_user.role != "customer":
            return redirect(url_for("views.home"))  # ✅ HOME PAGE
        return f(*args, **kwargs)

    return decorated_function


@views.route("/search")
def search():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify([])

    products = Product.query.filter(Product.name.ilike(f"%{q}%")).limit(10).all()

    return jsonify(
        [
            {"id": p.id, "name": p.name, "price": p.price, "image": p.image}
            for p in products
        ]
    )


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
    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if not current_user.check_password(old_password):
        flash("Old password is incorrect!", "danger")
        return redirect(url_for("views.profile"))

    if new_password != confirm_password:
        flash("New password and confirmation do not match!", "danger")
        return redirect(url_for("views.profile"))

    # Update password
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash("Password changed successfully!", "success")
    return redirect(url_for("views.profile"))


# ------------------------------------------------
# HOME + LOGIN + SIGNUP
# ------------------------------------------------
@views.route("/", methods=["GET", "POST"])
def home():
    
    categories = Category.query.all()
    # 🔐 If admin already logged in → go to dashboard
    if current_user.is_authenticated and current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    signup_form = SignupForm()
    login_form = LoginForm()

    # ---------------- LOGIN ----------------
    if login_form.validate_on_submit() and login_form.submit.data:
        user = User.query.filter_by(email=login_form.email.data).first()

        if user and user.check_password(login_form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")

            # 🔁 Redirect based on role
            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            else:
                return redirect(url_for("views.home"))

        flash("Invalid email or password", "danger")

    # ---------------- SIGNUP ----------------
    if signup_form.validate_on_submit() and signup_form.submit.data:
        existing_user = User.query.filter_by(email=signup_form.email.data).first()

        if existing_user:
            flash("Email already registered", "danger")
        else:
            user = User(
                name=signup_form.name.data,
                email=signup_form.email.data,
                role="customer",  # ✅ explicit
            )
            user.set_password(signup_form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for("views.home"))

    # ---------------- RENDER HOME ----------------
    return render_template(
        "home.html",
        signup_form=signup_form,
        login_form=login_form,
        user=current_user,
        categories=categories,
        products=all_products,
        
        title="Farm Fresh",
        subtitle="Organic & Healthy",
        description="Donec sed mauris non quam molestie imperdiet.<br>Integer ullamcorper, purus sit amet hendrerit tincidunt",
        image1="/static/images/1.jpg",
        image2="/static/images/2.jpg",
        image3="/static/images/3.jpg",
        image4="/static/images/4.jpg",
        image5="/static/images/5.jpg",
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
        image16="/static/images/dailyuse.jpg",
        image17="/static/images/bread.jpg",
        image18="/static/images/org juice.jpg",
        image19="/static/images/discount.png",
        image20="/static/images/orgjuice.jpg",
        image21="/static/images/orgfruit.jpg",
        image22="/static/images/b1.jpg",
        image23="/static/images/b2.jpg",
        image24="/static/images/b3.jpg",
        image25="/static/images/organic.jpg",
        image26="/static/images/orange.jpg",
        image27="/static/images/mix.jpg",
        image28="/static/images/green.jpg",
        image29="/static/images/almonds.jpg",
        image30="/static/images/chia.jpg",
        image31="/static/images/Brown Rice.jpg",
        image32="/static/images/jaggary.jpg",
        image33="/static/images/spinach.jpg",
        image34="/static/images/apple.jpg",
        image35="/static/images/testimonial.jpg",
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
# PROFILE PAGE
# ------------------------------------------------
@views.route("/profile")
@login_required
def profile():
    login_form = LoginForm()
    signup_form = SignupForm()

    orders = (
        Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    )

    return render_template(
        "profile.html",
        user=current_user,
        orders=orders,
        login_form=login_form,
        signup_form=signup_form,
    )


@views.route("/orders")
@login_required
def orders():
    # Fetch all orders for the current user, latest first
    orders = (
        Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    )

    order_list = []
    for order in orders:
        items = []
        for item in order.items:
            # you can also fetch product name dynamically if needed
            product = Product.query.get(item.product_id)
            print("ORDER:", order)
            if product:
                items.append(
                    {
                        "name": item.name,
                        "quantity": item.quantity,
                        "price": item.price,
                        "subtotal": item.price * item.quantity,
                    }
                )
        order_list.append(
            {
                "id": f"ORD{order.id}",
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at.strftime("%d-%m-%Y %H:%M"),
                "items": items,
            }
        )

    return render_template("orders.html", orders=order_list)


# ------------------------------------------------
# QUICK VIEW PAGE
# ------------------------------------------------


@views.route("/product/<int:product_id>")
def product_detail(product_id):
    product = next((p for p in all_products if p["id"] == product_id), None)
    login_form = LoginForm()
    signup_form = SignupForm()  
    if product:
        return render_template(
            "quick_view.html",
            product=product,
            login_form=login_form,
            signup_form=signup_form, 
        )


@views.route("/best-deals")
def best_deals():
    signup_form = SignupForm()
    login_form = LoginForm()

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
    login_form = LoginForm()

    return render_template(
        "about.html",
        signup_form=signup_form,
        login_form=login_form,
        user=current_user,
        products=all_products,
        image1="/static/images/about.jpg",
        image6="/static/images/tomato.jpg",
        image7="/static/images/juice.jpg",
        image2="/static/images/Granola Jar.jpg",
        image3="/static/images/peas.jpg",
        image4="/static/images/corn.jpg",
        image5="/static/images/peanut butter.jpg",
        image8="/static/images/j.jpg",
        image9="static/images/Brown Rice.jpg",
        image10="/static/images/bread.jpg",
        image11="/static/images/almonds.jpg",
    )


@views.route("/contact", methods=["GET", "POST"])
def contact():
    login_form = LoginForm()
    signup_form = SignupForm()

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        if name and email and phone and message:
            new_message = ContactMessage(
                name=name, email=email, phone=phone, message=message
            )
            db.session.add(new_message)
            db.session.commit()
            flash("Your message has been sent successfully!", "success")
            return redirect(url_for("views.contact"))
        else:
            flash("Please fill out all fields.", "danger")

    
    return render_template(
        "contact.html", login_form=login_form, signup_form=signup_form
    )


#  Add to Wishlist
@views.route("/add_to_wishlist/<int:product_id>")
@login_required
def add_to_wishlist(product_id):

    exists = Wishlist.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if not exists:
        wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        flash("Item added to Wishlist!", "success")
    else:
        flash("Item already in Wishlist!", "info")

    return redirect(request.referrer or url_for("views.home"))


# 🔹 Remove Single Item From Wishlist
@views.route("/remove_wishlist_item/<int:product_id>", methods=["POST"])
@login_required
def remove_wishlist_item(product_id):

    item = Wishlist.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed!", "danger")

    return redirect(url_for("views.wishlist"))


# 🔹 Clear Complete Wishlist
@views.route("/clear_wishlist", methods=["POST"])
@login_required
def clear_wishlist():

    Wishlist.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    flash("Wishlist cleared!", "danger")
    return redirect(url_for("views.wishlist"))


# 🔹 Move to Cart
@views.route("/add_to_cart/<int:product_id>", methods=["POST", "GET"])
@login_required
def add_to_cart(product_id):

    cart_item = Cart.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity += 1
        flash("Quantity updated in Cart!", "info")
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
        flash("Item added to Cart!", "success")

    db.session.commit()
    return redirect(request.referrer or url_for("views.shop"))


# 🔹 Wishlist Page
@views.route("/wishlist")
@login_required
def wishlist():

    login_form = LoginForm()
    signup_form = SignupForm()

    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()

    products = []
    for item in wishlist_items:
        product = next((p for p in all_products if p["id"] == item.product_id), None)
        if product:
            products.append(product)

    return render_template(
        "wishlist.html",
        wishlist=products,
        login_form=login_form,
        signup_form=signup_form,
    )


@views.route("/cart")
@login_required
def cart():

    login_form = LoginForm()
    signup_form = SignupForm()

    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    products = []
    total_price = 0

    for item in cart_items:
        product = next((p for p in all_products if p["id"] == item.product_id), None)
        if product:
            product["quantity"] = item.quantity
            product["subtotal"] = product["price"] * item.quantity
            total_price += product["subtotal"]
            products.append(product)

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

    cart_item = Cart.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

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


@views.route("/shop")
@login_required
@customer_required
def shop():
    signup_form = SignupForm()
    login_form = LoginForm()

    return render_template(
        "shop.html",
        signup_form=signup_form,
        login_form=login_form,
        user=current_user,
        products=all_products,
        image1="/static/images/apple.jpg",
        image2="/static/images/grapes.jpg",
        image3="/static/images/banana.jpg",
        image4="/static/images/orange1.jpg",
        image5="/static/images/mango.jpg",
        image6="/static/images/pineapple.jpg",
        image7="/static/images/strawberrie.jpg",
        image8="/static/images/kiwi.jpg",
        image9="/static/images/tomato.jpg",
        image10="/static/images/brocoli.jpg",
        image11="/static/images/carrots.jpg",
        image12="/static/images/Spinach.jpg",
        image13="/static/images/lettuce.jpg",
        image14="/static/images/bell-pepper.jpg",
        image15="/static/images/cauliflower.jpg",
        image16="/static/images/cucumber.jpg",
        image17="/static/images/milk.jpg",
        image18="/static/images/buffelo.jpg",
        image19="/static/images/cheese.jpg",
        image20="/static/images/paneer.jpg",
        image21="/static/images/butter.jpg",
        image22="/static/images/ghee.jpg",
        image23="/static/images/curd.jpg",
        image24="/static/images/egg.jpg",
        image25="/static/images/orange.jpg",
        image26="/static/images/apple-juice.jpg",
        image27="/static/images/coconut.jpg",
        image28="/static/images/coffee.jpg",
        image29="/static/images/tea.jpg",
        image30="/static/images/leamon.jpg",
        image31="/static/images/drink.jpg",
        image32="/static/images/green.jpg",
        image33="/static/images/almonds.jpg",
        image34="/static/images/cashew.jpg",
        image35="/static/images/nuts.jpg",
        image36="/static/images/peanut.jpg",
        image37="static/images/pistachios.jpg",
        image38="static/images/raisins.jpg",
        image39="static/images/chia.jpg",
        image40="/static/images/flax.jpg",
        image41="/static/images/oats.jpg",
        image42="static/images/quinoa.jpg",
        image43="/static/images/redchilli.jpg",
        image44="/static/images/termeric.jpg",
        image45="/static/images/cumin.jpg",
        image46="/static/images/black-pepper.jpg",
        image47="/static/images/potato-chips.jpg",
        image48="/static/images/cookies.jpg",
        image49="/static/images/french-fries.jpg",
        image50="/static/images/momos.jpg",
        image51="/static/images/natural.jpg",
        image52="/static/images/ginger-cube.jpg",
        image53="/static/images/wedges.jpg",
        image54="/static/images/blueberry.jpg",
        image55="/static/images/gel.jpg",
        image56="/static/images/shampoo.jpg",
        image57="/static/images/lotion.jpg",
        image58="/static/images/wash.jpg",
        image59="/static/images/coconut-oil.jpg",
    )


# @views.route("/checkout", methods=["GET", "POST"])
# @login_required
# def checkout():
#     login_form = LoginForm()
#     signup_form = SignupForm()

#     # ================= CALCULATE CART =================
#     cart_items = Cart.query.filter_by(user_id=current_user.id).all()
#     subtotal = 0
#     checkout_items = []

#     for item in cart_items:
#         # Use `all_products` to get product details
#         product = next((p for p in all_products if p["id"] == item.product_id), None)
#         if product:
#             total = product["price"] * item.quantity
#             subtotal += total
#             checkout_items.append({
#                 "id": product["id"],
#                 "name": product["name"],
#                 "price": product["price"],
#                 "quantity": item.quantity,
#                 "subtotal": total,
#             })

#     # ================= POST =================
#     if request.method == "POST":
#         if not checkout_items:
#             # Safety check: no valid items
#             return redirect(url_for("views.cart"))

#         payment_method = request.form.get("payment_method")  # optional field

#         try:
#             # 🔹 CREATE ORDER (flush first to get ID without commit)
#             order = Order(
#                 user_id=current_user.id,
#                 total_amount=subtotal,
#                 status="success"  # or "pending" if payment is online
#             )
#             db.session.add(order)
#             db.session.flush()  # generates order.id

#             # 🔹 ADD ORDER ITEMS
#             for item in checkout_items:
#                 db.session.add(OrderItem(
#                     order_id=order.id,
#                     product_id=item["id"],
#                     quantity=item["quantity"],
#                     price=item["price"]
#                 ))

#             # 🔹 CLEAR CART
#             Cart.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)

#             # 🔹 FINAL COMMIT
#             db.session.commit()

#             # 🔹 Redirect GET to reload page & show empty cart
#             return redirect(url_for("views.checkout"))

#         except Exception as e:
#             db.session.rollback()
#             print("Checkout Error:", e)
#             return redirect(url_for("views.checkout"))

#     # ================= GET =================
#     return render_template(
#         "checkout.html",
#         cart_items=checkout_items,
#         subtotal=subtotal,
#         login_form=login_form,
#         signup_form=signup_form
#     )

# @views.route("/checkout", methods=["GET", "POST"])
# @login_required
# def checkout():
#     login_form = LoginForm()
#     signup_form = SignupForm()

#     # ================= CALCULATE CART =================
#     cart_items = Cart.query.filter_by(user_id=current_user.id).all()
#     subtotal = 0
#     checkout_items = []

#     for item in cart_items:
#         product = next((p for p in all_products if p["id"] == item.product_id), None)
#         if product:
#             total = product["price"] * item.quantity
#             subtotal += total
#             checkout_items.append({
#                 "id": product["id"],
#                 "name": product["name"],
#                 "price": product["price"],
#                 "quantity": item.quantity,
#                 "subtotal": total,
#             })

#     # ================= POST =================
#     if request.method == "POST":
#         if not checkout_items:
#             return jsonify({"success": False, "message": "Cart is empty"})

#         payment_method = request.form.get("payment_method")

#         try:
#             # CREATE ORDER
#             order = Order(
#                 user_id=current_user.id,
#                 total_amount=subtotal,
#                 status="success"
#             )
#             db.session.add(order)
#             db.session.flush()  # get order.id

#             # ADD ORDER ITEMS
#             for item in checkout_items:
#                 db.session.add(OrderItem(
#                     order_id=order.id,
#                     product_id=item["id"],
#                     quantity=item["quantity"],
#                     price=item["price"]
#                 ))

#             # CLEAR CART
#             Cart.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)

#             # FINAL COMMIT
#             db.session.commit()

#             # ✅ RETURN JSON for AJAX
#             return jsonify({
#                 "success": True,
#                 "order_id": f"ORD{order.id}"  # display-friendly order ID
#             })

#         except Exception as e:
#             db.session.rollback()
#             print("Checkout Error:", e)
#             return jsonify({"success": False, "message": "Something went wrong"})

#     # ================= GET =================
#     return render_template(
#         "checkout.html",
#         cart_items=checkout_items,
#         subtotal=subtotal,
#         login_form=login_form,
#         signup_form=signup_form
#     )

# @views.route("/orders")
# @login_required
# def order_history():
#     login_form = LoginForm()
#     signup_form = SignupForm()

#     user_orders = Order.query.filter_by(
#         user_id=current_user.id
#     ).order_by(Order.id.desc()).all()

#     orders_list = []
#     for order in user_orders:
#         orders_list.append({
#             "id": order.id,
#             "status": order.status,
#             "total": order.total_amount,   # ✅ MATCH TEMPLATE
#             "items_count": sum(item.quantity for item in order.items)
#         })

#     return render_template(
#         "profile.html",
#         orders=orders_list,
#         user=current_user,
#         login_form=login_form,
#         signup_form=signup_form
#     )


@views.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    login_form = LoginForm()
    signup_form = SignupForm()

    # ================= LOAD CART =================
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    subtotal = 0
    checkout_items = []

    for item in cart_items:
        product = Product.query.get(item.product_id)  # 🔥 use DB Product
        if product:
            total = product.price * item.quantity
            subtotal += total
            checkout_items.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "quantity": item.quantity,
                    "subtotal": total,
                    "stock": product.stock,
                }
            )

    # ================= PLACE ORDER =================
    if request.method == "POST":
        if not checkout_items:
            return jsonify({"success": False, "message": "Cart is empty"})

        try:
            # 1️⃣ Create Order
            order = Order(
                user_id=current_user.id, total_amount=subtotal, status="Pending"
            )
            db.session.add(order)
            db.session.flush()  # get order.id

            # 2️⃣ Process each product
            for item in checkout_items:
                product = Product.query.get(item["id"])

                # ❌ Block if stock not enough
                if product.stock < item["quantity"]:
                    return jsonify(
                        {
                            "success": False,
                            "message": f"Only {product.stock} left for {product.name}",
                        }
                    )

                # 🔥 Reduce stock
                product.stock -= item["quantity"]

                # Save order item
                db.session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=item["quantity"],
                        price=product.price,
                    )
                )

            # 3️⃣ Clear user cart
            Cart.query.filter_by(user_id=current_user.id).delete()

            # 4️⃣ Commit everything
            db.session.commit()

            return jsonify({"success": True, "order_id": f"ORD{order.id}"})

        except Exception as e:
            db.session.rollback()
            print("Checkout Error:", e)
            return jsonify({"success": False, "message": "Checkout failed"})

    # ================= PAGE LOAD =================
    return render_template(
        "checkout.html",
        cart_items=checkout_items,
        subtotal=subtotal,
        login_form=login_form,
        signup_form=signup_form,
    )


# @views.route("/offers")
# def offers():
#     login_form = LoginForm()
#     signup_form = SignupForm()

#     newest = Product.query.order_by(Product.id.desc()).limit(8).all()
#     cheapest = Product.query.order_by(Product.price.asc()).limit(8).all()
#     combined = list({p.id: p for p in (newest + cheapest)}.values())

#     return render_template(
#         "offers.html",
#         products=combined,
#         user=current_user,
#         login_form=login_form,
#         signup_form=signup_form
#     )

@views.route("/dairy-beverages")
def dairy_beverages():
    login_form = LoginForm()
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
    login_form = LoginForm()
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
    login_form = LoginForm()
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

@views.route("/invoice/<order_code>")
@login_required
def invoice(order_code):
    # Convert ORD9 → 9
    order_id = int(order_code.replace("ORD", ""))

    order = Order.query.filter_by(
        id=order_id,
        user_id=current_user.id
    ).first_or_404()

    items = []
    subtotal = 0

    for item in order.items:
        product = Product.query.get(item.product_id)
        line_total = item.price * item.quantity
        subtotal += line_total

        items.append({
            "name": product.name if product else "Product",
            "quantity": item.quantity,
            "price": item.price,
            "total": line_total
        })

    tax = round(subtotal * 0.05, 2)   # 5% GST
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


@views.route("/invoice/pos/<order_code>")
@login_required
def pos_invoice(order_code):
    order_id = int(order_code.replace("ORD", ""))

    order = Order.query.filter_by(
        id=order_id,
        user_id=current_user.id
    ).first_or_404()

    buffer = io.BytesIO()

    # 🧾 POS size (80mm width)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(80 * mm, 200 * mm),
        rightMargin=10,
        leftMargin=10,
        topMargin=10,
        bottomMargin=10
    )

    styles = getSampleStyleSheet()
    elements = []

    # 🟢 STORE HEADER
    elements.append(Paragraph(
        "<b>GREENMART</b><br/>Fresh & Organic Store<br/>----------------------",
        styles["Title"]
    ))

    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        f"""
        Invoice: ORD{order.id}<br/>
        Date: {order.created_at.strftime('%d-%m-%Y %H:%M')}<br/>
        Customer: {current_user.name}
        <br/>----------------------
        """,
        styles["Normal"]
    ))

    # 🧾 ITEMS
    data = [["Item", "Qty", "Amt"]]
    subtotal = 0

    for item in order.items:
        total = item.price * item.quantity
        subtotal += total
        data.append([
            item.product.name[:12],
            str(item.quantity),
            f"{total:.2f}"
        ])

    table = Table(data, colWidths=[35*mm, 10*mm, 15*mm])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 6))

    tax = round(subtotal * 0.05, 2)
    grand = subtotal + tax

    elements.append(Paragraph(
        f"""
        ----------------------<br/>
        Subtotal: ${subtotal:.2f}<br/>
        GST (5%): ${tax:.2f}<br/>
        <b>Total: ${grand:.2f}</b><br/>
        ----------------------<br/>
        Thank you....!!<br/>
        Visit Again!
        """,
        styles["Normal"]
    ))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"POS_ORD{order.id}.pdf",
        mimetype="application/pdf"
    )