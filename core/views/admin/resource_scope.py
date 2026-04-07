"""Row-level security for generic CRUD: staff/superuser unrestricted; others scoped."""

from __future__ import annotations

from django.db.models import Q

from core import models as m

# Anonymous GET allowed (mobile splash / public bootstrap).
ANONYMOUS_GET_RESOURCES = frozenset({"app_settings", "app_versions"})


def is_staff_user(user) -> bool:
    return bool(user and user.is_authenticated and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)))


def scope_queryset(resource: str, qs, user):
    """Return scoped queryset for non-staff users. Staff should not call this."""
    if resource == "users":
        return qs.filter(pk=user.pk)

    if resource == "riders":
        return qs.filter(user=user)

    if resource == "ride_bookings":
        return qs.filter(Q(customer=user) | Q(rider__user=user))

    if resource == "tour_bookings":
        return qs.filter(customer=user)

    if resource == "scheduled_rides":
        return qs.filter(ride_booking__customer=user)

    if resource == "recurring_rides":
        return qs.filter(customer=user)

    if resource == "tour_bookings":
        return qs.filter(customer=user)

    if resource == "ride_bargains":
        return qs.filter(
            Q(rider__user=user)
            | Q(ride__customer=user)
        )

    if resource == "ride_ratings":
        return qs.filter(Q(rated_by=user) | Q(rated_user=user))

    if resource == "dispatch_config":
        return qs.filter(rider__user=user)

    if resource == "dispatch_events":
        return qs.filter(rider__user=user)

    if resource == "parcels":
        return qs.filter(
            Q(sender=user)
            | Q(delivery_person__user=user)
            | Q(delivery_person__isnull=True, status__in=("searching", "bargaining"))
        )

    if resource == "parcel_items":
        return qs.filter(
            Q(parcel_booking__sender=user)
            | Q(parcel_booking__delivery_person__user=user)
            | Q(
                parcel_booking__delivery_person__isnull=True,
                parcel_booking__status__in=("searching", "bargaining"),
            )
        )

    if resource == "parcel_agents":
        return qs.filter(user=user)

    if resource == "parcel_bargains":
        return qs.filter(
            Q(delivery_person__user=user)
            | Q(parcel__sender=user)
        )

    if resource == "restaurants":
        return qs.filter(Q(owner=user) | Q(is_approved=True))

    if resource == "food_categories":
        return qs.filter(Q(restaurant__owner=user) | Q(restaurant__is_approved=True))

    if resource == "menu_items":
        return qs.filter(Q(restaurant__owner=user) | Q(restaurant__is_approved=True))

    if resource == "food_orders":
        return qs.filter(Q(customer=user) | Q(restaurant__owner=user))

    if resource == "food_order_items":
        return qs.filter(Q(order__customer=user) | Q(order__restaurant__owner=user))

    if resource == "food_ratings":
        return qs.filter(customer=user)

    if resource == "vendors":
        return qs.filter(Q(user=user) | Q(is_approved=True))

    if resource == "products":
        return qs.filter(
            Q(vendor__user=user)
            | (Q(vendor__is_approved=True) & Q(is_active=True))
        )

    if resource == "product_categories":
        return qs  # catalog; no user FK — read-only safe tree for shoppers

    if resource == "product_images":
        return qs.filter(
            Q(product__vendor__user=user)
            | (Q(product__vendor__is_approved=True) & Q(product__is_active=True))
        )

    if resource == "ecommerce_orders":
        return qs.filter(Q(customer=user) | Q(vendor__user=user))

    if resource == "ecommerce_order_items":
        return qs.filter(Q(order__customer=user) | Q(order__vendor__user=user))

    if resource == "room_owners":
        return qs.filter(user=user)

    if resource == "room_listings":
        return qs.filter(Q(owner__user=user) | Q(is_approved=True, is_available=True))

    if resource == "room_inquiries":
        return qs.filter(Q(customer=user) | Q(room__owner__user=user))

    if resource == "room_requests":
        return qs.filter(Q(customer=user) | Q(room__owner__user=user))

    if resource == "wallets":
        return qs.filter(user=user)

    if resource == "wallet_transactions":
        return qs.filter(wallet__user=user)

    if resource == "coin_transactions":
        return qs.filter(user=user)

    if resource == "user_sessions":
        return qs.filter(user=user)

    if resource == "otps":
        return qs.filter(user=user)

    if resource == "support_tickets":
        return qs.filter(user=user)

    if resource == "support_messages":
        return qs.filter(ticket__user=user)

    if resource == "notif_inbox":
        return qs.filter(recipient=user)

    if resource == "saved_locations":
        return qs.filter(user=user)

    if resource == "loyalty_users":
        return qs.filter(user=user)

    if resource == "loyalty_transactions":
        return qs.filter(user=user)

    if resource == "streaks":
        return qs.filter(user=user)

    if resource == "topups":
        return qs.filter(user=user)

    if resource == "payouts":
        return qs.filter(rider__user=user)

    if resource == "referrals":
        return qs.filter(Q(referrer=user) | Q(referred_user=user))

    if resource == "popup_ads":
        return qs.filter(is_active=True)

    if resource == "promo_codes":
        return qs

    if resource == "promo_usage":
        return qs.filter(user=user)

    if resource == "birthday_promos":
        return qs

    if resource == "cancellation_policies":
        return qs

    if resource == "coin_rates":
        return qs.filter(is_active=True)

    if resource == "vehicle_types":
        return qs.filter(is_active=True)

    if resource == "surge_rules":
        return qs

    if resource == "loyalty_tiers":
        return qs

    if resource == "popup_ad_views":
        return qs.filter(user=user)

    if resource == "payments":
        return qs.filter(user=user)

    if resource == "payment_intents":
        return qs.filter(user=user)

    if resource == "qr_sessions":
        return qs.filter(payment_intent__user=user)

    # Default: deny (empty) for unknown / sensitive admin tables
    return qs.none()


def object_visible(resource: str, obj, user) -> bool:
    """Detail permission for non-staff."""
    qs = type(obj).objects.filter(pk=obj.pk)
    scoped = scope_queryset(resource, qs, user)
    return scoped.exists()


def enforce_create_fk(resource: str, data: dict, user) -> dict:
    """Force ownership on create for non-staff. Mutates data copy."""
    out = dict(data)

    if resource == "riders":
        out["user_id"] = str(user.pk)
    elif resource == "parcel_agents":
        out["user_id"] = str(user.pk)
    elif resource == "vendors":
        out["user_id"] = str(user.pk)
    elif resource == "room_owners":
        out["user_id"] = str(user.pk)
    elif resource == "restaurants":
        out["owner_id"] = str(user.pk)
    elif resource == "ride_bookings":
        if "customer_id" not in out:
            out["customer_id"] = str(user.pk)
    elif resource == "parcels":
        if "sender_id" not in out:
            out["sender_id"] = str(user.pk)
    elif resource == "food_orders":
        if "customer_id" not in out:
            out["customer_id"] = str(user.pk)
    elif resource == "ecommerce_orders":
        if "customer_id" not in out:
            out["customer_id"] = str(user.pk)
    elif resource == "wallets":
        out["user_id"] = str(user.pk)
    elif resource == "saved_locations":
        out["user_id"] = str(user.pk)
    elif resource == "support_tickets":
        out["user_id"] = str(user.pk)
    elif resource == "room_inquiries":
        out["customer_id"] = str(user.pk)
    elif resource == "room_requests":
        out["customer_id"] = str(user.pk)
    elif resource == "topups":
        out["user_id"] = str(user.pk)
    elif resource == "products":
        v = m.Vendor.objects.filter(user=user).first()
        if v:
            out["vendor_id"] = str(v.pk)
    elif resource == "product_images":
        pid = out.get("product_id") or out.get("product")
        if pid:
            if not m.Product.objects.filter(pk=pid, vendor__user=user).exists():
                out.pop("product_id", None)
                out.pop("product", None)
        if not out.get("product_id") and not out.get("product"):
            p = m.Product.objects.filter(vendor__user=user).first()
            if p:
                out["product_id"] = str(p.pk)
    elif resource == "food_categories":
        rid = out.get("restaurant_id") or out.get("restaurant")
        if rid and m.Restaurant.objects.filter(pk=rid, owner=user).exists():
            pass
        else:
            r = m.Restaurant.objects.filter(owner=user).first()
            if r:
                out["restaurant_id"] = str(r.pk)
    elif resource == "menu_items":
        rid = out.get("restaurant_id") or out.get("restaurant")
        if rid and not m.Restaurant.objects.filter(pk=rid, owner=user).exists():
            r = m.Restaurant.objects.filter(owner=user).first()
            if r:
                out["restaurant_id"] = str(r.pk)
    elif resource == "room_listings":
        ro = m.RoomOwnerProfile.objects.filter(user=user).first()
        if ro:
            out["owner_id"] = str(ro.pk)

    return out


# Non-staff cannot POST/PATCH/DELETE these resources (admin / system config).
_STAFF_ONLY_MUTATION = frozenset(
    {
        "admin_users",
        "activity_logs",
        "analytics",
        "app_settings",
        "app_versions",
        "mobile_app_release",
        "cancellation_policies",
        "coin_rates",
        "loyalty_tiers",
        "promo_codes",
        "birthday_promos",
        "popup_ads",
        "surge_rules",
        "fare_overrides",
        "fare_estimates",
        "demand_forecast",
        "send_push",
        "notif_templates",
        "push_logs",
        "quick_replies",
        "service_charges",
        "admin_activity_log",
        "rider_leaderboard",
        "loyalty_achievements",
        "trip_targets",
        "dispatch_events",
        "otps",
        "user_sessions",
    }
)


def non_staff_mutation_forbidden(resource: str) -> bool:
    return resource in _STAFF_ONLY_MUTATION
