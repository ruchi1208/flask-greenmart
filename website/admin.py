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
            stock=form.stock.data  
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


# ---------------- Manage Orders ----------------


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


@admin.route("/admin/products/delete/<int:id>", methods=["POST"])
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!")
    return redirect(url_for("admin.manage_products"))


@admin.route("/admin/orders/update/<int:id>", methods=["POST"])
@admin_required
def update_order_status(id):
    order = Order.query.get_or_404(id)
    new_status = request.form.get("status")
    order.status = new_status
    db.session.commit()
    flash("Order status updated!")
    return redirect(url_for("admin.manage_orders"))


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


@admin.route("/admin/reports")
@admin_required
def reports():
    login_form = LoginForm()
    signup_form = SignupForm()
    # Example stats, you can replace with real queries
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
        "admin/Manage_Categories.html",  # or rename the file to manage_categories.html
        form=form,
        login_form=login_form,
        signup_form=signup_form,
        categories=categories,
    )





@admin.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def settings():
    login_form = LoginForm()
    signup_form = SignupForm()
    # You can create a Settings model to store these
    form = SettingsForm()
    if form.validate_on_submit():
        # Save to database or config
        flash("Settings updated successfully!")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings.html", login_form=login_form, signup_form=signup_form, form=form
    )

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
