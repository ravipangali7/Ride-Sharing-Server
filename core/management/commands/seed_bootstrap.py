import base64
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import (
    AdminUser,
    AppSetting,
    CoinRate,
    LoyaltyTier,
    NotificationTemplate,
    QuickReplyTemplate,
    RiderAchievement,
    VehicleType,
)

# 1x1 transparent PNG
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class Command(BaseCommand):
    help = (
        "Idempotent reference data: vehicle types, loyalty tiers, quick replies, notification templates, "
        "AppSetting keys, CoinRate, sample achievements. "
        "Run seed_admin first so CoinRate.updated_by can be set."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-coin-rate",
            action="store_true",
            help="Skip CoinRate (e.g. no AdminUser yet)",
        )

    def _png(self, name="icon.png"):
        return ContentFile(TINY_PNG, name=name)

    def handle(self, *args, **options):
        admin = AdminUser.objects.filter(role="superadmin", is_active=True).select_related("user").first()
        if not admin and not options["skip_coin_rate"]:
            self.stdout.write(
                self.style.WARNING(
                    "No active superadmin AdminUser found; run seed_admin first. "
                    "Continuing without CoinRate (use --skip-coin-rate to silence)."
                )
            )

        with transaction.atomic():
            vt_specs = [
                ("Bike", "economy", Decimal("30"), Decimal("15"), Decimal("2"), 1),
                ("Car", "standard", Decimal("80"), Decimal("35"), Decimal("3"), 4),
                ("Auto", "economy", Decimal("50"), Decimal("25"), Decimal("2.5"), 3),
            ]
            for name, tier, base, km, pm, cap in vt_specs:
                vt, created = VehicleType.objects.get_or_create(
                    name=name,
                    defaults={
                        "icon": self._png(f"{name.lower()}.png"),
                        "base_fare": base,
                        "per_km_rate": km,
                        "per_minute_rate": pm,
                        "capacity": cap,
                        "vehicle_tier": tier,
                        "sort_order": 0,
                        "is_active": True,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"VehicleType: {name}"))

            tiers = [
                ("Bronze", 0, "#CD7F32"),
                ("Silver", 500, "#C0C0C0"),
                ("Gold", 2000, "#FFD700"),
                ("Platinum", 5000, "#E5E4E2"),
                ("Diamond", 10000, "#B9F2FF"),
            ]
            for name, min_pts, color in tiers:
                obj, created = LoyaltyTier.objects.get_or_create(
                    name=name,
                    defaults={
                        "min_points": min_pts,
                        "benefits": {"tier": name.lower()},
                        "badge_icon": self._png(f"tier-{name.lower()}.png"),
                        "color_hex": color,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"LoyaltyTier: {name}"))

            replies = [
                ("coming_2m", "Coming in 2 min", "2 minute ma aauchu", "both", "timer", 10),
                ("on_way", "On the way", "Ma aaisake", "both", "nav", 20),
                ("wait_pickup", "Please wait at pickup", "Pickup ma park garnus", "customer", "wait", 30),
            ]
            for key, en, np, who, icon, order in replies:
                _, created = QuickReplyTemplate.objects.get_or_create(
                    key=key,
                    defaults={
                        "label_en": en,
                        "label_np": np,
                        "applicable_to": who,
                        "icon": icon,
                        "sort_order": order,
                        "is_active": True,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"QuickReply: {key}"))

            templates = [
                ("ride_accepted", "Ride accepted", "Your rider is on the way.", "push", "customer"),
                ("parcel_picked", "Parcel picked up", "Your parcel is in transit.", "in_app", "customer"),
            ]
            for name, title, body, ntype, role in templates:
                _, created = NotificationTemplate.objects.get_or_create(
                    name=name,
                    defaults={
                        "title_template": title,
                        "body_template": body,
                        "notification_type": ntype,
                        "target_role": role,
                        "is_active": True,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"NotificationTemplate: {name}"))

            settings_seed = [
                ("coin_rupee_rate", "10", "decimal", "Rupees per coin (ride/parcel)", "it"),
                ("surge_pricing_enabled", "true", "boolean", "Master surge switch", "it"),
                ("bargain_window_seconds", "120", "integer", "Bargain timeout", "it"),
                ("dispatch_strategy", "mixed", "string", "Default dispatch strategy", "it"),
                ("loyalty_enabled", "true", "boolean", "Loyalty program", "ceo"),
                ("qr_payment_expiry_minutes", "15", "integer", "QR session TTL", "it"),
                ("popup_ads_enabled", "true", "boolean", "Popup ads", "marketing"),
                ("ride_female_filter_enabled", "true", "boolean", "Female-only ride filter", "it"),
            ]
            for key, val, vtype, desc, editable in settings_seed:
                _, created = AppSetting.objects.get_or_create(
                    key=key,
                    defaults={
                        "value": val,
                        "value_type": vtype,
                        "description": desc,
                        "editable_by": editable,
                        "updated_by": admin,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"AppSetting: {key}"))

            _, created = RiderAchievement.objects.get_or_create(
                name="Century Rider",
                defaults={
                    "description": "Complete 100 trips",
                    "icon": self._png("century.png"),
                    "badge_color": "#FF6600",
                    "achievement_type": "trip_count",
                    "threshold_value": 100,
                    "points_awarded": 500,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS("RiderAchievement: Century Rider"))

            if admin and not options["skip_coin_rate"]:
                active = CoinRate.objects.filter(is_active=True).exists()
                if not active:
                    CoinRate.objects.create(
                        rupees_per_coin=Decimal("10.00"),
                        is_active=True,
                        updated_by=admin,
                    )
                    self.stdout.write(self.style.SUCCESS("CoinRate: default 10 NPR / coin"))

        self.stdout.write(self.style.SUCCESS("seed_bootstrap completed (idempotent)."))
