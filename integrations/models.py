"""
Integration models for marketplace API connections and data synchronization.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, TimeStampedModel
import json


class Integration(BaseModel):
    """Base integration configuration."""
    
    INTEGRATION_TYPE_CHOICES = [
        ('amazon_sp_api', _('Amazon SP-API')),
        ('flipkart_marketplace', _('Flipkart Marketplace')),
        ('stripe_billing', _('Stripe Billing')),
        ('email_provider', _('Email Provider')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('error', _('Error')),
        ('configuring', _('Configuring')),
    ]
    
    integration_type = models.CharField(max_length=30, choices=INTEGRATION_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='configuring')
    
    # Configuration
    config = models.JSONField(default=dict)
    
    # Credentials reference
    credential = models.ForeignKey(
        'credentials.MarketplaceCredential',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Rate limiting
    rate_limit_per_second = models.PositiveIntegerField(default=10)
    
    # Last sync info
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=20, blank=True)
    last_error = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('Integration')
        verbose_name_plural = _('Integrations')
        unique_together = ['organization', 'integration_type', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.get_integration_type_display()}"


class SyncJob(BaseModel):
    """Synchronization job tracking."""
    
    JOB_TYPE_CHOICES = [
        ('full_sync', _('Full Synchronization')),
        ('incremental_sync', _('Incremental Sync')),
        ('product_sync', _('Product Sync')),
        ('price_sync', _('Price Sync')),
        ('inventory_sync', _('Inventory Sync')),
        ('order_sync', _('Order Sync')),
        ('competitor_sync', _('Competitor Sync')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='sync_jobs')
    
    # Job details
    job_type = models.CharField(max_length=30, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    records_processed = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    # Configuration
    job_config = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Sync Job')
        verbose_name_plural = _('Sync Jobs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['integration', 'status']),
            models.Index(fields=['job_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.integration.name} - {self.get_job_type_display()}"


class APICallLog(TimeStampedModel):
    """Log of API calls for monitoring and debugging."""
    
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='api_calls')
    
    # Request details
    method = models.CharField(max_length=10)
    url = models.URLField()
    headers = models.JSONField(default=dict, blank=True)
    request_body = models.TextField(blank=True)
    
    # Response details
    status_code = models.PositiveIntegerField()
    response_body = models.TextField(blank=True)
    response_headers = models.JSONField(default=dict, blank=True)
    
    # Timing
    request_time = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.PositiveIntegerField()
    
    # Context
    sync_job = models.ForeignKey(SyncJob, on_delete=models.SET_NULL, null=True, blank=True)
    operation = models.CharField(max_length=100, blank=True)
    
    # Error tracking
    is_error = models.BooleanField(default=False)
    error_type = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('API Call Log')
        verbose_name_plural = _('API Call Logs')
        ordering = ['-request_time']
        indexes = [
            models.Index(fields=['integration', 'request_time']),
            models.Index(fields=['is_error', 'request_time']),
            models.Index(fields=['status_code']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.url} - {self.status_code}"


class MarketplaceData(BaseModel):
    """Raw marketplace data cache."""
    
    DATA_TYPE_CHOICES = [
        ('product', _('Product Data')),
        ('price', _('Price Data')),
        ('inventory', _('Inventory Data')),
        ('order', _('Order Data')),
        ('competitor', _('Competitor Data')),
        ('category', _('Category Data')),
        ('fee', _('Fee Data')),
    ]
    
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='marketplace_data')
    
    # Data identification
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES)
    external_id = models.CharField(max_length=200)  # ID from marketplace
    
    # Data content
    raw_data = models.JSONField()
    processed_data = models.JSONField(default=dict, blank=True)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_errors = models.JSONField(default=list, blank=True)
    
    # Timestamps
    data_timestamp = models.DateTimeField()  # When the data was generated at source
    fetched_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('Marketplace Data')
        verbose_name_plural = _('Marketplace Data')
        unique_together = ['integration', 'data_type', 'external_id']
        indexes = [
            models.Index(fields=['integration', 'data_type']),
            models.Index(fields=['external_id']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['data_timestamp']),
        ]
    
    def __str__(self):
        return f"{self.integration.name} - {self.get_data_type_display()} - {self.external_id}"


class RateLimitTracker(models.Model):
    """Track API rate limits to prevent violations."""
    
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='rate_limits')
    
    # Rate limit window
    window_start = models.DateTimeField()
    window_duration_seconds = models.PositiveIntegerField()
    
    # Limit tracking
    limit_per_window = models.PositiveIntegerField()
    calls_made = models.PositiveIntegerField(default=0)
    
    # Status
    is_exceeded = models.BooleanField(default=False)
    reset_at = models.DateTimeField()
    
    class Meta:
        verbose_name = _('Rate Limit Tracker')
        verbose_name_plural = _('Rate Limit Trackers')
        unique_together = ['integration', 'window_start']
        indexes = [
            models.Index(fields=['integration', 'reset_at']),
            models.Index(fields=['is_exceeded']),
        ]
    
    def __str__(self):
        return f"{self.integration.name} - {self.calls_made}/{self.limit_per_window}"


class WebhookEndpoint(BaseModel):
    """Webhook endpoints for receiving marketplace events."""
    
    EVENT_TYPE_CHOICES = [
        ('order_created', _('Order Created')),
        ('order_updated', _('Order Updated')),
        ('inventory_changed', _('Inventory Changed')),
        ('price_changed', _('Price Changed')),
        ('listing_updated', _('Listing Updated')),
        ('fee_updated', _('Fee Updated')),
    ]
    
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='webhooks')
    
    # Webhook configuration
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    endpoint_url = models.URLField()
    secret_key = models.CharField(max_length=100)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Statistics
    events_received = models.PositiveIntegerField(default=0)
    last_event_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Webhook Endpoint')
        verbose_name_plural = _('Webhook Endpoints')
        unique_together = ['integration', 'event_type']
    
    def __str__(self):
        return f"{self.integration.name} - {self.get_event_type_display()}"


class WebhookEvent(TimeStampedModel):
    """Received webhook events."""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('processed', _('Processed')),
        ('failed', _('Failed')),
        ('ignored', _('Ignored')),
    ]
    
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='events')
    
    # Event data
    event_id = models.CharField(max_length=200)  # External event ID
    event_data = models.JSONField()
    headers = models.JSONField(default=dict, blank=True)
    
    # Processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    
    # Verification
    signature_valid = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Webhook Event')
        verbose_name_plural = _('Webhook Events')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['webhook', 'status']),
            models.Index(fields=['event_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.webhook.integration.name} - {self.event_id}"
