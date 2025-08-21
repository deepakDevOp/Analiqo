"""
Stripe integration client for billing and subscription management.
"""

import stripe
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
import logging

from django.conf import settings
from django.utils import timezone as django_timezone
from .models import Plan, Subscription, Invoice, PaymentMethod, UsageRecord

logger = logging.getLogger(__name__)


class StripeClient:
    """
    Client for Stripe API integration.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Stripe client.
        
        Args:
            api_key: Stripe API key (defaults to settings)
        """
        self.api_key = api_key or getattr(settings, 'STRIPE_SECRET_KEY', None)
        if not self.api_key:
            raise ValueError("Stripe API key not configured")
        
        stripe.api_key = self.api_key
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    
    def create_customer(self, organization) -> Dict[str, Any]:
        """
        Create a Stripe customer for an organization.
        
        Args:
            organization: Organization instance
        
        Returns:
            Stripe customer object
        """
        try:
            customer_data = {
                'name': organization.name,
                'email': organization.email,
                'description': f'Organization: {organization.name}',
                'metadata': {
                    'organization_id': str(organization.id),
                    'organization_name': organization.name,
                }
            }
            
            if organization.phone:
                customer_data['phone'] = organization.phone
            
            if organization.address_line1:
                customer_data['address'] = {
                    'line1': organization.address_line1,
                    'line2': organization.address_line2 or '',
                    'city': organization.city or '',
                    'state': organization.state or '',
                    'postal_code': organization.postal_code or '',
                    'country': organization.country or 'US',
                }
            
            customer = stripe.Customer.create(**customer_data)
            logger.info(f"Created Stripe customer {customer.id} for organization {organization.id}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise
    
    def create_product(self, plan: Plan) -> Dict[str, Any]:
        """
        Create a Stripe product for a billing plan.
        
        Args:
            plan: Plan instance
        
        Returns:
            Stripe product object
        """
        try:
            product_data = {
                'name': plan.name,
                'description': plan.description,
                'metadata': {
                    'plan_id': str(plan.id),
                    'plan_name': plan.name,
                }
            }
            
            product = stripe.Product.create(**product_data)
            logger.info(f"Created Stripe product {product.id} for plan {plan.id}")
            return product
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe product: {str(e)}")
            raise
    
    def create_price(self, plan: Plan, product_id: str) -> Dict[str, Any]:
        """
        Create a Stripe price for a billing plan.
        
        Args:
            plan: Plan instance
            product_id: Stripe product ID
        
        Returns:
            Stripe price object
        """
        try:
            price_data = {
                'product': product_id,
                'unit_amount': int(plan.price * 100),  # Convert to cents
                'currency': plan.currency.lower(),
                'metadata': {
                    'plan_id': str(plan.id),
                    'plan_name': plan.name,
                }
            }
            
            # Set billing period
            if plan.billing_period == 'monthly':
                price_data['recurring'] = {'interval': 'month'}
            elif plan.billing_period == 'yearly':
                price_data['recurring'] = {'interval': 'year'}
            elif plan.billing_period == 'weekly':
                price_data['recurring'] = {'interval': 'week'}
            else:
                # One-time payment
                pass
            
            price = stripe.Price.create(**price_data)
            logger.info(f"Created Stripe price {price.id} for plan {plan.id}")
            return price
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe price: {str(e)}")
            raise
    
    def create_subscription(self, customer_id: str, price_id: str, 
                          trial_days: Optional[int] = None,
                          metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a Stripe subscription.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Trial period in days
            metadata: Additional metadata
        
        Returns:
            Stripe subscription object
        """
        try:
            subscription_data = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'metadata': metadata or {},
                'collection_method': 'charge_automatically',
                'expand': ['latest_invoice.payment_intent'],
            }
            
            if trial_days and trial_days > 0:
                subscription_data['trial_period_days'] = trial_days
            
            subscription = stripe.Subscription.create(**subscription_data)
            logger.info(f"Created Stripe subscription {subscription.id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe subscription: {str(e)}")
            raise
    
    def update_subscription(self, subscription_id: str, 
                          **kwargs) -> Dict[str, Any]:
        """
        Update a Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            **kwargs: Fields to update
        
        Returns:
            Updated Stripe subscription object
        """
        try:
            subscription = stripe.Subscription.modify(subscription_id, **kwargs)
            logger.info(f"Updated Stripe subscription {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe subscription: {str(e)}")
            raise
    
    def cancel_subscription(self, subscription_id: str, 
                          at_period_end: bool = True) -> Dict[str, Any]:
        """
        Cancel a Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Whether to cancel at period end or immediately
        
        Returns:
            Cancelled Stripe subscription object
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Cancelled Stripe subscription {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription: {str(e)}")
            raise
    
    def create_payment_method(self, customer_id: str, payment_method_id: str) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Stripe payment method ID
        
        Returns:
            Stripe payment method object
        """
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
            return payment_method
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method: {str(e)}")
            raise
    
    def set_default_payment_method(self, customer_id: str, 
                                 payment_method_id: str) -> Dict[str, Any]:
        """
        Set default payment method for a customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Stripe payment method ID
        
        Returns:
            Updated Stripe customer object
        """
        try:
            customer = stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            
            logger.info(f"Set default payment method {payment_method_id} for customer {customer_id}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to set default payment method: {str(e)}")
            raise
    
    def create_usage_record(self, subscription_item_id: str, quantity: int, 
                          timestamp: Optional[datetime] = None,
                          action: str = 'set') -> Dict[str, Any]:
        """
        Create a usage record for metered billing.
        
        Args:
            subscription_item_id: Stripe subscription item ID
            quantity: Usage quantity
            timestamp: Timestamp of usage
            action: Usage record action ('set' or 'increment')
        
        Returns:
            Stripe usage record object
        """
        try:
            usage_data = {
                'quantity': quantity,
                'action': action,
            }
            
            if timestamp:
                usage_data['timestamp'] = int(timestamp.timestamp())
            
            usage_record = stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                **usage_data
            )
            
            logger.info(f"Created usage record for subscription item {subscription_item_id}")
            return usage_record
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create usage record: {str(e)}")
            raise
    
    def get_upcoming_invoice(self, customer_id: str, 
                           subscription_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get upcoming invoice for a customer.
        
        Args:
            customer_id: Stripe customer ID
            subscription_id: Optional subscription ID
        
        Returns:
            Stripe invoice object
        """
        try:
            params = {'customer': customer_id}
            if subscription_id:
                params['subscription'] = subscription_id
            
            invoice = stripe.Invoice.upcoming(**params)
            return invoice
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get upcoming invoice: {str(e)}")
            raise
    
    def create_invoice_item(self, customer_id: str, amount: int, 
                          currency: str = 'usd', 
                          description: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create an invoice item.
        
        Args:
            customer_id: Stripe customer ID
            amount: Amount in cents
            currency: Currency code
            description: Item description
            metadata: Additional metadata
        
        Returns:
            Stripe invoice item object
        """
        try:
            invoice_item_data = {
                'customer': customer_id,
                'amount': amount,
                'currency': currency,
                'metadata': metadata or {},
            }
            
            if description:
                invoice_item_data['description'] = description
            
            invoice_item = stripe.InvoiceItem.create(**invoice_item_data)
            logger.info(f"Created invoice item for customer {customer_id}")
            return invoice_item
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create invoice item: {str(e)}")
            raise
    
    def create_invoice(self, customer_id: str, auto_advance: bool = True) -> Dict[str, Any]:
        """
        Create and optionally finalize an invoice.
        
        Args:
            customer_id: Stripe customer ID
            auto_advance: Whether to automatically finalize the invoice
        
        Returns:
            Stripe invoice object
        """
        try:
            invoice_data = {
                'customer': customer_id,
                'auto_advance': auto_advance,
                'collection_method': 'charge_automatically',
            }
            
            invoice = stripe.Invoice.create(**invoice_data)
            
            if auto_advance:
                invoice = stripe.Invoice.finalize_invoice(invoice.id)
            
            logger.info(f"Created invoice {invoice.id} for customer {customer_id}")
            return invoice
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create invoice: {str(e)}")
            raise
    
    def pay_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Pay an invoice.
        
        Args:
            invoice_id: Stripe invoice ID
        
        Returns:
            Stripe invoice object
        """
        try:
            invoice = stripe.Invoice.pay(invoice_id)
            logger.info(f"Paid invoice {invoice_id}")
            return invoice
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to pay invoice: {str(e)}")
            raise
    
    def construct_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Construct webhook event from Stripe.
        
        Args:
            payload: Request payload
            sig_header: Stripe signature header
        
        Returns:
            Stripe event object
        """
        if not self.webhook_secret:
            raise ValueError("Webhook secret not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
            
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            raise
    
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get Stripe customer."""
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get customer: {str(e)}")
            raise
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get Stripe subscription."""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription: {str(e)}")
            raise
    
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get Stripe invoice."""
        try:
            return stripe.Invoice.retrieve(invoice_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get invoice: {str(e)}")
            raise
    
    def list_invoices(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List invoices for a customer."""
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            return invoices.data
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list invoices: {str(e)}")
            raise
