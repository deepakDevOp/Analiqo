"""
Django admin configuration for credentials app.
"""

from django.contrib import admin
from .models import MarketplaceCredential

# Simple admin registration for now
admin.site.register(MarketplaceCredential)