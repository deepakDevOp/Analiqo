"""
URL configuration for catalog app.
"""

from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # Listings
    path('listings/', views.ListingListView.as_view(), name='listing_list'),
    path('listings/add/', views.ListingCreateView.as_view(), name='listing_create'),
    path('listings/<uuid:pk>/', views.ListingDetailView.as_view(), name='listing_detail'),
    path('listings/<uuid:pk>/edit/', views.ListingUpdateView.as_view(), name='listing_update'),
    path('listings/<uuid:pk>/sync/', views.ListingSyncView.as_view(), name='listing_sync'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<uuid:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
    
    # Bulk operations
    path('bulk/import/', views.BulkImportView.as_view(), name='bulk_import'),
    path('bulk/export/', views.BulkExportView.as_view(), name='bulk_export'),
]
