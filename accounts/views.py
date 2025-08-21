"""
Views for user authentication, organization management, and onboarding.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    CreateView, UpdateView, ListView, DetailView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
import uuid

from .models import Organization, Membership, Invitation, Role
from .forms import OrganizationCreateForm, InvitationForm


class OnboardingView(LoginRequiredMixin, TemplateView):
    """Onboarding flow for new users."""
    template_name = 'accounts/onboarding.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user already has organizations
        user_orgs = self.request.user.memberships.filter(is_active=True)
        
        context.update({
            'user_organizations': user_orgs,
            'has_organizations': user_orgs.exists(),
            'pending_invitations': Invitation.objects.filter(
                email=self.request.user.email,
                status='pending'
            )
        })
        
        return context


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    """Create a new organization."""
    model = Organization
    form_class = OrganizationCreateForm
    template_name = 'accounts/organization_create.html'
    success_url = reverse_lazy('web:dashboard')
    
    def form_valid(self, form):
        with transaction.atomic():
            # Create the organization
            response = super().form_valid(form)
            
            # Get or create owner role
            owner_role, _ = Role.objects.get_or_create(
                name='Owner',
                defaults={
                    'description': 'Organization owner with full access',
                    'permissions': ['*'],  # All permissions
                    'is_system_role': True
                }
            )
            
            # Add user as owner
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                role=owner_role,
                is_active=True,
                is_primary=True
            )
            
            # Set as current organization in session
            self.request.session['current_organization_id'] = str(self.object.id)
            
            messages.success(
                self.request, 
                f'Organization "{self.object.name}" created successfully!'
            )
            
            return response


class OrganizationSwitchView(LoginRequiredMixin, TemplateView):
    """Switch between user's organizations."""
    template_name = 'accounts/organization_switch.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user_orgs = Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True
        ).distinct()
        
        current_org_id = self.request.session.get('current_organization_id')
        current_org = None
        if current_org_id:
            try:
                current_org = user_orgs.get(id=current_org_id)
            except Organization.DoesNotExist:
                pass
        
        context.update({
            'organizations': user_orgs,
            'current_organization': current_org
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        org_id = request.POST.get('organization_id')
        
        if org_id:
            try:
                # Verify user has access to this organization
                org = Organization.objects.get(
                    id=org_id,
                    memberships__user=request.user,
                    memberships__is_active=True
                )
                request.session['current_organization_id'] = str(org.id)
                messages.success(request, f'Switched to {org.name}')
                
            except Organization.DoesNotExist:
                messages.error(request, 'Invalid organization selected')
        
        return redirect('web:dashboard')


class InvitationCreateView(LoginRequiredMixin, CreateView):
    """Send invitations to join organization."""
    model = Invitation
    form_class = InvitationForm
    template_name = 'accounts/invitation_create.html'
    success_url = reverse_lazy('accounts:invitation_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.organization
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.invited_by = self.request.user
        
        # Generate unique token
        form.instance.token = uuid.uuid4().hex
        
        # Set expiry (30 days from now)
        form.instance.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        response = super().form_valid(form)
        
        # TODO: Send invitation email
        messages.success(
            self.request, 
            f'Invitation sent to {form.instance.email}'
        )
        
        return response


class InvitationAcceptView(TemplateView):
    """Accept an organization invitation."""
    template_name = 'accounts/invitation_accept.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        token = kwargs.get('token')
        invitation = get_object_or_404(
            Invitation,
            token=token,
            status='pending'
        )
        
        context['invitation'] = invitation
        context['can_accept'] = invitation.can_be_accepted()
        
        return context
    
    def post(self, request, *args, **kwargs):
        token = kwargs.get('token')
        invitation = get_object_or_404(
            Invitation,
            token=token,
            status='pending'
        )
        
        if not invitation.can_be_accepted():
            messages.error(request, 'This invitation has expired or is no longer valid')
            return redirect('account_login')
        
        if not request.user.is_authenticated:
            # Store token in session and redirect to login
            request.session['pending_invitation_token'] = token
            messages.info(request, 'Please log in to accept the invitation')
            return redirect('account_login')
        
        with transaction.atomic():
            # Create membership
            Membership.objects.create(
                user=request.user,
                organization=invitation.organization,
                role=invitation.role,
                is_active=True,
                invited_by=invitation.invited_by,
                invitation_accepted_at=timezone.now()
            )
            
            # Update invitation
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.accepted_by = request.user
            invitation.save()
            
            # Set as current organization if user doesn't have one
            if not request.session.get('current_organization_id'):
                request.session['current_organization_id'] = str(invitation.organization.id)
            
            messages.success(
                request, 
                f'Welcome to {invitation.organization.name}!'
            )
        
        return redirect('web:dashboard')


class InvitationListView(LoginRequiredMixin, ListView):
    """List organization invitations."""
    model = Invitation
    template_name = 'accounts/invitation_list.html'
    context_object_name = 'invitations'
    paginate_by = 20
    
    def get_queryset(self):
        if not self.request.organization:
            return Invitation.objects.none()
        
        return Invitation.objects.filter(
            organization=self.request.organization
        ).order_by('-created_at')


@login_required
def profile_view(request):
    """User profile view."""
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'organizations': request.user.memberships.filter(is_active=True)
    })


@login_required
def organization_settings_view(request):
    """Organization settings view."""
    if not request.organization:
        messages.error(request, 'No organization selected')
        return redirect('accounts:onboarding')
    
    return render(request, 'accounts/organization_settings.html', {
        'organization': request.organization,
        'members': request.organization.memberships.filter(is_active=True)
    })
