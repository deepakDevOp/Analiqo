"""
Billing views for subscription management and payment processing.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.views import View
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import stripe
import json
import logging

from .models import Plan, Subscription, Invoice, PaymentMethod
from .services import BillingService
from .stripe_client import StripeClient

logger = logging.getLogger(__name__)


class SubscriptionView(LoginRequiredMixin, TemplateView):
    """View for managing current subscription."""
    template_name = 'billing/subscription.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.request.user.organization
        
        try:
            subscription = organization.subscription
            context['subscription'] = subscription
            context['plan'] = subscription.plan
        except Subscription.DoesNotExist:
            context['subscription'] = None
            context['plan'] = None
        
        return context


class PlansView(LoginRequiredMixin, TemplateView):
    """View for displaying available subscription plans."""
    template_name = 'billing/plans.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = Plan.objects.filter(is_active=True, is_public=True)
        
        # Get current subscription if exists
        organization = self.request.user.organization
        try:
            context['current_subscription'] = organization.subscription
        except Subscription.DoesNotExist:
            context['current_subscription'] = None
        
        return context


class SubscribeView(LoginRequiredMixin, View):
    """Handle subscription to a plan."""
    
    def post(self, request, plan_slug):
        try:
            plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)
            organization = request.user.organization
            
            # Check if organization already has a subscription
            if hasattr(organization, 'subscription') and organization.subscription.is_active:
                messages.error(request, _('You already have an active subscription.'))
                return redirect('billing:subscription')
            
            # Create subscription using BillingService
            billing_service = BillingService()
            subscription = billing_service.create_subscription(organization, plan)
            
            messages.success(request, _('Successfully subscribed to {plan_name}!').format(plan_name=plan.name))
            return redirect('billing:subscription')
            
        except Exception as e:
            logger.error(f"Subscription creation failed: {str(e)}")
            messages.error(request, _('Failed to create subscription. Please try again.'))
            return redirect('billing:plans')


class CancelSubscriptionView(LoginRequiredMixin, View):
    """Handle subscription cancellation."""
    
    def post(self, request):
        try:
            organization = request.user.organization
            subscription = organization.subscription
            
            if not subscription.is_active:
                messages.error(request, _('No active subscription to cancel.'))
                return redirect('billing:subscription')
            
            # Cancel subscription using BillingService
            billing_service = BillingService()
            billing_service.cancel_subscription(subscription)
            
            messages.success(request, _('Subscription canceled successfully.'))
            return redirect('billing:subscription')
            
        except Exception as e:
            logger.error(f"Subscription cancellation failed: {str(e)}")
            messages.error(request, _('Failed to cancel subscription. Please try again.'))
            return redirect('billing:subscription')


class PaymentMethodsView(LoginRequiredMixin, ListView):
    """View for listing payment methods."""
    model = PaymentMethod
    template_name = 'billing/payment_methods.html'
    context_object_name = 'payment_methods'
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(organization=self.request.user.organization)


class AddPaymentMethodView(LoginRequiredMixin, TemplateView):
    """View for adding a new payment method."""
    template_name = 'billing/add_payment_method.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add Stripe publishable key for frontend
        context['stripe_publishable_key'] = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
        return context
    
    def post(self, request):
        try:
            payment_method_id = request.POST.get('payment_method_id')
            if not payment_method_id:
                messages.error(request, _('Invalid payment method.'))
                return redirect('billing:add_payment_method')
            
            organization = request.user.organization
            
            # Add payment method using BillingService
            billing_service = BillingService()
            payment_method = billing_service.add_payment_method(organization, payment_method_id)
            
            messages.success(request, _('Payment method added successfully.'))
            return redirect('billing:payment_methods')
            
        except Exception as e:
            logger.error(f"Adding payment method failed: {str(e)}")
            messages.error(request, _('Failed to add payment method. Please try again.'))
            return redirect('billing:add_payment_method')


class DeletePaymentMethodView(LoginRequiredMixin, View):
    """Handle payment method deletion."""
    
    def post(self, request, pm_id):
        try:
            payment_method = get_object_or_404(
                PaymentMethod, 
                id=pm_id, 
                organization=request.user.organization
            )
            
            # Delete payment method using BillingService
            billing_service = BillingService()
            billing_service.delete_payment_method(payment_method)
            
            messages.success(request, _('Payment method deleted successfully.'))
            return redirect('billing:payment_methods')
            
        except Exception as e:
            logger.error(f"Deleting payment method failed: {str(e)}")
            messages.error(request, _('Failed to delete payment method. Please try again.'))
            return redirect('billing:payment_methods')


class InvoiceListView(LoginRequiredMixin, ListView):
    """View for listing invoices."""
    model = Invoice
    template_name = 'billing/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        organization = self.request.user.organization
        try:
            subscription = organization.subscription
            return Invoice.objects.filter(subscription=subscription).order_by('-created_date')
        except Subscription.DoesNotExist:
            return Invoice.objects.none()


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """View for displaying invoice details."""
    model = Invoice
    template_name = 'billing/invoice_detail.html'
    context_object_name = 'invoice'
    pk_url_kwarg = 'invoice_id'
    
    def get_queryset(self):
        organization = self.request.user.organization
        try:
            subscription = organization.subscription
            return Invoice.objects.filter(subscription=subscription)
        except Subscription.DoesNotExist:
            return Invoice.objects.none()


class InvoiceDownloadView(LoginRequiredMixin, View):
    """Handle invoice PDF download."""
    
    def get(self, request, invoice_id):
        try:
            organization = request.user.organization
            subscription = organization.subscription
            invoice = get_object_or_404(Invoice, id=invoice_id, subscription=subscription)
            
            if invoice.invoice_pdf_url:
                return redirect(invoice.invoice_pdf_url)
            else:
                messages.error(request, _('Invoice PDF not available.'))
                return redirect('billing:invoice_detail', invoice_id=invoice_id)
                
        except Subscription.DoesNotExist:
            raise Http404("Invoice not found")
        except Exception as e:
            logger.error(f"Invoice download failed: {str(e)}")
            messages.error(request, _('Failed to download invoice.'))
            return redirect('billing:invoice_list')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Handle Stripe webhooks."""
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            logger.error("Invalid payload in Stripe webhook")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in Stripe webhook")
            return HttpResponse(status=400)
        
        # Handle the event
        try:
            stripe_client = StripeClient()
            stripe_client.handle_webhook_event(event)
            
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {str(e)}")
            return HttpResponse(status=500)
