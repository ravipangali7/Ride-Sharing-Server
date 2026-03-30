from django.urls import include, path

urlpatterns = [
    path("admin/", include("core.urls.admin_urls")),
    path("website/", include("core.urls.website_urls")),
    path("auth/", include("core.urls.auth_urls")),
]
