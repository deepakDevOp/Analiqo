"""
Management command to create default system roles.
"""

from django.core.management.base import BaseCommand
from accounts.models import Role


class Command(BaseCommand):
    help = 'Create default system roles'

    def handle(self, *args, **options):
        roles_data = [
            {
                'name': 'Owner',
                'description': 'Organization owner with full access to all features',
                'permissions': ['*'],  # All permissions
                'is_system_role': True
            },
            {
                'name': 'Admin',
                'description': 'Administrator with access to most features',
                'permissions': [
                    'manage_users', 'manage_settings', 'manage_billing',
                    'manage_products', 'manage_pricing', 'view_analytics'
                ],
                'is_system_role': True
            },
            {
                'name': 'Manager',
                'description': 'Manager with access to pricing and analytics',
                'permissions': [
                    'manage_products', 'manage_pricing', 'view_analytics'
                ],
                'is_system_role': True
            },
            {
                'name': 'Analyst',
                'description': 'Analyst with read-only access to data and analytics',
                'permissions': [
                    'view_products', 'view_pricing', 'view_analytics'
                ],
                'is_system_role': True
            },
            {
                'name': 'Operator',
                'description': 'Operator with basic access to products and pricing',
                'permissions': [
                    'view_products', 'manage_products'
                ],
                'is_system_role': True
            }
        ]

        created_count = 0
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Role already exists: {role.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nCreated {created_count} new roles')
        )
