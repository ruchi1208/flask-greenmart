"""
Run once to seed products & categories into SQLite DB.
Usage:  python seed_products.py
Place this file in your project root (same level as run.py / app.py).
"""

from website import create_app
from website.models import db, Product, Category
from website.products import all_products

app = create_app()

with app.app_context():
    db.create_all()

    # ── 1. Build Category rows ────────────────────────────
    category_names = list({p["category"] for p in all_products})
    for name in category_names:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
    db.session.commit()
    print(f"✅ {len(category_names)} categories seeded.")

    # ── 2. Build Product rows ─────────────────────────────
    added = 0
    for p in all_products:
        if Product.query.get(p["id"]):
            continue  # skip if already exists

        category = Category.query.filter_by(name=p["category"]).first()

        # image path: products.py has "images/tomato.jpg"
        # → store as "/static/images/tomato.jpg" for url_for compatibility
        image_path = p["image"]
        if not image_path.startswith("/static/"):
            image_path = "/static/" + image_path

        product = Product(
            id          = p["id"],
            name        = p["name"],
            price       = p["price"],
            image       = image_path,
            description = p.get("description", ""),
            stock       = 50,          # default stock
            category_id = category.id if category else None,
        )
        db.session.add(product)
        added += 1

    db.session.commit()
    print(f"✅ {added} products seeded into database.")
    print("🎉 Done! Your DB is ready.")