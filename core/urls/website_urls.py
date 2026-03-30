from django.urls import path

from core.views.website.home_views import website_home_summary

urlpatterns = [
    path("home/", website_home_summary, name="website-home-summary"),
]
