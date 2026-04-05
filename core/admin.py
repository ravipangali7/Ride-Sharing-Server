from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponse
from django.utils.html import format_html

from . import models
from .forms import (
    MenuItemAdminForm,
    PopupAdAdminForm,
    ProductImageAdminForm,
    RestaurantAdminForm,
    RiderProfileAdminForm,
    UserAdminChangeForm,
    UserAdminCreationForm,
    VehicleTypeAdminForm,
)


def admin_image_preview(obj, field_name, height=120):
    f = getattr(obj, field_name, None)
    if not f:
        return "—"
    try:
        url = f.url
    except ValueError:
        return "—"
    return format_html(
        '<img src="{}" alt="" style="max-height:{}px;max-width:320px;border-radius:6px;object-fit:contain"/>',
        url,
        height,
    )


@admin.action(description="Deactivate selected records")
def deactivate_records(modeladmin, request, queryset):
    if not hasattr(queryset.model, "is_active"):
        modeladmin.message_user(request, "This model has no is_active field.", level=messages.ERROR)
        return
    n = queryset.update(is_active=False)
    modeladmin.message_user(request, f"Deactivated {n} row(s).")


@admin.action(description="Activate selected records")
def activate_records(modeladmin, request, queryset):
    if not hasattr(queryset.model, "is_active"):
        modeladmin.message_user(request, "This model has no is_active field.", level=messages.ERROR)
        return
    n = queryset.update(is_active=True)
    modeladmin.message_user(request, f"Activated {n} row(s).")


@admin.action(description="Mark selected users verified")
def verify_users(modeladmin, request, queryset):
    queryset.update(is_verified=True)
    modeladmin.message_user(request, f"Verified {queryset.count()} user(s).")


@admin.action(description="Approve selected rider profiles")
def approve_riders(modeladmin, request, queryset):
    queryset.update(is_approved=True)
    modeladmin.message_user(request, f"Approved {queryset.count()} rider(s).")


@admin.action(description="Export selected IDs as CSV")
def export_ids_csv(modeladmin, request, queryset):
    import csv

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="export.csv"'
    w = csv.writer(response)
    w.writerow(["id"])
    for obj in queryset:
        w.writerow([obj.pk])
    return response


class AdminUserInline(admin.StackedInline):
    model = models.AdminUser
    extra = 0
    max_num = 1
    fk_name = "user"
    fields = ("role", "permissions", "is_active", "created_at")
    readonly_fields = ("created_at",)


class UserRoleInline(admin.StackedInline):
    model = models.UserRole
    extra = 0
    fields = ("role", "is_active", "created_at")
    readonly_fields = ("created_at",)


class UserSessionInline(admin.StackedInline):
    model = models.UserSession
    extra = 0
    fields = (
        "device_type",
        "device_token",
        "access_token",
        "refresh_token",
        "is_active",
        "last_active",
        "created_at",
    )
    readonly_fields = ("created_at",)


class OTPVerificationInline(admin.StackedInline):
    model = models.OTPVerification
    extra = 0
    fields = ("otp_code", "purpose", "is_used", "expires_at", "created_at")
    readonly_fields = ("created_at",)


class CoinTransactionInline(admin.TabularInline):
    model = models.CoinTransaction
    extra = 0
    fields = ("transaction_type", "coins", "source", "reference_id", "note", "created_at")
    readonly_fields = ("created_at",)


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    ordering = ("-created_at",)
    list_display = (
        "phone",
        "full_name",
        "email",
        "is_staff",
        "is_verified",
        "coin_balance",
        "created_at",
        "profile_thumb",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "is_verified", "gender", "created_at")
    search_fields = ("phone", "email", "full_name", "referral_code", "id")
    readonly_fields = (
        "referral_code",
        "created_at",
        "updated_at",
        "profile_photo_preview",
        "date_joined",
        "last_login",
    )
    actions = (verify_users, deactivate_records, activate_records, export_ids_csv)
    filter_horizontal = ("groups", "user_permissions")
    inlines = (AdminUserInline, UserRoleInline, UserSessionInline, OTPVerificationInline, CoinTransactionInline)

    @admin.display(description="Photo")
    def profile_thumb(self, obj):
        return admin_image_preview(obj, "profile_photo", 36)

    @admin.display(description="Profile photo preview")
    def profile_photo_preview(self, obj):
        return admin_image_preview(obj, "profile_photo", 200)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "full_name",
                    "email",
                    "profile_photo",
                    "profile_photo_preview",
                    "date_of_birth",
                    "gender",
                    "is_verified",
                    "coin_balance",
                )
            },
        ),
        ("Referral", {"fields": ("referral_code", "referred_by")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(models.AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("user__phone", "user__full_name", "user__email")
    autocomplete_fields = ("user",)
    actions = (deactivate_records, activate_records)


class RiderGenderVerificationInline(admin.StackedInline):
    model = models.RiderGenderVerification
    extra = 0
    max_num = 1
    raw_id_fields = ("verified_by",)


class RiderBehaviorProfileInline(admin.StackedInline):
    model = models.RiderBehaviorProfile
    extra = 0
    max_num = 1


class RiderEarnedAchievementInline(admin.TabularInline):
    model = models.RiderEarnedAchievement
    extra = 0
    raw_id_fields = ("achievement",)


@admin.register(models.RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    form = RiderProfileAdminForm
    list_display = ("user", "vehicle_type", "is_online", "is_approved", "rating", "total_rides", "license_thumb")
    list_filter = ("is_online", "is_approved", "vehicle_type", "created_at")
    search_fields = ("user__phone", "user__full_name", "vehicle_number", "license_number", "id")
    autocomplete_fields = ("user", "vehicle_type")
    raw_id_fields = ("user", "vehicle_type")
    readonly_fields = ("license_preview", "vehicle_preview")
    actions = (approve_riders, export_ids_csv)
    inlines = (RiderGenderVerificationInline, RiderBehaviorProfileInline, RiderEarnedAchievementInline)

    @admin.display(description="License")
    def license_thumb(self, obj):
        return admin_image_preview(obj, "license_photo", 32)

    @admin.display(description="License preview")
    def license_preview(self, obj):
        return admin_image_preview(obj, "license_photo", 160)

    @admin.display(description="Vehicle preview")
    def vehicle_preview(self, obj):
        return admin_image_preview(obj, "vehicle_photo", 160)


class RideBargainOfferInline(admin.TabularInline):
    model = models.RideBargainOffer
    extra = 0
    raw_id_fields = ("rider",)


class RideSharedRequestInline(admin.TabularInline):
    model = models.RideSharedRequest
    extra = 0
    raw_id_fields = ("second_customer",)


class GuestRideBookingInline(admin.StackedInline):
    model = models.GuestRideBooking
    extra = 0
    max_num = 3


class ScheduledRideBookingInline(admin.StackedInline):
    model = models.ScheduledRideBooking
    extra = 0
    max_num = 1


@admin.register(models.RideBooking)
class RideBookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "rider", "status", "vehicle_type", "estimated_fare", "created_at")
    list_filter = ("status", "booking_type", "is_female_only", "payment_method", "created_at")
    search_fields = ("pickup_address", "drop_address", "customer__phone", "id")
    raw_id_fields = ("customer", "rider", "vehicle_type", "payment_intent", "shared_with")
    date_hierarchy = "created_at"
    actions = (export_ids_csv,)
    inlines = (
        RideBargainOfferInline,
        RideSharedRequestInline,
        GuestRideBookingInline,
        ScheduledRideBookingInline,
    )


class FoodCategoryInline(admin.StackedInline):
    model = models.FoodCategory
    extra = 0


class MenuItemInline(admin.TabularInline):
    model = models.MenuItem
    form = MenuItemAdminForm
    extra = 0
    raw_id_fields = ("category",)
    readonly_fields = ("photo_thumb",)

    @admin.display(description="Photo")
    def photo_thumb(self, obj):
        return admin_image_preview(obj, "photo", 40)


@admin.register(models.Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    form = RestaurantAdminForm
    list_display = ("name", "owner", "is_approved", "is_open", "avg_rating", "created_at", "logo_thumb")
    list_filter = ("is_approved", "is_open", "is_cloud_kitchen", "created_at")
    search_fields = ("name", "phone", "owner__phone", "address")
    raw_id_fields = ("owner",)
    readonly_fields = ("logo_preview", "cover_preview")
    inlines = (FoodCategoryInline, MenuItemInline)
    actions = (export_ids_csv,)

    @admin.display(description="Logo")
    def logo_thumb(self, obj):
        return admin_image_preview(obj, "logo", 32)

    @admin.display(description="Logo preview")
    def logo_preview(self, obj):
        return admin_image_preview(obj, "logo", 120)

    @admin.display(description="Cover preview")
    def cover_preview(self, obj):
        return admin_image_preview(obj, "cover_photo", 120)


class ParcelItemInline(admin.TabularInline):
    model = models.ParcelItem
    extra = 0


class ParcelBargainOfferInline(admin.TabularInline):
    model = models.ParcelBargainOffer
    extra = 0
    raw_id_fields = ("delivery_person",)


@admin.register(models.ParcelBooking)
class ParcelBookingAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "status", "estimated_fare", "source", "created_at")
    list_filter = ("status", "source", "is_multiple", "payment_method", "created_at")
    search_fields = ("sender__phone", "sender_name", "receiver_name", "id")
    raw_id_fields = ("sender", "delivery_person", "payment_intent")
    date_hierarchy = "created_at"
    readonly_fields = ("parcel_photo_preview",)
    inlines = (ParcelItemInline, ParcelBargainOfferInline)
    actions = (export_ids_csv,)

    @admin.display(description="Parcel photo")
    def parcel_photo_preview(self, obj):
        return admin_image_preview(obj, "parcel_photo", 160)


class WeatherSurgeTriggerInline(admin.StackedInline):
    model = models.WeatherSurgeTrigger
    extra = 0


class GeoZoneSurgeTriggerInline(admin.StackedInline):
    model = models.GeoZoneSurgeTrigger
    extra = 0
    raw_id_fields = ("created_by",)


class FestivalSurgeTriggerInline(admin.StackedInline):
    model = models.FestivalSurgeTrigger
    extra = 0


class DemandSurgeTriggerInline(admin.StackedInline):
    model = models.DemandSurgeTrigger
    extra = 0


class BatteryBehaviorSurgeTriggerInline(admin.StackedInline):
    model = models.BatteryBehaviorSurgeTrigger
    extra = 0


@admin.register(models.SurgePricingRule)
class SurgePricingRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "trigger_type", "multiplier", "priority", "is_active", "created_at")
    list_filter = ("trigger_type", "is_active", "stackable", "created_at")
    search_fields = ("name",)
    raw_id_fields = ("created_by",)
    filter_horizontal = ("applicable_vehicle_types",)
    inlines = (
        WeatherSurgeTriggerInline,
        GeoZoneSurgeTriggerInline,
        FestivalSurgeTriggerInline,
        DemandSurgeTriggerInline,
        BatteryBehaviorSurgeTriggerInline,
    )
    actions = (activate_records, deactivate_records, export_ids_csv)


@admin.register(models.VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    form = VehicleTypeAdminForm
    list_display = ("name", "vehicle_tier", "is_active", "sort_order", "icon_thumb")
    list_filter = ("vehicle_tier", "is_active")
    search_fields = ("name",)
    readonly_fields = ("icon_preview",)
    actions = (activate_records, deactivate_records, export_ids_csv)

    @admin.display(description="Icon")
    def icon_thumb(self, obj):
        return admin_image_preview(obj, "icon", 28)

    @admin.display(description="Icon preview")
    def icon_preview(self, obj):
        return admin_image_preview(obj, "icon", 100)


@admin.register(models.ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    form = ProductImageAdminForm
    list_display = ("product", "is_primary", "order", "image_thumb")
    list_filter = ("is_primary",)
    search_fields = ("product__name",)
    raw_id_fields = ("product",)
    readonly_fields = ("image_preview",)

    @admin.display(description="Image")
    def image_thumb(self, obj):
        return admin_image_preview(obj, "image", 36)

    @admin.display(description="Preview")
    def image_preview(self, obj):
        return admin_image_preview(obj, "image", 160)


@admin.register(models.PopupAd)
class PopupAdAdmin(admin.ModelAdmin):
    form = PopupAdAdminForm
    list_display = ("title", "target_role", "is_active", "valid_from", "valid_until", "image_thumb")
    list_filter = ("is_active", "target_role", "display_frequency", "show_on_open")
    search_fields = ("title",)
    raw_id_fields = ("created_by",)
    readonly_fields = ("image_preview",)
    actions = (activate_records, deactivate_records, export_ids_csv)

    @admin.display(description="Image")
    def image_thumb(self, obj):
        return admin_image_preview(obj, "image", 32)

    @admin.display(description="Image preview")
    def image_preview(self, obj):
        return admin_image_preview(obj, "image", 160)


class SupportMessageInline(admin.StackedInline):
    model = models.SupportMessage
    extra = 0
    raw_id_fields = ("sender",)


@admin.register(models.SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("subject", "user", "category", "status", "priority", "created_at")
    list_filter = ("status", "priority", "category", "created_at")
    search_fields = ("subject", "user__phone", "user__full_name", "description")
    raw_id_fields = ("user", "assigned_to")
    date_hierarchy = "created_at"
    inlines = (SupportMessageInline,)
    actions = (export_ids_csv,)


class RoomMediaInline(admin.TabularInline):
    model = models.RoomMedia
    extra = 0


@admin.register(models.RoomListing)
class RoomListingAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "city", "monthly_rent", "is_available", "is_approved", "created_at")
    list_filter = ("is_available", "is_approved", "room_type", "allowed_gender", "created_at")
    search_fields = ("title", "city", "area", "full_address")
    raw_id_fields = ("owner",)
    inlines = (RoomMediaInline,)
    actions = (activate_records, deactivate_records, export_ids_csv)


class DefaultCoreAdmin(admin.ModelAdmin):
    list_display = ("id",)
    search_fields = ("id",)
    list_per_page = 40
    show_full_result_count = False


_BULK_REGISTER = (
    models.ProductCategory,
    models.LoyaltyTier,
    models.QuickReplyTemplate,
    models.NotificationTemplate,
    models.RiderAchievement,
    models.PaymentTransaction,
    models.Wallet,
    models.WalletTransaction,
    models.CoinRate,
    models.Notification,
    models.AdminPushLog,
    models.BirthdayPromo,
    models.CallLog,
    models.SavedLocation,
    models.RiderLeaderboard,
    models.RideChat,
    models.RideChatMessage,
    models.RideRating,
    models.GroupRideBooking,
    models.GroupRideMember,
    models.TourBooking,
    models.RecurringRideTemplate,
    models.RecurringRideAdvancePayment,
    models.RecurringRideInstance,
    models.TripSafetyShare,
    models.CustomerSafetySettings,
    models.UserTripPattern,
    models.TripSuggestionLog,
    models.UserLoyaltyProfile,
    models.LoyaltyPointTransaction,
    models.UserStreak,
    models.FavouriteRider,
    models.RiderCustomerNote,
    models.CustomerPreferenceProfile,
    models.GeoZoneSurgeTrigger,
    models.AdminFareOverride,
    models.FareCalculationConfig,
    models.FareEstimateLog,
    models.RiderDispatchConfig,
    models.RiderDispatchEvent,
    models.RiderTripTarget,
    models.RiderTargetProgress,
    models.DemandForecast,
    models.RiderNudge,
    models.ParcelDeliveryProfile,
    models.FoodOrderItem,
    models.FoodRating,
    models.Vendor,
    models.Product,
    models.EcommerceOrderItem,
    models.ProductReview,
    models.RoomOwnerProfile,
    models.RoomInquiry,
    models.RoomBookingRequest,
    models.QRPaymentSession,
    models.WalletTopupRequest,
    models.RiderPayoutRequest,
    models.PromoUsage,
    models.ReferralReward,
    models.CancellationPolicy,
    models.PopupAdView,
    models.ServiceChargeConfig,
    models.AppVersionControl,
    models.MobileAppReleaseConfig,
    models.AdminActivityLog,
    models.FoodCategory,
)

for _model in _BULK_REGISTER:
    admin.site.register(_model, DefaultCoreAdmin)

@admin.register(models.PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "module", "status", "initiated_at")
    list_filter = ("status", "module", "payment_method", "initiated_at")
    search_fields = ("user__phone", "reference_model", "id")
    raw_id_fields = ("user",)
    date_hierarchy = "initiated_at"
    actions = (export_ids_csv,)


@admin.register(models.FoodOrder)
class FoodOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "restaurant", "status", "total_amount", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("customer__phone", "id")
    raw_id_fields = ("customer", "restaurant", "parcel_booking", "payment_intent")
    actions = (export_ids_csv,)


@admin.register(models.EcommerceOrder)
class EcommerceOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "vendor", "status", "total_amount", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("customer__phone", "id")
    raw_id_fields = ("customer", "vendor", "parcel_booking", "payment_intent")
    actions = (export_ids_csv,)


@admin.register(models.PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "promo_type", "discount_value", "applicable_on", "is_active", "valid_until")
    list_filter = ("promo_type", "applicable_on", "is_active", "is_birthday_promo")
    search_fields = ("code",)
    raw_id_fields = ("created_by",)
    actions = (activate_records, deactivate_records, export_ids_csv)


@admin.register(models.AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value_type", "editable_by", "updated_at")
    list_filter = ("value_type", "editable_by")
    search_fields = ("key", "description")
    raw_id_fields = ("updated_by",)


@admin.register(models.MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    form = MenuItemAdminForm
    list_display = ("name", "restaurant", "category", "price", "is_available", "photo_thumb")
    list_filter = ("is_available", "is_veg", "restaurant")
    search_fields = ("name", "restaurant__name")
    raw_id_fields = ("restaurant", "category")
    readonly_fields = ("photo_preview",)

    @admin.display(description="Photo")
    def photo_thumb(self, obj):
        return admin_image_preview(obj, "photo", 36)

    @admin.display(description="Photo preview")
    def photo_preview(self, obj):
        return admin_image_preview(obj, "photo", 140)
