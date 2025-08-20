"""
Main web views for SSR interface.
"""

from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta


class LandingView(TemplateView):
    """Landing page for unauthenticated users."""
    
    template_name = 'web/landing.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('web:dashboard')
        return super().dispatch(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view."""
    
    template_name = 'web/dashboard.html'
    login_url = reverse_lazy('account_login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user has completed onboarding
        if not self.request.organization:
            return redirect('web:onboarding')
        
        # Dashboard metrics
        context.update({
            'total_products': self.get_total_products(),
            'active_listings': self.get_active_listings(),
            'repricing_runs_today': self.get_repricing_runs_today(),
            'buy_box_percentage': self.get_buy_box_percentage(),
            'recent_alerts': self.get_recent_alerts(),
            'recent_activities': self.get_recent_activities(),
        })
        
        return context
    
    def get_total_products(self):
        """Get total number of products."""
        from catalog.models import Product
        return Product.objects.filter(
            organization=self.request.organization,
            is_deleted=False
        ).count()
    
    def get_active_listings(self):
        """Get number of active listings."""
        from catalog.models import Listing
        return Listing.objects.filter(
            organization=self.request.organization,
            status='active',
            is_deleted=False
        ).count()
    
    def get_repricing_runs_today(self):
        """Get number of repricing runs today."""
        from repricer.models import RepricingRun
        today = timezone.now().date()
        return RepricingRun.objects.filter(
            organization=self.request.organization,
            created_at__date=today
        ).count()
    
    def get_buy_box_percentage(self):
        """Get buy box win percentage."""
        from catalog.models import Listing
        total_listings = Listing.objects.filter(
            organization=self.request.organization,
            status='active',
            is_deleted=False
        ).count()
        
        if total_listings == 0:
            return 0
        
        buy_box_listings = Listing.objects.filter(
            organization=self.request.organization,
            status='active',
            has_buy_box=True,
            is_deleted=False
        ).count()
        
        return round((buy_box_listings / total_listings) * 100, 1)
    
    def get_recent_alerts(self):
        """Get recent alerts."""
        from notifications.models import Notification
        return Notification.objects.filter(
            organization=self.request.organization,
            is_read=False
        ).order_by('-created_at')[:5]
    
    def get_recent_activities(self):
        """Get recent activities."""
        from audit.models import AuditLog
        return AuditLog.objects.filter(
            organization=self.request.organization,
            user=self.request.user
        ).order_by('-timestamp')[:10]


class OnboardingView(LoginRequiredMixin, TemplateView):
    """Onboarding flow start."""
    
    template_name = 'web/onboarding/start.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user already has an organization set up
        if request.organization and hasattr(request.organization, 'subscription'):
            return redirect('web:dashboard')
        return super().dispatch(request, *args, **kwargs)


class CredentialsSetupView(LoginRequiredMixin, TemplateView):
    """Credentials setup step in onboarding."""
    
    template_name = 'web/onboarding/credentials.html'


class PricingSetupView(LoginRequiredMixin, TemplateView):
    """Pricing setup step in onboarding."""
    
    template_name = 'web/onboarding/pricing.html'


class OnboardingCompleteView(LoginRequiredMixin, TemplateView):
    """Onboarding completion."""
    
    template_name = 'web/onboarding/complete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        messages.success(
            self.request,
            'Welcome to RepricingPro! Your account is now set up and ready to use.'
        )
        return context


class DashboardMetricsView(LoginRequiredMixin, TemplateView):
    """Dashboard metrics partial for Unpoly updates."""
    
    template_name = 'web/partials/dashboard_metrics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Similar to DashboardView but returns only metrics
        context.update({
            'total_products': self.get_total_products(),
            'active_listings': self.get_active_listings(),
            'repricing_runs_today': self.get_repricing_runs_today(),
            'buy_box_percentage': self.get_buy_box_percentage(),
        })
        
        return context
    
    # Reuse methods from DashboardView
    get_total_products = DashboardView.get_total_products
    get_active_listings = DashboardView.get_active_listings
    get_repricing_runs_today = DashboardView.get_repricing_runs_today
    get_buy_box_percentage = DashboardView.get_buy_box_percentage


class DashboardAlertsView(LoginRequiredMixin, TemplateView):
    """Dashboard alerts partial for Unpoly updates."""
    
    template_name = 'web/partials/dashboard_alerts.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_alerts'] = self.get_recent_alerts()
        return context
    
    get_recent_alerts = DashboardView.get_recent_alerts


class RecentActivityView(LoginRequiredMixin, TemplateView):
    """Recent activity partial for Unpoly updates."""
    
    template_name = 'web/partials/recent_activity.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_activities'] = self.get_recent_activities()
        return context
    
    get_recent_activities = DashboardView.get_recent_activities
