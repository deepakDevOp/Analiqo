"""
Models for secure credential storage with encryption.
"""

from django.db import modelsfrom django.utils.translation import gettext_lazy as _
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import json
from core.models import BaseModel


class CredentialManager(models.Manager):
    """Manager for credential operations with encryption."""
    
    def create_credential(self, organization, marketplace, credential_type, data):
        """Create an encrypted credential."""
        encrypted_data = self._encrypt_data(data)
        return self.create(
            organization=organization,
            marketplace=marketplace,
            credential_type=credential_type,
            encrypted_data=encrypted_data
        )
    
    def _encrypt_data(self, data):
        """Encrypt credential data."""
        # In production, use proper key management (AWS KMS, HashiCorp Vault, etc.)
        key = getattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', Fernet.generate_key())
        fernet = Fernet(key)
        
        json_data = json.dumps(data).encode()
        encrypted = fernet.encrypt(json_data)
        return base64.b64encode(encrypted).decode()


class MarketplaceCredential(BaseModel):
    """Encrypted storage for marketplace API credentials."""
    
    MARKETPLACE_CHOICES = [
        ('amazon', _('Amazon SP-API')),
        ('flipkart', _('Flipkart Marketplace API')),
    ]
    
    CREDENTIAL_TYPE_CHOICES = [
        ('oauth', _('OAuth Credentials')),
        ('api_key', _('API Key')),
        ('token', _('Access Token')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('expired', _('Expired')),
        ('revoked', _('Revoked')),
        ('invalid', _('Invalid')),
    ]
    
    marketplace = models.CharField(max_length=20, choices=MARKETPLACE_CHOICES)
    credential_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPE_CHOICES)
    
    # Encrypted credential data
    encrypted_data = models.TextField()
    
    # Metadata
    name = models.CharField(max_length=200)  # User-friendly name
    description = models.TextField(blank=True)
    
    # Status and validation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_validated_at = models.DateTimeField(null=True, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    
    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    objects = CredentialManager()
    
    class Meta:
        verbose_name = _('Marketplace Credential')
        verbose_name_plural = _('Marketplace Credentials')
        unique_together = ['organization', 'marketplace', 'name']
        indexes = [
            models.Index(fields=['marketplace', 'status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['last_validated_at']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.get_marketplace_display()} - {self.name}"
    
    def decrypt_data(self):
        """Decrypt and return credential data."""
        try:
            # In production, use proper key management
            key = getattr(settings, 'CREDENTIAL_ENCRYPTION_KEY', None)
            if not key:
                raise ValueError("Encryption key not configured")
            
            fernet = Fernet(key)
            encrypted_bytes = base64.b64decode(self.encrypted_data.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {e}")
    
    def update_credentials(self, data):
        """Update encrypted credential data."""
        self.encrypted_data = self.__class__.objects._encrypt_data(data)
        self.save(update_fields=['encrypted_data', 'updated_at'])
    
    @property
    def is_expired(self):
        """Check if credentials are expired."""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if credentials are valid and active."""
        return self.status == 'active' and not self.is_expired


class AmazonCredential(BaseModel):
    """Amazon SP-API specific credentials."""
    
    credential = models.OneToOneField(
        MarketplaceCredential, 
        on_delete=models.CASCADE, 
        related_name='amazon_details'
    )
    
    # Amazon-specific fields
    client_id = models.CharField(max_length=100)
    marketplace_ids = models.JSONField(default=list)  # List of marketplace IDs
    seller_id = models.CharField(max_length=50)
    
    # OAuth flow
    auth_url = models.URLField(blank=True)
    redirect_uri = models.URLField(blank=True)
    
    # Regional settings
    region = models.CharField(max_length=20, default='us-east-1')
    
    class Meta:
        verbose_name = _('Amazon Credential')
        verbose_name_plural = _('Amazon Credentials')
    
    def __str__(self):
        return f"Amazon - {self.seller_id}"


class FlipkartCredential(BaseModel):
    """Flipkart Marketplace API specific credentials."""
    
    credential = models.OneToOneField(
        MarketplaceCredential, 
        on_delete=models.CASCADE, 
        related_name='flipkart_details'
    )
    
    # Flipkart-specific fields
    seller_id = models.CharField(max_length=100)
    application_id = models.CharField(max_length=100, blank=True)
    
    # Environment
    environment = models.CharField(
        max_length=20, 
        choices=[('sandbox', 'Sandbox'), ('production', 'Production')],
        default='sandbox'
    )
    
    class Meta:
        verbose_name = _('Flipkart Credential')
        verbose_name_plural = _('Flipkart Credentials')
    
    def __str__(self):
        return f"Flipkart - {self.seller_id}"


class CredentialValidation(models.Model):
    """Credential validation history."""
    
    credential = models.ForeignKey(
        MarketplaceCredential, 
        on_delete=models.CASCADE, 
        related_name='validations'
    )
    
    # Validation results
    is_valid = models.BooleanField()
    validation_message = models.TextField(blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    
    # Timing
    validated_at = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Credential Validation')
        verbose_name_plural = _('Credential Validations')
        ordering = ['-validated_at']
        indexes = [
            models.Index(fields=['credential', 'validated_at']),
            models.Index(fields=['is_valid']),
        ]
    
    def __str__(self):
        status = "Valid" if self.is_valid else "Invalid"
        return f"{self.credential.name} - {status} at {self.validated_at}"

