"""
Side effects aligned with docs/models_logic.md (wallet ledger, coins, fulfillment).
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core import models
from core.services.realtime_notify import (
    broadcast_parcel_open,
    broadcast_ride_open,
    notify_room,
    parcel_booking_socket_snapshot,
    ride_booking_socket_snapshot,
    ride_bargain_offer_payload,
)
from core.services.parcels import ensure_parcel_for_ecommerce_order, ensure_parcel_for_food_order
from core.services.wallet_ledger import apply_payout_paid_ledger, apply_topup_success_ledger

logger = logging.getLogger(__name__)


@receiver(post_save, sender=models.WalletTopupRequest)
def wallet_topup_success_ledger(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if instance.status == "success":
        try:
            apply_topup_success_ledger(instance)
        except Exception:
            logger.exception("Wallet top-up ledger failed for %s", instance.pk)


@receiver(post_save, sender=models.RiderPayoutRequest)
def rider_payout_paid_ledger(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if instance.status == "paid":
        try:
            apply_payout_paid_ledger(instance)
        except Exception:
            logger.exception("Rider payout ledger failed for %s", instance.pk)


def _coin_delta(tx: models.CoinTransaction) -> int:
    if tx.transaction_type == "earn":
        return abs(int(tx.coins))
    if tx.transaction_type == "spend":
        return -abs(int(tx.coins))
    return int(tx.coins)


@receiver(post_save, sender=models.CoinTransaction)
def coin_transaction_sync_balance(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if not created:
        return
    delta = _coin_delta(instance)
    if delta == 0:
        return
    with transaction.atomic():
        user = models.User.objects.select_for_update().get(pk=instance.user_id)
        new_bal = int(user.coin_balance) + delta
        if new_bal < 0:
            logger.error("CoinTransaction %s would make balance negative; clamping to 0", instance.pk)
            new_bal = 0
        user.coin_balance = new_bal
        user.save(update_fields=["coin_balance"])


def _schedule_food_parcel(order_id):
    def _run():
        try:
            order = models.FoodOrder.objects.prefetch_related("items__menu_item").get(pk=order_id)
            ensure_parcel_for_food_order(order)
        except models.FoodOrder.DoesNotExist:
            return
        except Exception:
            logger.exception("Food order parcel creation failed for %s", order_id)

    transaction.on_commit(_run)


def _schedule_ecommerce_parcel(order_id):
    def _run():
        try:
            order = models.EcommerceOrder.objects.prefetch_related("items__product").get(pk=order_id)
            ensure_parcel_for_ecommerce_order(order)
        except models.EcommerceOrder.DoesNotExist:
            return
        except ValueError as e:
            logger.error("Ecommerce parcel skipped for %s: %s", order_id, e)
        except Exception:
            logger.exception("Ecommerce parcel creation failed for %s", order_id)

    transaction.on_commit(_run)


@receiver(post_save, sender=models.FoodOrder)
def food_order_auto_parcel(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    _schedule_food_parcel(instance.pk)


@receiver(post_save, sender=models.EcommerceOrder)
def ecommerce_order_auto_parcel(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    _schedule_ecommerce_parcel(instance.pk)


def _push_ride_booking_realtime(booking_id):
    def _run():
        try:
            b = models.RideBooking.objects.get(pk=booking_id)
        except models.RideBooking.DoesNotExist:
            return
        snap = ride_booking_socket_snapshot(b)
        notify_room(f"ride:{b.pk}", "ride:patch", snap)
        if b.status == "searching" and b.rider_id is None:
            broadcast_ride_open(str(b.vehicle_type_id), snap)

    transaction.on_commit(_run)


@receiver(post_save, sender=models.RideBooking)
def ride_booking_realtime_notify(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    _push_ride_booking_realtime(instance.pk)


def _push_parcel_booking_realtime(parcel_id):
    def _run():
        try:
            p = models.ParcelBooking.objects.get(pk=parcel_id)
        except models.ParcelBooking.DoesNotExist:
            return
        snap = parcel_booking_socket_snapshot(p)
        notify_room(f"parcel:{p.pk}", "parcel:patch", snap)
        if p.status == "searching" and p.delivery_person_id is None:
            broadcast_parcel_open(snap)

    transaction.on_commit(_run)


@receiver(post_save, sender=models.ParcelBooking)
def parcel_booking_realtime_notify(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    _push_parcel_booking_realtime(instance.pk)


def _push_ride_bargain_realtime(offer_id):
    def _run():
        try:
            o = models.RideBargainOffer.objects.get(pk=offer_id)
        except models.RideBargainOffer.DoesNotExist:
            return
        notify_room(f"ride:{o.ride_id}", "ride:bargain:patch", ride_bargain_offer_payload(o))

    transaction.on_commit(_run)


@receiver(post_save, sender=models.RideBargainOffer)
def ride_bargain_realtime_notify(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    _push_ride_bargain_realtime(instance.pk)


@receiver(post_save, sender=models.SupportTicket)
def support_ticket_resolved_timestamp(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    if instance.status in ("resolved", "closed") and instance.resolved_at is None:
        from django.utils import timezone

        models.SupportTicket.objects.filter(pk=instance.pk, resolved_at__isnull=True).update(
            resolved_at=timezone.now()
        )
