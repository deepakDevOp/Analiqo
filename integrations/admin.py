"""
Django admin configuration for integrations app.
"""

from django.contrib import admin
from .models import SyncJob, MarketplaceData, WebhookEvent, Integration

# Simple admin registration for now
admin.site.register(SyncJob)
admin.site.register(MarketplaceData)
admin.site.register(WebhookEvent)
admin.site.register(Integration)