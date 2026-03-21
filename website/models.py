from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import string

db = SQLAlchemy()


def generate_tracking_id():
    year = datetime.utcnow().year
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"GM-{year}-{code}"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(50), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role          = db.Column(db.String(20), default="customer")
    is_verified   = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = "product"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    price       = db.Column(db.Float, nullable=False)
    image       = db.Column(db.String(300))
    description = db.Column(db.String(500))
    stock       = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)


class ContactMessage(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    email      = db.Column(db.String(150), nullable=False)
    phone      = db.Column(db.String(50), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Wishlist(db.Model):
    __tablename__ = "wishlist"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_user_product"),
    )


class Cart(db.Model):
    __tablename__ = "cart"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity   = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship("User", backref=db.backref("cart_items", lazy=True))
    product    = db.relationship("Product")
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_cart_item"),
    )

    def __repr__(self):
        return f"<Cart user={self.user_id} product={self.product_id} qty={self.quantity}>"


# ═══════════════════════════════════════════════════════════
#  COUPON — flat = Rs.X off | percent = X% off
# ═══════════════════════════════════════════════════════════
class Coupon(db.Model):
    __tablename__  = "coupon"
    id             = db.Column(db.Integer, primary_key=True)
    code           = db.Column(db.String(20), unique=True, nullable=False)
    coupon_type    = db.Column(db.String(10), nullable=False, default="flat")
    discount_value = db.Column(db.Float, nullable=False)
    min_order      = db.Column(db.Float, default=0)
    max_discount   = db.Column(db.Float, nullable=True)
    is_active      = db.Column(db.Boolean, default=True)
    usage_limit    = db.Column(db.Integer, nullable=True)
    used_count     = db.Column(db.Integer, default=0)
    expires_at     = db.Column(db.DateTime, nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self):
        if not self.is_active:
            return False, "Coupon inactive છે."
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False, "Coupon expired થઈ ગયો છે."
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon limit પૂરી થઈ ગઈ છે."
        return True, "Valid"

    def calculate_discount(self, subtotal):
        if subtotal < self.min_order:
            return 0, f"Minimum order Rs.{self.min_order:.0f} જોઈએ."
        if self.coupon_type == "flat":
            return min(self.discount_value, subtotal), "OK"
        elif self.coupon_type == "percent":
            disc = subtotal * self.discount_value / 100
            if self.max_discount:
                disc = min(disc, self.max_discount)
            return round(disc, 2), "OK"
        return 0, "Invalid type"


# ═══════════════════════════════════════════════════════════
#  DELIVERY ZONE — city based charges
# ═══════════════════════════════════════════════════════════
class DeliveryZone(db.Model):
    __tablename__ = "delivery_zone"
    id        = db.Column(db.Integer, primary_key=True)
    city      = db.Column(db.String(100), nullable=False)
    charge    = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)

    @staticmethod
    def get_charge(city_name):
        if not city_name:
            return 50.0
        zone = DeliveryZone.query.filter(
            db.func.lower(DeliveryZone.city) == city_name.strip().lower(),
            DeliveryZone.is_active == True
        ).first()
        return zone.charge if zone else 50.0


class Order(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"))
    total_amount = db.Column(db.Float)
    status       = db.Column(db.String(20), default="Pending")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    tracking_id     = db.Column(db.String(20), nullable=True)
    coupon_code     = db.Column(db.String(20), nullable=True)
    discount_amount = db.Column(db.Float, default=0)
    delivery_charge = db.Column(db.Float, default=0)

    shipping_name   = db.Column(db.String(100))
    shipping_phone  = db.Column(db.String(15))
    shipping_street = db.Column(db.String(200))
    shipping_city   = db.Column(db.String(100))
    shipping_state  = db.Column(db.String(100))
    shipping_pin    = db.Column(db.String(10))

    payment_method     = db.Column(db.String(20), default="cod")
    payment_status     = db.Column(db.String(20), default="Unpaid")
    utr_number         = db.Column(db.String(50), nullable=True)
    payment_screenshot = db.Column(db.String(300), nullable=True)

    cancel_reason  = db.Column(db.String(200), nullable=True)
    cancel_note    = db.Column(db.String(500), nullable=True)
    cancelled_at   = db.Column(db.DateTime, nullable=True)
    cancel_flagged = db.Column(db.Boolean, default=False)

    user  = db.relationship("User", backref=db.backref("orders", lazy=True))
    items = db.relationship("OrderItem", backref="order", lazy=True)


class OrderItem(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("order.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity   = db.Column(db.Integer)
    price      = db.Column(db.Float)
    product    = db.relationship("Product")


class Category(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100))
    products = db.relationship("Product", backref="category")


class Address(db.Model):
    __tablename__ = "address"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name  = db.Column(db.String(100), nullable=False)
    phone      = db.Column(db.String(15), nullable=False)
    street     = db.Column(db.String(200), nullable=False)
    city       = db.Column(db.String(100), nullable=False)
    state      = db.Column(db.String(100), nullable=False)
    pin        = db.Column(db.String(10), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    user       = db.relationship("User", backref=db.backref("addresses", lazy=True))


class OTPVerification(db.Model):
    __tablename__ = "otp_verification"
    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(150), nullable=False, index=True)
    otp_code   = db.Column(db.String(6), nullable=False)
    purpose    = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used    = db.Column(db.Boolean, default=False)

    def is_valid(self):
        return not self.is_used and datetime.utcnow() < self.expires_at

    @staticmethod
    def generate(email, purpose):
        OTPVerification.query.filter_by(email=email, purpose=purpose).delete()
        otp = OTPVerification(
            email      = email,
            otp_code   = str(random.randint(100000, 999999)),
            purpose    = purpose,
            expires_at = datetime.utcnow() + timedelta(minutes=10)
        )
        return otp