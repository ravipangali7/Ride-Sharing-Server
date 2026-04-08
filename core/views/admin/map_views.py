"""Admin map feed: real coordinates from riders, parcel carriers, and static business locations."""

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core import models


def _float(v):
    if v is None:
        return None
    return float(v)


@api_view(["GET"])
def admin_map_entities(request):
    """Return mappable entities for the God Eye admin map. Requires staff JWT."""
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."}, status=401)
    if not getattr(request.user, "is_staff", False):
        return Response({"detail": "Forbidden"}, status=403)

    entities = []

    for r in (
        models.RiderProfile.objects.select_related("user")
        .filter(current_latitude__isnull=False, current_longitude__isnull=False)
        .order_by("-created_at")[:150]
    ):
        lat, lng = _float(r.current_latitude), _float(r.current_longitude)
        if lat is None or lng is None:
            continue
        name = (r.user.full_name or r.user.phone or str(r.user_id))[:80]
        entities.append(
            {
                "type": "rider",
                "name": name,
                "lat": lat,
                "lng": lng,
                "status": "online" if r.is_online else "offline",
                "detail": "Approved" if r.is_approved else "Pending approval",
            }
        )

    for p in (
        models.ParcelDeliveryProfile.objects.select_related("user")
        .filter(current_latitude__isnull=False, current_longitude__isnull=False)
        .order_by("-created_at")[:80]
    ):
        lat, lng = _float(p.current_latitude), _float(p.current_longitude)
        if lat is None or lng is None:
            continue
        name = (p.user.full_name or p.user.phone or "Parcel agent")[:80]
        entities.append(
            {
                "type": "parcel_agent",
                "name": name,
                "lat": lat,
                "lng": lng,
                "status": "online" if p.is_online else "offline",
                "detail": "Parcel delivery",
            }
        )

    for rest in models.Restaurant.objects.filter(is_approved=True).order_by("-created_at")[:80]:
        lat, lng = _float(rest.latitude), _float(rest.longitude)
        if lat is None or lng is None:
            continue
        entities.append(
            {
                "type": "restaurant",
                "name": rest.name[:80],
                "lat": lat,
                "lng": lng,
                "status": "open" if rest.is_open else "closed",
                "detail": "Restaurant",
            }
        )

    for v in models.Vendor.objects.filter(is_approved=True).order_by("-created_at")[:80]:
        lat, lng = _float(v.latitude), _float(v.longitude)
        if lat is None or lng is None:
            continue
        entities.append(
            {
                "type": "vendor",
                "name": v.store_name[:80],
                "lat": lat,
                "lng": lng,
                "status": "active",
                "detail": "E-commerce vendor",
            }
        )

    for room in models.RoomListing.objects.filter(is_available=True).order_by("-created_at")[:80]:
        lat, lng = _float(room.latitude), _float(room.longitude)
        if lat is None or lng is None:
            continue
        entities.append(
            {
                "type": "room_lister",
                "name": room.title[:80],
                "lat": lat,
                "lng": lng,
                "status": "listed",
                "detail": f"{room.city} · {room.room_type}",
            }
        )

    return Response(
        {
            "entities": entities,
            "updated_at": timezone.now().isoformat(),
        }
    )
