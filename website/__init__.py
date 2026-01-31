from flask import Flask
from .models import db, User
from flask_login import LoginManager
from flask_migrate import Migrate
import os

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "1234"

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        BASE_DIR, "..", "instance", "greenmart.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -------------------------
    # INIT DATABASE
    # -------------------------
    db.init_app(app)
    migrate = Migrate(app, db)

    # -------------------------
    # LOGIN MANAGER
    # -------------------------
    login_manager = LoginManager()
    login_manager.login_view = "admin.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # -------------------------
    # REGISTER BLUEPRINTS
    # -------------------------
    from .views import views
    from .auth import auth
    from .admin import admin

    app.register_blueprint(views)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    # -------------------------
    # CREATE DATABASE TABLES
    # -------------------------
    with app.app_context():
        os.makedirs("instance", exist_ok=True)
        db.create_all()

    return app
