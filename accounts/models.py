"""
User and organization models for multi-tenant SaaS.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField
from core.models import TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with email as username."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    timezone = TimeZoneField(default='UTC')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    
    # Terms and privacy acceptance
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Last activity tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    notification_preferences = models.JSONField(default=dict, blank=True)
    ui_preferences = models.JSONField(default=dict, blank=True)
    
    username = None  # Remove username field
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_primary_organization(self):
        """Get the user's primary organization."""
        membership = self.memberships.filter(is_primary=True).first()
        return membership.organization if membership else None


class Organization(UUIDModel, TimeStampedModel):
    """Organization model for multi-tenancy."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='organization_logos/', blank=True, null=True)
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, blank=True)  # ISO country code
    
    # Settings
    timezone = TimeZoneField(default='UTC')
    currency = models.CharField(max_length=3, default='USD')  # ISO currency code
    
    # Business details
    tax_id = models.CharField(max_length=50, blank=True)
    business_type = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Feature flags
    features_enabled = models.JSONField(default=dict, blank=True)
    
    # Usage limits
    usage_limits = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return f"/organizations/{self.slug}/"
    
    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()


class Role(UUIDModel, TimeStampedModel):
    """Role model for RBAC."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=list)  # List of permission codes
    is_system_role = models.BooleanField(default=False)  # Cannot be deleted
    
    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Membership(UUIDModel, TimeStampedModel):
    """User membership in organizations with roles."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)  # Primary org for user
    
    # Invitation details
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='membership_invitations')
    invitation_accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Access control
    permissions_override = models.JSONField(default=dict, blank=True)  # Additional permissions
    
    class Meta:
        verbose_name = _('Membership')
        verbose_name_plural = _('Memberships')
        unique_together = ['user', 'organization']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['organization', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.organization.name} as {self.role.name}"
    
    def has_permission(self, permission):
        """Check if the membership has a specific permission."""
        # Check role permissions
        if permission in self.role.permissions:
            return True
        
        # Check permission overrides
        return permission in self.permissions_override.get('additional', [])


class Invitation(UUIDModel, TimeStampedModel):
    """Organization invitations."""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('declined', _('Declined')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    
    # Invitee details
    email = models.EmailField(validators=[EmailValidator()])
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    # Invitation details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    
    # Response tracking
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_invitations')
    
    # Message
    message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('Invitation')
        verbose_name_plural = _('Invitations')
        unique_together = ['organization', 'email', 'status']  # Prevent duplicate pending invitations
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Invitation to {self.email} for {self.organization.name}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_be_accepted(self):
        return self.status == 'pending' and not self.is_expired


class APIKey(UUIDModel, TimeStampedModel):
    """API keys for programmatic access."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='api_keys')
    
    name = models.CharField(max_length=200)
    key_hash = models.CharField(max_length=128, unique=True)  # Hashed API key
    prefix = models.CharField(max_length=8)  # First 8 chars for identification
    
    # Permissions
    permissions = models.JSONField(default=list)
    
    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('API Key')
        verbose_name_plural = _('API Keys')
        indexes = [
            models.Index(fields=['key_hash']),
            models.Index(fields=['prefix']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.prefix}***)"
