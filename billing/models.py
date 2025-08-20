"""
Billing models for subscription management and usage tracking.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import BaseModel, TimeStampedModel, UUIDModel


class Plan(UUIDModel, TimeStampedModel):
    """Subscription plans available to organizations."""
    
    PLAN_TYPE_CHOICES = [
        ('free', _('Free')),
        ('pro', _('Pro')),
        ('enterprise', _('Enterprise')),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    
    # Stripe integration
    stripe_price_id = models.CharField(max_length=100, blank=True)
    stripe_product_id = models.CharField(max_length=100, blank=True)
    
    # Features and limits
    features = models.JSONField(default=dict)
    limits = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)  # Visible to users
    
    # Trial settings
    trial_days = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = _('Plan')
        verbose_name_plural = _('Plans')
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"
    
    @property
    def monthly_price(self):
        """Calculate monthly equivalent price."""
        if self.billing_cycle == 'yearly':
            return self.price / 12
        return self.price


class Subscription(BaseModel):
    """Organization subscriptions."""
    
    STATUS_CHOICES = [
        ('trialing', _('Trialing')),
        ('active', _('Active')),
        ('past_due', _('Past Due')),
        ('canceled', _('Canceled')),
        ('unpaid', _('Unpaid')),
    ]
    
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    
    # Stripe integration
    stripe_subscription_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    
    # Subscription details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    trial_end = models.DateTimeField(null=True, blank=True)
    
    # Billing
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    usage_data = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
        indexes = [
            models.Index(fields=['stripe_subscription_id']),
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.plan.name}"
    
    @property
    def is_active(self):
        return self.status in ['trialing', 'active']
    
    @property
    def is_trial(self):
        from django.utils import timezone
        return (
            self.status == 'trialing' and 
            self.trial_end and 
            timezone.now() < self.trial_end
        )
    
    def get_usage_limit(self, feature):
        """Get usage limit for a specific feature."""
        return self.plan.limits.get(feature)
    
    def get_current_usage(self, feature):
        """Get current usage for a specific feature."""
        return self.usage_data.get(feature, 0)
    
    def is_feature_enabled(self, feature):
        """Check if a feature is enabled in the current plan."""
        return self.plan.features.get(feature, False)
    
    def has_usage_limit_exceeded(self, feature):
        """Check if usage limit is exceeded for a feature."""
        limit = self.get_usage_limit(feature)
        if limit is None:  # Unlimited
            return False
        return self.get_current_usage(feature) >= limit


class Invoice(BaseModel):
    """Invoice records from Stripe."""
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('open', _('Open')),
        ('paid', _('Paid')),
        ('uncollectible', _('Uncollectible')),
        ('void', _('Void')),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='invoices')
    
    # Stripe integration
    stripe_invoice_id = models.CharField(max_length=100, unique=True)
    
    # Invoice details
    number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Amounts
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_remaining = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    currency = models.CharField(max_length=3, default='USD')
    
    # Dates
    created_date = models.DateTimeField()
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # URLs
    hosted_invoice_url = models.URLField(blank=True)
    invoice_pdf_url = models.URLField(blank=True)
    
    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['stripe_invoice_id']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"Invoice {self.number} - {self.organization.name}"


class PaymentMethod(BaseModel):
    """Customer payment methods."""
    
    TYPE_CHOICES = [
        ('card', _('Credit Card')),
        ('bank_account', _('Bank Account')),
    ]
    
    # Stripe integration
    stripe_payment_method_id = models.CharField(max_length=100, unique=True)
    
    # Payment method details
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Card details (if type is card)
    card_brand = models.CharField(max_length=20, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.PositiveIntegerField(null=True, blank=True)
    card_exp_year = models.PositiveIntegerField(null=True, blank=True)
    
    # Bank account details (if type is bank_account)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_last4 = models.CharField(max_length=4, blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Payment Method')
        verbose_name_plural = _('Payment Methods')
        indexes = [
            models.Index(fields=['stripe_payment_method_id']),
        ]
    
    def __str__(self):
        if self.type == 'card':
            return f"{self.card_brand} ****{self.card_last4}"
        elif self.type == 'bank_account':
            return f"{self.bank_name} ****{self.bank_last4}"
        return f"{self.get_type_display()}"


class UsageRecord(TimeStampedModel):
    """Usage tracking for metered billing."""
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='usage_records')
    
    # Usage details
    feature = models.CharField(max_length=100)  # e.g., 'api_calls', 'repricing_runs'
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField()
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Stripe integration (for metered billing)
    stripe_usage_record_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('Usage Record')
        verbose_name_plural = _('Usage Records')
        indexes = [
            models.Index(fields=['subscription', 'feature', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.subscription.organization.name} - {self.feature}: {self.quantity}"


class BillingAlert(BaseModel):
    """Billing alerts for usage limits and payment issues."""
    
    ALERT_TYPE_CHOICES = [
        ('usage_limit', _('Usage Limit')),
        ('payment_failed', _('Payment Failed')),
        ('trial_ending', _('Trial Ending')),
        ('subscription_canceled', _('Subscription Canceled')),
    ]
    
    SEVERITY_CHOICES = [
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('critical', _('Critical')),
    ]
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Alert data
    data = models.JSONField(default=dict, blank=True)
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Billing Alert')
        verbose_name_plural = _('Billing Alerts')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.title}"
