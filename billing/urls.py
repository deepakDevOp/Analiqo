"""
URL configuration for billing app.
"""

from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Subscription management
    path('subscription/', views.SubscriptionView.as_view(), name='subscription'),
    path('plans/', views.PlansView.as_view(), name='plans'),
    path('subscribe/<slug:plan_slug>/', views.SubscribeView.as_view(), name='subscribe'),
    path('cancel/', views.CancelSubscriptionView.as_view(), name='cancel_subscription'),
    
    # Payment methods
    path('payment-methods/', views.PaymentMethodsView.as_view(), name='payment_methods'),
    path('payment-methods/add/', views.AddPaymentMethodView.as_view(), name='add_payment_method'),
    path('payment-methods/<uuid:pm_id>/delete/', views.DeletePaymentMethodView.as_view(), name='delete_payment_method'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<uuid:invoice_id>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:invoice_id>/download/', views.InvoiceDownloadView.as_view(), name='invoice_download'),
    
    # Webhooks
    path('webhooks/stripe/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
]
