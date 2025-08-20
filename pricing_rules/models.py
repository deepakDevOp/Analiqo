"""
Pricing rules models for rule-based repricing strategies.
"""

from django.db import modelsfrom django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import BaseModel
import json


class PricingStrategy(BaseModel):
    """Base pricing strategy configuration."""
    
    STRATEGY_TYPE_CHOICES = [
        ('rule_based', _('Rule-Based')),
        ('ml_based', _('ML-Based')),
        ('hybrid', _('Hybrid')),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPE_CHOICES, default='rule_based')
    
    # Configuration
    config = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Assignments
    products = models.ManyToManyField('catalog.Product', through='StrategyAssignment', blank=True)
    
    class Meta:
        verbose_name = _('Pricing Strategy')
        verbose_name_plural = _('Pricing Strategies')
        unique_together = ['organization', 'name']
    
    def __str__(self):
        return self.name


class RuleSet(BaseModel):
    """Collection of pricing rules."""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    strategy = models.ForeignKey(PricingStrategy, on_delete=models.CASCADE, related_name='rule_sets')
    
    # Priority and conditions
    priority = models.PositiveIntegerField(default=100)
    conditions = models.JSONField(default=dict)  # When to apply this rule set
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Rule Set')
        verbose_name_plural = _('Rule Sets')
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.strategy.name} - {self.name}"


class PricingRule(BaseModel):
    """Individual pricing rule."""
    
    RULE_TYPE_CHOICES = [
        ('undercut_amount', _('Undercut by Amount')),
        ('undercut_percentage', _('Undercut by Percentage')),
        ('match_buybox', _('Match Buy Box')),
        ('fixed_margin', _('Fixed Margin')),
        ('dynamic_margin', _('Dynamic Margin')),
        ('competitor_based', _('Competitor-Based')),
        ('inventory_based', _('Inventory-Based')),
    ]
    
    ACTION_CHOICES = [
        ('increase', _('Increase Price')),
        ('decrease', _('Decrease Price')),
        ('set_price', _('Set Price')),
        ('no_change', _('No Change')),
    ]
    
    rule_set = models.ForeignKey(RuleSet, on_delete=models.CASCADE, related_name='rules')
    
    # Rule definition
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Rule parameters
    parameters = models.JSONField(default=dict)
    
    # Action to take
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Constraints
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Priority within rule set
    priority = models.PositiveIntegerField(default=100)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Pricing Rule')
        verbose_name_plural = _('Pricing Rules')
        ordering = ['rule_set', 'priority', 'name']
    
    def __str__(self):
        return f"{self.rule_set.name} - {self.name}"


class StrategyAssignment(BaseModel):
    """Assignment of strategies to products."""
    
    strategy = models.ForeignKey(PricingStrategy, on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    
    # Assignment configuration
    config_override = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Schedule
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Strategy Assignment')
        verbose_name_plural = _('Strategy Assignments')
        unique_together = ['organization', 'strategy', 'product']
    
    def __str__(self):
        return f"{self.product.sku} -> {self.strategy.name}"


class ConditionalStrategy(BaseModel):
    """Conditional strategy switching based on context."""
    
    CONDITION_TYPE_CHOICES = [
        ('inventory_level', _('Inventory Level')),
        ('sales_velocity', _('Sales Velocity')),
        ('time_of_day', _('Time of Day')),
        ('day_of_week', _('Day of Week')),
        ('competitor_count', _('Competitor Count')),
        ('buy_box_status', _('Buy Box Status')),
        ('margin_level', _('Margin Level')),
        ('ad_spend_acos', _('Ad Spend ACOS')),
    ]
    
    OPERATOR_CHOICES = [
        ('eq', _('Equals')),
        ('ne', _('Not Equals')),
        ('gt', _('Greater Than')),
        ('gte', _('Greater Than or Equal')),
        ('lt', _('Less Than')),
        ('lte', _('Less Than or Equal')),
        ('in', _('In')),
        ('not_in', _('Not In')),
        ('between', _('Between')),
    ]
    
    strategy = models.ForeignKey(PricingStrategy, on_delete=models.CASCADE, related_name='conditional_strategies')
    
    # Condition
    condition_type = models.CharField(max_length=30, choices=CONDITION_TYPE_CHOICES)
    operator = models.CharField(max_length=10, choices=OPERATOR_CHOICES)
    condition_value = models.JSONField()  # Value(s) to compare against
    
    # Target strategy to switch to
    target_strategy = models.ForeignKey(
        PricingStrategy, 
        on_delete=models.CASCADE, 
        related_name='triggered_by_conditions'
    )
    
    # Priority
    priority = models.PositiveIntegerField(default=100)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Conditional Strategy')
        verbose_name_plural = _('Conditional Strategies')
        ordering = ['strategy', 'priority']
    
    def __str__(self):
        return f"{self.strategy.name} -> {self.target_strategy.name} when {self.get_condition_type_display()}"


class SafetyConstraint(BaseModel):
    """Safety constraints to prevent dangerous pricing."""
    
    CONSTRAINT_TYPE_CHOICES = [
        ('min_price_absolute', _('Minimum Price (Absolute)')),
        ('min_price_cost_plus', _('Minimum Price (Cost Plus)')),
        ('max_price_absolute', _('Maximum Price (Absolute)')),
        ('max_price_multiplier', _('Maximum Price (Multiplier)')),
        ('max_price_change_percentage', _('Max Price Change %')),
        ('min_margin_percentage', _('Minimum Margin %')),
        ('competitor_blacklist', _('Competitor Blacklist')),
        ('fulfillment_filter', _('Fulfillment Filter')),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    constraint_type = models.CharField(max_length=30, choices=CONSTRAINT_TYPE_CHOICES)
    
    # Constraint value
    constraint_value = models.JSONField()
    
    # Scope
    applies_to_all_products = models.BooleanField(default=True)
    products = models.ManyToManyField('catalog.Product', blank=True)
    categories = models.ManyToManyField('catalog.Category', blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Violation handling
    violation_action = models.CharField(
        max_length=20,
        choices=[
            ('block', _('Block Price Change')),
            ('adjust', _('Adjust to Constraint')),
            ('warn', _('Warn Only')),
        ],
        default='block'
    )
    
    class Meta:
        verbose_name = _('Safety Constraint')
        verbose_name_plural = _('Safety Constraints')
        unique_together = ['organization', 'name']
    
    def __str__(self):
        return self.name

