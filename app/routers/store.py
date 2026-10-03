from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Customer,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    Refund,
)
from app.models.enums import (
    MODIFIABLE_ORDER_STATUSES,
    OrderStatus,
    PaymentStatus,
    RefundStatus,
)

router = APIRouter(prefix="/api", tags=["store"])


def get_order_or_404(db: Session, order_number: str) -> Order:
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def refund_to_dict(refund: Refund) -> dict:
    return {
        "refund_id": refund.id,
        "payment_id": refund.payment_id,
        "amount": float(refund.amount),
        "status": refund.status,
        "reference": refund.reference,
    }


class ModifyRequest(BaseModel):
    from_sku: str
    to_sku: str


class RefundRequest(BaseModel):
    order_number: str


@router.get("/orders/{order_number}")
def get_order(order_number: str, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_number)
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


@router.post("/orders/{order_number}/modify")
def modify_order(order_number: str, body: ModifyRequest, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_number)

    # Rule: an order can only be modified before it is packed
    if order.status not in MODIFIABLE_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Order can no longer be modified")

    old_variant = db.query(ProductVariant).filter(ProductVariant.sku == body.from_sku).first()
    new_variant = db.query(ProductVariant).filter(ProductVariant.sku == body.to_sku).first()
    if old_variant is None or new_variant is None:
        raise HTTPException(status_code=404, detail="SKU not found")

    item = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id, OrderItem.variant_id == old_variant.id)
        .first()
    )
    if item is None:
        # Also covers a repeated call: the item was already swapped
        raise HTTPException(status_code=400, detail="Order does not contain the from_sku item")

    # Rule: the MVP only swaps variants that cost the same
    if new_variant.price != item.unit_price:
        raise HTTPException(status_code=400, detail="Price differs, cancel and reorder instead")

    # Rule: the requested variant must have enough stock
    if new_variant.stock_quantity < item.quantity:
        if new_variant.stock_quantity == 0:
            detail = "Requested variant is out of stock"
        else:
            detail = (
                f"Only {new_variant.stock_quantity} available, "
                f"{item.quantity} needed"
            )
        raise HTTPException(status_code=400, detail=detail)

    # Swap the item and move stock from the new variant back to the old one
    old_variant.stock_quantity += item.quantity
    new_variant.stock_quantity -= item.quantity
    item.variant_id = new_variant.id
    db.commit()

    return {
        "order_number": order.order_number,
        "status": order.status,
        "from_sku": body.from_sku,
        "to_sku": body.to_sku,
        "message": f"Order modified {body.from_sku} to {body.to_sku}",
    }



@router.post("/orders/{order_number}/cancel")
def cancel_order(order_number: str, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_number)

    # Safe to call twice: an already cancelled order is returned as it is
    if order.status == OrderStatus.CANCELLED.value:
        return {"order_number": order.order_number, "status": order.status, "message": "Order already cancelled"}

    if order.status not in MODIFIABLE_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Order can no longer be cancelled")

    # Return the stock of every item, then mark the order cancelled (never delete it)
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in items:
        variant = db.get(ProductVariant, item.variant_id)
        variant.stock_quantity += item.quantity

    order.status = OrderStatus.CANCELLED.value
    db.commit()

    return {"order_number": order.order_number, "status": order.status, "message": "Order cancelled"}


@router.post("/refunds")
def create_refund(body: RefundRequest, db: Session = Depends(get_db)):
    order = get_order_or_404(db, body.order_number)

    # Rule: only a cancelled order can be refunded
    if order.status != OrderStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Only cancelled orders can be refunded")

    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Safe to call twice: return the existing refund instead of creating a second one
    existing = db.query(Refund).filter(Refund.payment_id == payment.id).first()
    if existing is not None:
        return {**refund_to_dict(existing), "message": "Refund already exists"}

    if payment.status != PaymentStatus.PAID.value:
        raise HTTPException(status_code=400, detail="Payment is not in PAID state")

    # Simulated refund: it completes immediately, no real payment gateway
    refund = Refund(
        payment_id=payment.id,
        amount=payment.amount,
        status=RefundStatus.COMPLETED.value,
        reference=f"RF-{order.order_number}",
    )
    payment.status = PaymentStatus.REFUNDED.value
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return refund_to_dict(refund)


@router.get("/refunds/{refund_id}")
def get_refund(refund_id: int, db: Session = Depends(get_db)):
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund_to_dict(refund)