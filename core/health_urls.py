"""
URL configuration for health checks.
"""

from django.urls import path
from . import health_views

app_name = 'health'

urlpatterns = [
    path('', health_views.health_check, name='health_check'),
    path('ready/', health_views.readiness_check, name='readiness_check'),
    path('live/', health_views.liveness_check, name='liveness_check'),
]