"""
Signal handlers for accounts app.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Organization, Membership, Role

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_organization(sender, instance, created, **kwargs):
    """Create a personal organization for new users."""
    if created and not instance.is_superuser:
        # Create personal organization
        org_name = f"{instance.first_name} {instance.last_name}".strip()
        if not org_name:
            org_name = instance.email.split('@')[0]
        
        organization = Organization.objects.create(
            name=f"{org_name}'s Organization",
            slug=f"{instance.id}-personal",
        )
        
        # Get or create Owner role
        owner_role, _ = Role.objects.get_or_create(
            name='Owner',
            defaults={
                'description': 'Full access to organization',
                'permissions': ['*'],  # All permissions
                'is_system_role': True,
            }
        )
        
        # Create membership
        Membership.objects.create(
            user=instance,
            organization=organization,
            role=owner_role,
            is_primary=True,
            is_active=True,
        )


@receiver(post_save, sender=Organization)
def create_default_roles(sender, instance, created, **kwargs):
    """Create default roles for new organizations."""
    if created:
        default_roles = [
            {
                'name': 'Owner',
                'description': 'Full access to organization',
                'permissions': ['*'],
                'is_system_role': True,
            },
            {
                'name': 'Admin',
                'description': 'Administrative access to organization',
                'permissions': [
                    'organization.manage',
                    'users.manage',
                    'billing.view',
                    'pricing.manage',
                    'analytics.view',
                    'repricing.manage',
                ],
                'is_system_role': True,
            },
            {
                'name': 'Analyst',
                'description': 'Analytics and reporting access',
                'permissions': [
                    'analytics.view',
                    'pricing.view',
                    'repricing.view',
                    'catalog.view',
                ],
                'is_system_role': True,
            },
            {
                'name': 'Operator',
                'description': 'Operational access for day-to-day tasks',
                'permissions': [
                    'pricing.manage',
                    'repricing.execute',
                    'catalog.manage',
                ],
                'is_system_role': True,
            },
        ]
        
        for role_data in default_roles:
            Role.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
