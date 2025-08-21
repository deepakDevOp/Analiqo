"""
Views for user authentication and organization management.
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


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    """Create a new organization."""
    model = Organization
    form_class = OrganizationCreateForm
    template_name = 'accounts/organization_create.html'
    success_url = reverse_lazy('web:dashboard')
    
    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            
            # Create owner membership for the user
            admin_role, _ = Role.objects.get_or_create(
                name='admin',
                defaults={
                    'permissions': {
                        'manage_organization': True,
                        'manage_users': True,
                        'manage_billing': True,
                        'view_analytics': True,
                        'manage_repricing': True,
                    }
                }
            )
            
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                role=admin_role,
                is_active=True
            )
            
            # Set this as the current organization
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
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.request.organization
        form.instance.invited_by = self.request.user
        
        # Generate unique token
        form.instance.token = str(uuid.uuid4())
        
        response = super().form_valid(form)
        
        # TODO: Send invitation email here
        # send_invitation_email(form.instance)
        
        messages.success(
            self.request,
            f'Invitation sent to {form.instance.email}'
        )
        
        return response


class InvitationListView(LoginRequiredMixin, ListView):
    """List invitations for the current organization."""
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


class InvitationAcceptView(DetailView):
    """Accept an invitation to join an organization."""
    model = Invitation
    template_name = 'accounts/invitation_accept.html'
    slug_field = 'token'
    slug_url_kwarg = 'token'
    
    def get_queryset(self):
        return Invitation.objects.filter(
            status='pending',
            expires_at__gt=timezone.now()
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invitation = self.get_object()
        
        # Check if user is already authenticated
        if self.request.user.is_authenticated:
            # Check if user email matches invitation
            if self.request.user.email != invitation.email:
                context['email_mismatch'] = True
        
        return context
    
    def post(self, request, *args, **kwargs):
        invitation = self.get_object()
        
        # Validate user email matches invitation
        if request.user.email != invitation.email:
            messages.error(request, 'Your email does not match the invitation.')
            return redirect('web:dashboard')
        
        # Check if user is already a member
        existing_membership = Membership.objects.filter(
            user=request.user,
            organization=invitation.organization,
            is_active=True
        ).first()
        
        if existing_membership:
            messages.info(request, 'You are already a member of this organization.')
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save()
            return redirect('web:dashboard')
        
        # Create membership
        with transaction.atomic():
            # Get default role (if specified) or member role
            role = invitation.role
            if not role:
                role, _ = Role.objects.get_or_create(
                    name='member',
                    defaults={
                        'permissions': {
                            'view_analytics': True,
                            'manage_repricing': False,
                        }
                    }
                )
            
            Membership.objects.create(
                user=request.user,
                organization=invitation.organization,
                role=role,
                is_active=True
            )
            
            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save()
            
            # Set as current organization
            request.session['current_organization_id'] = str(invitation.organization.id)
        
        messages.success(
            request,
            f'Successfully joined {invitation.organization.name}!'
        )
        
        return redirect('web:dashboard')


@login_required
def profile_view(request):
    """User profile view and edit."""
    # Implementation here
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required  
def organization_settings_view(request):
    """Organization settings view."""
    if not request.organization:
        return redirect('web:dashboard')
    
    # Check if user has permission to manage organization
    membership = request.user.memberships.filter(
        organization=request.organization,
        is_active=True
    ).first()
    
    if not membership or not membership.role.permissions.get('manage_organization', False):
        messages.error(request, 'You do not have permission to manage organization settings.')
        return redirect('web:dashboard')
    
    # Implementation here
    return render(request, 'accounts/organization_settings.html', {
        'organization': request.organization
    })
