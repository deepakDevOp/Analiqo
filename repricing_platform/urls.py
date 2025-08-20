"""
URL configuration for repricing_platform project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path(f"{settings.ADMIN_URL if hasattr(settings, 'ADMIN_URL') else 'admin/'}", admin.site.urls),
    
    # Authentication (django-allauth)
    path("accounts/", include("allauth.urls")),
    
    # Core application URLs
    path("", include("web.urls")),
    path("api/", include("repricing_platform.api_urls")),
    
    # App-specific URLs
    path("accounts/", include("accounts.urls")),
    path("billing/", include("billing.urls")),
    path("credentials/", include("credentials.urls")),
    path("catalog/", include("catalog.urls")),
    path("pricing/", include("pricing_rules.urls")),
    path("ml/", include("pricing_ml.urls")),
    path("repricing/", include("repricer.urls")),
    path("analytics/", include("analytics.urls")),
    path("notifications/", include("notifications.urls")),
    path("admin-panel/", include("adminpanel.urls")),
    
    # Health checks
    path("health/", include("core.health_urls")),
    
    # Monitoring
    path("metrics/", include("django_prometheus.urls")),
    
    # API Documentation
    path("api/schema/", include("drf_spectacular.urls")),
    
    # Static pages
    path("privacy/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    path("terms/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("support/", TemplateView.as_view(template_name="pages/support.html"), name="support"),
]

# Add debug toolbar URLs in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Error handlers
handler404 = "web.views.errors.handler404"
handler500 = "web.views.errors.handler500"
handler403 = "web.views.errors.handler403"
