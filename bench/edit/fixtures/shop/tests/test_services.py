import pytest

from shop.api import App
from shop.services import ShopService


@pytest.fixture
def svc():
    s = ShopService()
    s.add_product("Choy", 12000, stock=10)
    s.add_product("Non", 4000, stock=50)
    s.create_customer("Ali", "ali@example.com")
    return s


def test_create_order_reduces_stock(svc):
    order = svc.create_order(1, [(1, 2), (2, 3)])
    assert order.total == 2 * 12000 + 3 * 4000
    assert svc.products.get(1).stock == 8


def test_not_enough_stock(svc):
    with pytest.raises(ValueError):
        svc.create_order(1, [(1, 100)])


def test_discount(svc):
    order = svc.create_order(1, [(1, 1)])
    svc.apply_discount(order.id, 10)
    assert order.total == 10800


def test_pay_twice(svc):
    order = svc.create_order(1, [(1, 1)])
    svc.pay_order(order.id)
    with pytest.raises(ValueError):
        svc.pay_order(order.id)


def test_api_get_order(svc):
    app = App(svc)
    svc.create_order(1, [(2, 1)])
    status, body = app.handle("GET", "/orders/1")
    assert status == 200 and body["total"] == 4000
    assert app.handle("GET", "/orders/99")[0] == 404
