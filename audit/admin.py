"""
Django admin configuration for audit app.
"""

from django.contrib import admin
from .models import AuditLog, SecurityEvent, DataExport, DataDeletion

# Simple admin registration for now
admin.site.register(AuditLog)
admin.site.register(SecurityEvent)
admin.site.register(DataExport)
admin.site.register(DataDeletion)