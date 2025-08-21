"""
Django admin configuration for pricing_rules app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    PricingStrategy, RuleSet, PricingRule, SafetyConstraint,
    StrategyAssignment, ConditionalStrategy
)

# Simple admin registration for now
admin.site.register(PricingStrategy)
admin.site.register(RuleSet)
admin.site.register(PricingRule)
admin.site.register(SafetyConstraint)
admin.site.register(StrategyAssignment)
admin.site.register(ConditionalStrategy)

# Detailed admin configs can be added later