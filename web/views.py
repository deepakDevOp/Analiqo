"""
Views for the main web interface (SSR).
"""

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy


class LandingView(TemplateView):
    """Landing page for anonymous users."""
    template_name = 'web/landing.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('web:dashboard')
        return super().dispatch(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Minimal dashboard without cross-app dependencies."""

    template_name = 'web/dashboard.html'
    login_url = reverse_lazy('account_login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'has_organization': getattr(self.request, 'organization', None) is not None,
            'total_products': 0,
            'active_listings': 0,
            'repricing_runs_today': 0,
            'buy_box_percentage': 0,
            'recent_alerts': [],
            'recent_activities': [],
        })
        return context


class DashboardMetricsView(LoginRequiredMixin, TemplateView):
    template_name = 'web/partials/dashboard_metrics.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'total_products': 0,
            'active_listings': 0,
            'repricing_runs_today': 0,
            'buy_box_percentage': 0,
        })
        return context


class DashboardAlertsView(LoginRequiredMixin, TemplateView):
    template_name = 'web/partials/dashboard_alerts.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_alerts'] = []
        return context


class RecentActivityView(LoginRequiredMixin, TemplateView):
    template_name = 'web/partials/recent_activity.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_activities'] = []
        return context


# Error handlers
def handler404(request, exception):
    return render(request, 'errors/error.html', status=404)


def handler500(request):
    return render(request, 'errors/error.html', status=500)


def handler403(request, exception):
    return render(request, 'errors/error.html', status=403)