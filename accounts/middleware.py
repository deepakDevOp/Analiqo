"""
Middleware for handling organization context in multi-tenant setup.
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import Http404
from .models import Organization


class OrganizationMiddleware(MiddlewareMixin):
    """
    Middleware to set the current organization context.
    """
    
    def process_request(self, request):
        # Initialize organization context
        request.organization = None
        
        # Skip organization context for certain paths
        skip_paths = [
            '/admin/',
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/static/',
            '/media/',
        ]
        
        # Only skip organization context for non-authentication paths
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # For authentication paths, we still want to set organization context
        # but only after the user is authenticated
        
        # Get organization from session or user's primary organization
        if request.user.is_authenticated:
            org_id = request.session.get('current_organization_id')
            
            if org_id:
                try:
                    organization = Organization.objects.get(
                        id=org_id,
                        memberships__user=request.user,
                        memberships__is_active=True
                    )
                    request.organization = organization
                except Organization.DoesNotExist:
                    # Clear invalid organization from session
                    request.session.pop('current_organization_id', None)
            
            # Fallback to user's first active organization if no primary is set
            if not request.organization:
                first_membership = request.user.memberships.filter(is_active=True).first()
                if first_membership:
                    organization = first_membership.organization
                    request.organization = organization
                    request.session['current_organization_id'] = str(organization.id)
        
        return None
