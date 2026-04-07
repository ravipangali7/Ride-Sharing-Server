"""Admin authentication views."""

import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import OTPVerification, User, UserRole


def _tokens_for_user(user):
    """Return a new access + refresh JWT pair for the given user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@api_view(["POST"])
def admin_login(request):
    identifier = (request.data.get("phone") or request.data.get("email") or "").strip()
    password = (request.data.get("password") or "").strip()

    if not identifier or not password:
        return Response({"error": "Phone/email and password are required"}, status=400)

    user_obj = (
        User.objects.filter(phone=identifier).first()
        or User.objects.filter(email=identifier).first()
    )

    if not user_obj:
        return Response({"error": "Invalid credentials"}, status=401)

    user = authenticate(request, username=user_obj.username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    if not (user.is_staff or user.is_superuser):
        return Response({"error": "Not authorized as admin"}, status=403)

    tokens = _tokens_for_user(user)
    return Response({
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    })


@api_view(["POST"])
def customer_register(request):
    """Register a new customer (no is_staff required)."""
    phone = (request.data.get("phone") or "").strip()
    password = (request.data.get("password") or "").strip()
    full_name = (request.data.get("full_name") or "").strip()

    if not phone or not password or not full_name:
        return Response({"error": "phone, password, and full_name are required"}, status=400)

    if User.objects.filter(phone=phone).exists():
        return Response({"error": "Phone number already registered"}, status=409)

    user = User.objects.create_user(
        username=phone,
        phone=phone,
        password=password,
        full_name=full_name,
        email=request.data.get("email", "").strip() or None,
    )
    UserRole.objects.get_or_create(
        user=user,
        role="customer",
        defaults={"is_active": True},
    )
    tokens = _tokens_for_user(user)
    return Response({
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": _serialize_user(user),
    }, status=201)


@api_view(["POST"])
def customer_login(request):
    """Authenticate a customer by phone + password (no staff gate)."""
    phone = (request.data.get("phone") or "").strip()
    password = (request.data.get("password") or "").strip()

    if not phone or not password:
        return Response({"error": "phone and password are required"}, status=400)

    user_obj = User.objects.filter(phone=phone).first()
    if not user_obj:
        return Response({"error": "Invalid credentials"}, status=401)

    user = authenticate(request, username=user_obj.username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    tokens = _tokens_for_user(user)
    return Response({
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": _serialize_user(user),
    })


_PURPOSE_ALIASES = {
    "register": "registration",
    "registration": "registration",
    "login": "login",
    "reset": "reset",
    "booking_confirm": "booking_confirm",
}


@api_view(["POST"])
def request_otp(request):
    """Create a one-time code for an existing user (e.g. after register, or login-with-OTP)."""
    phone = (request.data.get("phone") or "").strip()
    raw_purpose = (request.data.get("purpose") or "login").strip().lower()
    purpose = _PURPOSE_ALIASES.get(raw_purpose, raw_purpose)
    valid = {c[0] for c in OTPVerification._meta.get_field("purpose").choices}
    if purpose not in valid:
        return Response({"error": "invalid purpose"}, status=400)
    if not phone:
        return Response({"error": "phone is required"}, status=400)

    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({"error": "No account found for this phone"}, status=404)

    code = f"{random.randint(0, 999999):06d}"
    OTPVerification.objects.create(
        user=user,
        otp_code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    payload = {"message": "OTP sent", "expires_in": 600}
    if settings.DEBUG:
        payload["debug_otp"] = code
    return Response(payload)


@api_view(["POST"])
def verify_otp(request):
    """Validate OTP; for login purpose returns JWT pair."""
    phone = (request.data.get("phone") or "").strip()
    otp_code = (request.data.get("otp") or request.data.get("otp_code") or "").strip()
    if not phone or not otp_code:
        return Response({"error": "phone and otp are required"}, status=400)

    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({"error": "Invalid code"}, status=401)

    rec = (
        OTPVerification.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    if not rec:
        return Response({"error": "Invalid or expired code"}, status=400)

    rec.is_used = True
    rec.save(update_fields=["is_used"])

    if rec.purpose == "registration":
        user.is_verified = True
        user.save(update_fields=["is_verified"])

    if rec.purpose == "login":
        tokens = _tokens_for_user(user)
        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": _serialize_user(user),
        })

    return Response({"verified": True, "purpose": rec.purpose})


def _serialize_user(user):
    """Shared user payload for auth responses."""
    from core.models import RiderProfile
    roles = list(
        UserRole.objects.filter(user=user, is_active=True).values_list("role", flat=True)
    )
    has_rider = RiderProfile.objects.filter(user=user).exists()
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email or "",
        "phone": user.phone,
        "profile_photo": user.profile_photo.url if user.profile_photo else None,
        "gender": user.gender,
        "date_of_birth": str(user.date_of_birth) if user.date_of_birth else None,
        "is_verified": user.is_verified,
        "coin_balance": user.coin_balance,
        "referral_code": user.referral_code,
        "roles": roles,
        "is_rider": has_rider,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_me(request):
    """Return current user (roles, flags) for app refresh after token restore."""
    return Response(_serialize_user(request.user))


@api_view(["POST"])
def admin_token_refresh(request):
    """Exchange a refresh token for a new access token."""
    from rest_framework_simplejwt.tokens import RefreshToken as RT
    from rest_framework_simplejwt.exceptions import TokenError

    refresh_token = (request.data.get("refresh") or "").strip()
    if not refresh_token:
        return Response({"error": "refresh token required"}, status=400)
    try:
        token = RT(refresh_token)
        return Response({"access": str(token.access_token)})
    except TokenError as exc:
        return Response({"error": str(exc)}, status=401)
