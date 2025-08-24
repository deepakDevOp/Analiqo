"""
Views for the main web interface (SSR).
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from allauth.account.views import LoginView, SignupView


class LandingView(TemplateView):
    """Landing page for anonymous users."""
    template_name = 'landing.html'
    # Authenticated users can still view the landing page


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'


# Error handlers
def handler404(request, exception):
    return render(request, 'errors/error.html', status=404)


def handler500(request):
    return render(request, 'errors/error.html', status=500)


def handler403(request, exception):
    return render(request, 'errors/error.html', status=403)


class BootstrapLoginView(LoginView):
    template_name = "login.html"


class BootstrapSignupView(SignupView):
    template_name = "signup.html"