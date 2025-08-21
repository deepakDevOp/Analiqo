"""
Audit middleware for logging user actions and security events.
"""

import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from .models import AuditLog, SecurityEvent
import logging

logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to audit user actions and API calls.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request for audit logging."""
        request.audit_start_time = time.time()
        request.audit_user_ip = self.get_client_ip(request)
        request.audit_user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Skip audit for certain paths
        skip_paths = [
            '/static/',
            '/media/',
            '/health/',
            '/metrics/',
            '/favicon.ico'
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            request.skip_audit = True
        else:
            request.skip_audit = False
        
        return None
    
    def process_response(self, request, response):
        """Process response and create audit log."""
        if getattr(request, 'skip_audit', True):
            return response
        
        try:
            # Calculate processing time
            processing_time = time.time() - getattr(request, 'audit_start_time', time.time())
            
            # Create audit log
            self.create_audit_log(request, response, processing_time)
            
            # Check for security events
            self.check_security_events(request, response)
            
        except Exception as e:
            logger.error(f"Audit logging failed: {str(e)}")
        
        return response
    
    def create_audit_log(self, request, response, processing_time):
        """Create an audit log entry."""
        # Determine action type
        action_type = self.determine_action_type(request)
        
        # Get request data (sanitized)
        request_data = self.sanitize_request_data(request)
        
        # Create audit log
        AuditLog.objects.create(
            organization=getattr(request, 'organization', None),
            user=request.user if not isinstance(request.user, AnonymousUser) else None,
            action_type=action_type,
            resource_type=self.get_resource_type(request),
            resource_id=self.get_resource_id(request),
            request_method=request.method,
            request_path=request.path,
            request_data=request_data,
            response_status=response.status_code,
            ip_address=getattr(request, 'audit_user_ip', ''),
            user_agent=getattr(request, 'audit_user_agent', ''),
            processing_time_ms=int(processing_time * 1000),
            metadata={
                'content_type': response.get('Content-Type', ''),
                'content_length': len(response.content) if hasattr(response, 'content') else 0,
                'referer': request.META.get('HTTP_REFERER', ''),
            }
        )
    
    def check_security_events(self, request, response):
        """Check for potential security events."""
        # Failed login attempts
        if (request.path.startswith('/accounts/login/') and 
            request.method == 'POST' and 
            response.status_code in [400, 401, 403]):
            
            self.log_security_event(
                request, 
                'failed_login',
                'Failed login attempt',
                {'status_code': response.status_code}
            )
        
        # Suspicious API access patterns
        if (response.status_code == 429):  # Rate limited
            self.log_security_event(
                request,
                'rate_limit_exceeded',
                'Rate limit exceeded',
                {'path': request.path, 'method': request.method}
            )
        
        # Unauthorized access attempts
        if response.status_code == 403:
            self.log_security_event(
                request,
                'unauthorized_access',
                'Unauthorized access attempt',
                {'path': request.path, 'method': request.method}
            )
    
    def log_security_event(self, request, event_type, description, additional_data=None):
        """Log a security event."""
        try:
            SecurityEvent.objects.create(
                organization=getattr(request, 'organization', None),
                user=request.user if not isinstance(request.user, AnonymousUser) else None,
                event_type=event_type,
                severity='medium',
                description=description,
                ip_address=getattr(request, 'audit_user_ip', ''),
                user_agent=getattr(request, 'audit_user_agent', ''),
                request_path=request.path,
                request_method=request.method,
                metadata=additional_data or {}
            )
        except Exception as e:
            logger.error(f"Security event logging failed: {str(e)}")
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def determine_action_type(self, request):
        """Determine the action type based on request."""
        method = request.method.lower()
        path = request.path.lower()
        
        if method == 'post':
            if 'login' in path:
                return 'login'
            elif 'logout' in path:
                return 'logout'
            else:
                return 'create'
        elif method == 'put' or method == 'patch':
            return 'update'
        elif method == 'delete':
            return 'delete'
        elif method == 'get':
            return 'read'
        else:
            return 'unknown'
    
    def get_resource_type(self, request):
        """Determine resource type from URL path."""
        path_parts = request.path.strip('/').split('/')
        
        if len(path_parts) >= 1:
            # Map URL patterns to resource types
            resource_map = {
                'accounts': 'user',
                'billing': 'subscription',
                'catalog': 'product',
                'pricing': 'pricing_rule',
                'analytics': 'report',
                'credentials': 'credential',
                'integrations': 'integration'
            }
            return resource_map.get(path_parts[0], path_parts[0])
        
        return 'unknown'
    
    def get_resource_id(self, request):
        """Extract resource ID from URL if available."""
        path_parts = request.path.strip('/').split('/')
        
        # Look for UUID or numeric IDs in the path
        for part in path_parts:
            if part.isdigit() or self.is_uuid(part):
                return part
        
        return None
    
    def is_uuid(self, value):
        """Check if a string is a valid UUID."""
        try:
            import uuid
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def sanitize_request_data(self, request):
        """Sanitize request data for logging (remove sensitive fields)."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, 'body') and request.body:
                    data = json.loads(request.body.decode('utf-8'))
                else:
                    data = dict(request.POST)
                
                # Remove sensitive fields
                sensitive_fields = [
                    'password', 'password1', 'password2', 'old_password',
                    'new_password', 'confirm_password', 'token', 'secret',
                    'api_key', 'private_key', 'credit_card', 'ssn', 'social_security'
                ]
                
                for field in sensitive_fields:
                    if field in data:
                        data[field] = '[REDACTED]'
                
                return data
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {'error': 'Unable to parse request data'}
        
        return {}


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "font-src 'self' https://cdn.jsdelivr.net",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Other security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS (only for HTTPS)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}
        self.window_size = 60  # 1 minute window
        self.max_requests = 100  # Max requests per window
        super().__init__(get_response)
    
    def process_request(self, request):
        """Check rate limits for the request."""
        # Skip rate limiting for certain paths
        skip_paths = ['/static/', '/media/', '/health/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Get client identifier
        client_id = self.get_client_id(request)
        current_time = time.time()
        
        # Clean old entries
        self.cleanup_old_requests(current_time)
        
        # Check current request count
        if client_id in self.request_counts:
            if len(self.request_counts[client_id]) >= self.max_requests:
                # Rate limit exceeded
                response = HttpResponse(
                    json.dumps({'error': 'Rate limit exceeded. Please try again later.'}),
                    content_type='application/json',
                    status=429
                )
                response['Retry-After'] = str(self.window_size)
                return response
        
        # Record this request
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []
        
        self.request_counts[client_id].append(current_time)
        
        return None
    
    def get_client_id(self, request):
        """Get client identifier for rate limiting."""
        # Use IP address as client identifier
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        # If user is authenticated, use user ID
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user_{request.user.id}"
        
        return f"ip_{ip}"
    
    def cleanup_old_requests(self, current_time):
        """Remove old request records outside the time window."""
        cutoff_time = current_time - self.window_size
        
        for client_id in list(self.request_counts.keys()):
            self.request_counts[client_id] = [
                timestamp for timestamp in self.request_counts[client_id]
                if timestamp > cutoff_time
            ]
            
            # Remove empty entries
            if not self.request_counts[client_id]:
                del self.request_counts[client_id]