from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Order, OrderItem, Payment, Product, ProductVariant, Refund

router = APIRouter(prefix="/api", tags=["store"])


@router.get("/orders/{order_number}")
def get_order(order_number: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    customer = db.get(Customer, order.customer_id)

    # Join each order item with its variant and product
    rows = (
        db.query(OrderItem, ProductVariant, Product)
        .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(OrderItem.order_id == order.id)
        .all()
    )
    payments = db.query(Payment).filter(Payment.order_id == order.id).all()

    return {
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "created_at": order.created_at,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
        },
        "items": [
            {
                "product": product.name,
                "sku": variant.sku,
                "size": variant.size,
                "color": variant.color,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
            }
            for item, variant, product in rows
        ],
        "payments": [
            {
                "status": p.status,
                "method": p.method,
                "amount": float(p.amount),
                "reference": p.reference,
            }
            for p in payments
        ],
    }


@router.get("/inventory/{sku}")
def get_inventory(sku: str, db: Session = Depends(get_db)):
    row = (
        db.query(ProductVariant, Product)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(ProductVariant.sku == sku)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="SKU not found")

    variant, product = row
    return {
        "sku": variant.sku,
        "product": product.name,
        "size": variant.size,
        "color": variant.color,
        "price": float(variant.price),
        "stock_quantity": variant.stock_quantity,
        "in_stock": variant.stock_quantity > 0,
    }