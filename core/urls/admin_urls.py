from django.urls import path

from core.views.admin.dashboard_views import (
    admin_dashboard_overview,
    admin_dashboard_activity,
    admin_dashboard_revenue_series,
    admin_dashboard_top_performers,
)
from core.views.admin.user_views import (
    generic_list_view,
    generic_detail_view,
    generic_stats_view,
    user_adjust_coins_view,
)
from core.views.admin.map_views import admin_map_entities

urlpatterns = [
    path("dashboard/overview/", admin_dashboard_overview, name="admin-dashboard-overview"),
    path("dashboard/activity/", admin_dashboard_activity, name="admin-dashboard-activity"),
    path("dashboard/revenue/", admin_dashboard_revenue_series, name="admin-dashboard-revenue"),
    path("dashboard/top-performers/", admin_dashboard_top_performers, name="admin-dashboard-top-performers"),
    path("users/<uuid:pk>/adjust-coins/", user_adjust_coins_view, name="admin-user-adjust-coins"),
    path("map/entities/", admin_map_entities, name="admin-map-entities"),
    path("<str:resource>/stats/", generic_stats_view, name="admin-generic-stats"),
    path("<str:resource>/", generic_list_view, name="admin-generic-list"),
    path("<str:resource>/<uuid:pk>/", generic_detail_view, name="admin-generic-detail"),
]
