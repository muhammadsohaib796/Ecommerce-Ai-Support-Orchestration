from app.database import SessionLocal
from app.models import (
    ActionRecord,
    AuditLog,
    Customer,
    EmailMessage,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    Refund,
    SupportTicket,
)
from app.seed import seed


def reset():
    db = SessionLocal()

    # Delete child tables first so foreign keys never block the delete
    for model in [
        AuditLog,
        ActionRecord,
        EmailMessage,
        SupportTicket,
        Refund,
        Payment,
        OrderItem,
        Order,
        ProductVariant,
        Product,
        Customer,
    ]:
        db.query(model).delete()

    db.commit()
    db.close()
    seed()


if __name__ == "__main__":
    reset()