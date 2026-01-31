from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import db, User
from .forms import SignupForm, LoginForm
from flask_login import login_user, logout_user, login_required, current_user
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)


# ----------------------------------
# LOGIN
# ----------------------------------
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # 🔹 GET request → redirect to home (popup is there)
    if request.method == 'GET':
        return redirect(url_for('views.home'))

    # 🔹 POST request → login logic
    if not form.validate_on_submit():
        flash("Please fill login form correctly!", "danger")
        return redirect(url_for('views.home'))

    user = User.query.filter_by(email=form.email.data).first()

    if user and user.check_password(form.password.data):
        login_user(user)
        flash(f"Welcome back, {user.name}!", "success")

        next_page = request.args.get('next')
        return redirect(next_page or url_for('views.home'))

    flash("Invalid email or password!", "danger")
    return redirect(url_for('views.home'))



# ----------------------------------
# SIGNUP
# ----------------------------------
@auth.route('/signup', methods=['POST'])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for('views.home'))

    flash("Signup failed. Please check details.", "danger")
    return redirect(url_for('views.home'))


# ----------------------------------
# LOGOUT
# ----------------------------------
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('views.home'))

@auth.route("/forgot_password/reset_password", methods=["POST"])
def reset_password():
    data = request.json
    if not data or "email" not in data or "new_password" not in data:
        return jsonify({"status": "error", "message": "Invalid data sent."})

    user = User.query.filter_by(email=data["email"]).first()
    if user:
        user.password = generate_password_hash(data["new_password"])
        db.session.commit()
        return jsonify({"status": "ok", "message": "Password reset successfully!"})
    return jsonify({"status": "error", "message": "Email not found."})

