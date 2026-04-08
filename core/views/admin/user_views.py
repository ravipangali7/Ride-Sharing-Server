import uuid as _uuid
from decimal import Decimal

from django.db import models as dj_models, transaction
from django.db.models import Count, F, Sum
from django.http import Http404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core import models
from core.views.admin.resource_scope import (
    ANONYMOUS_GET_RESOURCES,
    enforce_create_fk,
    is_staff_user,
    non_staff_mutation_forbidden,
    object_visible,
    scope_queryset,
)


MODEL_REGISTRY = {
    "users": models.User,
    "riders": models.RiderProfile,
    "ride_bookings": models.RideBooking,
    "tour_bookings": models.TourBooking,
    "scheduled_rides": models.ScheduledRideBooking,
    "recurring_rides": models.RecurringRideTemplate,
    "ride_bargains": models.RideBargainOffer,
    "dispatch_config": models.RiderDispatchConfig,
    "parcels": models.ParcelBooking,
    "parcel_items": models.ParcelItem,
    "parcel_bargains": models.ParcelBargainOffer,
    "parcel_agents": models.ParcelDeliveryProfile,
    "restaurants": models.Restaurant,
    "food_orders": models.FoodOrder,
    "food_order_items": models.FoodOrderItem,
    "food_categories": models.FoodCategory,
    "menu_items": models.MenuItem,
    "vendors": models.Vendor,
    "products": models.Product,
    "product_categories": models.ProductCategory,
    "ecommerce_orders": models.EcommerceOrder,
    "ecommerce_order_items": models.EcommerceOrderItem,
    "product_images": models.ProductImage,
    "room_listings": models.RoomListing,
    "room_owners": models.RoomOwnerProfile,
    "room_inquiries": models.RoomInquiry,
    "room_requests": models.RoomBookingRequest,
    "wallets": models.Wallet,
    "wallet_transactions": models.WalletTransaction,
    "coin_transactions": models.CoinTransaction,
    "user_sessions": models.UserSession,
    "otps": models.OTPVerification,
    "payments": models.PaymentTransaction,
    "payment_intents": models.PaymentIntent,
    "qr_sessions": models.QRPaymentSession,
    "topups": models.WalletTopupRequest,
    "payouts": models.RiderPayoutRequest,
    "vehicle_types": models.VehicleType,
    "surge_rules": models.SurgePricingRule,
    "fare_overrides": models.AdminFareOverride,
    "fare_estimates": models.FareEstimateLog,
    "coin_rates": models.CoinRate,
    "promo_codes": models.PromoCode,
    "promo_usage": models.PromoUsage,
    "birthday_promos": models.BirthdayPromo,
    "referrals": models.ReferralReward,
    "popup_ads": models.PopupAd,
    "popup_ad_views": models.PopupAdView,
    "loyalty_tiers": models.LoyaltyTier,
    "loyalty_users": models.UserLoyaltyProfile,
    "loyalty_transactions": models.LoyaltyPointTransaction,
    "streaks": models.UserStreak,
    "loyalty_achievements": models.RiderAchievement,
    "trip_targets": models.RiderTripTarget,
    "demand_forecast": models.DemandForecast,
    "send_push": models.AdminPushLog,
    "notif_templates": models.NotificationTemplate,
    "push_logs": models.AdminPushLog,
    "notif_inbox": models.Notification,
    "saved_locations": models.SavedLocation,
    "support_tickets": models.SupportTicket,
    "support_messages": models.SupportMessage,
    "app_settings": models.AppSetting,
    "service_charges": models.ServiceChargeConfig,
    "app_versions": models.AppVersionControl,
    "mobile_app_release": models.MobileAppReleaseConfig,
    "quick_replies": models.QuickReplyTemplate,
    "cancellation_policies": models.CancellationPolicy,
    "admin_users": models.AdminUser,
    "activity_logs": models.AdminActivityLog,
    "analytics": models.AdminActivityLog,
    "rider_leaderboard": models.RiderLeaderboard,
    "rider_achievements": models.RiderAchievement,
    "dispatch_events": models.RiderDispatchEvent,
    "ride_ratings": models.RideRating,
    "food_ratings": models.FoodRating,
}

# Per-resource annotations that enrich FK fields with human-readable display names.
# Keys are the annotation name returned to the frontend; values are Django F() expressions.
ANNOTATION_REGISTRY = {
    "riders": {
        "user_full_name": F("user__full_name"),
        "user_phone": F("user__phone"),
    },
    "ride_bookings": {
        "customer_full_name": F("customer__full_name"),
        "customer_phone": F("customer__phone"),
        "rider_user_name": F("rider__user__full_name"),
        "vehicle_type_name": F("vehicle_type__name"),
    },
    "food_orders": {
        "customer_full_name": F("customer__full_name"),
        "restaurant_name": F("restaurant__name"),
    },
    "ecommerce_orders": {
        "customer_full_name": F("customer__full_name"),
        "vendor_store_name": F("vendor__store_name"),
    },
    "parcels": {
        "sender_full_name": F("sender__full_name"),
        "sender_user_phone": F("sender__phone"),
        "delivery_person_name": F("delivery_person__user__full_name"),
    },
    "parcel_agents": {
        "user_full_name": F("user__full_name"),
        "user_phone": F("user__phone"),
    },
    "menu_items": {
        "restaurant_name": F("restaurant__name"),
        "category_name": F("category__name"),
    },
    "food_categories": {
        "restaurant_name": F("restaurant__name"),
    },
    "parcel_bargains": {
        "delivery_person_name": F("delivery_person__user__full_name"),
        "parcel_status": F("parcel__status"),
    },
    "restaurants": {
        "owner_full_name": F("owner__full_name"),
        "owner_phone": F("owner__phone"),
    },
    "vendors": {
        "user_full_name": F("user__full_name"),
        "user_phone": F("user__phone"),
    },
    "products": {
        "vendor_store_name": F("vendor__store_name"),
        "category_name": F("category__name"),
    },
    "room_listings": {
        "owner_display_name": F("owner__full_name"),
        "owner_phone": F("owner__phone"),
    },
    "topups": {
        "user_full_name": F("user__full_name"),
        "user_phone": F("user__phone"),
    },
    "payouts": {
        "rider_full_name": F("rider__user__full_name"),
    },
    "support_tickets": {
        "user_full_name": F("user__full_name"),
    },
    "ride_ratings": {
        "rated_by_name": F("rated_by__full_name"),
        "rated_user_name": F("rated_user__full_name"),
    },
    "dispatch_events": {
        "rider_name": F("rider__user__full_name"),
    },
    "tour_bookings": {
        "customer_full_name": F("customer__full_name"),
        "customer_phone": F("customer__phone"),
        "assigned_rider_name": F("assigned_rider__user__full_name"),
        "vehicle_type_name": F("vehicle_type__name"),
    },
    "recurring_rides": {
        "customer_full_name": F("customer__full_name"),
        "customer_phone": F("customer__phone"),
        "vehicle_type_name": F("vehicle_type__name"),
    },
    "ride_bargains": {
        "rider_name": F("rider__user__full_name"),
    },
    "coin_transactions": {
        "user_full_name": F("user__full_name"),
    },
    "loyalty_transactions": {
        "user_full_name": F("user__full_name"),
    },
    "loyalty_users": {
        "user_full_name": F("user__full_name"),
        "tier_name": F("current_tier__name"),
    },
    "streaks": {
        "user_full_name": F("user__full_name"),
    },
    "food_order_items": {
        "menu_item_name": F("menu_item__name"),
        "order_restaurant": F("order__restaurant__name"),
    },
    "ecommerce_order_items": {
        "product_name": F("product__name"),
        "order_vendor": F("order__vendor__store_name"),
    },
    "product_images": {
        "product_name": F("product__name"),
    },
    "saved_locations": {
        "user_full_name": F("user__full_name"),
    },
    "support_messages": {
        "ticket_subject": F("ticket__subject"),
    },
    "notif_inbox": {
        "recipient_name": F("recipient__full_name"),
    },
}

# Query params that are NOT interpreted as field filters
_FILTER_SKIP_PARAMS = frozenset({"page", "page_size", "q", "search", "ordering", "status"})

# Allowed ORM suffixes for direct (non-FK) fields, e.g. monthly_rent__gte
_ALLOWED_DIRECT_LOOKUP_SUFFIXES = frozenset(
    {
        "gte",
        "lte",
        "gt",
        "lt",
        "exact",
        "iexact",
        "contains",
        "icontains",
        "startswith",
        "istartswith",
        "endswith",
        "iendswith",
        "isnull",
        "year",
        "month",
        "day",
        "date",
    }
)


def _allowed_user_roles():
    role_field = models.UserRole._meta.get_field("role")
    return {choice[0] for choice in role_field.choices}


def _get_user_roles(user_id):
    return list(
        models.UserRole.objects.filter(user_id=user_id, is_active=True)
        .values_list("role", flat=True)
        .order_by("created_at")
    )


def _sync_user_roles(user, roles):
    if roles is None:
        return
    desired = [r for r in roles if isinstance(r, str)]
    desired_set = set(desired) & _allowed_user_roles()
    existing_qs = models.UserRole.objects.filter(user=user)
    existing_map = {row.role: row for row in existing_qs}
    for role, row in existing_map.items():
        if role in desired_set:
            if not row.is_active:
                row.is_active = True
                row.save(update_fields=["is_active"])
        else:
            row.delete()
    for role in desired_set:
        if role not in existing_map:
            models.UserRole.objects.create(user=user, role=role, is_active=True)


def _serialize_item(obj, extra_annotation_keys=None):
    """Convert a model instance to a JSON-safe dict.

    extra_annotation_keys: list of attribute names added via .annotate() on the queryset.
    """
    result = {}
    for field in obj._meta.concrete_fields:
        name = field.name
        if isinstance(field, dj_models.ForeignKey):
            fk_id = getattr(obj, f"{name}_id", None)
            result[name] = str(fk_id) if fk_id is not None else None
        elif isinstance(field, (dj_models.ImageField, dj_models.FileField)):
            file_val = getattr(obj, name, None)
            result[name] = file_val.name if file_val else None
        else:
            value = getattr(obj, name, None)
            if isinstance(value, _uuid.UUID):
                result[name] = str(value)
            elif isinstance(value, Decimal):
                result[name] = float(value)
            elif hasattr(value, "isoformat"):
                result[name] = value.isoformat()
            else:
                result[name] = value

    result["id"] = str(obj.pk)

    # Include annotated display-name fields (added via queryset.annotate())
    for key in (extra_annotation_keys or []):
        val = getattr(obj, key, None)
        if isinstance(val, _uuid.UUID):
            val = str(val)
        result[key] = val

    if obj._meta.model_name == "user":
        result["roles"] = _get_user_roles(obj.pk)
    return result


def _default_ordering(model_cls):
    field_names = {f.name for f in model_cls._meta.fields}
    if "created_at" in field_names:
        return "-created_at"
    if "initiated_at" in field_names:
        return "-initiated_at"
    return "-pk"


def _parse_pagination(request):
    page = max(int(request.GET.get("page", 1)), 1)
    page_size = min(max(int(request.GET.get("page_size", 20)), 1), 200)
    return page, page_size


def _apply_search(qs, model_cls, query):
    if not query:
        return qs
    text_fields = [
        f.name for f in model_cls._meta.fields
        if isinstance(f, (dj_models.CharField, dj_models.TextField))
    ]
    if not text_fields:
        return qs
    condition = dj_models.Q()
    for field in text_fields[:6]:
        condition |= dj_models.Q(**{f"{field}__icontains": query})
    return qs.filter(condition)


def _apply_field_filters(qs, model_cls, request):
    """Apply query params as ORM filters: exact fields, FK traversals, and direct-field lookups (e.g. monthly_rent__gte)."""
    direct_field_names = {f.name for f in model_cls._meta.fields}
    fk_field_names = {
        f.name for f in model_cls._meta.fields
        if isinstance(f, dj_models.ForeignKey)
    }

    for param, value in request.GET.items():
        if param in _FILTER_SKIP_PARAMS or not value:
            continue

        if param in direct_field_names:
            try:
                qs = qs.filter(**{param: value})
            except Exception:
                pass
            continue

        if "__" not in param:
            continue

        base, remainder = param.split("__", 1)
        if base in fk_field_names:
            try:
                qs = qs.filter(**{param: value})
            except Exception:
                pass
            continue

        if base in direct_field_names and "__" not in remainder and remainder in _ALLOWED_DIRECT_LOOKUP_SUFFIXES:
            try:
                if remainder == "isnull":
                    v = value.lower() in ("1", "true", "yes")
                    qs = qs.filter(**{param: v})
                else:
                    qs = qs.filter(**{param: value})
            except Exception:
                pass

    return qs


def _writable_fields(model_cls):
    return {
        f.name for f in model_cls._meta.concrete_fields
        if not f.primary_key
        and not getattr(f, "auto_now_add", False)
        and not getattr(f, "auto_now", False)
    }


def _fk_attname_map(model_cls):
    """Map FK field display names to their DB attname (e.g. vehicle_type -> vehicle_type_id)."""
    return {
        f.name: f.attname
        for f in model_cls._meta.concrete_fields
        if isinstance(f, dj_models.ForeignKey)
    }


def _remap_fk_fields(data, fk_map, allowed):
    """Remap FK field names to their _id attnames so Django accepts UUID values directly."""
    fk_attnames = set(fk_map.values())
    result = {}
    for k, v in data.items():
        if k in fk_map:
            result[fk_map[k]] = v
        elif k in fk_attnames:
            result[k] = v
        elif k in allowed:
            result[k] = v
    return result


def _normalize_request_payload(request):
    """Return a plain dict from request.data with multipart list-values flattened.

    DRF multipart payloads can produce QueryDict-like data where `dict(request.data)`
    yields values as lists (including UploadedFile lists). That breaks model create/
    serialize paths expecting scalar values for single-value fields.
    """
    src = request.data
    out = {}
    # QueryDict / MultiValueDict path
    if hasattr(src, "lists"):
        for key, values in src.lists():
            if isinstance(values, (list, tuple)):
                if not values:
                    out[key] = None
                else:
                    out[key] = values[-1] if len(values) == 1 else list(values)
            else:
                out[key] = values
        return out
    # Fallback for plain mapping payloads (JSON, etc.)
    for key, value in dict(src).items():
        if isinstance(value, (list, tuple)):
            if not value:
                out[key] = None
            else:
                out[key] = value[-1] if len(value) == 1 else list(value)
        else:
            out[key] = value
    return out


# ─── List + Create ────────────────────────────────────────────────────────────

@api_view(["GET", "POST"])
def generic_list_view(request, resource):
    model_cls = MODEL_REGISTRY.get(resource)
    if not model_cls:
        raise Http404("Unknown resource")

    if request.method == "POST":
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=401)
        if not is_staff_user(request.user) and non_staff_mutation_forbidden(resource):
            return Response({"error": "Forbidden"}, status=403)
        if resource == "users" and not is_staff_user(request.user):
            return Response({"error": "Forbidden"}, status=403)
        allowed = _writable_fields(model_cls)
        fk_map = _fk_attname_map(model_cls)
        payload = _normalize_request_payload(request)
        if not is_staff_user(request.user):
            payload = enforce_create_fk(resource, payload, request.user)
        role_values = payload.pop("roles", None) if resource == "users" else None
        data = _remap_fk_fields(payload, fk_map, allowed)
        try:
            with transaction.atomic():
                obj = model_cls.objects.create(**data)
                if resource == "users":
                    _sync_user_roles(obj, role_values)
            return Response(_serialize_item(obj), status=201)
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)

    # GET – list
    if resource in ANONYMOUS_GET_RESOURCES:
        qs = model_cls.objects.all()
    elif not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."}, status=401)
    else:
        qs = model_cls.objects.all()
        if not is_staff_user(request.user):
            qs = scope_queryset(resource, qs, request.user)
    status_val = request.GET.get("status")
    query = request.GET.get("q") or request.GET.get("search")
    ordering = request.GET.get("ordering", _default_ordering(model_cls))

    if status_val and any(f.name == "status" for f in model_cls._meta.fields):
        if "," in status_val:
            parts = [s.strip() for s in status_val.split(",") if s.strip()]
            if parts:
                qs = qs.filter(status__in=parts)
        else:
            qs = qs.filter(status=status_val)

    qs = _apply_field_filters(qs, model_cls, request)
    qs = _apply_search(qs, model_cls, query)

    try:
        qs = qs.order_by(ordering)
    except Exception:
        qs = qs.order_by(_default_ordering(model_cls))

    # Apply display-name annotations for this resource
    extra_keys = []
    annotations = ANNOTATION_REGISTRY.get(resource, {})
    if annotations:
        try:
            qs = qs.annotate(**annotations)
            extra_keys = list(annotations.keys())
        except Exception:
            extra_keys = []

    page, page_size = _parse_pagination(request)
    total = qs.count()
    start = (page - 1) * page_size
    rows = [_serialize_item(x, extra_annotation_keys=extra_keys) for x in qs[start: start + page_size]]
    return Response({
        "resource": resource,
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": rows,
    })


# ─── Detail + Update + Delete ─────────────────────────────────────────────────

@api_view(["GET", "PATCH", "DELETE"])
def generic_detail_view(request, resource, pk):
    model_cls = MODEL_REGISTRY.get(resource)
    if not model_cls:
        raise Http404("Unknown resource")

    if not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."}, status=401)

    obj = model_cls.objects.filter(pk=pk).first()
    if not obj:
        raise Http404("Not found")

    if not is_staff_user(request.user) and not object_visible(resource, obj, request.user):
        raise Http404("Not found")

    if request.method == "PATCH":
        if not is_staff_user(request.user) and non_staff_mutation_forbidden(resource):
            return Response({"error": "Forbidden"}, status=403)
        allowed = _writable_fields(model_cls)
        fk_map = _fk_attname_map(model_cls)
        role_values = request.data.get("roles") if resource == "users" else None
        if resource == "users" and not is_staff_user(request.user):
            role_values = None
        update_fields = []
        for key, value in request.data.items():
            if resource == "users" and key == "roles":
                continue
            if key in fk_map:
                attname = fk_map[key]
                setattr(obj, attname, value)
                update_fields.append(attname)
            elif key in allowed:
                setattr(obj, key, value)
                update_fields.append(key)
        try:
            with transaction.atomic():
                obj.save(update_fields=update_fields if update_fields else None)
                if resource == "users":
                    _sync_user_roles(obj, role_values)
            return Response(_serialize_item(obj))
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)

    if request.method == "DELETE":
        if not is_staff_user(request.user) and non_staff_mutation_forbidden(resource):
            return Response({"error": "Forbidden"}, status=403)
        if resource == "users" and not is_staff_user(request.user):
            return Response({"error": "Forbidden"}, status=403)
        obj.delete()
        return Response(status=204)

    return Response(_serialize_item(obj))


@api_view(["POST"])
def user_adjust_coins_view(request, pk):
    if not request.user.is_authenticated or not is_staff_user(request.user):
        return Response({"error": "Forbidden"}, status=403)
    user = models.User.objects.filter(pk=pk).first()
    if not user:
        raise Http404("Not found")

    try:
        amount = int(request.data.get("amount", 0))
    except (TypeError, ValueError):
        return Response({"error": "amount must be an integer"}, status=400)
    reason = str(request.data.get("reason", "")).strip()

    if amount == 0:
        return Response({"error": "amount must be non-zero"}, status=400)
    if amount < 0 and int(user.coin_balance) + amount < 0:
        return Response({"error": "insufficient coin balance"}, status=400)

    try:
        with transaction.atomic():
            tx = models.CoinTransaction.objects.create(
                user=user,
                transaction_type="admin_adjust",
                coins=amount,
                source="admin",
                note=reason,
            )
            user.refresh_from_db(fields=["coin_balance"])
        return Response(
            {
                "user_id": str(user.pk),
                "coin_balance": int(user.coin_balance),
                "transaction_id": str(tx.pk),
            }
        )
    except Exception as exc:
        return Response({"error": str(exc)}, status=400)


# ─── Aggregated Stats ─────────────────────────────────────────────────────────

@api_view(["GET"])
def generic_stats_view(request, resource):
    """Return live aggregated stats for any registered resource.

    Response: { total, today, by_status: {status: count}, bool_counts: {field: count}, total_amount? }
    """
    model_cls = MODEL_REGISTRY.get(resource)
    if not model_cls:
        raise Http404("Unknown resource")

    if not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."}, status=401)

    qs = model_cls.objects.all()
    if not is_staff_user(request.user):
        qs = scope_queryset(resource, qs, request.user)

    field_names = {f.name for f in model_cls._meta.fields}

    total = qs.count()

    # Records created today
    today_count = 0
    if "created_at" in field_names:
        try:
            today_count = qs.filter(
                created_at__date=timezone.now().date()
            ).count()
        except Exception:
            pass

    # Counts by status
    by_status: dict = {}
    if "status" in field_names:
        try:
            rows = qs.values("status").annotate(n=Count("id"))
            by_status = {r["status"]: r["n"] for r in rows if r["status"]}
        except Exception:
            pass

    # Boolean flag counts
    bool_counts: dict = {}
    for bf in ("is_active", "is_online", "is_approved", "is_open", "is_verified", "is_frozen"):
        if bf in field_names:
            try:
                bool_counts[bf] = qs.filter(**{bf: True}).count()
            except Exception:
                pass

    # Total monetary amount and derived stats
    total_amount = None
    avg_amount = None
    today_amount = None
    amount_field = None
    for mf in ("final_fare", "total_amount", "amount", "balance", "price", "offered_price"):
        if mf in field_names:
            amount_field = mf
            try:
                agg = qs.aggregate(s=Sum(mf))
                total_amount = float(agg["s"] or 0)
                if total > 0:
                    avg_amount = round(total_amount / total, 2)
            except Exception:
                pass
            # Today's revenue
            if "created_at" in field_names and today_count > 0:
                try:
                    today_agg = qs.filter(
                        created_at__date=timezone.now().date()
                    ).aggregate(s=Sum(mf))
                    today_amount = float(today_agg["s"] or 0)
                except Exception:
                    pass
            break

    # Extra: stock=0 count for models with a stock field
    out_of_stock = None
    if "stock" in field_names:
        try:
            out_of_stock = qs.filter(stock=0).count()
        except Exception:
            pass

    resp: dict = {
        "total": total,
        "today": today_count,
        "by_status": by_status,
        "bool_counts": bool_counts,
    }
    if total_amount is not None:
        resp["total_amount"] = total_amount
    if avg_amount is not None:
        resp["avg_amount"] = avg_amount
    if today_amount is not None:
        resp["today_amount"] = today_amount
    if out_of_stock is not None:
        resp["out_of_stock"] = out_of_stock

    return Response(resp)
