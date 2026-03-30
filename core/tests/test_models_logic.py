"""Regression tests for docs/models_logic.md implementations."""

from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core import models
from core.services.wallet_ledger import apply_topup_success_ledger


class WalletTopupLedgerTests(TestCase):
    def test_success_topup_credits_wallet_once(self):
        user = models.User.objects.create_user(
            phone="9800000001",
            password="testpass123",
            full_name="Topup User",
        )
        topup = models.WalletTopupRequest.objects.create(
            user=user,
            amount=Decimal("250.00"),
            gateway="esewa",
            status="success",
        )
        wallet = models.Wallet.objects.get(user=user)
        self.assertEqual(wallet.balance, Decimal("250.00"))
        self.assertEqual(
            models.WalletTransaction.objects.filter(source="topup", reference_id=topup.pk).count(),
            1,
        )
        topup.save()
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("250.00"))
        apply_topup_success_ledger(topup)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("250.00"))


class CoinBalanceSyncTests(TestCase):
    def test_coin_transaction_updates_user_balance(self):
        user = models.User.objects.create_user(
            phone="9800000002",
            password="testpass123",
            full_name="Coin User",
        )
        self.assertEqual(user.coin_balance, 0)
        models.CoinTransaction.objects.create(
            user=user,
            transaction_type="earn",
            coins=10,
            source="ride",
        )
        user.refresh_from_db()
        self.assertEqual(user.coin_balance, 10)
        models.CoinTransaction.objects.create(
            user=user,
            transaction_type="spend",
            coins=3,
            source="ride",
        )
        user.refresh_from_db()
        self.assertEqual(user.coin_balance, 7)


class RiderDispatchConfigCleanTests(TestCase):
    def test_mixed_weights_must_sum_to_one(self):
        admin_user = models.User.objects.create_user(
            phone="9800000003",
            password="testpass123",
            full_name="Admin Person",
            is_staff=True,
        )
        admin = models.AdminUser.objects.create(user=admin_user, role="it", permissions={})
        cfg = models.RiderDispatchConfig(
            dispatch_strategy="mixed",
            proximity_weight=Decimal("0.5"),
            rating_weight=Decimal("0.5"),
            behavior_weight=Decimal("0.1"),
            trip_count_weight=Decimal("0.1"),
            updated_by=admin,
        )
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            cfg.full_clean()


def _tiny_image():
    return SimpleUploadedFile("x.jpg", b"fake", content_type="image/jpeg")


class RiderPayoutLedgerTests(TestCase):
    def test_paid_payout_debits_rider_wallet(self):
        vt = models.VehicleType.objects.create(
            name="Bike",
            icon=_tiny_image(),
            base_fare=Decimal("50"),
            per_km_rate=Decimal("10"),
            per_minute_rate=Decimal("2"),
            capacity=1,
            vehicle_tier="economy",
        )
        rider_user = models.User.objects.create_user(
            phone="9800000004",
            password="testpass123",
            full_name="Rider User",
        )
        models.Wallet.objects.create(user=rider_user, balance=Decimal("500.00"))
        img = _tiny_image()
        rider = models.RiderProfile.objects.create(
            user=rider_user,
            license_number="L1",
            license_photo=img,
            citizenship_photo_front=img,
            citizenship_photo_back=img,
            vehicle_type=vt,
            vehicle_number="BA1PA1234",
            vehicle_photo=img,
        )
        payout = models.RiderPayoutRequest.objects.create(
            rider=rider,
            amount=Decimal("100.00"),
            status="pending",
        )
        payout.status = "paid"
        payout.full_clean()
        payout.save()
        wallet = models.Wallet.objects.get(user=rider_user)
        self.assertEqual(wallet.balance, Decimal("400.00"))
        self.assertEqual(
            models.WalletTransaction.objects.filter(
                source="payout", reference_id=payout.pk, transaction_type="debit"
            ).count(),
            1,
        )
