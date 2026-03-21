from flask import Flask
from .models import db, User
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
import os

mail = Mail()  # ✅ Global — auth.py ma import karso

def create_app():
    app = Flask(__name__)

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
    app.config["MAIL_DEFAULT_SENDER"] = ("GreenMart", "YOUR_GMAIL@gmail.com")
    # ──────────────────────────────────────────────────────

    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)  # ✅ Mail init

    login_manager = LoginManager()
    login_manager.login_view = "admin.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .views import views
    from .auth import auth
    from .admin import admin

    app.register_blueprint(views)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    with app.app_context():
        os.makedirs("instance", exist_ok=True)
        db.create_all()

    return app