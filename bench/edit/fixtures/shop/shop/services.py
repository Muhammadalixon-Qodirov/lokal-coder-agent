from __future__ import annotations

from shop.models import Customer, Order, OrderItem, Product
from shop.repository import CustomerRepository, OrderRepository, ProductRepository


class ShopService:
    def __init__(self) -> None:
        self.products = ProductRepository()
        self.orders = OrderRepository()
        self.customers = CustomerRepository()

    # --- mahsulotlar

    def add_product(self, name: str, price: int, stock: int = 0) -> Product:
        if price <= 0:
            raise ValueError("price must be positive")
        return self.products.add(Product(self.products.next_id(), name, price, stock))

    # --- mijozlar

    def create_customer(self, name: str, email: str) -> Customer:
        if not name.strip():
            raise ValueError("name required")
        return self.customers.add(Customer(self.customers.next_id(), name.strip(), email.strip()))

    # --- buyurtmalar

    def create_order(self, customer_id: int, items: list[tuple[int, int]]) -> Order:
        """items: [(product_id, quantity), ...]"""
        if self.customers.get(customer_id) is None:
            raise ValueError("unknown customer")
        order = Order(self.orders.next_id(), customer_id)
        for product_id, qty in items:
            product = self.products.get(product_id)
            if product is None:
                raise ValueError(f"unknown product {product_id}")
            if qty <= 0:
                raise ValueError("quantity must be positive")
            if product.stock < qty:
                raise ValueError(f"not enough stock for {product.name}")
            product.stock -= qty
            order.items.append(OrderItem(product_id, qty, product.price))
        return self.orders.add(order)

    def get_order(self, order_id: int) -> Order | None:
        return self.orders.get(order_id)

    def apply_discount(self, order_id: int, percent: int) -> Order:
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError("unknown order")
        order.discount_percent = percent
        return order

    def pay_order(self, order_id: int) -> Order:
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError("unknown order")
        if order.status != "new":
            raise ValueError("order already processed")
        order.status = "paid"
        return order
