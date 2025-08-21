"""
URL configuration for repricing_platform project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path(f"{getattr(settings, 'ADMIN_URL', 'admin/')}", admin.site.urls),

    # Auth via django-allauth
    path("accounts/", include("allauth.urls")),

    # Project apps
    path("accounts/", include("accounts.urls")),
    path("", include("web.urls")),
]

# Serve media files in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
