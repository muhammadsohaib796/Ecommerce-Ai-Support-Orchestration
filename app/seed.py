from app.database import SessionLocal
from app.models import Customer, Product, ProductVariant, Order, OrderItem, Payment


def seed():
    db = SessionLocal()

    # Skip if the database already has data, so running this twice is safe
    if db.query(Customer).count() > 0:
        print("Database already has data, skipping seed")
        db.close()
        return

    # Customers
    ali = Customer(name="Ali Khan", email="ali@example.com", phone="03001111111")
    sara = Customer(name="Sara Ahmed", email="sara@example.com", phone="03002222222")
    bilal = Customer(name="Bilal Raza", email="bilal@example.com", phone="03003333333")
    ayesha = Customer(name="Ayesha Noor", email="ayesha@example.com", phone="03004444444")
    db.add_all([ali, sara, bilal, ayesha])

    # Products
    black_shirt = Product(name="Black Shirt")
    blue_shirt = Product(name="Blue Shirt")
    premium_shirt = Product(name="Premium Black Shirt")
    red_hoodie = Product(name="Red Hoodie")
    db.add_all([black_shirt, blue_shirt, premium_shirt, red_hoodie])
    db.flush()  # assigns ids so variants can reference them

    # Variants
    bs_m = ProductVariant(product_id=black_shirt.id, sku="BLK-SHIRT-M", size="M", color="Black", price=3500, stock_quantity=10)
    bs_l = ProductVariant(product_id=black_shirt.id, sku="BLK-SHIRT-L", size="L", color="Black", price=3500, stock_quantity=8)
    blu_m = ProductVariant(product_id=blue_shirt.id, sku="BLU-SHIRT-M", size="M", color="Blue", price=3500, stock_quantity=10)
    pbs_m = ProductVariant(product_id=premium_shirt.id, sku="PBLK-SHIRT-M", size="M", color="Black", price=4200, stock_quantity=6)
    rh_m = ProductVariant(product_id=red_hoodie.id, sku="RED-HOOD-M", size="M", color="Red", price=5000, stock_quantity=5)
    rh_l = ProductVariant(product_id=red_hoodie.id, sku="RED-HOOD-L", size="L", color="Red", price=5000, stock_quantity=0)
    db.add_all([bs_m, bs_l, blu_m, pbs_m, rh_m, rh_l])
    db.flush()

    # Orders: (order_number, customer, status, variant, price)
    orders = [
        ("ORD-1001", ali, "PLACED", bs_m, 3500),       # same price, size change
        ("ORD-1002", sara, "PLACED", blu_m, 3500),     # different price, color change
        ("ORD-1003", bilal, "PROCESSING", rh_m, 5000), # requested variant out of stock
        ("ORD-1004", ayesha, "SHIPPED", bs_m, 3500),   # already shipped
    ]

    for number, customer, status, variant, price in orders:
        order = Order(
            order_number=number,
            customer_id=customer.id,
            status=status,
            total_amount=price,
        )
        db.add(order)
        db.flush()

        db.add(OrderItem(order_id=order.id, variant_id=variant.id, quantity=1, unit_price=price))
        db.add(Payment(
            order_id=order.id,
            method="CARD",
            status="PAID",
            amount=price,
            reference=f"TXN-{number}",
        ))

    db.commit()
    db.close()
    print("Seed data created")


if __name__ == "__main__":
    seed()