"""
URL configuration for web app (SSR views).
"""

from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    # Profile view
    path('profile/<uuid:pk>/', views.ProfileView.as_view(), name='profile_view'),
    path('profile/edit/', views.EditProfileView.as_view(), name='profile_edit'),
]
