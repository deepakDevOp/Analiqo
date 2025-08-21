"""
Forms for user authentication and account management.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Organization, Invitation, Role, User


class SignupForm(forms.Form):
    """Custom signup form with additional fields."""
    
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
        """Called by allauth to customize the signup process."""
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()


class OrganizationCreateForm(forms.ModelForm):
    """Form for creating a new organization."""
    
    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'website', 'phone', 'email',
            'address_line1', 'address_line2', 'city', 'state', 
            'postal_code', 'country', 'timezone', 'currency'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organization name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of your organization'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@example.com'
            }),
            'address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apartment, suite, etc. (optional)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP/Postal code'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country code (e.g., US)'
            }),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'USD'
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Organization.objects.filter(name__iexact=name).exists():
            raise ValidationError('An organization with this name already exists.')
        return name


class InvitationForm(forms.ModelForm):
    """Form for sending organization invitations."""
    
    class Meta:
        model = Invitation
        fields = ['email', 'first_name', 'last_name', 'role', 'message']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'user@example.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional message to include with the invitation'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter roles for this organization
        if self.organization:
            self.fields['role'].queryset = Role.objects.filter(
                is_system_role=True
            ).exclude(name='Owner')  # Don't allow inviting as owner
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if user is already a member
        if self.organization and self.organization.memberships.filter(
            user__email=email, 
            is_active=True
        ).exists():
            raise ValidationError('This user is already a member of the organization.')
        
        # Check if there's already a pending invitation
        if self.organization and Invitation.objects.filter(
            organization=self.organization,
            email=email,
            status='pending'
        ).exists():
            raise ValidationError('There is already a pending invitation for this email.')
        
        return email


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'timezone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
        }
