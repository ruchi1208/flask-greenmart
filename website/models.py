from __future__ import annotations
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

    @property
    def active_sale(self):
        """Returns ProductSale if currently live, else None."""
        sale = getattr(self, 'sale', None)
        return sale if (sale and sale.is_live) else None


class Review(db.Model):
    __tablename__ = "review"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)
    comment    = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user    = db.relationship("User", backref=db.backref("reviews", lazy=True))
    product = db.relationship("Product", backref=db.backref("reviews", lazy=True))

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_user_review"),
    )


class NewsletterSubscriber(db.Model):
    __tablename__  = "newsletter_subscriber"
    id             = db.Column(db.Integer, primary_key=True)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    is_active      = db.Column(db.Boolean, default=True)
    subscribed_at  = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=False)
    phone      = db.Column(db.String(20))
    subject    = db.Column(db.String(100))
    message    = db.Column(db.Text, nullable=False)
    is_read    = db.Column(db.Boolean, default=False)
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
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id   = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity     = db.Column(db.Integer, default=1, nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    custom_price = db.Column(db.Float, nullable=True)

    
    variant_id   = db.Column(db.Integer, db.ForeignKey("product_variant.id"), nullable=True)
    variant      = db.relationship("ProductVariant")

    user    = db.relationship("User", backref=db.backref("cart_items", lazy=True))
    product = db.relationship("Product")

    
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", "variant_id", name="unique_cart_item"),
    )

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

    
    variant_id    = db.Column(db.Integer, db.ForeignKey("product_variant.id"), nullable=True)
    variant_label = db.Column(db.String(50), nullable=True)   

    product = db.relationship("Product")
    variant = db.relationship("ProductVariant")


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


class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'

    id         = db.Column(db.String(64), primary_key=True)
    user_name  = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(150), nullable=True)
    status     = db.Column(db.String(20), default='active')
    ended_by   = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('ChatMessage', backref='session', lazy=True,
                                order_by='ChatMessage.timestamp')
    rating   = db.relationship('ChatRating', backref='session', uselist=False, lazy=True)

    def to_dict(self):
        last_msg = self.messages[-1] if self.messages else None
        unread   = sum(1 for m in self.messages if m.sender == 'user' and not m.is_read)
        return {
            'id':                self.id,
            'user_name':         self.user_name,
            'user_email':        self.user_email or '',
            'status':            self.status,
            'ended_by':          self.ended_by or '',
            'created_at':        self.created_at.strftime('%d %b %Y, %H:%M'),
            'last_message':      last_msg.message if last_msg else 'Chat started',
            'last_message_time': last_msg.timestamp.strftime('%H:%M') if last_msg else '',
            'unread_count':      unread,
            'rating':            self.rating.stars if self.rating else None,
            'rating_comment':    self.rating.comment if self.rating else '',
        }


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id          = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.String(64), db.ForeignKey('chat_sessions.id'), nullable=False)
    sender      = db.Column(db.String(10), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    message     = db.Column(db.Text, nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    is_read     = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id':          self.id,
            'session_id':  self.session_id,
            'sender':      self.sender,
            'sender_name': self.sender_name,
            'message':     self.message,
            'timestamp':   self.timestamp.strftime('%H:%M'),
            'is_read':     self.is_read,
        }


class QuickReply(db.Model):
    __tablename__ = 'quick_replies'

    id         = db.Column(db.Integer, primary_key=True)
    message    = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatRating(db.Model):
    __tablename__ = 'chat_ratings'

    id         = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('chat_sessions.id'), nullable=False, unique=True)
    stars      = db.Column(db.Integer, nullable=False)
    comment    = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'stars':      self.stars,
            'comment':    self.comment or '',
            'created_at': self.created_at.strftime('%d %b %Y, %H:%M'),
        }


class TestimonialRewardConfig(db.Model):
    __tablename__ = "testimonial_reward_config"
    id            = db.Column(db.Integer, primary_key=True)
    reward_points = db.Column(db.Integer, default=50, nullable=False)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_points():
        cfg = TestimonialRewardConfig.query.first()
        return cfg.reward_points if cfg else 50


class RewardWallet(db.Model):
    __tablename__ = "reward_wallet"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    points     = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("reward_wallet", uselist=False, lazy=True))

    @staticmethod
    def get_or_create(user_id):
        wallet = RewardWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = RewardWallet(user_id=user_id, points=0)
            db.session.add(wallet)
            db.session.flush()
        return wallet


class RewardTransaction(db.Model):
    __tablename__ = "reward_transaction"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    points      = db.Column(db.Integer, nullable=False)
    reason      = db.Column(db.String(200), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("reward_transactions", lazy=True))


class Testimonial(db.Model):
    __tablename__ = "testimonial"

    STATUS_PENDING  = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    rating      = db.Column(db.Integer, nullable=False)
    headline    = db.Column(db.String(120), nullable=False)
    body        = db.Column(db.Text, nullable=False)
    product_id  = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    order_id    = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=True)

    status           = db.Column(db.String(20), default="pending", nullable=False)
    admin_note       = db.Column(db.String(300), nullable=True)
    is_featured      = db.Column(db.Boolean, default=False)
    reward_given     = db.Column(db.Boolean, default=False)
    display_name     = db.Column(db.String(80), nullable=True)
    moderated_at     = db.Column(db.DateTime, nullable=True)
    moderated_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", name="unique_user_testimonial"),
    )

    user         = db.relationship("User", foreign_keys=[user_id],
                                   backref=db.backref("testimonial", uselist=False, lazy=True))
    product      = db.relationship("Product", backref=db.backref("testimonials", lazy=True))
    order        = db.relationship("Order", backref=db.backref("testimonial", uselist=False, lazy=True))
    moderated_by = db.relationship("User", foreign_keys=[moderated_by_id])

    def star_range(self):
        return range(1, 6)
    



class FlashSale(db.Model):
    __tablename__ = "flash_sale"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)   
    is_active   = db.Column(db.Boolean, default=False)
    starts_at   = db.Column(db.DateTime, nullable=False)
    ends_at     = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("FlashSaleItem", backref="sale", lazy=True,
                            cascade="all, delete-orphan")

    @property
    def is_live(self):
        now = datetime.utcnow()
        return self.is_active and self.starts_at <= now <= self.ends_at

    @property
    def seconds_remaining(self):
        if not self.is_live:
            return 0
        return int((self.ends_at - datetime.utcnow()).total_seconds())


class FlashSaleItem(db.Model):
    __tablename__ = "flash_sale_item"

    id              = db.Column(db.Integer, primary_key=True)
    flash_sale_id   = db.Column(db.Integer, db.ForeignKey("flash_sale.id"), nullable=False)
    product_id      = db.Column(db.Integer, db.ForeignKey("product.id"),    nullable=False)
    discount_pct    = db.Column(db.Float, nullable=False, default=10.0)  # 10 = 10%

    product = db.relationship("Product", backref="flash_items", lazy=True)

    @property
    def sale_price(self):
        return round(self.product.price * (1 - self.discount_pct / 100), 2)
    
class ProductSale(db.Model):
    __tablename__ = "product_sale"

    id           = db.Column(db.Integer, primary_key=True)
    product_id   = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, unique=True)
    discount_pct = db.Column(db.Float, nullable=False, default=10.0)
    label        = db.Column(db.String(50), nullable=True)
    is_active    = db.Column(db.Boolean, default=True)
    starts_at    = db.Column(db.DateTime, nullable=True)
    ends_at      = db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", backref=db.backref("sale", uselist=False, lazy=True))

    @property
    def is_live(self):
        if not self.is_active:
            return False
        now = datetime.utcnow()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    @property
    def sale_price(self):
        return round(self.product.price * (1 - self.discount_pct / 100), 2)

class BundleGroup(db.Model):
    """
    Ek bundle = multiple products nu group with a deal type.
    Deal types:
      'fixed'    — bundle mate fixed total price
      'percent'  — overall % discount on MRP sum
      'bxgy'     — Buy X Get Y free  (buy_qty / free_qty fields use thay)
      'free_qty' — Har product ni custom quantity set thay (BundleItem.quantity use thay)
    """
    __tablename__ = "bundle_groups"
 
    TYPES = [
        ("fixed",    "Fixed Price Bundle"),
        ("percent",  "Discount % on Bundle"),
        ("bxgy",     "Buy X Get Y Free"),
        ("free_qty", "Custom Qty per Product"),
    ]
 
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    description   = db.Column(db.Text, default="")
    deal_type     = db.Column(db.String(20), nullable=False, default="percent")  # fixed/percent/bxgy/free_qty
 
    # For 'fixed' — total bundle price
    fixed_price   = db.Column(db.Float, nullable=True)
 
    # For 'percent' — discount percentage
    discount_pct  = db.Column(db.Float, nullable=True)
 
    # For 'bxgy' — buy X get Y
    buy_qty       = db.Column(db.Integer, nullable=True)   # e.g. 2
    free_qty      = db.Column(db.Integer, nullable=True)   # e.g. 1
 
    # Display
    badge_label   = db.Column(db.String(60), default="")   # e.g. "🔥 Best Value"
    image         = db.Column(db.String(255), default="")  # optional hero image
    is_active     = db.Column(db.Boolean, default=True)
 
    # Validity window (optional)
    starts_at     = db.Column(db.DateTime, nullable=True)
    ends_at       = db.Column(db.DateTime, nullable=True)
 
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)
 
    items         = db.relationship(
        "BundleItem", back_populates="bundle",
        cascade="all, delete-orphan", lazy="select"
    )
 
    # ── Computed helpers ───────────────────────────────────────────
    @property
    def mrp_total(self):
        """Sum of all product MRPs × quantity"""
        return sum(
            (item.product.price * item.quantity)
            for item in self.items
            if item.product
        )
 
    @property
    def effective_price(self):
        """Final price customer pays"""
        if self.deal_type == "fixed" and self.fixed_price:
            return round(self.fixed_price, 2)
        if self.deal_type == "percent" and self.discount_pct:
            return round(self.mrp_total * (1 - self.discount_pct / 100), 2)
        if self.deal_type == "bxgy":
            # Cheapest free_qty items are free
            prices = sorted(
                [item.product.price for item in self.items if item.product],
                reverse=False
            )
            free_total = sum(prices[: self.free_qty or 0])
            return round(self.mrp_total - free_total, 2)
        # free_qty / default — MRP sum (discount already per item)
        return round(self.mrp_total, 2)
 
    @property
    def savings(self):
        return round(self.mrp_total - self.effective_price, 2)
 
    @property
    def savings_pct(self):
        if self.mrp_total == 0:
            return 0
        return round(self.savings / self.mrp_total * 100, 1)
 
    @property
    def is_live(self):
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True
 
    def __repr__(self):
        return f"<BundleGroup {self.id}: {self.name}>"
 
 
class BundleItem(db.Model):
    """One product inside a bundle, with an optional custom quantity."""
    __tablename__ = "bundle_items"
 
    id            = db.Column(db.Integer, primary_key=True)
    bundle_id     = db.Column(db.Integer, db.ForeignKey("bundle_groups.id"), nullable=False)
    product_id    = db.Column(db.Integer, db.ForeignKey("product.id"),       nullable=False)
    quantity      = db.Column(db.Integer, default=1)   # used for free_qty / custom bundles
 
    bundle        = db.relationship("BundleGroup", back_populates="items")
    product       = db.relationship("Product")
 
    def __repr__(self):
        return f"<BundleItem bundle={self.bundle_id} product={self.product_id} qty={self.quantity}>"
    

class ProductVariant(db.Model):
    __tablename__ = "product_variant"

    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    label      = db.Column(db.String(50), nullable=False)   # "250g", "500g", "1kg", "1L"
    price      = db.Column(db.Float, nullable=False)
    stock      = db.Column(db.Integer, default=0)
    is_active  = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)           # display order mate

    product = db.relationship("Product", backref=db.backref("variants", lazy=True))

    def __repr__(self):
        return f"<ProductVariant {self.product_id} | {self.label} | ₹{self.price}>"
    
        
class RecentlyViewed(db.Model):
    __tablename__ = "recently_viewed"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    viewed_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user    = db.relationship("User", backref=db.backref("recently_viewed", lazy=True))
    product = db.relationship("Product")

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_user_product_view"),
    )