"""
Billing services for subscription and payment management.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Plan, Subscription, Invoice, PaymentMethod, UsageRecord, BillingAlert
from .stripe_client import StripeClient
from accounts.models import Organization

logger = logging.getLogger(__name__)


class BillingService:
    """
    Service for managing billing operations.
    """
    
    def __init__(self, organization: Organization):
        self.organization = organization
        self.stripe_client = StripeClient()
    
    def create_subscription(self, plan_id: str, payment_method_id: Optional[str] = None,
                          trial_days: Optional[int] = None) -> Subscription:
        """
        Create a new subscription for the organization.
        
        Args:
            plan_id: ID of the plan to subscribe to
            payment_method_id: Stripe payment method ID (optional)
            trial_days: Trial period in days (optional)
        
        Returns:
            Created Subscription instance
        """
        try:
            with transaction.atomic():
                # Get the plan
                plan = Plan.objects.get(id=plan_id, is_active=True)
                
                # Ensure organization has a Stripe customer
                customer_id = self._ensure_stripe_customer()
                
                # Attach payment method if provided
                if payment_method_id:
                    self.stripe_client.create_payment_method(customer_id, payment_method_id)
                    self.stripe_client.set_default_payment_method(customer_id, payment_method_id)
                
                # Create Stripe subscription
                stripe_subscription = self.stripe_client.create_subscription(
                    customer_id=customer_id,
                    price_id=plan.stripe_price_id,
                    trial_days=trial_days,
                    metadata={
                        'organization_id': str(self.organization.id),
                        'plan_id': str(plan.id),
                    }
                )
                
                # Create local subscription record
                subscription = Subscription.objects.create(
                    organization=self.organization,
                    plan=plan,
                    stripe_subscription_id=stripe_subscription.id,
                    stripe_customer_id=customer_id,
                    status=stripe_subscription.status,
                    current_period_start=datetime.fromtimestamp(
                        stripe_subscription.current_period_start, tz=timezone.utc
                    ),
                    current_period_end=datetime.fromtimestamp(
                        stripe_subscription.current_period_end, tz=timezone.utc
                    ),
                    trial_start=datetime.fromtimestamp(
                        stripe_subscription.trial_start, tz=timezone.utc
                    ) if stripe_subscription.trial_start else None,
                    trial_end=datetime.fromtimestamp(
                        stripe_subscription.trial_end, tz=timezone.utc
                    ) if stripe_subscription.trial_end else None,
                )
                
                logger.info(f"Created subscription {subscription.id} for organization {self.organization.id}")
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise
    
    def change_plan(self, subscription_id: str, new_plan_id: str, 
                   prorate: bool = True) -> Subscription:
        """
        Change subscription plan.
        
        Args:
            subscription_id: Current subscription ID
            new_plan_id: New plan ID
            prorate: Whether to prorate the change
        
        Returns:
            Updated Subscription instance
        """
        try:
            with transaction.atomic():
                subscription = Subscription.objects.get(
                    id=subscription_id,
                    organization=self.organization
                )
                
                new_plan = Plan.objects.get(id=new_plan_id, is_active=True)
                
                # Update Stripe subscription
                updated_stripe_subscription = self.stripe_client.update_subscription(
                    subscription.stripe_subscription_id,
                    items=[{
                        'id': subscription.stripe_subscription_id,  # This would need the subscription item ID
                        'price': new_plan.stripe_price_id,
                    }],
                    proration_behavior='create_prorations' if prorate else 'none'
                )
                
                # Update local subscription
                subscription.plan = new_plan
                subscription.status = updated_stripe_subscription.status
                subscription.save()
                
                logger.info(f"Changed plan for subscription {subscription.id} to {new_plan.name}")
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to change plan: {str(e)}")
            raise
    
    def cancel_subscription(self, subscription_id: str, 
                          at_period_end: bool = True, 
                          reason: Optional[str] = None) -> Subscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID to cancel
            at_period_end: Whether to cancel at period end
            reason: Cancellation reason
        
        Returns:
            Updated Subscription instance
        """
        try:
            with transaction.atomic():
                subscription = Subscription.objects.get(
                    id=subscription_id,
                    organization=self.organization
                )
                
                # Cancel Stripe subscription
                cancelled_stripe_subscription = self.stripe_client.cancel_subscription(
                    subscription.stripe_subscription_id,
                    at_period_end=at_period_end
                )
                
                # Update local subscription
                subscription.status = cancelled_stripe_subscription.status
                subscription.cancelled_at = timezone.now()
                subscription.cancellation_reason = reason
                
                if not at_period_end:
                    subscription.ended_at = timezone.now()
                
                subscription.save()
                
                logger.info(f"Cancelled subscription {subscription.id}")
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            raise
    
    def record_usage(self, subscription_id: str, metric_name: str, 
                    quantity: int, timestamp: Optional[datetime] = None) -> UsageRecord:
        """
        Record usage for metered billing.
        
        Args:
            subscription_id: Subscription ID
            metric_name: Name of the metric (e.g., 'api_calls', 'repricing_runs')
            quantity: Usage quantity
            timestamp: Usage timestamp (defaults to now)
        
        Returns:
            Created UsageRecord instance
        """
        try:
            subscription = Subscription.objects.get(
                id=subscription_id,
                organization=self.organization
            )
            
            if timestamp is None:
                timestamp = timezone.now()
            
            # Create usage record
            usage_record = UsageRecord.objects.create(
                organization=self.organization,
                subscription=subscription,
                metric_name=metric_name,
                quantity=quantity,
                billing_period_start=subscription.current_period_start,
                billing_period_end=subscription.current_period_end,
                recorded_at=timestamp,
                description=f"{metric_name} usage for {timestamp.date()}"
            )
            
            # If plan has metered pricing, report to Stripe
            if subscription.plan.pricing_type == 'metered':
                # This would require subscription item ID for the specific metric
                # For simplicity, we'll skip the Stripe reporting here
                pass
            
            # Check usage limits and create alerts if needed
            self._check_usage_limits(subscription, metric_name)
            
            logger.info(f"Recorded usage: {quantity} {metric_name} for subscription {subscription.id}")
            return usage_record
            
        except Exception as e:
            logger.error(f"Failed to record usage: {str(e)}")
            raise
    
    def get_usage_summary(self, subscription_id: str, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get usage summary for a subscription.
        
        Args:
            subscription_id: Subscription ID
            start_date: Start date for summary
            end_date: End date for summary
        
        Returns:
            Usage summary dictionary
        """
        try:
            subscription = Subscription.objects.get(
                id=subscription_id,
                organization=self.organization
            )
            
            if start_date is None:
                start_date = subscription.current_period_start
            if end_date is None:
                end_date = subscription.current_period_end
            
            # Get usage records
            usage_records = UsageRecord.objects.filter(
                subscription=subscription,
                recorded_at__gte=start_date,
                recorded_at__lte=end_date
            )
            
            # Aggregate by metric
            usage_summary = {}
            for record in usage_records:
                metric = record.metric_name
                if metric not in usage_summary:
                    usage_summary[metric] = {
                        'total_quantity': 0,
                        'record_count': 0,
                        'last_recorded': None
                    }
                
                usage_summary[metric]['total_quantity'] += record.quantity
                usage_summary[metric]['record_count'] += 1
                
                if (usage_summary[metric]['last_recorded'] is None or 
                    record.recorded_at > usage_summary[metric]['last_recorded']):
                    usage_summary[metric]['last_recorded'] = record.recorded_at
            
            return {
                'subscription_id': subscription_id,
                'period_start': start_date,
                'period_end': end_date,
                'metrics': usage_summary,
                'total_records': usage_records.count()
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage summary: {str(e)}")
            raise
    
    def create_one_time_charge(self, amount: Decimal, description: str,
                             currency: str = 'USD') -> Invoice:
        """
        Create a one-time charge for the organization.
        
        Args:
            amount: Charge amount
            description: Charge description
            currency: Currency code
        
        Returns:
            Created Invoice instance
        """
        try:
            with transaction.atomic():
                customer_id = self._ensure_stripe_customer()
                
                # Create invoice item
                self.stripe_client.create_invoice_item(
                    customer_id=customer_id,
                    amount=int(amount * 100),  # Convert to cents
                    currency=currency.lower(),
                    description=description,
                    metadata={
                        'organization_id': str(self.organization.id),
                        'charge_type': 'one_time'
                    }
                )
                
                # Create and finalize invoice
                stripe_invoice = self.stripe_client.create_invoice(
                    customer_id=customer_id,
                    auto_advance=True
                )
                
                # Create local invoice record
                invoice = Invoice.objects.create(
                    organization=self.organization,
                    stripe_invoice_id=stripe_invoice.id,
                    stripe_customer_id=customer_id,
                    amount_due=Decimal(stripe_invoice.amount_due) / 100,
                    amount_paid=Decimal(stripe_invoice.amount_paid) / 100,
                    currency=stripe_invoice.currency.upper(),
                    status=stripe_invoice.status,
                    invoice_date=datetime.fromtimestamp(
                        stripe_invoice.created, tz=timezone.utc
                    ),
                    due_date=datetime.fromtimestamp(
                        stripe_invoice.due_date, tz=timezone.utc
                    ) if stripe_invoice.due_date else None,
                    description=description
                )
                
                logger.info(f"Created one-time charge {invoice.id} for {amount} {currency}")
                return invoice
                
        except Exception as e:
            logger.error(f"Failed to create one-time charge: {str(e)}")
            raise
    
    def get_billing_history(self, limit: int = 10) -> List[Invoice]:
        """
        Get billing history for the organization.
        
        Args:
            limit: Maximum number of invoices to return
        
        Returns:
            List of Invoice instances
        """
        return Invoice.objects.filter(
            organization=self.organization
        ).order_by('-invoice_date')[:limit]
    
    def get_current_subscription(self) -> Optional[Subscription]:
        """
        Get the current active subscription for the organization.
        
        Returns:
            Current Subscription instance or None
        """
        return Subscription.objects.filter(
            organization=self.organization,
            status__in=['active', 'trialing']
        ).first()
    
    def sync_with_stripe(self) -> Dict[str, int]:
        """
        Sync local billing data with Stripe.
        
        Returns:
            Dictionary with sync results
        """
        synced_count = {
            'subscriptions': 0,
            'invoices': 0,
            'payment_methods': 0
        }
        
        try:
            # Sync subscriptions
            for subscription in Subscription.objects.filter(organization=self.organization):
                try:
                    stripe_subscription = self.stripe_client.get_subscription(
                        subscription.stripe_subscription_id
                    )
                    
                    # Update local data
                    subscription.status = stripe_subscription.status
                    subscription.current_period_start = datetime.fromtimestamp(
                        stripe_subscription.current_period_start, tz=timezone.utc
                    )
                    subscription.current_period_end = datetime.fromtimestamp(
                        stripe_subscription.current_period_end, tz=timezone.utc
                    )
                    subscription.save()
                    
                    synced_count['subscriptions'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync subscription {subscription.id}: {str(e)}")
            
            # Sync invoices
            customer_id = self.organization.stripe_customer_id
            if customer_id:
                stripe_invoices = self.stripe_client.list_invoices(customer_id, limit=50)
                
                for stripe_invoice in stripe_invoices:
                    invoice, created = Invoice.objects.get_or_create(
                        stripe_invoice_id=stripe_invoice.id,
                        defaults={
                            'organization': self.organization,
                            'stripe_customer_id': customer_id,
                            'amount_due': Decimal(stripe_invoice.amount_due) / 100,
                            'amount_paid': Decimal(stripe_invoice.amount_paid) / 100,
                            'currency': stripe_invoice.currency.upper(),
                            'status': stripe_invoice.status,
                            'invoice_date': datetime.fromtimestamp(
                                stripe_invoice.created, tz=timezone.utc
                            ),
                            'due_date': datetime.fromtimestamp(
                                stripe_invoice.due_date, tz=timezone.utc
                            ) if stripe_invoice.due_date else None,
                        }
                    )
                    
                    if not created:
                        # Update existing invoice
                        invoice.status = stripe_invoice.status
                        invoice.amount_paid = Decimal(stripe_invoice.amount_paid) / 100
                        invoice.save()
                    
                    synced_count['invoices'] += 1
            
            logger.info(f"Sync completed: {synced_count}")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync with Stripe: {str(e)}")
            raise
    
    def _ensure_stripe_customer(self) -> str:
        """
        Ensure organization has a Stripe customer and return customer ID.
        
        Returns:
            Stripe customer ID
        """
        if self.organization.stripe_customer_id:
            return self.organization.stripe_customer_id
        
        # Create Stripe customer
        customer = self.stripe_client.create_customer(self.organization)
        
        # Update organization
        self.organization.stripe_customer_id = customer.id
        self.organization.save()
        
        return customer.id
    
    def _check_usage_limits(self, subscription: Subscription, metric_name: str):
        """
        Check usage limits and create alerts if necessary.
        
        Args:
            subscription: Subscription instance
            metric_name: Metric name to check
        """
        # Get plan limits
        plan_limits = subscription.plan.features.get('limits', {})
        metric_limit = plan_limits.get(metric_name)
        
        if not metric_limit:
            return  # No limit configured
        
        # Calculate current usage
        current_usage = UsageRecord.objects.filter(
            subscription=subscription,
            metric_name=metric_name,
            billing_period_start=subscription.current_period_start,
            billing_period_end=subscription.current_period_end
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        usage_percentage = (current_usage / metric_limit) * 100
        
        # Create alerts at different thresholds
        if usage_percentage >= 90:
            self._create_usage_alert(
                subscription, metric_name, current_usage, metric_limit,
                'high', 'Approaching usage limit'
            )
        elif usage_percentage >= 75:
            self._create_usage_alert(
                subscription, metric_name, current_usage, metric_limit,
                'medium', 'High usage warning'
            )
    
    def _create_usage_alert(self, subscription: Subscription, metric_name: str,
                          current_usage: int, limit: int, severity: str, title: str):
        """
        Create a usage alert.
        
        Args:
            subscription: Subscription instance
            metric_name: Metric name
            current_usage: Current usage amount
            limit: Usage limit
            severity: Alert severity
            title: Alert title
        """
        usage_percentage = (current_usage / limit) * 100
        
        BillingAlert.objects.get_or_create(
            organization=self.organization,
            alert_type='usage_limit',
            title=title,
            defaults={
                'severity': severity,
                'message': f'You have used {current_usage:,} of {limit:,} {metric_name} ({usage_percentage:.1f}%)',
                'data': {
                    'metric_name': metric_name,
                    'current_usage': current_usage,
                    'limit': limit,
                    'usage_percentage': usage_percentage,
                    'subscription_id': str(subscription.id)
                }
            }
        )
