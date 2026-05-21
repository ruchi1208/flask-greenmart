from flask import Flask
from .models import db, User
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
import os
from flask import render_template
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import CSRFProtect, generate_csrf

mail = Mail()

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    
       # ── Custom 404 ──────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404
 
    # ── Custom 500 ──────────────────────────────────────────────────
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500
 
    # ── (Optional) 403 Forbidden ────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("404.html"), 403   # reuse 404 page
 

    app.config["SECRET_KEY"] = "greenmart_secret_2025"

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        BASE_DIR, "..", "instance", "greenmart.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── FLASK-MAIL CONFIG ──────────────────────────────────
    app.config["MAIL_SERVER"]         = "smtp.gmail.com"
    app.config["MAIL_PORT"]           = 587
    app.config["MAIL_USE_TLS"]        = True
    app.config["MAIL_USERNAME"]       = "greenmartatshopping@gmail.com"
    app.config["MAIL_PASSWORD"]       = "tpwr fjdo kvim mkta"
    app.config["MAIL_DEFAULT_SENDER"] = ("GreenMart", "greenmartatshopping@gmail.com")
    # ──────────────────────────────────────────────────────

    csrf.init_app(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "admin.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Blueprints register ────────────────────────────────
    from .views       import views
    from .auth        import auth
    from .admin       import admin
    # from .chat_routes import chat_bp

    app.register_blueprint(views)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    # app.register_blueprint(chat_bp)
    # ──────────────────────────────────────────────────────
    csrf.exempt(views)
    csrf.exempt(auth)
    csrf.exempt(admin)
    
    @app.after_request
    def set_csrf_cookie(response):
        generate_csrf()
        return response

    with app.app_context():
        os.makedirs("instance", exist_ok=True)
        db.create_all()

    return app