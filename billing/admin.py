"""
Django admin configuration for billing app.
"""

from django.contrib import admin
from .models import Plan, Subscription, Invoice, PaymentMethod, UsageRecord, BillingAlert

# Simple admin registration for now
admin.site.register(Plan)
admin.site.register(Subscription)
admin.site.register(Invoice)
admin.site.register(PaymentMethod)
admin.site.register(UsageRecord)
admin.site.register(BillingAlert)