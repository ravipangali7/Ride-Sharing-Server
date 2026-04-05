from django.urls import path

from core.views.website.home_views import website_home_summary, website_mobile_app

urlpatterns = [
    path("home/", website_home_summary, name="website-home-summary"),
    path("mobile-app/", website_mobile_app, name="website-mobile-app"),
]
