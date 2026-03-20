from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from flask_mail import Message
from . import mail
from .models import db, User, OTPVerification
from .forms import SignupForm, LoginForm

auth = Blueprint('auth', __name__)


# ── OTP Email Helper ──────────────────────────────────────────
def send_otp_email(email, otp_code, purpose):
    if purpose == "signup":
        subject = "🌿 GreenMart — Email Verify OTP"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:32px;background:#f9fff9;border-radius:12px;border:1px solid #d1fae5;">
          <h2 style="color:#2d6a4f;text-align:center;">🌿 GreenMart</h2>
          <p style="color:#333;">Namaste! GreenMart account verify karva mate aa OTP use karo:</p>
          <div style="text-align:center;margin:28px 0;">
            <span style="font-size:36px;font-weight:800;letter-spacing:10px;color:#2d6a4f;background:#e1f5ee;padding:14px 28px;border-radius:12px;display:inline-block;">{otp_code}</span>
          </div>
          <p style="color:#888;font-size:13px;text-align:center;">⏱ Aa OTP <strong>10 minutes</strong> ma expire thase.</p>
          <p style="color:#aaa;font-size:12px;text-align:center;">GreenMart — Fresh &amp; Organic Store, Ahmedabad</p>
        </div>"""
    else:
        subject = "🔐 GreenMart — Password Reset OTP"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:32px;background:#fff5f5;border-radius:12px;border:1px solid #f5c6cb;">
          <h2 style="color:#2d6a4f;text-align:center;">🌿 GreenMart</h2>
          <p style="color:#333;">Taro password reset karva mate aa OTP use karo:</p>
          <div style="text-align:center;margin:28px 0;">
            <span style="font-size:36px;font-weight:800;letter-spacing:10px;color:#dc3545;background:#fff5f5;padding:14px 28px;border-radius:12px;display:inline-block;border:2px solid #f5c6cb;">{otp_code}</span>
          </div>
          <p style="color:#888;font-size:13px;text-align:center;">⏱ Aa OTP <strong>10 minutes</strong> ma expire thase.</p>
          <p style="color:#aaa;font-size:12px;text-align:center;">GreenMart — Fresh &amp; Organic Store, Ahmedabad</p>
        </div>"""
    msg = Message(subject=subject, recipients=[email], html=body)
    mail.send(msg)


# ── LOGIN ─────────────────────────────────────────────────────
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return redirect(url_for('views.home'))
    if not form.validate_on_submit():
        flash("Please fill login form correctly!", "danger")
        return redirect(url_for('views.home'))
    user = User.query.filter_by(email=form.email.data).first()
    if user and user.check_password(form.password.data):
        if hasattr(user, 'is_verified') and not user.is_verified:
            flash("Pehla email verify karo! Signup pharthi karo.", "danger")
            return redirect(url_for('views.home'))
        login_user(user)
        flash(f"Welcome back, {user.name}!", "success")
        next_page = request.args.get('next')
        if user.role == "admin":
            return redirect(url_for('admin.dashboard'))
        return redirect(next_page or url_for('views.home'))
    flash("Invalid email or password!", "danger")
    return redirect(url_for('views.home'))


# ── SIGNUP (form-based — fallback) ────────────────────────────
@auth.route('/signup', methods=['POST'])
def signup():
    form = SignupForm()
    if not form.validate_on_submit():
        flash("Signup failed. Please check details.", "danger")
        return redirect(url_for('views.home'))
    email = form.email.data.strip().lower()
    name  = form.name.data.strip()
    if User.query.filter_by(email=email).first():
        flash("Email already registered! Please login.", "danger")
        return redirect(url_for('views.home'))
    session["pending_signup"] = {
        "name":     name,
        "email":    email,
        "password": generate_password_hash(form.password.data)
    }
    otp = OTPVerification.generate(email, "signup")
    db.session.add(otp)
    db.session.commit()
    try:
        send_otp_email(email, otp.otp_code, "signup")
    except Exception as e:
        print("Mail Error:", e)
        flash("Email moklava ma error! SMTP config check karo.", "danger")
        return redirect(url_for('views.home'))
    flash(f"OTP moklayo {email} par! 10 minutes ma verify karo.", "success")
    return redirect(url_for('auth.verify_otp_page', purpose="signup"))


# ── OTP PAGE (fallback — agar session thi aavo) ───────────────
@auth.route("/verify-otp/<purpose>")
def verify_otp_page(purpose):
    login_form  = LoginForm()
    signup_form = SignupForm()
    email = ""
    if purpose == "signup" and "pending_signup" in session:
        email = session["pending_signup"].get("email", "")
    elif purpose == "reset" and "reset_email" in session:
        email = session["reset_email"]
    return render_template("otp_verify.html", purpose=purpose, email=email,
                           login_form=login_form, signup_form=signup_form)


# ── OTP VERIFY (form-based — fallback) ────────────────────────
@auth.route("/verify-otp", methods=["POST"])
def verify_otp():
    purpose  = request.form.get("purpose")
    otp_code = request.form.get("otp_code", "").strip()

    if purpose == "signup":
        data = session.get("pending_signup")
        if not data:
            flash("Session expire thayi! Pharthi signup karo.", "danger")
            return redirect(url_for('views.home'))
        email  = data["email"]
        record = OTPVerification.query.filter_by(
            email=email, purpose="signup", is_used=False
        ).order_by(OTPVerification.id.desc()).first()
        if not record or not record.is_valid():
            flash("OTP expire thayo! Pharthi signup karo.", "danger")
            return redirect(url_for('views.home'))
        if record.otp_code != otp_code:
            flash("Wrong OTP! Pharthi try karo.", "danger")
            return redirect(url_for('auth.verify_otp_page', purpose="signup"))
        user = User(name=data["name"], email=data["email"], role="customer")
        user.password_hash = data["password"]
        if hasattr(user, 'is_verified'):
            user.is_verified = True
        db.session.add(user)
        record.is_used = True
        db.session.commit()
        session.pop("pending_signup", None)
        login_user(user)
        flash(f"Welcome {user.name}! Account verify thayo! 🎉", "success")
        return redirect(url_for('views.home'))

    elif purpose == "reset":
        email        = session.get("reset_email")
        new_password = session.get("reset_new_password")
        if not email or not new_password:
            flash("Session expire thayi!", "danger")
            return redirect(url_for('views.home'))
        record = OTPVerification.query.filter_by(
            email=email, purpose="reset", is_used=False
        ).order_by(OTPVerification.id.desc()).first()
        if not record or not record.is_valid():
            flash("OTP expire thayo!", "danger")
            return redirect(url_for('views.home'))
        if record.otp_code != otp_code:
            flash("Wrong OTP!", "danger")
            return redirect(url_for('auth.verify_otp_page', purpose="reset"))
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(new_password)
            record.is_used     = True
            db.session.commit()
        session.pop("reset_email", None)
        session.pop("reset_new_password", None)
        flash("Password successfully reset! Login karo.", "success")
        return redirect(url_for('views.home'))

    flash("Invalid request!", "danger")
    return redirect(url_for('views.home'))


# ── FORGOT PASSWORD (form-based) ──────────────────────────────
@auth.route("/forgot_password/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json()
    if not data or "email" not in data or "new_password" not in data:
        return jsonify({"status": "error", "message": "Invalid data sent."})
    email        = data["email"].strip().lower()
    new_password = data["new_password"]
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status": "error", "message": "Email registered nathi!"})
    session["reset_email"]        = email
    session["reset_new_password"] = new_password
    otp = OTPVerification.generate(email, "reset")
    db.session.add(otp)
    db.session.commit()
    try:
        send_otp_email(email, otp.otp_code, "reset")
        return jsonify({
            "status":  "otp_sent",
            "message": f"OTP moklayo {email} par!",
            "redirect": url_for("auth.verify_otp_page", purpose="reset")
        })
    except Exception as e:
        print("Reset Mail Error:", e)
        return jsonify({"status": "error", "message": "Email moklava ma error!"})


# ── LOGOUT ────────────────────────────────────────────────────
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('views.home'))


# ════════════════════════════════════════════════════════════
# AJAX ROUTES — Modal OTP (base.html sathe kaam kare)
# ════════════════════════════════════════════════════════════

@auth.route('/ajax/send-signup-otp', methods=['POST'])
def ajax_send_signup_otp():
    data     = request.get_json()
    name     = data.get('name',     '').strip()
    email    = data.get('email',    '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'Badha fields jaruri che!'})
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered!'})

    session['pending_signup'] = {
        'name':     name,
        'email':    email,
        'password': generate_password_hash(password)
    }

    otp = OTPVerification.generate(email, 'signup')
    db.session.add(otp)
    db.session.commit()

    try:
        send_otp_email(email, otp.otp_code, 'signup')
        return jsonify({'success': True, 'message': f'OTP moklayo {email} par!'})
    except Exception as e:
        print('OTP Mail Error:', e)
        return jsonify({'success': False, 'message': 'Email moklava ma error! SMTP check karo.'})


@auth.route('/ajax/verify-otp', methods=['POST'])
def ajax_verify_otp():
    data    = request.get_json()
    code    = data.get('code',    '').strip()
    purpose = data.get('purpose', '')

    if purpose == 'signup':
        pending = session.get('pending_signup')
        if not pending:
            return jsonify({'success': False, 'message': 'Session expire thayi! Pharthi try karo.'})
        email  = pending['email']
        record = OTPVerification.query.filter_by(
            email=email, purpose='signup', is_used=False
        ).order_by(OTPVerification.id.desc()).first()
        if not record or not record.is_valid():
            return jsonify({'success': False, 'message': 'OTP expire thayo! Resend karo.'})
        if record.otp_code != code:
            return jsonify({'success': False, 'message': 'Wrong OTP! Pharthi try karo.'})
        user = User(name=pending['name'], email=pending['email'], role='customer')
        user.password_hash = pending['password']
        if hasattr(user, 'is_verified'):
            user.is_verified = True
        db.session.add(user)
        record.is_used = True
        db.session.commit()
        session.pop('pending_signup', None)
        login_user(user)
        return jsonify({'success': True, 'message': f'Welcome {user.name}! Account verify thayo!'})

    elif purpose == 'reset':
        email        = session.get('reset_email')
        new_password = session.get('reset_new_password')
        if not email or not new_password:
            return jsonify({'success': False, 'message': 'Session expire thayi!'})
        record = OTPVerification.query.filter_by(
            email=email, purpose='reset', is_used=False
        ).order_by(OTPVerification.id.desc()).first()
        if not record or not record.is_valid():
            return jsonify({'success': False, 'message': 'OTP expire thayo! Resend karo.'})
        if record.otp_code != code:
            return jsonify({'success': False, 'message': 'Wrong OTP!'})
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(new_password)
            record.is_used     = True
            db.session.commit()
        session.pop('reset_email', None)
        session.pop('reset_new_password', None)
        return jsonify({'success': True, 'message': 'Password successfully reset! Login karo.'})

    return jsonify({'success': False, 'message': 'Invalid request!'})


@auth.route('/ajax/resend-otp/<purpose>', methods=['POST'])
def ajax_resend_otp(purpose):
    if purpose == 'signup':
        pending = session.get('pending_signup')
        if not pending:
            return jsonify({'success': False, 'message': 'Session expire thayi!'})
        email = pending['email']
    elif purpose == 'reset':
        email = session.get('reset_email')
        if not email:
            return jsonify({'success': False, 'message': 'Session expire thayi!'})
    else:
        return jsonify({'success': False, 'message': 'Invalid!'})

    otp = OTPVerification.generate(email, purpose)
    db.session.add(otp)
    db.session.commit()

    try:
        send_otp_email(email, otp.otp_code, purpose)
        return jsonify({'success': True, 'message': f'Navo OTP moklayo {email} par!'})
    except Exception as e:
        print('Resend Error:', e)
        return jsonify({'success': False, 'message': 'Email moklava ma error!'})