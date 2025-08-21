"""
Django signals for accounts app.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

from .models import User, Organization, Membership, Invitation

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Handle user creation."""
    if created:
        logger.info(f"New user created: {instance.email}")
        # TODO: Send welcome email
        # TODO: Create user profile


@receiver(post_save, sender=Organization)
def organization_created(sender, instance, created, **kwargs):
    """Handle organization creation."""
    if created:
        logger.info(f"New organization created: {instance.name}")
        # TODO: Set up default settings
        # TODO: Create default roles if needed


@receiver(post_save, sender=Membership)
def membership_created(sender, instance, created, **kwargs):
    """Handle membership creation."""
    if created:
        logger.info(f"New membership: {instance.user.email} joined {instance.organization.name}")
        # TODO: Send invitation accepted email
        # TODO: Log in audit system


@receiver(post_save, sender=Invitation)
def invitation_created(sender, instance, created, **kwargs):
    """Handle invitation creation."""
    if created:
        logger.info(f"New invitation sent to: {instance.email}")
        # TODO: Send invitation email
        # TODO: Schedule reminder emails