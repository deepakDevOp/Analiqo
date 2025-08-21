"""
URL configuration for web app (SSR views).
"""

from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    # Landing and authentication
    path('', views.LandingView.as_view(), name='landing'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Dashboard components (for Unpoly updates)
    path('dashboard/metrics/', views.DashboardMetricsView.as_view(), name='dashboard_metrics'),
    path('dashboard/alerts/', views.DashboardAlertsView.as_view(), name='dashboard_alerts'),
    path('dashboard/recent-activity/', views.RecentActivityView.as_view(), name='recent_activity'),
]
