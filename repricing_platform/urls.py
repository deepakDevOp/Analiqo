"""
URL configuration for repricing_platform project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from web.views import BootstrapLoginView, BootstrapSignupView

urlpatterns = [
    # Admin
    path(f"{getattr(settings, 'ADMIN_URL', 'admin/')}", admin.site.urls),
    path("", include("web.urls")),
    # Override allauth templates with our Bootstrap versions
    path("accounts/login/", BootstrapLoginView.as_view(), name="account_login"),
    path("accounts/signup/", BootstrapSignupView.as_view(), name="account_signup"),

    # Auth via django-allauth (keep after overrides)
    path("accounts/", include("allauth.urls")),

    # User app: profile views
    path("user/", include("user.urls")),
]

# Serve media files in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
