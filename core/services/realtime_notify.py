"""
Push ride/parcel/bargain updates to the Node Socket.IO server (internal HTTP).

Configure ridesharing.settings REALTIME_INTERNAL_BASE_URL (and optional secret).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _decimal_str(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return format(v, "f")


def ride_booking_socket_snapshot(booking) -> dict[str, Any]:
    """Shape aligned with Flutter RideBooking.toSocketSnapshot()."""
    from core import models

    if not isinstance(booking, models.RideBooking):
        raise TypeError("expected RideBooking")
    b = booking
    out: dict[str, Any] = {
        "id": str(b.id),
        "customer": str(b.customer_id),
        "pickup_address": b.pickup_address,
        "pickup_latitude": str(b.pickup_latitude),
        "pickup_longitude": str(b.pickup_longitude),
        "drop_address": b.drop_address,
        "drop_latitude": str(b.drop_latitude),
        "drop_longitude": str(b.drop_longitude),
        "distance_km": str(b.distance_km),
        "estimated_fare": str(b.estimated_fare),
        "status": b.status,
        "booking_type": b.booking_type,
        "is_shared_ride": b.is_shared_ride,
        "is_female_only": b.is_female_only,
        "share_contact": b.share_contact,
        "payment_method": b.payment_method,
    }
    if b.rider_id:
        out["rider"] = str(b.rider_id)
    out["vehicle_type"] = str(b.vehicle_type_id)
    ff = _decimal_str(b.final_fare)
    if ff is not None:
        out["final_fare"] = ff
    bp = _decimal_str(b.bargain_price)
    if bp is not None:
        out["bargain_price"] = bp
    if b.otp:
        out["otp"] = b.otp
    return out


def parcel_booking_socket_snapshot(parcel) -> dict[str, Any]:
    """Shape aligned with Flutter ParcelBooking.toSocketSnapshot()."""
    from core import models

    if not isinstance(parcel, models.ParcelBooking):
        raise TypeError("expected ParcelBooking")
    p = parcel
    out: dict[str, Any] = {
        "id": str(p.id),
        "sender_name": p.sender_name,
        "sender_phone": p.sender_phone,
        "sender_address": p.sender_address,
        "sender_latitude": str(p.sender_latitude),
        "sender_longitude": str(p.sender_longitude),
        "receiver_name": p.receiver_name,
        "receiver_phone": p.receiver_phone,
        "receiver_address": p.receiver_address,
        "receiver_latitude": str(p.receiver_latitude),
        "receiver_longitude": str(p.receiver_longitude),
        "is_fragile": p.is_fragile,
        "parcel_description": p.parcel_description,
        "estimated_fare": str(p.estimated_fare),
        "status": p.status,
        "payment_method": p.payment_method,
        "source": p.source,
    }
    out["sender"] = str(p.sender_id)
    if p.delivery_person_id:
        out["delivery_person"] = str(p.delivery_person_id)
    if p.parcel_weight_kg is not None:
        out["parcel_weight_kg"] = str(p.parcel_weight_kg)
    if p.otp:
        out["otp"] = p.otp
    return out


def ride_bargain_offer_payload(offer) -> dict[str, Any]:
    from core import models

    if not isinstance(offer, models.RideBargainOffer):
        raise TypeError("expected RideBargainOffer")
    return {
        "ride_id": str(offer.ride_id),
        "offer": {
            "id": str(offer.id),
            "ride": str(offer.ride_id),
            "rider": str(offer.rider_id),
            "offered_price": str(offer.offered_price),
            "status": offer.status,
        },
    }


def _internal_headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    secret = getattr(settings, "REALTIME_INTERNAL_SECRET", "") or ""
    if secret:
        h["X-Internal-Secret"] = secret
    return h


def _post(path: str, body: dict[str, Any]) -> None:
    base = (getattr(settings, "REALTIME_INTERNAL_BASE_URL", "") or "").rstrip("/")
    if not base:
        return
    url = f"{base}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_internal_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status not in (200, 204):
                logger.warning("Realtime notify unexpected status %s for %s", resp.status, path)
    except urllib.error.HTTPError as e:
        logger.warning("Realtime notify HTTP %s for %s: %s", e.code, path, e.reason)
    except urllib.error.URLError as e:
        logger.warning("Realtime notify failed for %s: %s", path, e.reason)
    except Exception:
        logger.exception("Realtime notify error for %s", path)


def notify_room(room: str, event: str, payload: dict[str, Any]) -> None:
    _post("/internal/notify", {"room": room, "event": event, "payload": payload})


def broadcast_ride_open(vehicle_type_id: str, booking_snapshot: dict[str, Any]) -> None:
    _post(
        "/internal/broadcast-ride-open",
        {"vehicleType": str(vehicle_type_id), "booking": booking_snapshot},
    )


def broadcast_parcel_open(parcel_snapshot: dict[str, Any]) -> None:
    _post("/internal/broadcast-parcel-open", {"parcel": parcel_snapshot})
