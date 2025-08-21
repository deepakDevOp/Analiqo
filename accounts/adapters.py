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
        """Always redirect to dashboard after login."""
        return '/dashboard/'
    
    def get_signup_redirect_url(self, request):
        """Always redirect to dashboard after signup."""
        return '/dashboard/'


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for allauth."""
    
    def save_user(self, request, sociallogin, form=None):
        """Save user from social login."""
        user = super().save_user(request, sociallogin, form)
        
        # Add any custom logic for social users here
        
        return user
