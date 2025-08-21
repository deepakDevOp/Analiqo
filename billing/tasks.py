"""
Celery tasks for billing and subscription management.
"""

from celery import shared_task
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_usage_metering(self, organization_id=None):
    """
    Process usage metering for billing.
    """
    from accounts.models import Organization
    from .models import Subscription, UsageRecord
    
    logger.info(f"Processing usage metering for organization: {organization_id}")
    
    try:
        # Get active subscriptions
        subscriptions = Subscription.objects.filter(
            status='active'
        )
        
        if organization_id:
            subscriptions = subscriptions.filter(organization_id=organization_id)
        
        processed_count = 0
        
        for subscription in subscriptions:
            # Calculate current period usage
            current_period_start = subscription.current_period_start
            current_period_end = subscription.current_period_end
            
            # Mock usage calculation - replace with actual logic
            api_calls = 150  # Example metric
            repricing_runs = 5  # Example metric
            
            # Create usage records
            UsageRecord.objects.create(
                organization=subscription.organization,
                subscription=subscription,
                metric_name='api_calls',
                quantity=api_calls,
                billing_period_start=current_period_start,
                billing_period_end=current_period_end,
                recorded_at=timezone.now(),
                description=f'API calls for {current_period_start.date()}'
            )
            
            UsageRecord.objects.create(
                organization=subscription.organization,
                subscription=subscription,
                metric_name='repricing_runs',
                quantity=repricing_runs,
                billing_period_start=current_period_start,
                billing_period_end=current_period_end,
                recorded_at=timezone.now(),
                description=f'Repricing runs for {current_period_start.date()}'
            )
            
            processed_count += 1
        
        logger.info(f"Usage metering processed for {processed_count} subscriptions")
        return {"status": "success", "processed": processed_count}
        
    except Exception as e:
        logger.error(f"Usage metering failed: {str(e)}")
        raise


@shared_task(bind=True)
def sync_stripe_data(self, organization_id=None):
    """
    Sync billing data with Stripe.
    """
    from .models import Subscription, Invoice
    
    logger.info(f"Syncing Stripe data for organization: {organization_id}")
    
    try:
        # TODO: Implement actual Stripe API sync
        # This would fetch invoices, payment methods, etc. from Stripe
        
        synced_count = 0
        
        # Mock sync process
        subscriptions = Subscription.objects.filter(
            stripe_subscription_id__isnull=False
        )
        
        if organization_id:
            subscriptions = subscriptions.filter(organization_id=organization_id)
        
        for subscription in subscriptions:
            # Mock: Update subscription status from Stripe
            # subscription.status = stripe_subscription.status
            # subscription.save()
            synced_count += 1
        
        logger.info(f"Stripe data synced for {synced_count} subscriptions")
        return {"status": "success", "synced": synced_count}
        
    except Exception as e:
        logger.error(f"Stripe sync failed: {str(e)}")
        raise


@shared_task(bind=True)
def generate_usage_alerts(self, organization_id=None):
    """
    Generate alerts for usage limits and billing issues.
    """
    from accounts.models import Organization
    from .models import BillingAlert, Subscription
    
    logger.info(f"Generating usage alerts for organization: {organization_id}")
    
    try:
        # Get subscriptions to check
        subscriptions = Subscription.objects.filter(status='active')
        
        if organization_id:
            subscriptions = subscriptions.filter(organization_id=organization_id)
        
        alerts_created = 0
        
        for subscription in subscriptions:
            plan = subscription.plan
            
            # Check if organization is approaching limits
            # Mock logic - replace with actual usage calculation
            current_usage = 850  # Example: 850 API calls
            plan_limit = 1000  # Example: 1000 API calls limit
            
            usage_percentage = (current_usage / plan_limit) * 100
            
            if usage_percentage > 90:
                # Create high usage alert
                alert, created = BillingAlert.objects.get_or_create(
                    organization=subscription.organization,
                    alert_type='usage_limit',
                    title='Approaching Usage Limit',
                    defaults={
                        'severity': 'high',
                        'message': f'You have used {usage_percentage:.1f}% of your plan limit.',
                        'data': {
                            'current_usage': current_usage,
                            'plan_limit': plan_limit,
                            'usage_percentage': usage_percentage
                        }
                    }
                )
                
                if created:
                    alerts_created += 1
            
            elif usage_percentage > 75:
                # Create medium usage alert
                alert, created = BillingAlert.objects.get_or_create(
                    organization=subscription.organization,
                    alert_type='usage_warning',
                    title='High Usage Warning',
                    defaults={
                        'severity': 'medium',
                        'message': f'You have used {usage_percentage:.1f}% of your plan limit.',
                        'data': {
                            'current_usage': current_usage,
                            'plan_limit': plan_limit,
                            'usage_percentage': usage_percentage
                        }
                    }
                )
                
                if created:
                    alerts_created += 1
        
        logger.info(f"Generated {alerts_created} usage alerts")
        return {"status": "success", "alerts_created": alerts_created}
        
    except Exception as e:
        logger.error(f"Usage alert generation failed: {str(e)}")
        raise


@shared_task(bind=True)
def process_failed_payments(self):
    """
    Process failed payments and update subscription statuses.
    """
    from .models import Invoice, Subscription
    
    logger.info("Processing failed payments")
    
    try:
        # Get failed invoices
        failed_invoices = Invoice.objects.filter(
            status='payment_failed'
        )
        
        processed_count = 0
        
        for invoice in failed_invoices:
            # TODO: Implement failed payment handling
            # - Send dunning emails
            # - Update subscription status
            # - Apply grace periods
            processed_count += 1
        
        logger.info(f"Processed {processed_count} failed payments")
        return {"status": "success", "processed": processed_count}
        
    except Exception as e:
        logger.error(f"Failed payment processing failed: {str(e)}")
        raise
