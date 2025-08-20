"""
Error handling views.
"""

from django.shortcuts import render
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
