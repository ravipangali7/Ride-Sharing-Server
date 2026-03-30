"""
Auto-create ParcelBooking for food / ecommerce orders (docs/models_logic.md).
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import F

from core import models

logger = logging.getLogger(__name__)


def _describe_food_items(order: models.FoodOrder) -> str:
    parts = []
    for line in order.items.select_related("menu_item").all():
        parts.append(f"{line.menu_item.name} x{line.quantity}")
    return ", ".join(parts) if parts else "Food order"


def _describe_ecommerce_items(order: models.EcommerceOrder) -> str:
    parts = []
    for line in order.items.select_related("product").all():
        parts.append(f"{line.product.name} x{line.quantity}")
    return ", ".join(parts) if parts else "Ecommerce order"


@transaction.atomic
def ensure_parcel_for_food_order(order: models.FoodOrder) -> models.ParcelBooking | None:
    """
    When restaurant accepts (status >= confirmed), create parcel: pickup at restaurant, drop at customer.
    """
    if order.parcel_booking_id:
        return order.parcel_booking
    if order.status in ("pending", "cancelled"):
        return None

    restaurant = order.restaurant
    customer = order.customer

    parcel = models.ParcelBooking.objects.create(
        sender=customer,
        delivery_person=None,
        sender_name=restaurant.name[:100],
        sender_phone=restaurant.phone,
        sender_address=restaurant.address,
        sender_latitude=restaurant.latitude,
        sender_longitude=restaurant.longitude,
        receiver_name=customer.full_name[:100],
        receiver_phone=customer.phone,
        receiver_address=order.delivery_address,
        receiver_latitude=order.delivery_latitude,
        receiver_longitude=order.delivery_longitude,
        is_fragile=False,
        parcel_description=_describe_food_items(order)[:500],
        estimated_fare=order.delivery_charge,
        status="searching",
        payment_method=order.payment_method,
        payment_intent=order.payment_intent,
        source="restaurant",
        reference_order_id=order.pk,
    )
    models.FoodOrder.objects.filter(pk=order.pk).update(parcel_booking=parcel)
    return parcel


@transaction.atomic
def ensure_parcel_for_ecommerce_order(order: models.EcommerceOrder) -> models.ParcelBooking | None:
    """
    When vendor confirms (status >= confirmed), decrement stock once and create delivery parcel.
    """
    if order.parcel_booking_id:
        return order.parcel_booking
    if order.status in ("pending", "cancelled"):
        return None

    vendor = order.vendor
    customer = order.customer

    lines = list(order.items.select_related("product").all())
    for line in lines:
        updated = models.Product.objects.filter(
            pk=line.product_id,
            stock__gte=line.quantity,
        ).update(stock=F("stock") - line.quantity)
        if updated == 0:
            logger.error(
                "Insufficient stock for product %s on order %s; parcel not created",
                line.product_id,
                order.pk,
            )
            raise ValueError(f"Insufficient stock for product {line.product_id}")

    pay_map = {
        "cash_on_delivery": "cash",
        "wallet": "wallet",
        "qr_esewa": "qr_esewa",
        "qr_khalti": "qr_khalti",
        "qr_ime": "qr_ime",
    }
    parcel_pay = pay_map.get(order.payment_method, "cash")

    parcel = models.ParcelBooking.objects.create(
        sender=customer,
        delivery_person=None,
        sender_name=vendor.store_name[:100],
        sender_phone=vendor.user.phone,
        sender_address=vendor.address,
        sender_latitude=vendor.latitude,
        sender_longitude=vendor.longitude,
        receiver_name=customer.full_name[:100],
        receiver_phone=customer.phone,
        receiver_address=order.delivery_address,
        receiver_latitude=order.delivery_latitude,
        receiver_longitude=order.delivery_longitude,
        is_fragile=False,
        parcel_description=_describe_ecommerce_items(order)[:500],
        estimated_fare=order.delivery_charge,
        status="searching",
        payment_method=parcel_pay,
        payment_intent=order.payment_intent,
        source="ecommerce",
        reference_order_id=order.pk,
    )

    models.EcommerceOrder.objects.filter(pk=order.pk).update(parcel_booking=parcel)
    return parcel
