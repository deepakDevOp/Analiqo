"""
Audit middleware for automatic logging of user activities.
"""

import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog, SecurityEvent

User = get_user_model()


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log user activities for audit trails.
    """
    
    # Sensitive fields to exclude from logging
    SENSITIVE_FIELDS = {
        'password', 'password1', 'password2', 'old_password', 'new_password',
        'csrfmiddlewaretoken', 'api_key', 'secret_key', 'access_token',
        'refresh_token', 'encrypted_data'
    }
    
    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {
        '/health/', '/metrics/', '/static/', '/media/', '/admin/jsi18n/',
        '/api/schema/', '/__debug__/'
    }
    
    # Actions that should be audited
    AUDIT_ACTIONS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def __call__(self, request):
        # Store request start time
        request._audit_start_time = time.time()
        
        # Pre-process request data
        self._prepare_audit_data(request)
        
        response = self.get_response(request)
        
        # Post-process and log if needed
        self._process_audit_log(request, response)
        
        return response
    
    def _prepare_audit_data(self, request):
        """Prepare audit data from the request."""
        request._audit_data = {
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'request_path': request.path,
            'request_method': request.method,
            'session_key': request.session.session_key if hasattr(request, 'session') else '',
        }
        
        # Store request data for POST/PUT/PATCH requests
        if request.method in self.AUDIT_ACTIONS:
            request._audit_request_data = self._sanitize_data(
                getattr(request, request.method, {})
            )
    
    def _process_audit_log(self, request, response):
        """Process and create audit log entries."""
        # Skip if path is excluded
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return
        
        # Skip if not an action that needs auditing
        if request.method not in self.AUDIT_ACTIONS and response.status_code != 200:
            return
        
        # Skip if no user (unless it's a security-relevant event)
        if not request.user.is_authenticated and response.status_code < 400:
            return
        
        # Detect security events
        self._check_security_events(request, response)
        
        # Create audit log for significant actions
        if self._should_audit(request, response):
            self._create_audit_log(request, response)
    
    def _should_audit(self, request, response):
        """Determine if this request should be audited."""
        # Always audit authentication events
        if 'login' in request.path or 'logout' in request.path:
            return True
        
        # Audit failed requests
        if response.status_code >= 400:
            return True
        
        # Audit state-changing operations
        if request.method in self.AUDIT_ACTIONS:
            return True
        
        # Audit data exports
        if 'export' in request.path:
            return True
        
        return False
    
    def _create_audit_log(self, request, response):
        """Create an audit log entry."""
        try:
            # Determine action type
            action = self._determine_action(request, response)
            
            # Get resource information
            resource_type, resource_id = self._get_resource_info(request)
            
            # Determine severity
            severity = self._determine_severity(request, response)
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                organization=getattr(request, 'organization', None),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                severity=severity,
                message=self._generate_message(request, response, action),
                metadata={
                    'response_status': response.status_code,
                    'response_time_ms': int((time.time() - request._audit_start_time) * 1000),
                    'request_data': getattr(request, '_audit_request_data', {}),
                },
                is_security_event=response.status_code >= 400,
                is_gdpr_relevant=self._is_gdpr_relevant(request),
                is_financial_data=self._is_financial_data(request),
                **request._audit_data
            )
        except Exception as e:
            # Don't let audit logging break the application
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log: {e}")
    
    def _check_security_events(self, request, response):
        """Check for and log security events."""
        # Failed login attempts
        if (request.path.endswith('/login/') and 
            request.method == 'POST' and 
            response.status_code >= 400):
            self._create_security_event(
                request,
                'login_failure',
                'Failed Login Attempt',
                f"Failed login attempt from {self._get_client_ip(request)}",
                'medium'
            )
        
        # Permission violations
        if response.status_code == 403:
            self._create_security_event(
                request,
                'permission_violation',
                'Permission Denied',
                f"User attempted to access restricted resource: {request.path}",
                'medium'
            )
        
        # Suspicious 404s (potential reconnaissance)
        if (response.status_code == 404 and 
            any(suspicious in request.path.lower() for suspicious in 
                ['admin', 'config', 'backup', '.env', 'wp-admin'])):
            self._create_security_event(
                request,
                'suspicious_activity',
                'Suspicious 404 Request',
                f"Potential reconnaissance attempt: {request.path}",
                'low'
            )
    
    def _create_security_event(self, request, event_type, title, description, severity):
        """Create a security event."""
        try:
            SecurityEvent.objects.create(
                event_type=event_type,
                severity=severity,
                user=request.user if request.user.is_authenticated else None,
                organization=getattr(request, 'organization', None),
                title=title,
                description=description,
                details={
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create security event: {e}")
    
    def _determine_action(self, request, response):
        """Determine the audit action type."""
        if 'login' in request.path:
            return 'login'
        elif 'logout' in request.path:
            return 'logout'
        elif 'export' in request.path:
            return 'export'
        elif request.method == 'POST':
            return 'create'
        elif request.method in ['PUT', 'PATCH']:
            return 'update'
        elif request.method == 'DELETE':
            return 'delete'
        else:
            return 'read'
    
    def _get_resource_info(self, request):
        """Extract resource type and ID from request."""
        path_parts = [part for part in request.path.split('/') if part]
        
        if len(path_parts) >= 1:
            resource_type = path_parts[0]
            resource_id = path_parts[1] if len(path_parts) > 1 else ''
            return resource_type, resource_id
        
        return 'unknown', ''
    
    def _determine_severity(self, request, response):
        """Determine the severity of the audit event."""
        if response.status_code >= 500:
            return 'critical'
        elif response.status_code >= 400:
            return 'high'
        elif request.method in ['DELETE', 'PUT', 'PATCH']:
            return 'medium'
        else:
            return 'low'
    
    def _generate_message(self, request, response, action):
        """Generate a human-readable audit message."""
        user_info = f"{request.user.email}" if request.user.is_authenticated else "Anonymous"
        return f"{user_info} performed {action} on {request.path} (Status: {response.status_code})"
    
    def _is_gdpr_relevant(self, request):
        """Check if the request involves GDPR-relevant data."""
        gdpr_paths = ['users', 'profile', 'personal', 'export', 'delete']
        return any(path in request.path.lower() for path in gdpr_paths)
    
    def _is_financial_data(self, request):
        """Check if the request involves financial data."""
        financial_paths = ['billing', 'payment', 'invoice', 'subscription']
        return any(path in request.path.lower() for path in financial_paths)
    
    def _get_client_ip(self, request):
        """Get the client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def _sanitize_data(self, data):
        """Remove sensitive data from logged information."""
        if isinstance(data, dict):
            return {
                key: '[REDACTED]' if key.lower() in self.SENSITIVE_FIELDS else value
                for key, value in data.items()
            }
        return data
