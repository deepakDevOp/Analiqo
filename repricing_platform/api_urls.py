"""
API URL configuration for internal endpoints.
"""

from django.urls import path, include

app_name = "api"

urlpatterns = [
    path("accounts/", include("accounts.api_urls")),
]
