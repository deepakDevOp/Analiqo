"""
Core middleware for the repricing platform.
"""

from django.utils import timezone
from django.contrib.auth import get_user_model
import pytz

User = get_user_model()


class TimezoneMiddleware:
    """
    Middleware to set the timezone based on user preferences.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            user_timezone = getattr(request.user, 'timezone', None)
            if user_timezone:
                timezone.activate(pytz.timezone(user_timezone))
            else:
                timezone.deactivate()
        else:
            timezone.deactivate()
        
        response = self.get_response(request)
        return response
