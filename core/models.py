"""
Core base models and mixins.
"""

from django.db import models
from django.utils import timezone
import uuid


class TimeStampedModel(models.Model):
    """Abstract base class with created and updated timestamps."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract base class with UUID primary key."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True

class TenantModel(models.Model):
    """Abstract base class for multi-tenant models."""
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
    
    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base class with soft delete functionality."""
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def delete(self, using=None, keep_parents=False):
        """Soft delete the object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)
    
    def hard_delete(self, using=None, keep_parents=False):
        """Actually delete the object from database."""
        super().delete(using=using, keep_parents=keep_parents)
    
    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel, TenantModel, SoftDeleteModel):
    """Base model combining all common functionality."""
    
    class Meta:
        abstract = True

