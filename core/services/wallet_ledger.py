"""
Atomic wallet balance updates + WalletTransaction rows (deposit/top-up, withdraw/payout).
See docs/models_logic.md — Payment spine / Wallet sections.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from core import models

logger = logging.getLogger(__name__)


def get_or_create_wallet(user: models.User) -> models.Wallet:
    wallet, _ = models.Wallet.objects.get_or_create(
        user=user,
        defaults={"balance": Decimal("0.00")},
    )
    return wallet


def _topup_ledger_exists(topup: models.WalletTopupRequest) -> bool:
    return models.WalletTransaction.objects.filter(
        source="topup",
        reference_id=topup.pk,
    ).exists()


def _payout_ledger_exists(payout: models.RiderPayoutRequest) -> bool:
    return models.WalletTransaction.objects.filter(
        source="payout",
        reference_id=payout.pk,
        transaction_type="debit",
    ).exists()


@transaction.atomic
def apply_topup_success_ledger(topup: models.WalletTopupRequest) -> None:
    """
    Idempotent: credit wallet once per successful top-up request.
    Optionally creates/links PaymentTransaction if missing.
    """
    if topup.status != "success":
        return
    if _topup_ledger_exists(topup):
        return

    wallet = get_or_create_wallet(topup.user)
    amount = topup.amount
    if amount <= 0:
        logger.warning("Top-up %s success with non-positive amount; skipping ledger", topup.pk)
        return

    wallet = models.Wallet.objects.select_for_update().get(pk=wallet.pk)

    if topup.payment_transaction_id is None:
        pt = models.PaymentTransaction.objects.create(
            user=topup.user,
            amount=amount,
            currency="NPR",
            gateway=topup.gateway,
            gateway_txn_id=None,
            status="success",
            purpose="wallet_topup",
            reference_id=topup.pk,
        )
        models.WalletTopupRequest.objects.filter(pk=topup.pk).update(payment_transaction=pt)

    models.WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="credit",
        amount=amount,
        source="topup",
        reference_id=topup.pk,
        note="Wallet top-up",
    )
    wallet.balance += amount
    wallet.save(update_fields=["balance"])


@transaction.atomic
def apply_payout_paid_ledger(payout: models.RiderPayoutRequest) -> None:
    """
    Idempotent: debit rider's user wallet once when payout is marked paid.
    """
    if payout.status != "paid":
        return
    if _payout_ledger_exists(payout):
        return

    user = payout.rider.user
    wallet = get_or_create_wallet(user)
    amount = payout.amount
    if amount <= 0:
        logger.warning("Payout %s paid with non-positive amount; skipping ledger", payout.pk)
        return

    wallet = models.Wallet.objects.select_for_update().get(pk=wallet.pk)
    if wallet.balance < amount:
        logger.error(
            "Payout %s marked paid but wallet balance %.2f < amount %.2f for user %s",
            payout.pk,
            wallet.balance,
            amount,
            user.pk,
        )
        return

    models.WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="debit",
        amount=amount,
        source="payout",
        reference_id=payout.pk,
        note="Rider payout withdrawal",
    )
    wallet.balance -= amount
    wallet.save(update_fields=["balance"])
