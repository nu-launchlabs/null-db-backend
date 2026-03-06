"""
Cycle URL configuration.

All routes are relative to /api/v1/cycles/ (set in config/urls.py).
"""

from django.urls import path

from apps.cycles import views

app_name = "cycles"

urlpatterns = [
    # POST /api/v1/cycles/              → Create new cycle (Admin)
    path("", views.CreateCycleView.as_view(), name="create"),

    # GET  /api/v1/cycles/list/         → List all cycles (Admin/Ops)
    path("list/", views.CycleListView.as_view(), name="list"),

    # GET  /api/v1/cycles/current/      → Get active cycle (Authenticated)
    path("current/", views.CurrentCycleView.as_view(), name="current"),

    # PATCH /api/v1/cycles/{id}/toggles/ → Update toggles (Admin)
    path(
        "<int:cycle_id>/toggles/",
        views.UpdateCycleTogglesView.as_view(),
        name="update-toggles",
    ),

    # POST /api/v1/cycles/{id}/close/   → Close cycle (Admin)
    path(
        "<int:cycle_id>/close/",
        views.CloseCycleView.as_view(),
        name="close",
    ),

    # GET /api/v1/cycles/{id}/stats/    → Cycle stats (Admin/Ops)
    path(
        "<int:cycle_id>/stats/",
        views.CycleStatsView.as_view(),
        name="stats",
    ),
]