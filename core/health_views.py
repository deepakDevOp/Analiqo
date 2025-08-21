"""
Health check views for monitoring and load balancers.
"""

import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Basic health check endpoint.
    """
    return JsonResponse({
        "status": "healthy",
        "message": "Application is running"
    })


def liveness_check(request):
    """
    Liveness probe - basic check that the application is running.
    This should be lightweight and not depend on external services.
    """
    return JsonResponse({
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"  # Will be dynamic in real implementation
    })


def readiness_check(request):
    """
    Readiness probe - check that the application is ready to serve traffic.
    This includes checking dependencies like database and cache.
    """
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "checks": {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis cache
    try:
        cache.get("health_check_key")
        health_status["checks"]["cache"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        health_status["checks"]["cache"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Celery (if configured)
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        if stats:
            health_status["checks"]["celery"] = {"status": "healthy"}
        else:
            health_status["checks"]["celery"] = {"status": "unhealthy", "error": "No workers available"}
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        health_status["checks"]["celery"] = {"status": "unhealthy", "error": str(e)}
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=status_code)
