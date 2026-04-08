"""Ecommerce order integrity: delivery charge from vendor, line-item pricing, rolled-up totals."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from core import models


def effective_product_unit_price(product: models.Product) -> Decimal:
    if product.discounted_price is not None and product.discounted_price < product.price:
        return product.discounted_price
    return product.price


def normalize_ecommerce_order_delivery_for_customer(data: dict) -> dict:
    """Force delivery_charge from the vendor row (customers cannot pick arbitrary delivery fees)."""
    vid = data.get("vendor_id")
    if not vid:
        return data
    vendor = models.Vendor.objects.filter(pk=vid).first()
    if vendor:
        data["delivery_charge"] = vendor.delivery_charge
    return data


def _require_order_visible_to_user(order: models.EcommerceOrder, user) -> None:
    if order.customer_id != user.pk:
        raise ValueError("Order does not belong to the current user")


def validate_ecommerce_order_item_create(data: dict, user, *, acting_as_staff: bool) -> None:
    """Ensure line items match catalog prices, vendor, and available stock."""
    oid = data.get("order_id") or data.get("order")
    pid = data.get("product_id") or data.get("product")
    if not oid or not pid:
        raise ValueError("order and product are required")

    order = models.EcommerceOrder.objects.select_related("vendor").filter(pk=oid).first()
    if not order:
        raise ValueError("Order not found")

    if not acting_as_staff:
        _require_order_visible_to_user(order, user)

    if order.status in ("delivered", "cancelled"):
        raise ValueError("Cannot add items to a closed order")

    product = models.Product.objects.filter(pk=pid).select_related("vendor").first()
    if not product:
        raise ValueError("Product not found")

    if product.vendor_id != order.vendor_id:
        raise ValueError("Product does not belong to this order's vendor")

    try:
        qty = int(data.get("quantity") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid quantity") from exc
    if qty < 1:
        raise ValueError("Invalid quantity")

    existing_same = (
        models.EcommerceOrderItem.objects.filter(order_id=oid, product_id=pid).aggregate(s=Sum("quantity"))["s"] or 0
    )
    if existing_same + qty > product.stock:
        raise ValueError("Insufficient stock for this product")

    unit = Decimal(str(data.get("unit_price", "0")))
    line_total = Decimal(str(data.get("total_price", "0")))
    expected_unit = effective_product_unit_price(product)
    expected_line = (expected_unit * qty).quantize(Decimal("0.01"))

    if unit != expected_unit or line_total != expected_line:
        raise ValueError("Line totals do not match current product price")


def recalculate_ecommerce_order_totals(order_id) -> None:
    """Recompute subtotal / delivery / total from line items and vendor delivery charge."""
    order = models.EcommerceOrder.objects.select_related("vendor").filter(pk=order_id).first()
    if not order:
        return
    agg = models.EcommerceOrderItem.objects.filter(order_id=order_id).aggregate(s=Sum("total_price"))
    subtotal: Decimal = agg["s"] or Decimal("0")
    delivery = order.vendor.delivery_charge if order.vendor_id else order.delivery_charge
    total = (subtotal + delivery).quantize(Decimal("0.01"))
    models.EcommerceOrder.objects.filter(pk=order_id).update(
        subtotal=subtotal.quantize(Decimal("0.01")),
        delivery_charge=delivery,
        total_amount=total,
    )


def touch_delivered_at_if_needed(order: models.EcommerceOrder, previous_status: str | None) -> None:
    if order.status == "delivered" and previous_status != "delivered":
        if order.delivered_at is None:
            models.EcommerceOrder.objects.filter(pk=order.pk).update(delivered_at=timezone.now())
    elif order.status != "delivered" and previous_status == "delivered":
        models.EcommerceOrder.objects.filter(pk=order.pk).update(delivered_at=None)
