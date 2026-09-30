import enum


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    PROCESSING = "PROCESSING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"


# Business rule: an order can be modified until it is packed.
MODIFIABLE_ORDER_STATUSES = {
    OrderStatus.PLACED,
    OrderStatus.PROCESSING,
}