"""Juda oddiy routing: (method, path) → handler. Handler (status, body) qaytaradi."""

from __future__ import annotations

import re
from typing import Callable

from shop.services import ShopService

Handler = Callable[..., tuple[int, dict]]


class App:
    def __init__(self, service: ShopService | None = None) -> None:
        self.service = service or ShopService()
        self.routes: list[tuple[str, re.Pattern, Handler]] = []
        self._register()

    def route(self, method: str, pattern: str, handler: Handler) -> None:
        regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>\\d+)", pattern) + "$")
        self.routes.append((method, regex, handler))

    def handle(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        for m, regex, handler in self.routes:
            match = regex.match(path)
            if m == method and match:
                kwargs = {k: int(v) for k, v in match.groupdict().items()}
                try:
                    return handler(body or {}, **kwargs)
                except ValueError as e:
                    return 400, {"error": str(e)}
        return 404, {"error": "not found"}

    # ------------------------------------------------------------ handlers

    def _register(self) -> None:
        self.route("GET", "/products", self.list_products)
        self.route("POST", "/products", self.create_product)
        self.route("POST", "/orders", self.create_order)
        self.route("GET", "/orders/{order_id}", self.get_order)

    def list_products(self, body: dict) -> tuple[int, dict]:
        return 200, {"items": [p.to_dict() for p in self.service.products.all()]}

    def create_product(self, body: dict) -> tuple[int, dict]:
        p = self.service.add_product(body.get("name", ""), int(body.get("price", 0)), int(body.get("stock", 0)))
        return 201, p.to_dict()

    def create_order(self, body: dict) -> tuple[int, dict]:
        items = [(int(i["product_id"]), int(i["quantity"])) for i in body.get("items", [])]
        order = self.service.create_order(int(body.get("customer_id", 0)), items)
        return 201, order.to_dict()

    def get_order(self, body: dict, order_id: int) -> tuple[int, dict]:
        order = self.service.get_order(order_id)
        if order is None:
            return 404, {"error": "order not found"}
        return 200, order.to_dict()
