from rest_framework.decorators import api_view
from rest_framework.response import Response

from core import models


@api_view(["GET"])
def website_home_summary(request):
    payload = {
        "vehicle_types": list(models.VehicleType.objects.filter(is_active=True).values("id", "name", "base_fare")),
        "active_riders": models.RiderProfile.objects.filter(is_online=True, is_approved=True).count(),
        "popular_routes": list(
            models.RideBooking.objects.values("pickup_address", "drop_address")
            .order_by("-created_at")[:8]
        ),
        "promos": list(models.PromoCode.objects.filter(is_active=True).values("id", "code", "promo_type", "discount_value")[:8]),
    }
    return Response(payload)
