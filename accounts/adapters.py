"""
Allauth adapters for custom authentication behavior.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for allauth."""
    
    def save_user(self, request, user, form, commit=True):
        """Save user instance with custom fields."""
        user = super().save_user(request, user, form, commit=False)
        
        # Add any custom logic here
        if hasattr(form, 'cleaned_data'):
            if 'first_name' in form.cleaned_data:
                user.first_name = form.cleaned_data['first_name']
            if 'last_name' in form.cleaned_data:
                user.last_name = form.cleaned_data['last_name']
        
        if commit:
            user.save()
        return user
    
    def get_login_redirect_url(self, request):
        """Custom login redirect logic."""
        print(f"DEBUG: get_login_redirect_url called for user: {request.user}")
        print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
        
        # If user has memberships, redirect to dashboard
        if hasattr(request, 'user') and request.user.is_authenticated:
            print(f"DEBUG: Checking memberships for user: {request.user}")
            if request.user.memberships.exists():
                print(f"DEBUG: User has memberships, redirecting to dashboard")
                return '/dashboard/'
            else:
                print(f"DEBUG: User has no memberships, redirecting to onboarding")
                # If user has no memberships, redirect to onboarding
                return '/onboarding/'
        
        print(f"DEBUG: Fallback to default behavior")
        # Fallback to default behavior
        return super().get_login_redirect_url(request)
    
    def get_signup_redirect_url(self, request):
        """Redirect new users to onboarding after signup."""
        return '/onboarding/'
    
    def get_redirect_url(self, request):
        """Override the main redirect method to ensure proper redirection."""
        # For login, check if user has memberships
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.memberships.exists():
                return '/dashboard/'
            else:
                return '/onboarding/'
        
        # Fallback to default behavior
        return super().get_redirect_url(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for allauth."""
    
    def save_user(self, request, sociallogin, form=None):
        """Save user from social login."""
        user = super().save_user(request, sociallogin, form)
        
        # Add any custom logic for social users here
        
        return user
