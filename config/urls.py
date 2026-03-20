"""
Root URL configuration for NU Launch Labs.

All API endpoints are versioned under /api/v1/.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# API v1 URL Patterns

api_v1_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("cycles/", include("apps.cycles.urls")),           # Phase 2
    path("audit/", include("apps.audit.urls")),             # Phase 2
    path("launch/", include("apps.launch.urls")),         # Phase 3
    # path("innovation/", include("apps.innovation.urls")), # Phase 4
]

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include(api_v1_patterns)),
    # API Documentation
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# Debug toolbar URLs (dev only)
if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Admin site customization
admin.site.site_header = "NU Launch Labs Administration"
admin.site.site_title = "NU Launch Labs Admin"
admin.site.index_title = "Dashboard"