from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Product:
    id: int
    name: str
    price: int  # so'mda
    stock: int = 0

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "price": self.price, "stock": self.stock}


@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: int

    @property
    def subtotal(self) -> int:
        return self.quantity * self.unit_price


@dataclass
class Order:
    id: int
    customer_id: int
    items: list[OrderItem] = field(default_factory=list)
    status: str = "new"  # new | paid | shipped | cancelled
    discount_percent: int = 0

    @property
    def total(self) -> int:
        gross = sum(i.subtotal for i in self.items)
        return gross - gross * self.discount_percent // 100

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "status": self.status,
            "items": [{"product_id": i.product_id, "quantity": i.quantity, "unit_price": i.unit_price} for i in self.items],
            "total": self.total,
        }


@dataclass
class Customer:
    id: int
    name: str
    email: str
