"""
Django admin configuration for catalog app.
"""

from django.contrib import admin
from .models import Category, Brand, Product, Listing

# Simple admin registration for now
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(Listing)