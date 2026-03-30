import secrets
import string
import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


def upload_media(instance, filename):
    """Module-level upload_to so migrations can reference core.models.upload_media."""
    folder = instance._meta.label_lower.replace(".", "_")
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{folder}/{uuid.uuid4().hex}.{ext}"


def _referral_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, phone, password, **extra):
        if not phone:
            raise ValueError("phone is required")
        phone = str(phone).strip()
        extra.setdefault("username", phone)
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("superuser must have is_staff=True")
        if extra.get("is_superuser") is not True:
            raise ValueError("superuser must have is_superuser=True")
        return self._create(phone, password, **extra)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    full_name = models.CharField(max_length=100)
    profile_photo = models.ImageField(upload_to=upload_media, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        blank=True,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
    )
    is_verified = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=10, unique=True, editable=False)
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    coin_balance = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def save(self, *args, **kwargs):
        self.username = self.phone
        if not self.referral_code:
            for _ in range(20):
                code = _referral_code()
                if not User.objects.filter(referral_code=code).exclude(pk=self.pk).exists():
                    self.referral_code = code
                    break
            else:
                self.referral_code = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)


class AdminUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    role = models.CharField(
        max_length=20,
        choices=[
            ("superadmin", "Superadmin"),
            ("admin", "Admin"),
            ("ceo", "CEO"),
            ("marketing", "Marketing"),
            ("it", "IT"),
            ("support", "Support"),
        ],
    )
    permissions = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "admin user"
        verbose_name_plural = "admin users"

    def __str__(self):
        return f"{self.user.phone} ({self.role})"


class VehicleType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    icon = models.ImageField(upload_to=upload_media)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    per_km_rate = models.DecimalField(max_digits=10, decimal_places=2)
    per_minute_rate = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField()
    is_female_driver_available = models.BooleanField(default=False)
    show_ac_badge = models.BooleanField(default=False)
    max_luggage_kg = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    vehicle_tier = models.CharField(
        max_length=20,
        choices=[
            ("economy", "Economy"),
            ("standard", "Standard"),
            ("premium", "Premium"),
            ("luxury", "Luxury"),
        ],
    )
    estimated_arrival_minutes = models.PositiveIntegerField(blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="children",
    )
    icon = models.ImageField(upload_to=upload_media, blank=True, null=True)

    def __str__(self):
        return self.name


class LoyaltyTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    min_points = models.PositiveIntegerField()
    benefits = models.JSONField(default=dict)
    badge_icon = models.ImageField(upload_to=upload_media)
    color_hex = models.CharField(max_length=7)

    def __str__(self):
        return self.name


class QuickReplyTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=50, unique=True)
    label_en = models.CharField(max_length=100)
    label_np = models.CharField(max_length=100)
    applicable_to = models.CharField(
        max_length=10,
        choices=[("rider", "Rider"), ("customer", "Customer"), ("both", "Both")],
    )
    icon = models.CharField(max_length=50)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.key


class NotificationTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(max_length=255)
    body_template = models.TextField()
    notification_type = models.CharField(
        max_length=10,
        choices=[("push", "Push"), ("sms", "SMS"), ("in_app", "In-app")],
    )
    target_role = models.CharField(
        max_length=20,
        choices=[
            ("all", "All"),
            ("customer", "Customer"),
            ("rider", "Rider"),
            ("parcel_delivery", "Parcel delivery"),
            ("vendor", "Vendor"),
            ("restaurant", "Restaurant"),
            ("room_owner", "Room owner"),
        ],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RiderAchievement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.ImageField(upload_to=upload_media)
    badge_color = models.CharField(max_length=7)
    achievement_type = models.CharField(
        max_length=20,
        choices=[
            ("trip_count", "Trip count"),
            ("rating", "Rating"),
            ("streak", "Streak"),
            ("weather", "Weather"),
            ("time_based", "Time based"),
            ("special", "Special"),
        ],
    )
    threshold_value = models.PositiveIntegerField()
    points_awarded = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PaymentIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_intents")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=5, default="NPR")
    module = models.CharField(
        max_length=20,
        choices=[
            ("ride", "Ride"),
            ("parcel", "Parcel"),
            ("food", "Food"),
            ("ecommerce", "Ecommerce"),
            ("room", "Room"),
            ("tour", "Tour"),
            ("wallet_topup", "Wallet topup"),
        ],
    )
    reference_id = models.UUIDField()
    reference_model = models.CharField(max_length=50)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("wallet", "Wallet"),
            ("cash", "Cash"),
            ("qr_esewa", "QR eSewa"),
            ("qr_khalti", "QR Khalti"),
            ("qr_ime", "QR IME"),
            ("card", "Card"),
        ],
    )
    status = models.CharField(
        max_length=25,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
            ("partially_refunded", "Partially refunded"),
        ],
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)


class PaymentTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=5, default="NPR")
    gateway = models.CharField(
        max_length=20,
        choices=[
            ("esewa", "eSewa"),
            ("khalti", "Khalti"),
            ("ime_pay", "IME Pay"),
            ("cash", "Cash"),
        ],
    )
    gateway_txn_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
    )
    purpose = models.CharField(
        max_length=20,
        choices=[
            ("wallet_topup", "Wallet topup"),
            ("ride", "Ride"),
            ("parcel", "Parcel"),
            ("food", "Food"),
            ("ecommerce", "Ecommerce"),
            ("tour", "Tour"),
            ("room", "Room"),
        ],
    )
    reference_id = models.UUIDField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)


class WalletTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=10, choices=[("credit", "Credit"), ("debit", "Debit")])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(
        max_length=20,
        choices=[
            ("topup", "Topup"),
            ("refund", "Refund"),
            ("payout", "Payout"),
            ("ride", "Ride"),
            ("parcel", "Parcel"),
            ("food", "Food"),
            ("ecommerce", "Ecommerce"),
        ],
    )
    reference_id = models.UUIDField(blank=True, null=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(
        max_length=20,
        choices=[
            ("customer", "Customer"),
            ("rider", "Rider"),
            ("parcel_delivery", "Parcel delivery"),
            ("vendor", "Vendor"),
            ("restaurant", "Restaurant"),
            ("room_owner", "Room owner"),
        ],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OTPVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_verifications")
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ("registration", "Registration"),
            ("login", "Login"),
            ("reset", "Reset"),
            ("booking_confirm", "Booking confirm"),
        ],
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    device_token = models.TextField()
    device_type = models.CharField(
        max_length=10,
        choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")],
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    is_active = models.BooleanField(default=True)
    last_active = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class CoinTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coin_transactions")
    transaction_type = models.CharField(
        max_length=15,
        choices=[("earn", "Earn"), ("spend", "Spend"), ("admin_adjust", "Admin adjust")],
    )
    coins = models.IntegerField()
    source = models.CharField(max_length=15, choices=[("ride", "Ride"), ("parcel", "Parcel"), ("admin", "Admin")])
    reference_id = models.UUIDField(blank=True, null=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CoinRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rupees_per_coin = models.DecimalField(max_digits=8, decimal_places=2, default=10)
    is_active = models.BooleanField()
    updated_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="coin_rate_updates")
    updated_at = models.DateTimeField(auto_now=True)


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(
        max_length=10,
        choices=[("push", "Push"), ("sms", "SMS"), ("in_app", "In-app")],
    )
    category = models.CharField(
        max_length=20,
        choices=[
            ("booking", "Booking"),
            ("promo", "Promo"),
            ("birthday", "Birthday"),
            ("greeting", "Greeting"),
            ("system", "System"),
            ("marketing", "Marketing"),
        ],
    )
    is_read = models.BooleanField(default=False)
    reference_id = models.UUIDField(blank=True, null=True)
    reference_type = models.CharField(max_length=20, blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)


class AdminPushLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sent_by = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name="push_logs")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="admin_push_receipts")
    target_role = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    send_type = models.CharField(
        max_length=15,
        choices=[("individual", "Individual"), ("bulk", "Bulk"), ("role_based", "Role based")],
    )
    notification_ref = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="admin_push_logs",
    )
    fcm_status = models.CharField(
        max_length=10,
        choices=[("sent", "Sent"), ("failed", "Failed"), ("pending", "Pending")],
    )
    sent_at = models.DateTimeField(auto_now_add=True)


class BirthdayPromo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=12, choices=[("percentage", "Percentage"), ("flat", "Flat")])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_days = models.PositiveIntegerField()
    is_active = models.BooleanField()
    send_notification = models.BooleanField(default=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="birthday_promos")


class CallLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calls_made")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calls_received")
    call_type = models.CharField(max_length=10, choices=[("voip", "VoIP"), ("masked", "Masked")])
    reference_type = models.CharField(max_length=10, choices=[("ride", "Ride"), ("parcel", "Parcel")])
    reference_id = models.UUIDField()
    status = models.CharField(
        max_length=15,
        choices=[
            ("initiated", "Initiated"),
            ("ringing", "Ringing"),
            ("answered", "Answered"),
            ("missed", "Missed"),
            ("ended", "Ended"),
        ],
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    call_preference_used = models.CharField(
        max_length=20,
        choices=[("in_app_voip", "In-app VoIP"), ("masked_phone", "Masked phone")],
    )
    customer_initiated = models.BooleanField(default=True)
    recording_consent = models.BooleanField(default=False)
    initiated_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)


class SavedLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_locations")
    label = models.CharField(max_length=10, choices=[("home", "Home"), ("work", "Work"), ("other", "Other")])
    custom_label = models.CharField(max_length=50, blank=True)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)


class RiderProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="rider_profile")
    license_number = models.CharField(max_length=50)
    license_photo = models.ImageField(upload_to=upload_media)
    citizenship_photo_front = models.ImageField(upload_to=upload_media)
    citizenship_photo_back = models.ImageField(upload_to=upload_media)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="riders")
    vehicle_number = models.CharField(max_length=20)
    vehicle_photo = models.ImageField(upload_to=upload_media)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_online = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=4, decimal_places=2, default=5)
    total_rides = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class RiderGenderVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider_profile = models.OneToOneField(RiderProfile, on_delete=models.CASCADE, related_name="gender_verification")
    gender = models.CharField(max_length=10, choices=[("male", "Male"), ("female", "Female"), ("other", "Other")])
    verified_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="gender_verifications")
    verified_at = models.DateTimeField()
    id_document_match = models.BooleanField()


class RiderBehaviorProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.OneToOneField(RiderProfile, on_delete=models.CASCADE, related_name="behavior_profile")
    acceptance_rate = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    cancellation_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avg_response_time_seconds = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    late_arrival_count = models.PositiveIntegerField(default=0)
    rude_reports = models.PositiveIntegerField(default=0)
    behavior_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    behavior_tier = models.CharField(
        max_length=15,
        choices=[
            ("platinum", "Platinum"),
            ("gold", "Gold"),
            ("silver", "Silver"),
            ("bronze", "Bronze"),
            ("probation", "Probation"),
        ],
    )
    last_calculated_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)


class RiderEarnedAchievement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="earned_achievements")
    achievement = models.ForeignKey(RiderAchievement, on_delete=models.CASCADE, related_name="earned_by")
    earned_at = models.DateTimeField()
    notified = models.BooleanField(default=False)


class RiderLeaderboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.CharField(max_length=10, choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")])
    period_date = models.DateField()
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="leaderboard_rows")
    rank = models.PositiveIntegerField()
    total_trips = models.PositiveIntegerField()
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2)
    score = models.DecimalField(max_digits=12, decimal_places=2)
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prize_paid = models.BooleanField(default=False)


class RideBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ride_bookings")
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_rides",
    )
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="ride_bookings")
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    drop_address = models.TextField()
    drop_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    drop_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2)
    final_fare = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    bargain_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("searching", "Searching"),
            ("bargaining", "Bargaining"),
            ("accepted", "Accepted"),
            ("arrived", "Arrived"),
            ("started", "Started"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
    )
    booking_type = models.CharField(max_length=15, choices=[("app", "App"), ("manual_call", "Manual call")])
    is_shared_ride = models.BooleanField(default=False)
    shared_with = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="shared_from",
    )
    is_female_only = models.BooleanField(default=False)
    share_contact = models.BooleanField(default=True)
    payment_method = models.CharField(
        max_length=15,
        choices=[
            ("cash", "Cash"),
            ("wallet", "Wallet"),
            ("coins", "Coins"),
            ("qr_esewa", "QR eSewa"),
            ("qr_khalti", "QR Khalti"),
            ("qr_ime", "QR IME"),
        ],
    )
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ride_bookings",
    )
    tip_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    otp = models.CharField(max_length=6, blank=True, null=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)


class RideChat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride_booking = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="chats")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RideChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(RideChat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ride_chat_messages")
    message_type = models.CharField(
        max_length=15,
        choices=[
            ("text", "Text"),
            ("quick_reply", "Quick reply"),
            ("location_pin", "Location pin"),
            ("image", "Image"),
        ],
    )
    content = models.TextField()
    quick_reply_key = models.CharField(max_length=50, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)


class RideBargainOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="bargain_offers")
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="ride_bargains")
    offered_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RideSharedRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="shared_requests")
    second_customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shared_ride_requests")
    second_pickup_address = models.TextField()
    second_pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    second_pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RideRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.OneToOneField(RideBooking, on_delete=models.CASCADE, related_name="rating")
    rated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings_given")
    rated_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings_received")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    tip_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class GuestRideBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guest_rides_booked")
    passenger_name = models.CharField(max_length=100)
    passenger_phone = models.CharField(max_length=15)
    passenger_note = models.TextField(blank=True)
    ride_booking = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="guest_details")
    notify_passenger = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GroupRideBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organized_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_rides")
    group_name = models.CharField(max_length=100)
    total_members = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class GroupRideMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(GroupRideBooking, on_delete=models.CASCADE, related_name="members")
    member_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="group_ride_memberships")
    member_name = models.CharField(max_length=100, blank=True)
    member_phone = models.CharField(max_length=15)
    ride_booking = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="group_membership")
    payment_by = models.CharField(max_length=12, choices=[("organizer", "Organizer"), ("self", "Self")])
    created_at = models.DateTimeField(auto_now_add=True)


class TourBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tour_bookings")
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="tour_bookings")
    tour_type = models.CharField(
        max_length=20,
        choices=[
            ("one_way", "One way"),
            ("round_trip", "Round trip"),
            ("full_day_hire", "Full day hire"),
            ("multi_stop", "Multi stop"),
        ],
    )
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    destination_address = models.TextField()
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    stops = models.JSONField(blank=True, null=True)
    travel_date = models.DateField()
    return_date = models.DateField(blank=True, null=True)
    estimated_km = models.DecimalField(max_digits=8, decimal_places=2)
    duration_hours = models.DecimalField(max_digits=7, decimal_places=2)
    quoted_fare = models.DecimalField(max_digits=12, decimal_places=2)
    fare_includes = models.JSONField(default=dict)
    assigned_rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tour_assignments",
    )
    status = models.CharField(
        max_length=15,
        choices=[
            ("pending", "Pending"),
            ("quoted", "Quoted"),
            ("confirmed", "Confirmed"),
            ("ongoing", "Ongoing"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[("cash", "Cash"), ("wallet", "Wallet"), ("advance_partial", "Advance partial")],
    )
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tour_bookings",
    )
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    special_request = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ScheduledRideBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride_booking = models.OneToOneField(RideBooking, on_delete=models.CASCADE, related_name="schedule")
    scheduled_datetime = models.DateTimeField()
    reminder_before_minutes = models.PositiveIntegerField(default=30)
    auto_dispatch_before_minutes = models.PositiveIntegerField(default=15)
    reminder_sent = models.BooleanField(default=False)
    dispatch_initiated = models.BooleanField(default=False)
    status = models.CharField(
        max_length=15,
        choices=[
            ("pending", "Pending"),
            ("reminded", "Reminded"),
            ("dispatching", "Dispatching"),
            ("assigned", "Assigned"),
            ("cancelled", "Cancelled"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RecurringRideTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_ride_templates")
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="recurring_templates")
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    drop_address = models.TextField()
    drop_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    drop_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recurrence_days = models.JSONField(default=list)
    pickup_time = models.TimeField()
    preferred_rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="preferred_recurring_templates",
    )
    is_female_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    advance_weeks_to_generate = models.PositiveIntegerField(default=2)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("advance_wallet", "Advance wallet"),
            ("per_ride_cash", "Per ride cash"),
            ("per_ride_wallet", "Per ride wallet"),
        ],
    )
    advance_payment_ref = models.ForeignKey(
        "RecurringRideAdvancePayment",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="linked_templates",
    )
    notes = models.TextField(blank=True)
    valid_until = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RecurringRideAdvancePayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recurring_template = models.ForeignKey(RecurringRideTemplate, on_delete=models.CASCADE, related_name="advance_payments")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_advance_payments")
    total_rides_paid_for = models.PositiveIntegerField()
    rides_remaining = models.PositiveIntegerField()
    amount_per_ride = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_transaction = models.ForeignKey(PaymentTransaction, on_delete=models.PROTECT, related_name="recurring_advances")
    status = models.CharField(
        max_length=12,
        choices=[
            ("active", "Active"),
            ("exhausted", "Exhausted"),
            ("refunded", "Refunded"),
            ("cancelled", "Cancelled"),
        ],
    )
    valid_until = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)


class RecurringRideInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(RecurringRideTemplate, on_delete=models.CASCADE, related_name="instances")
    ride_booking = models.ForeignKey(
        RideBooking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="recurring_instances",
    )
    scheduled_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending_generation", "Pending generation"),
            ("generated", "Generated"),
            ("completed", "Completed"),
            ("missed", "Missed"),
            ("cancelled", "Cancelled"),
        ],
    )
    advance_payment_deducted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class TripSafetyShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride_booking = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="safety_shares")
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trip_shares")
    recipient_phone = models.CharField(max_length=15)
    share_token = models.CharField(max_length=64, unique=True)
    tracking_url = models.URLField()
    is_active = models.BooleanField(default=True)
    shared_at = models.DateTimeField(auto_now_add=True)


class CustomerSafetySettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="safety_settings")
    default_female_only = models.BooleanField(default=False)
    call_preference = models.CharField(
        max_length=20,
        choices=[
            ("in_app_voip", "In-app VoIP"),
            ("masked_phone", "Masked phone"),
            ("both", "Both"),
        ],
    )
    share_ride_preference = models.BooleanField(default=True)
    trusted_contacts = models.JSONField(default=list)
    auto_share_trip = models.BooleanField(default=False)
    panic_button_contacts = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)


class UserTripPattern(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trip_patterns")
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    drop_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    drop_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_address = models.TextField()
    drop_address = models.TextField()
    typical_time = models.TimeField()
    typical_days = models.JSONField(default=list)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="trip_patterns")
    trip_count = models.PositiveIntegerField(default=1)
    last_seen_at = models.DateTimeField()
    confidence_score = models.DecimalField(max_digits=6, decimal_places=2)
    converted_to_recurring = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


class TripSuggestionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trip_suggestion_logs")
    pattern = models.ForeignKey(UserTripPattern, on_delete=models.CASCADE, related_name="suggestion_logs")
    suggested_at = models.DateTimeField()
    suggestion_type = models.CharField(
        max_length=20,
        choices=[
            ("push_notification", "Push notification"),
            ("in_app_banner", "In-app banner"),
            ("home_screen", "Home screen"),
        ],
    )
    was_tapped = models.BooleanField(default=False)
    booking_created = models.ForeignKey(
        RideBooking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="suggestion_bookings",
    )
    dismissed = models.BooleanField(default=False)


class UserLoyaltyProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="loyalty_profile")
    current_tier = models.ForeignKey(LoyaltyTier, on_delete=models.PROTECT, related_name="users")
    total_points = models.PositiveIntegerField(default=0)
    points_this_month = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(blank=True, null=True)
    lifetime_rides = models.PositiveIntegerField(default=0)
    lifetime_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tier_upgraded_at = models.DateTimeField(blank=True, null=True)


class LoyaltyPointTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="loyalty_point_transactions")
    points = models.IntegerField()
    source = models.CharField(
        max_length=15,
        choices=[
            ("ride", "Ride"),
            ("food", "Food"),
            ("parcel", "Parcel"),
            ("ecommerce", "Ecommerce"),
            ("referral", "Referral"),
            ("streak", "Streak"),
            ("birthday", "Birthday"),
            ("bonus", "Bonus"),
        ],
    )
    reference_id = models.UUIDField(blank=True, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class UserStreak(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="streaks")
    streak_type = models.CharField(
        max_length=20,
        choices=[
            ("daily_ride", "Daily ride"),
            ("weekly_order", "Weekly order"),
            ("monthly_active", "Monthly active"),
        ],
    )
    current_count = models.PositiveIntegerField(default=0)
    best_count = models.PositiveIntegerField(default=0)
    last_completed_date = models.DateField(blank=True, null=True)
    reward_at_count = models.PositiveIntegerField()
    next_reward_points = models.PositiveIntegerField()


class FavouriteRider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favourite_riders")
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="favourited_by")
    nickname = models.CharField(max_length=50, blank=True, null=True)
    total_rides_together = models.PositiveIntegerField(default=0)
    last_ride_together = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RiderCustomerNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="customer_notes")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rider_notes_about_me")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class CustomerPreferenceProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preference_profile")
    preferred_music = models.BooleanField(default=False)
    preferred_ac = models.BooleanField(default=False)
    preferred_quiet = models.BooleanField(default=False)
    preferred_fast_route = models.BooleanField(default=True)
    carries_luggage = models.BooleanField(default=False)
    show_preferences_to_rider = models.BooleanField(default=True)


class SurgePricingRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    trigger_type = models.CharField(
        max_length=20,
        choices=[
            ("weather", "Weather"),
            ("geo_zone", "Geo zone"),
            ("time_schedule", "Time schedule"),
            ("demand", "Demand"),
            ("admin_manual", "Admin manual"),
            ("battery_behavior", "Battery behavior"),
            ("festival", "Festival"),
        ],
    )
    multiplier = models.DecimalField(max_digits=6, decimal_places=2)
    flat_addition = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_fare_cap = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    min_fare_floor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    priority = models.PositiveIntegerField(default=10)
    stackable = models.BooleanField(default=False)
    applicable_vehicle_types = models.ManyToManyField(VehicleType, blank=True, related_name="surge_rules")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="surge_rules_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WeatherSurgeTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surge_rule = models.ForeignKey(SurgePricingRule, on_delete=models.CASCADE, related_name="weather_triggers")
    weather_condition = models.CharField(
        max_length=20,
        choices=[
            ("rain", "Rain"),
            ("heavy_rain", "Heavy rain"),
            ("fog", "Fog"),
            ("snow", "Snow"),
            ("storm", "Storm"),
            ("extreme_heat", "Extreme heat"),
        ],
    )
    min_intensity = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    weather_api_source = models.CharField(max_length=20, choices=[("openweather", "OpenWeather"), ("custom", "Custom")])
    auto_activate = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(blank=True, null=True)


class GeoZoneSurgeTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surge_rule = models.ForeignKey(SurgePricingRule, on_delete=models.CASCADE, related_name="geo_triggers")
    zone_name = models.CharField(max_length=100)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(max_digits=7, decimal_places=2)
    polygon_coords = models.JSONField(blank=True, null=True)
    zone_type = models.CharField(
        max_length=15,
        choices=[
            ("protest", "Protest"),
            ("traffic", "Traffic"),
            ("flood", "Flood"),
            ("event", "Event"),
            ("restricted", "Restricted"),
        ],
    )
    active_from = models.DateTimeField(blank=True, null=True)
    active_until = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="geo_zones_created")


class FestivalSurgeTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surge_rule = models.ForeignKey(SurgePricingRule, on_delete=models.CASCADE, related_name="festival_triggers")
    festival_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    peak_hours_only = models.BooleanField(default=False)
    peak_start_time = models.TimeField(blank=True, null=True)
    peak_end_time = models.TimeField(blank=True, null=True)
    discount_mode = models.BooleanField(default=False)


class DemandSurgeTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surge_rule = models.ForeignKey(SurgePricingRule, on_delete=models.CASCADE, related_name="demand_triggers")
    active_rider_threshold = models.PositiveIntegerField()
    pending_ride_threshold = models.PositiveIntegerField()
    check_interval_minutes = models.PositiveIntegerField(default=5)
    cooldown_minutes = models.PositiveIntegerField(default=15)
    geo_restricted = models.BooleanField(default=False)


class BatteryBehaviorSurgeTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surge_rule = models.ForeignKey(SurgePricingRule, on_delete=models.CASCADE, related_name="battery_triggers")
    avg_accept_time_threshold_seconds = models.PositiveIntegerField()
    reduce_bargain_window_to_seconds = models.PositiveIntegerField()
    lock_price_to_estimated = models.BooleanField(default=False)
    notify_admin = models.BooleanField(default=True)


class AdminFareOverride(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    override_type = models.CharField(
        max_length=20,
        choices=[
            ("flat", "Flat"),
            ("percentage", "Percentage"),
            ("distance_based", "Distance based"),
            ("time_based", "Time based"),
        ],
    )
    override_value = models.DecimalField(max_digits=10, decimal_places=2)
    distance_brackets = models.JSONField(blank=True, null=True)
    time_brackets = models.JSONField(blank=True, null=True)
    applicable_vehicle_types = models.ManyToManyField(VehicleType, blank=True, related_name="fare_overrides")
    applicable_zone = models.ForeignKey(
        GeoZoneSurgeTrigger,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="fare_overrides",
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(blank=True, null=True)
    reason = models.TextField()
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="fare_overrides")
    created_at = models.DateTimeField(auto_now_add=True)


class FareCalculationConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle_type = models.OneToOneField(VehicleType, on_delete=models.CASCADE, related_name="fare_config")
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    per_km_rate = models.DecimalField(max_digits=8, decimal_places=2)
    per_minute_rate = models.DecimalField(max_digits=8, decimal_places=2)
    minimum_fare = models.DecimalField(max_digits=10, decimal_places=2)
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    night_multiplier = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    night_start_time = models.TimeField(default="22:00")
    night_end_time = models.TimeField(default="06:00")
    waiting_charge_per_min = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    free_waiting_minutes = models.PositiveIntegerField(default=3)
    distance_brackets = models.JSONField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="fare_configs_updated")
    updated_at = models.DateTimeField(auto_now=True)


class FareEstimateLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride_booking = models.OneToOneField(RideBooking, on_delete=models.CASCADE, related_name="fare_estimate_log")
    base_fare_calculated = models.DecimalField(max_digits=10, decimal_places=2)
    surge_rules_applied = models.JSONField(default=list)
    surge_multiplier_total = models.DecimalField(max_digits=6, decimal_places=2)
    flat_additions_total = models.DecimalField(max_digits=10, decimal_places=2)
    admin_override_applied = models.ForeignKey(
        AdminFareOverride,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="estimate_logs",
    )
    final_estimated_fare = models.DecimalField(max_digits=10, decimal_places=2)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RiderDispatchConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispatch_strategy = models.CharField(
        max_length=20,
        choices=[
            ("proximity_first", "Proximity first"),
            ("rating_first", "Rating first"),
            ("behavior_score", "Behavior score"),
            ("fair_rotation", "Fair rotation"),
            ("mixed", "Mixed"),
        ],
    )
    proximity_weight = models.DecimalField(max_digits=6, decimal_places=2, default=0.4)
    rating_weight = models.DecimalField(max_digits=6, decimal_places=2, default=0.25)
    behavior_weight = models.DecimalField(max_digits=6, decimal_places=2, default=0.2)
    trip_count_weight = models.DecimalField(max_digits=6, decimal_places=2, default=0.15)
    max_radius_km = models.DecimalField(max_digits=7, decimal_places=2, default=5)
    expand_radius_if_none_km = models.DecimalField(max_digits=7, decimal_places=2, default=10)
    broadcast_to_top_n = models.PositiveIntegerField(default=5)
    accept_window_seconds = models.PositiveIntegerField(default=30)
    female_only_rider_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="dispatch_configs")
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from decimal import Decimal

        from django.core.exceptions import ValidationError

        super().clean()
        if self.dispatch_strategy != "mixed":
            return
        total = (
            self.proximity_weight
            + self.rating_weight
            + self.behavior_weight
            + self.trip_count_weight
        )
        if abs(total - Decimal("1")) > Decimal("0.0001"):
            raise ValidationError(
                {"dispatch_strategy": "Mixed strategy weights must sum to 1.0 (current sum: %s)." % total}
            )


class RiderDispatchEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride_booking = models.ForeignKey(RideBooking, on_delete=models.CASCADE, related_name="dispatch_events")
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="dispatch_events")
    dispatch_rank = models.PositiveIntegerField()
    score_at_dispatch = models.DecimalField(max_digits=8, decimal_places=2)
    notified_at = models.DateTimeField()
    response = models.CharField(
        max_length=15,
        choices=[
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("timeout", "Timeout"),
            ("no_response", "No response"),
        ],
    )
    responded_at = models.DateTimeField(blank=True, null=True)


class RiderTripTarget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_name = models.CharField(max_length=100)
    target_type = models.CharField(
        max_length=10,
        choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("custom", "Custom")],
    )
    min_trips = models.PositiveIntegerField()
    bonus_type = models.CharField(max_length=10, choices=[("wallet", "Wallet"), ("coins", "Coins"), ("both", "Both")])
    wallet_bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coin_bonus_amount = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    applicable_vehicle_types = models.ManyToManyField(VehicleType, blank=True, related_name="trip_targets")
    min_rating_to_qualify = models.DecimalField(max_digits=4, decimal_places=2, default=4)
    min_behavior_score = models.DecimalField(max_digits=6, decimal_places=2, default=60)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="trip_targets")


class RiderTargetProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="target_progress")
    target = models.ForeignKey(RiderTripTarget, on_delete=models.CASCADE, related_name="progress_rows")
    trips_completed = models.PositiveIntegerField(default=0)
    bonus_paid = models.BooleanField(default=False)
    bonus_paid_at = models.DateTimeField(blank=True, null=True)
    qualifying_rides = models.JSONField(default=list)
    last_updated_at = models.DateTimeField(auto_now=True)


class DemandForecast(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    zone_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    zone_radius_km = models.DecimalField(max_digits=7, decimal_places=2)
    forecast_datetime = models.DateTimeField()
    predicted_demand = models.PositiveIntegerField()
    available_riders = models.PositiveIntegerField()
    demand_gap = models.IntegerField()
    confidence_pct = models.DecimalField(max_digits=6, decimal_places=2)
    data_source = models.CharField(
        max_length=20,
        choices=[
            ("historical", "Historical"),
            ("event_based", "Event based"),
            ("weather_adjusted", "Weather adjusted"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RiderNudge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="nudges")
    nudge_type = models.CharField(
        max_length=15,
        choices=[("go_online", "Go online"), ("move_to_zone", "Move to zone"), ("extend_shift", "Extend shift")],
    )
    message = models.TextField()
    target_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    target_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    forecast = models.ForeignKey(
        DemandForecast,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="nudges",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    was_acted_on = models.BooleanField(default=False)


class ParcelDeliveryProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="parcel_profile")
    license_number = models.CharField(max_length=50)
    license_photo = models.ImageField(upload_to=upload_media)
    citizenship_photo_front = models.ImageField(upload_to=upload_media)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="parcel_carriers")
    vehicle_number = models.CharField(max_length=20)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_online = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=4, decimal_places=2, default=5)
    created_at = models.DateTimeField(auto_now_add=True)


class ParcelBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parcel_bookings_sent")
    delivery_person = models.ForeignKey(
        ParcelDeliveryProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="deliveries",
    )
    sender_name = models.CharField(max_length=100)
    sender_phone = models.CharField(max_length=15)
    sender_address = models.TextField()
    sender_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    sender_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    receiver_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=15)
    receiver_address = models.TextField()
    receiver_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    receiver_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_fragile = models.BooleanField(default=False)
    parcel_description = models.TextField()
    parcel_weight_kg = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    parcel_photo = models.ImageField(upload_to=upload_media, blank=True, null=True)
    bargain_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2)
    final_fare = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("searching", "Searching"),
            ("bargaining", "Bargaining"),
            ("accepted", "Accepted"),
            ("picked_up", "Picked up"),
            ("in_transit", "In transit"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
    )
    is_multiple = models.BooleanField(default=False)
    payment_method = models.CharField(
        max_length=15,
        choices=[
            ("cash", "Cash"),
            ("wallet", "Wallet"),
            ("coins", "Coins"),
            ("qr_esewa", "QR eSewa"),
            ("qr_khalti", "QR Khalti"),
            ("qr_ime", "QR IME"),
        ],
    )
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="parcel_bookings",
    )
    source = models.CharField(
        max_length=15,
        choices=[("customer", "Customer"), ("ecommerce", "Ecommerce"), ("restaurant", "Restaurant")],
    )
    reference_order_id = models.UUIDField(blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)


class ParcelBargainOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parcel = models.ForeignKey(ParcelBooking, on_delete=models.CASCADE, related_name="bargain_offers")
    delivery_person = models.ForeignKey(ParcelDeliveryProfile, on_delete=models.CASCADE, related_name="bargain_offers")
    offered_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class ParcelItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parcel_booking = models.ForeignKey(ParcelBooking, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    is_fragile = models.BooleanField()
    note = models.TextField(blank=True)


class Restaurant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restaurants_owned")
    name = models.CharField(max_length=150)
    description = models.TextField()
    logo = models.ImageField(upload_to=upload_media)
    cover_photo = models.ImageField(upload_to=upload_media)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    phone = models.CharField(max_length=15)
    pan_vat_number = models.CharField(max_length=20, blank=True)
    is_cloud_kitchen = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_open = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    delivery_radius_km = models.DecimalField(max_digits=7, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class FoodCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField()


class MenuItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_items")
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=150)
    description = models.TextField()
    photo = models.ImageField(upload_to=upload_media)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    is_veg = models.BooleanField(default=False)
    preparation_time_minutes = models.PositiveIntegerField()


class FoodOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="food_orders")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    parcel_booking = models.ForeignKey(
        ParcelBooking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="food_orders",
    )
    delivery_address = models.TextField()
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=15,
        choices=[
            ("cash", "Cash"),
            ("wallet", "Wallet"),
            ("qr_esewa", "QR eSewa"),
            ("qr_khalti", "QR Khalti"),
            ("qr_ime", "QR IME"),
        ],
    )
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="food_orders",
    )
    status = models.CharField(
        max_length=15,
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("preparing", "Preparing"),
            ("ready", "Ready"),
            ("picked_up", "Picked up"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
    )
    special_instruction = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)


class FoodOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(FoodOrder, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="order_lines")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)


class FoodRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(FoodOrder, on_delete=models.CASCADE, related_name="rating")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="food_ratings")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="ratings")
    food_rating = models.PositiveSmallIntegerField()
    delivery_rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Vendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendor_profile")
    store_name = models.CharField(max_length=150)
    store_logo = models.ImageField(upload_to=upload_media)
    store_banner = models.ImageField(upload_to=upload_media)
    description = models.TextField()
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    pan_number = models.CharField(max_length=20, blank=True)
    vat_number = models.CharField(max_length=20, blank=True)
    registration_doc = models.FileField(upload_to=upload_media)
    is_approved = models.BooleanField(default=False)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField()
    sku = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=upload_media)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField()


class EcommerceOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ecommerce_orders")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="orders")
    parcel_booking = models.ForeignKey(
        ParcelBooking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ecommerce_orders",
    )
    delivery_address = models.TextField()
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash_on_delivery", "Cash on delivery"),
            ("wallet", "Wallet"),
            ("qr_esewa", "QR eSewa"),
            ("qr_khalti", "QR Khalti"),
            ("qr_ime", "QR IME"),
        ],
    )
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ecommerce_orders",
    )
    status = models.CharField(
        max_length=15,
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("packed", "Packed"),
            ("picked_up", "Picked up"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)


class EcommerceOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(EcommerceOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_lines")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)


class ProductReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_reviews")
    order = models.ForeignKey(EcommerceOrder, on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RoomOwnerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="room_owner_profile")
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    citizenship_photo = models.ImageField(upload_to=upload_media)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class RoomListing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(RoomOwnerProfile, on_delete=models.CASCADE, related_name="listings")
    title = models.CharField(max_length=200)
    description = models.TextField()
    full_address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100)
    room_type = models.CharField(
        max_length=10,
        choices=[
            ("single", "Single"),
            ("double", "Double"),
            ("flat", "Flat"),
            ("hostel", "Hostel"),
            ("pg", "PG"),
        ],
    )
    floor = models.PositiveIntegerField(blank=True, null=True)
    total_floors = models.PositiveIntegerField(blank=True, null=True)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2)
    advance_months = models.PositiveIntegerField(default=2)
    is_furnished = models.BooleanField()
    has_parking = models.BooleanField()
    has_wifi = models.BooleanField()
    has_water = models.BooleanField()
    has_electricity = models.BooleanField()
    allowed_gender = models.CharField(
        max_length=10,
        choices=[("any", "Any"), ("male", "Male"), ("female", "Female")],
    )
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    service_charge_type = models.CharField(max_length=15, choices=[("percentage", "Percentage"), ("membership", "Membership")])
    service_charge_value = models.DecimalField(max_digits=8, decimal_places=2)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class RoomMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(RoomListing, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=10, choices=[("photo", "Photo"), ("video", "Video")])
    file = models.FileField(upload_to=upload_media)
    external_link = models.URLField(blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField()


class RoomInquiry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(RoomListing, on_delete=models.CASCADE, related_name="inquiries")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="room_inquiries")
    message = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("replied", "Replied"), ("closed", "Closed")],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class RoomBookingRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(RoomListing, on_delete=models.CASCADE, related_name="booking_requests")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="room_booking_requests")
    move_in_date = models.DateField()
    duration_months = models.PositiveIntegerField(blank=True, null=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")],
    )
    created_at = models.DateTimeField(auto_now_add=True)


class QRPaymentSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_intent = models.OneToOneField(
        PaymentIntent,
        on_delete=models.CASCADE,
        related_name="qr_session",
    )
    qr_code_data = models.TextField()
    qr_image = models.ImageField(upload_to=upload_media, blank=True, null=True)
    gateway = models.CharField(
        max_length=15,
        choices=[
            ("esewa", "eSewa"),
            ("khalti", "Khalti"),
            ("ime_pay", "IME Pay"),
            ("fonepay", "Fonepay"),
        ],
    )
    deep_link_url = models.URLField()
    expires_at = models.DateTimeField()
    scanned_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("scanned", "Scanned"),
            ("completed", "Completed"),
            ("expired", "Expired"),
        ],
    )


class WalletTopupRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallet_topups")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gateway = models.CharField(
        max_length=15,
        choices=[("esewa", "eSewa"), ("khalti", "Khalti"), ("ime_pay", "IME Pay")],
    )
    payment_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="topup_requests",
    )
    status = models.CharField(
        max_length=12,
        choices=[
            ("initiated", "Initiated"),
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)


class RiderPayoutRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="payout_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=30, blank=True, null=True)
    esewa_id = models.CharField(max_length=50, blank=True, null=True)
    khalti_id = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(
        max_length=12,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("paid", "Paid"),
            ("rejected", "Rejected"),
        ],
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, blank=True, null=True, related_name="payouts_processed")
    processed_at = models.DateTimeField(blank=True, null=True)
    transaction_ref = models.CharField(max_length=100, blank=True, null=True)

    def clean(self):
        from decimal import Decimal

        from django.core.exceptions import ValidationError

        super().clean()
        if self.status != "paid" or not self.rider_id or not self.amount:
            return
        if self.pk and WalletTransaction.objects.filter(
            source="payout",
            reference_id=self.pk,
            transaction_type="debit",
        ).exists():
            return
        wallet = Wallet.objects.filter(user_id=self.rider.user_id).first()
        bal = wallet.balance if wallet else Decimal("0")
        if bal < self.amount:
            raise ValidationError(
                {"status": "Insufficient wallet balance to mark payout as paid (available: %s)." % bal}
            )


class PromoCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    promo_type = models.CharField(max_length=12, choices=[("percentage", "Percentage"), ("flat", "Flat")])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    applicable_on = models.CharField(
        max_length=12,
        choices=[
            ("ride", "Ride"),
            ("parcel", "Parcel"),
            ("food", "Food"),
            ("ecommerce", "Ecommerce"),
            ("all", "All"),
        ],
    )
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    usage_per_user = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_birthday_promo = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="promo_codes")


class PromoUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="promo_usages")
    reference_id = models.UUIDField()
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)


class ReferralReward(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referral_rewards_given")
    referred_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referral_rewards_received")
    reward_type = models.CharField(max_length=10, choices=[("coins", "Coins"), ("wallet", "Wallet"), ("both", "Both")])
    coins_awarded = models.PositiveIntegerField(default=0)
    wallet_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    trigger_event = models.CharField(
        max_length=20,
        choices=[
            ("first_ride", "First ride"),
            ("first_order", "First order"),
            ("registration", "Registration"),
        ],
    )
    rewarded_at = models.DateTimeField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)


class CancellationPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    applies_after_status = models.CharField(max_length=20)
    grace_period_minutes = models.PositiveIntegerField(default=2)
    fee_type = models.CharField(max_length=12, choices=[("flat", "Flat"), ("percentage", "Percentage")])
    fee_value = models.DecimalField(max_digits=10, decimal_places=2)
    fee_recipient = models.CharField(max_length=10, choices=[("rider", "Rider"), ("platform", "Platform"), ("split", "Split")])
    rider_pct = models.DecimalField(max_digits=6, decimal_places=2, default=80)
    is_active = models.BooleanField()
    updated_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="cancellation_policies")


class PopupAd(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to=upload_media)
    link_url = models.URLField(blank=True)
    target_role = models.CharField(
        max_length=20,
        choices=[
            ("all", "All"),
            ("customer", "Customer"),
            ("rider", "Rider"),
            ("parcel_delivery", "Parcel delivery"),
            ("vendor", "Vendor"),
            ("restaurant", "Restaurant"),
            ("room_owner", "Room owner"),
        ],
    )
    is_active = models.BooleanField()
    show_on_open = models.BooleanField(default=True)
    display_frequency = models.CharField(
        max_length=15,
        choices=[("every_open", "Every open"), ("once_daily", "Once daily"), ("once_ever", "Once ever")],
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="popup_ads")
    created_at = models.DateTimeField(auto_now_add=True)


class PopupAdView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.ForeignKey(PopupAd, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="popup_views")
    viewed_at = models.DateTimeField(auto_now_add=True)


class AppSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    value_type = models.CharField(
        max_length=10,
        choices=[
            ("string", "String"),
            ("integer", "Integer"),
            ("decimal", "Decimal"),
            ("boolean", "Boolean"),
            ("json", "JSON"),
        ],
    )
    description = models.TextField()
    editable_by = models.CharField(
        max_length=12,
        choices=[
            ("superadmin", "Superadmin"),
            ("admin", "Admin"),
            ("ceo", "CEO"),
            ("it", "IT"),
        ],
    )
    updated_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, blank=True, null=True, related_name="settings_updates")
    updated_at = models.DateTimeField(auto_now=True)


class ServiceChargeConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.CharField(max_length=12, choices=[("room", "Room"), ("food", "Food"), ("ecommerce", "Ecommerce")])
    charge_type = models.CharField(max_length=12, choices=[("percentage", "Percentage"), ("membership", "Membership")])
    charge_value = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField()
    updated_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="service_charge_updates")
    updated_at = models.DateTimeField(auto_now=True)


class AppVersionControl(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.CharField(max_length=10, choices=[("android", "Android"), ("ios", "iOS")])
    version_code = models.PositiveIntegerField()
    version_name = models.CharField(max_length=20)
    force_update = models.BooleanField(default=False)
    update_message = models.TextField()
    store_url = models.URLField()
    released_at = models.DateTimeField()
    created_by = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name="app_versions")


class AdminActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name="activity_logs")
    action_type = models.CharField(
        max_length=15,
        choices=[
            ("create", "Create"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("approve", "Approve"),
            ("reject", "Reject"),
            ("override", "Override"),
        ],
    )
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()
    before_state = models.JSONField(blank=True, null=True)
    after_state = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SupportTicket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=15,
        choices=[
            ("ride", "Ride"),
            ("parcel", "Parcel"),
            ("food", "Food"),
            ("ecommerce", "Ecommerce"),
            ("room", "Room"),
            ("payment", "Payment"),
            ("account", "Account"),
            ("other", "Other"),
        ],
    )
    reference_id = models.UUIDField(blank=True, null=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("open", "Open"),
            ("in_progress", "In progress"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
        ],
    )
    priority = models.CharField(max_length=10, choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")])
    assigned_to = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, blank=True, null=True, related_name="tickets_assigned")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)


class SupportMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_messages")
    message = models.TextField()
    attachment = models.FileField(upload_to=upload_media, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
