"""
Audit logging models for compliance and security tracking.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
import uuid

User = get_user_model()


class AuditLog(models.Model):
    """Central audit log for all system activities."""
    
    ACTION_CHOICES = [
        ('create', _('Create')),
        ('read', _('Read')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('export', _('Export')),
        ('import', _('Import')),
        ('approve', _('Approve')),
        ('reject', _('Reject')),
        ('execute', _('Execute')),
    ]
    
    SEVERITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    # Basic audit info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # User and session info
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(
        'accounts.Organization', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    session_key = models.CharField(max_length=40, blank=True)
    
    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100)  # Model name or resource type
    resource_id = models.CharField(max_length=100, blank=True)  # Resource identifier
    
    # Generic foreign key for linking to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Request info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    
    # Change details
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    changes = models.JSONField(default=dict, blank=True)  # Diff of changes
    
    # Additional context
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Risk assessment
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low')
    risk_score = models.PositiveIntegerField(default=0)
    
    # Compliance flags
    is_gdpr_relevant = models.BooleanField(default=False)
    is_financial_data = models.BooleanField(default=False)
    is_security_event = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['organization', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'timestamp']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_security_event']),
            models.Index(fields=['is_gdpr_relevant']),
        ]
    
    def __str__(self):
        user_info = f"{self.user.email}" if self.user else "Anonymous"
        return f"{self.timestamp} - {user_info} - {self.action} {self.resource_type}"


class DataExport(models.Model):
    """Track data exports for GDPR compliance."""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('expired', _('Expired')),
    ]
    
    FORMAT_CHOICES = [
        ('json', _('JSON')),
        ('csv', _('CSV')),
        ('pdf', _('PDF')),
        ('xml', _('XML')),
    ]
    
    REQUEST_TYPE_CHOICES = [
        ('gdpr_export', _('GDPR Data Export')),
        ('analytics_export', _('Analytics Export')),
        ('report_export', _('Report Export')),
        ('backup_export', _('Backup Export')),
    ]
    
    # Request details
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='data_exports')
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE)
    
    # Export configuration
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPE_CHOICES)
    data_types = models.JSONField(default=list)  # List of data types to export
    date_from = models.DateTimeField(null=True, blank=True)
    date_to = models.DateTimeField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='json')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()  # Auto-delete after this date
    
    # Results
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    record_count = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Download tracking
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Data Export')
        verbose_name_plural = _('Data Exports')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requested_by', 'created_at']),
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_request_type_display()} by {self.requested_by.email}"


class DataDeletion(models.Model):
    """Track data deletion requests for GDPR compliance."""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('rejected', _('Rejected')),
    ]
    
    DELETION_TYPE_CHOICES = [
        ('gdpr_erasure', _('GDPR Right to Erasure')),
        ('account_closure', _('Account Closure')),
        ('data_retention', _('Data Retention Policy')),
        ('manual_request', _('Manual Request')),
    ]
    
    # Request details
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deletion_requests')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deletion_records')
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True)
    
    # Deletion configuration
    deletion_type = models.CharField(max_length=30, choices=DELETION_TYPE_CHOICES)
    data_types = models.JSONField(default=list)  # List of data types to delete
    reason = models.TextField()
    
    # Approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_deletions'
    )
    approval_notes = models.TextField(blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    records_deleted = models.PositiveIntegerField(null=True, blank=True)
    deletion_summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('Data Deletion')
        verbose_name_plural = _('Data Deletions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['deletion_type']),
        ]
    
    def __str__(self):
        return f"{self.get_deletion_type_display()} for {self.target_user.email}"


class SecurityEvent(models.Model):
    """Security-related events and alerts."""
    
    EVENT_TYPE_CHOICES = [
        ('login_failure', _('Login Failure')),
        ('suspicious_activity', _('Suspicious Activity')),
        ('permission_violation', _('Permission Violation')),
        ('data_breach', _('Data Breach')),
        ('unauthorized_access', _('Unauthorized Access')),
        ('rate_limit_exceeded', _('Rate Limit Exceeded')),
        ('api_abuse', _('API Abuse')),
        ('malicious_request', _('Malicious Request')),
    ]
    
    SEVERITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('open', _('Open')),
        ('investigating', _('Investigating')),
        ('resolved', _('Resolved')),
        ('false_positive', _('False Positive')),
    ]
    
    # Event details
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    
    # Associated entities
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(
        'accounts.Organization', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Event data
    title = models.CharField(max_length=200)
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    # Response
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_security_events'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Timing
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Security Event')
        verbose_name_plural = _('Security Events')
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['event_type', 'detected_at']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['user', 'detected_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.title}"
