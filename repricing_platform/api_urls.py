"""
API URL configuration for internal endpoints.
"""

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

app_name = "api"

urlpatterns = [
    # API Documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
    
    # App API endpoints
    path("accounts/", include("accounts.api_urls")),
    path("billing/", include("billing.api_urls")),
    path("catalog/", include("catalog.api_urls")),
    path("pricing/", include("pricing_rules.api_urls")),
    path("ml/", include("pricing_ml.api_urls")),
    path("repricing/", include("repricer.api_urls")),
    path("analytics/", include("analytics.api_urls")),
    path("integrations/", include("integrations.api_urls")),
]
