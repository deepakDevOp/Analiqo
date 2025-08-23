from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff',
        'email_verified', 'last_login', 'date_joined'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'email_verified',
        'date_joined', 'last_login'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('id', 'date_joined', 'last_login', 'last_activity')

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
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
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


