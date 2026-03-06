"""
Audit URL configuration.

All routes are relative to /api/v1/audit/ (set in config/urls.py).
"""

from django.urls import path

from apps.audit import views

app_name = "audit"

urlpatterns = [
    # GET /api/v1/audit/logs/  List audit logs (Admin/Ops)
    path("logs/", views.AuditLogListView.as_view(), name="log-list"),
]