"""
Health check URLs.
"""

from django.urls import path
from . import health_views

urlpatterns = [
    path("live/", health_views.liveness_check, name="liveness"),
    path("ready/", health_views.readiness_check, name="readiness"),
]
