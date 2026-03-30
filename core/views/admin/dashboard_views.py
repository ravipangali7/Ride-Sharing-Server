from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.timesince import timesince
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core import models


@api_view(["GET"])
def admin_dashboard_overview(request):
    rides = models.RideBooking.objects
    parcels = models.ParcelBooking.objects
    food = models.FoodOrder.objects
    ecom = models.EcommerceOrder.objects
    users = models.User.objects

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    def _revenue_for_date(d):
        return (
            (rides.filter(created_at__date=d).aggregate(v=Sum("final_fare"))["v"] or 0)
            + (parcels.filter(created_at__date=d).aggregate(v=Sum("final_fare"))["v"] or 0)
            + (food.filter(created_at__date=d).aggregate(v=Sum("total_amount"))["v"] or 0)
            + (ecom.filter(created_at__date=d).aggregate(v=Sum("total_amount"))["v"] or 0)
        )

    revenue_today = _revenue_for_date(today)
    revenue_yesterday = _revenue_for_date(yesterday)

    # Trend helpers — None when previous value is 0 (avoid division by zero)
    def _pct_change(current, previous):
        if not previous:
            return None
        pct = round((float(current) - float(previous)) / float(previous) * 100, 1)
        return {"value": f"{'+' if pct >= 0 else ''}{pct}%", "up": pct >= 0}

    rides_completed_today = rides.filter(
        status="completed", created_at__date=today
    ).count()
    rides_completed_yesterday = rides.filter(
        status="completed", created_at__date=yesterday
    ).count()

    rider_count = models.RiderProfile.objects.count()
    rider_rating_sum = float(
        models.RiderProfile.objects.aggregate(v=Sum("rating"))["v"] or 0
    )
    avg_rider_rating = round(rider_rating_sum / rider_count, 2) if rider_count else 0

    payload = {
        "kpis": {
            "live_rides": rides.filter(status__in=["accepted", "arrived", "started"]).count(),
            "live_deliveries": parcels.filter(status__in=["accepted", "picked_up", "in_transit"]).count(),
            "revenue_today": float(revenue_today),
            "revenue_yesterday": float(revenue_yesterday),
            "revenue_trend": _pct_change(revenue_today, revenue_yesterday),
            "rides_completed_today": rides_completed_today,
            "rides_completed_trend": _pct_change(rides_completed_today, rides_completed_yesterday),
            "active_users": users.filter(is_active=True).count(),
            "avg_rider_rating": avg_rider_rating,
            "open_tickets": models.SupportTicket.objects.filter(status__in=["open", "in_progress"]).count(),
            "surge_active": models.SurgePricingRule.objects.filter(is_active=True).count(),
            "push_sent": models.AdminPushLog.objects.count(),
        },
        "module_counts": {
            "rides": rides.count(),
            "parcels": parcels.count(),
            "food": food.count(),
            "ecommerce": ecom.count(),
        },
        "pending_actions": [
            {
                "label": "Rider payout requests pending",
                "count": models.RiderPayoutRequest.objects.filter(status="pending").count(),
                "priority": "high",
                "path": "/admin/finance/payouts",
            },
            {
                "label": "Rider approvals pending",
                "count": models.RiderProfile.objects.filter(is_approved=False).count(),
                "priority": "high",
                "path": "/admin/riders",
            },
            {
                "label": "Vendor approvals pending",
                "count": models.Vendor.objects.filter(is_approved=False).count(),
                "priority": "medium",
                "path": "/admin/ecommerce/vendors",
            },
            {
                "label": "Restaurant approvals pending",
                "count": models.Restaurant.objects.filter(is_approved=False).count(),
                "priority": "medium",
                "path": "/admin/food/restaurants",
            },
            {
                "label": "High priority tickets",
                "count": models.SupportTicket.objects.filter(status__in=["open", "in_progress"], priority="high").count(),
                "priority": "high",
                "path": "/admin/support",
            },
        ],
        "support_status": list(
            models.SupportTicket.objects.values("status").annotate(count=Count("id"))
        ),
    }
    return Response(payload)


@api_view(["GET"])
def admin_dashboard_activity(request):
    """Recent activity feed from live DB events."""
    events = []
    now = timezone.now()

    for ride in models.RideBooking.objects.order_by("-created_at")[:4]:
        icon = "🟢" if ride.status in ("searching", "accepted") else "✅" if ride.status == "completed" else "🔴"
        events.append({
            "icon": icon,
            "text": f"Ride {ride.status} — {ride.pickup_address or '?'} → {ride.drop_address or '?'}",
            "time": timesince(ride.created_at, now) + " ago" if ride.created_at else "",
            "_ts": ride.created_at.timestamp() if ride.created_at else 0,
        })

    for user in models.User.objects.order_by("-created_at")[:3]:
        events.append({
            "icon": "🆕",
            "text": f"New user registered — {user.phone}",
            "time": timesince(user.created_at, now) + " ago" if user.created_at else "",
            "_ts": user.created_at.timestamp() if user.created_at else 0,
        })

    for topup in models.WalletTopupRequest.objects.order_by("-initiated_at")[:2]:
        events.append({
            "icon": "💰",
            "text": f"Wallet topup — Rs. {topup.amount} via {topup.gateway}",
            "time": timesince(topup.initiated_at, now) + " ago" if topup.initiated_at else "",
            "_ts": topup.initiated_at.timestamp() if topup.initiated_at else 0,
        })

    for ticket in models.SupportTicket.objects.order_by("-created_at")[:2]:
        events.append({
            "icon": "🎫",
            "text": f"Support ticket — {ticket.subject or ticket.category}",
            "time": timesince(ticket.created_at, now) + " ago" if ticket.created_at else "",
            "_ts": ticket.created_at.timestamp() if ticket.created_at else 0,
        })

    events.sort(key=lambda x: x["_ts"], reverse=True)
    for e in events:
        e.pop("_ts", None)

    return Response(events[:10])


@api_view(["GET"])
def admin_dashboard_revenue_series(request):
    """Daily revenue breakdown for the past 7 days."""
    today = timezone.now().date()
    days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append({
            "day": day.strftime("%a"),
            "ride": float(
                models.RideBooking.objects.filter(created_at__date=day)
                .aggregate(v=Sum("final_fare"))["v"] or 0
            ),
            "parcel": float(
                models.ParcelBooking.objects.filter(created_at__date=day)
                .aggregate(v=Sum("final_fare"))["v"] or 0
            ),
            "food": float(
                models.FoodOrder.objects.filter(created_at__date=day)
                .aggregate(v=Sum("total_amount"))["v"] or 0
            ),
            "ecom": float(
                models.EcommerceOrder.objects.filter(created_at__date=day)
                .aggregate(v=Sum("total_amount"))["v"] or 0
            ),
        })
    return Response(days)


@api_view(["GET"])
def admin_dashboard_top_performers(request):
    """Top riders, restaurants and vendors by performance metrics."""
    top_riders = list(
        models.RiderProfile.objects.select_related("user")
        .order_by("-total_rides")[:5]
        .values("user__full_name", "total_rides", "rating")
    )
    top_restaurants = list(
        models.Restaurant.objects.order_by("-avg_rating")[:5]
        .values("name", "avg_rating")
    )
    top_vendors = list(
        models.Vendor.objects.order_by("-avg_rating")[:5]
        .values("store_name", "avg_rating")
    )

    return Response({
        "top_riders": [
            {
                "name": r["user__full_name"] or "—",
                "metric": f"{r['total_rides'] or 0} rides",
                "extra": f"Rating: {round(float(r['rating'] or 0), 1)}",
            }
            for r in top_riders
        ],
        "top_restaurants": [
            {
                "name": r["name"],
                "metric": f"Rating: {round(float(r['avg_rating'] or 0), 1)}",
                "extra": "",
            }
            for r in top_restaurants
        ],
        "top_vendors": [
            {
                "name": r["store_name"],
                "metric": f"Rating: {round(float(r['avg_rating'] or 0), 1)}",
                "extra": "",
            }
            for r in top_vendors
        ],
    })
