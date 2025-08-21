"""
Django admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Organization, Role, Membership, Invitation, APIKey

# Simple admin registration - we'll enhance these later
# admin.site.register(Organization)
# admin.site.register(Role)
# admin.site.register(Membership)
# admin.site.register(Invitation)
# admin.site.register(APIKey)

# Temporarily commenting out detailed admin configs to fix startup issues


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    
    list_display = (
        'email', 'first_name', 'last_name', 'is_active', 'is_staff', 
        'email_verified', 'last_login', 'date_joined'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'email_verified',
        'date_joined', 'last_login'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('id', 'date_joined', 'last_login', 'last_activity')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'phone', 'avatar', 'timezone')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
        }),
        (_('Email Verification'), {
            'fields': ('email_verified', 'email_verification_token'),
        }),
        (_('Terms & Privacy'), {
            'fields': ('terms_accepted_at', 'privacy_accepted_at'),
        }),
        (_('Activity'), {
            'fields': ('last_login', 'last_login_ip', 'last_activity', 'date_joined'),
        }),
        (_('Preferences'), {
            'fields': ('notification_preferences', 'ui_preferences'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for Organization model."""
    
    list_display = (
        'name', 'slug', 'email', 'phone', 'city', 'country',
        'is_active', 'member_count', 'created_at'
    )
    list_filter = ('is_active', 'country', 'business_type', 'created_at')
    search_fields = ('name', 'slug', 'email', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'member_count', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'description', 'website', 'logo')
        }),
        (_('Contact Information'), {
            'fields': ('email', 'phone')
        }),
        (_('Address'), {
            'fields': (
                'address_line1', 'address_line2', 'city', 
                'state', 'postal_code', 'country'
            )
        }),
        (_('Settings'), {
            'fields': ('timezone', 'currency', 'is_active')
        }),
        (_('Business Details'), {
            'fields': ('tax_id', 'business_type')
        }),
        (_('Configuration'), {
            'fields': ('features_enabled', 'usage_limits'),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""
    
    list_display = ('name', 'description', 'is_system_role', 'created_at')
    list_filter = ('is_system_role', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'is_system_role')
        }),
        (_('Permissions'), {
            'fields': ('permissions',),
            'description': 'JSON list of permission codes'
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


class MembershipInline(admin.TabularInline):
    """Inline admin for Membership model."""
    model = Membership
    extra = 0
    readonly_fields = ('id', 'invitation_accepted_at', 'created_at')
    fields = (
        'user', 'role', 'is_active', 'is_primary', 
        'invited_by', 'invitation_accepted_at'
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model."""
    
    list_display = (
        'user', 'organization', 'role', 'is_active', 
        'is_primary', 'invited_by', 'created_at'
    )
    list_filter = ('is_active', 'is_primary', 'role', 'created_at')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'organization__name'
    )
    readonly_fields = ('id', 'invitation_accepted_at', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Membership'), {
            'fields': ('user', 'organization', 'role')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_primary')
        }),
        (_('Invitation'), {
            'fields': ('invited_by', 'invitation_accepted_at')
        }),
        (_('Permissions Override'), {
            'fields': ('permissions_override',),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Admin interface for Invitation model."""
    
    list_display = (
        'email', 'organization', 'role', 'status', 
        'invited_by', 'expires_at', 'created_at'
    )
    list_filter = ('status', 'expires_at', 'created_at')
    search_fields = (
        'email', 'first_name', 'last_name', 
        'organization__name', 'invited_by__email'
    )
    readonly_fields = (
        'id', 'token', 'accepted_at', 'accepted_by', 
        'is_expired', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        (_('Invitation Details'), {
            'fields': ('organization', 'role', 'invited_by')
        }),
        (_('Invitee Information'), {
            'fields': ('email', 'first_name', 'last_name')
        }),
        (_('Status & Timing'), {
            'fields': ('status', 'expires_at', 'is_expired')
        }),
        (_('Response'), {
            'fields': ('accepted_at', 'accepted_by')
        }),
        (_('Message'), {
            'fields': ('message',)
        }),
        (_('System'), {
            'fields': ('token',),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin interface for APIKey model."""
    
    list_display = (
        'name', 'user', 'organization', 'prefix', 
        'is_active', 'last_used_at', 'usage_count', 'expires_at'
    )
    list_filter = ('is_active', 'expires_at', 'created_at', 'last_used_at')
    search_fields = (
        'name', 'prefix', 'user__email', 'organization__name'
    )
    readonly_fields = (
        'id', 'key_hash', 'prefix', 'last_used_at', 
        'usage_count', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        (_('API Key Details'), {
            'fields': ('name', 'user', 'organization')
        }),
        (_('Security'), {
            'fields': ('key_hash', 'prefix', 'is_active', 'expires_at')
        }),
        (_('Permissions'), {
            'fields': ('permissions',),
            'description': 'JSON list of permission codes'
        }),
        (_('Usage Tracking'), {
            'fields': ('last_used_at', 'usage_count')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


# Add inline to Organization admin
OrganizationAdmin.inlines = [MembershipInline]

