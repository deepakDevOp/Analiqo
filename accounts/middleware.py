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
            '/accounts/',
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/static/',
            '/media/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
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
            
            # Fallback to user's primary organization
            if not request.organization:
                primary_org = request.user.get_primary_organization()
                if primary_org:
                    request.organization = primary_org
                    request.session['current_organization_id'] = str(primary_org.id)
        
        return None
