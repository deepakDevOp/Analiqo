"""
URL configuration for accounts app.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Profile management
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    
    # Organization management
    path('organization/', views.OrganizationView.as_view(), name='organization_settings'),
    path('organization/members/', views.OrganizationMembersView.as_view(), name='organization_members'),
    path('organization/invite/', views.InviteMemberView.as_view(), name='invite_member'),
    path('organization/switch/<uuid:org_id>/', views.SwitchOrganizationView.as_view(), name='switch_organization'),
    
    # Invitation handling
    path('invitations/', views.InvitationListView.as_view(), name='invitation_list'),
    path('invitations/<uuid:token>/accept/', views.AcceptInvitationView.as_view(), name='accept_invitation'),
    path('invitations/<uuid:token>/decline/', views.DeclineInvitationView.as_view(), name='decline_invitation'),
]
