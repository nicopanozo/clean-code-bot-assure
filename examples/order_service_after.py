"""
Checkout order orchestration for the storefront monolith.

Handles pricing from the product catalog, payment pre-checks, persistence into ``orders`` /
``order_lines``, and a post-commit customer email. Error responses intentionally mirror the
legacy ``{"e": ...}`` contract consumed by the BFF.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PaymentMethod = Literal["cc", "po"]


@dataclass(frozen=True)
class LineItem:
    """Single sellable line: product identifier and requested quantity."""

    product_id: int
    quantity: int


class OrderService:
    """
    Application service that owns the happy-path for placing an order.

    Parameters
    ----------
    database:
        Thin query executor used elsewhere in this service (raw SQL kept for parity with legacy).
    mailer:
        Outbound notification adapter (SMTP abstraction in production).
    """

    def __init__(self, database: Any, mailer: Any) -> None:
        self._database = database
        self._mailer = mailer

    def place_order(
        self,
        user_id: int,
        items: list[dict[str, int]],
        payment_method: PaymentMethod,
    ) -> dict[str, Any]:
        """
        Attempt to place an order for ``user_id``.

        Returns
        -------
        dict
            ``{"ok": True, "id": <order_id>, "t": <total>}`` on success, otherwise ``{"e": <code>}``.
        """
        user = self._database.q("select * from users where id=?", user_id)
        if not user:
            return {"e": "no user"}

        line_items = [LineItem(product_id=item["pid"], quantity=item["q"]) for item in items]
        total = self._calculate_total(line_items)
        if isinstance(total, dict):
            return total

        payment_error = self._authorize_payment(
            user_id=user_id,
            user=user,
            total=total,
            payment_method=payment_method,
        )
        if payment_error:
            return payment_error

        order_id = self._persist_order(
            user_id=user_id,
            total=total,
            payment_method=payment_method,
            items=line_items,
        )
        self._mailer.send(user[1], "order", str(order_id))
        return {"ok": True, "id": order_id, "t": total}

    def _calculate_total(self, items: list[LineItem]) -> float | dict[str, str]:
        total = 0.0
        for item in items:
            row = self._database.q("select price from products where id=?", item.product_id)
            if not row:
                return {"e": "bad product"}
            total += row[0] * item.quantity
        return total

    def _authorize_payment(
        self,
        *,
        user_id: int,
        user: tuple[Any, ...],
        total: float,
        payment_method: PaymentMethod,
    ) -> dict[str, str] | None:
        if payment_method == "cc":
            ok = self._database.q("insert into charges (user,amt) values (?,?)", user_id, total)
            if not ok:
                return {"e": "charge fail"}
        elif payment_method == "po":
            if user[3] < total:
                return {"e": "credit"}
        else:
            return {"e": "pay"}
        return None

    def _persist_order(
        self,
        *,
        user_id: int,
        total: float,
        payment_method: PaymentMethod,
        items: list[LineItem],
    ) -> Any:
        order_id = self._database.q(
            "insert into orders (user,total,pay) values (?,?,?)",
            user_id,
            total,
            payment_method,
        )
        for item in items:
            self._database.q(
                "insert into order_lines (order,pid,q) values (?,?,?)",
                order_id,
                item.product_id,
                item.quantity,
            )
        return order_id
