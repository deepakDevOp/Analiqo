"""
Celery configuration for repricing_platform project.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricing_platform.settings.dev')

app = Celery('repricing_platform')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    # Data synchronization tasks
    'sync-amazon-data': {
        'task': 'integrations.tasks.sync_amazon_data',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'integrations'}
    },
    'sync-flipkart-data': {
        'task': 'integrations.tasks.sync_flipkart_data',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'integrations'}
    },
    
    # Repricing tasks
    'run-repricing-engine': {
        'task': 'repricer.tasks.run_repricing_engine',
        'schedule': 600.0,  # Every 10 minutes
        'options': {'queue': 'repricing'}
    },
    
    # Analytics and aggregation
    'compute-analytics-aggregates': {
        'task': 'analytics.tasks.compute_daily_aggregates',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'analytics'}
    },
    
    # ML model training
    'retrain-ml-models': {
        'task': 'pricing_ml.tasks.retrain_models',
        'schedule': 86400.0,  # Daily
        'options': {'queue': 'ml'}
    },
    
    # Cleanup tasks
    'cleanup-old-logs': {
        'task': 'audit.tasks.cleanup_old_audit_logs',
        'schedule': 86400.0,  # Daily
    },
    
    # Billing tasks
    'process-usage-metering': {
        'task': 'billing.tasks.process_usage_metering',
        'schedule': 3600.0,  # Every hour
    },
    
    # Alert processing
    'process-alerts': {
        'task': 'notifications.tasks.process_pending_alerts',
        'schedule': 60.0,  # Every minute
    },
}

# Queue configuration
app.conf.task_routes = {
    # Integration tasks
    'integrations.*': {'queue': 'integrations'},
    # ML tasks
    'pricing_ml.*': {'queue': 'ml'},
    # Repricing tasks
    'repricer.*': {'queue': 'repricing'},
    # Analytics tasks
    'analytics.*': {'queue': 'analytics'},
    # Default queue for other tasks
    '*': {'queue': 'default'},
}

# Task configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
