"""
Forms for minimal authentication customizations.
"""

from django import forms
from django.forms import ModelForm
from .models import User


class SignupForm(forms.Form):
    """Custom signup form to collect required names."""

    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email address'})
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label='I accept the Terms of Service and Privacy Policy'
    )

    def signup(self, request, user):
        user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.save()


class UserUpdateForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'timezone',
            'phone',
            'avatar',
            'notification_preferences',
            'ui_preferences',
        ]

