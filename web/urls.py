"""
URL configuration for web app (SSR views).
"""

from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    # Landing only
    path('', views.LandingView.as_view(), name='landing'),
    path('home/', views.HomeView.as_view(), name='home'),
]
