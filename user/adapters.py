"""
Allauth adapters for custom authentication behavior.
"""

from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if hasattr(form, 'cleaned_data'):
            if 'first_name' in form.cleaned_data:
                user.first_name = form.cleaned_data['first_name']
            if 'last_name' in form.cleaned_data:
                user.last_name = form.cleaned_data['last_name']
        if commit:
            user.save()
        return user

    def get_login_redirect_url(self, request):
        return '/home/'

    def get_signup_redirect_url(self, request):
        return '/home/'


