from __future__ import annotations

from typing import Generic, TypeVar

from shop.models import Customer, Order, Product

T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[int, T] = {}
        self._next_id = 1

    def next_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def add(self, item: T) -> T:
        self._items[item.id] = item  # type: ignore[attr-defined]
        return item

    def get(self, item_id: int) -> T | None:
        return self._items.get(item_id)

    def all(self) -> list[T]:
        return list(self._items.values())

    def delete(self, item_id: int) -> None:
        self._items.pop(item_id, None)


class ProductRepository(InMemoryRepository[Product]):
    def in_stock(self) -> list[Product]:
        return [p for p in self.all() if p.stock > 0]


class OrderRepository(InMemoryRepository[Order]):
    def by_customer(self, customer_id: int) -> list[Order]:
        return [o for o in self.all() if o.customer_id == customer_id]


class CustomerRepository(InMemoryRepository[Customer]):
    pass
