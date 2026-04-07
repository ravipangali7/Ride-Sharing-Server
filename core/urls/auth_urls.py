from django.urls import path

from core.views.admin.auth_views import (
    admin_login,
    admin_token_refresh,
    customer_me,
    customer_register,
    customer_login,
    request_otp,
    verify_otp,
)

urlpatterns = [
    path("login/", admin_login, name="auth-admin-login"),
    path("register/", customer_register, name="auth-customer-register"),
    path("customer-login/", customer_login, name="auth-customer-login"),
    path("request-otp/", request_otp, name="auth-request-otp"),
    path("verify-otp/", verify_otp, name="auth-verify-otp"),
    path("me/", customer_me, name="auth-customer-me"),
    path("token/refresh/", admin_token_refresh, name="auth-token-refresh"),
]
