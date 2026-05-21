from website import create_app
from website.models import db, Product, Category
from website.products import all_products

app = create_app()

with app.app_context():
    # Step 1 - Clear everything
    Product.query.delete()
    Category.query.delete()
    db.session.commit()
    print("✅ Cleared all products and categories")

    # Step 2 - Create categories
    category_names = list({p["category"] for p in all_products})
    cat_map = {}
    for name in category_names:
        c = Category(name=name)
        db.session.add(c)
        db.session.flush()
        cat_map[name] = c.id
    db.session.commit()
    print(f"✅ {len(category_names)} categories created: {category_names}")

    # Step 3 - Seed unique products only
    seen_ids = set()
    added = 0
    for p in all_products:
        if p["id"] in seen_ids:
            print(f"⚠️  Skipping duplicate id={p['id']} ({p['name']})")
            continue
        seen_ids.add(p["id"])
        product = Product(
            id          = p["id"],
            name        = p["name"],
            price       = p["price"],
            image       = p["image"],
            description = p.get("description", ""),
            stock       = 50,
            category_id = cat_map.get(p["category"]),
        )
        db.session.add(product)
        added += 1

    db.session.commit()
    print(f"✅ {added} unique products seeded!")
    print("🎉 Done! Restart Flask now.")