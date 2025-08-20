"""
Context processors for accounts app.
"""

def organization(request):
    """Add organization context to templates."""
    context = {
        'current_organization': getattr(request, 'organization', None),
        'user_organizations': [],
    }
    
    if request.user.is_authenticated:
        context['user_organizations'] = request.user.memberships.filter(
            is_active=True
        ).select_related('organization', 'role').order_by('organization__name')
    
    return context
