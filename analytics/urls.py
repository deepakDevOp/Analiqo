"""
URL configuration for analytics app.
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Dashboard
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.AnalyticsDashboardView.as_view(), name='dashboard_alt'),
    
    # API endpoints for charts
    path('api/', views.AnalyticsAPIView.as_view(), name='api'),
    
    # Reports
    path('reports/', views.ReportsView.as_view(), name='reports'),
]
