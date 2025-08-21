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
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has an organization. If not, redirect to onboarding.
        if not getattr(request, 'organization', None):
            return redirect('web:onboarding')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
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
    
    template_name = 'accounts/onboarding.html'
    
    def dispatch(self, request, *args, **kwargs):
        # If user already has an organization, redirect to the dashboard
        if hasattr(request, 'organization') and request.organization:
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


# Error handlers
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden


def handler404(request, exception):
    """Custom 404 error handler."""
    context = {
        'error_code': '404',
        'error_title': 'Page Not Found',
        'error_message': 'The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.',
    }
    return HttpResponseNotFound(render(request, 'errors/error.html', context))


def handler500(request):
    """Custom 500 error handler."""
    context = {
        'error_code': '500',
        'error_title': 'Server Error',
        'error_message': 'An unexpected error occurred. Our team has been notified and is working to resolve the issue.',
    }
    return HttpResponseServerError(render(request, 'errors/error.html', context))


def handler403(request, exception):
    """Custom 403 error handler."""
    context = {
        'error_code': '403',
        'error_title': 'Access Forbidden',
        'error_message': 'You do not have permission to access this resource.',
    }
    return HttpResponseForbidden(render(request, 'errors/error.html', context))