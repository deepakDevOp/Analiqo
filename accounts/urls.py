"""
URL configuration for accounts app.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Organization management
    path('organizations/create/', views.OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/switch/', views.OrganizationSwitchView.as_view(), name='organization_switch'),
    path('organizations/settings/', views.organization_settings_view, name='organization_settings'),
    
    # User profile
    path('profile/', views.profile_view, name='profile'),
    
    # Invitations
    path('invitations/', views.InvitationListView.as_view(), name='invitation_list'),
    path('invitations/create/', views.InvitationCreateView.as_view(), name='invitation_create'),
    path('invitations/<str:token>/', views.InvitationAcceptView.as_view(), name='invitation_accept'),
]
