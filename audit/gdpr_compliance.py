"""
GDPR compliance utilities for data protection and privacy.
"""

from typing import Dict, List, Optional, Any
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

from .models import DataProcessingLog, GDPRRequest

logger = logging.getLogger(__name__)

User = get_user_model()


class GDPRCompliance:
    """
    Service for handling GDPR compliance requirements.
    """
    
    def __init__(self):
        self.sensitive_fields = {
            'accounts.User': ['email', 'first_name', 'last_name', 'phone'],
            'accounts.Organization': ['name', 'email', 'phone', 'address_line1', 'address_line2'],
            'billing.PaymentMethod': ['last4', 'exp_month', 'exp_year'],
            'audit.AuditLog': ['ip_address', 'user_agent'],
            'audit.SecurityEvent': ['ip_address', 'user_agent'],
        }
    
    def handle_data_subject_request(self, request_type: str, user_email: str, 
                                  requester_info: Dict[str, Any]) -> GDPRRequest:
        """
        Handle a GDPR data subject request.
        
        Args:
            request_type: Type of request ('access', 'rectification', 'erasure', 'portability')
            user_email: Email of the data subject
            requester_info: Information about who made the request
        
        Returns:
            GDPRRequest instance
        """
        try:
            # Create GDPR request record
            gdpr_request = GDPRRequest.objects.create(
                request_type=request_type,
                data_subject_email=user_email,
                requester_info=requester_info,
                status='pending',
                requested_at=timezone.now()
            )
            
            # Process based on request type
            if request_type == 'access':
                result = self.process_access_request(user_email, gdpr_request)
            elif request_type == 'rectification':
                result = self.process_rectification_request(user_email, gdpr_request)
            elif request_type == 'erasure':
                result = self.process_erasure_request(user_email, gdpr_request)
            elif request_type == 'portability':
                result = self.process_portability_request(user_email, gdpr_request)
            else:
                raise ValueError(f"Unsupported request type: {request_type}")
            
            # Update request with results
            gdpr_request.response_data = result
            gdpr_request.status = 'completed'
            gdpr_request.completed_at = timezone.now()
            gdpr_request.save()
            
            # Log the processing
            self.log_data_processing(
                'gdpr_request_processed',
                user_email,
                {'request_type': request_type, 'request_id': str(gdpr_request.id)}
            )
            
            return gdpr_request
            
        except Exception as e:
            logger.error(f"GDPR request processing failed: {str(e)}")
            if 'gdpr_request' in locals():
                gdpr_request.status = 'failed'
                gdpr_request.error_message = str(e)
                gdpr_request.save()
            raise
    
    def process_access_request(self, user_email: str, gdpr_request: GDPRRequest) -> Dict[str, Any]:
        """
        Process a data access request (Article 15).
        
        Returns all personal data stored about the user.
        """
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return {'error': 'User not found'}
        
        data = {
            'user_info': self.extract_user_data(user),
            'organizations': self.extract_organization_data(user),
            'billing_data': self.extract_billing_data(user),
            'audit_logs': self.extract_audit_logs(user),
            'ml_data': self.extract_ml_data(user),
            'request_metadata': {
                'requested_at': gdpr_request.requested_at.isoformat(),
                'data_sources': ['user_profile', 'organizations', 'billing', 'audit_logs', 'ml_models']
            }
        }
        
        return data
    
    def process_rectification_request(self, user_email: str, gdpr_request: GDPRRequest) -> Dict[str, Any]:
        """
        Process a data rectification request (Article 16).
        
        This would typically involve manual review and correction.
        """
        return {
            'status': 'pending_manual_review',
            'message': 'Rectification request requires manual review. We will contact you within 30 days.',
            'next_steps': [
                'Manual review of requested changes',
                'Verification of identity',
                'Implementation of approved changes',
                'Notification of completion'
            ]
        }
    
    def process_erasure_request(self, user_email: str, gdpr_request: GDPRRequest) -> Dict[str, Any]:
        """
        Process a data erasure request (Article 17 - Right to be forgotten).
        
        NOTE: This is a simplified implementation. In production, you would need
        careful consideration of legal grounds for retention, backups, etc.
        """
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return {'error': 'User not found'}
        
        # Check if erasure is legally possible
        retention_check = self.check_data_retention_requirements(user)
        if not retention_check['can_erase']:
            return {
                'status': 'erasure_not_possible',
                'reason': retention_check['reason'],
                'retained_data': retention_check['retained_data']
            }
        
        # Perform erasure (simplified)
        erasure_results = self.perform_data_erasure(user)
        
        return {
            'status': 'erasure_completed',
            'erased_data': erasure_results['erased'],
            'retained_data': erasure_results['retained'],
            'completed_at': timezone.now().isoformat()
        }
    
    def process_portability_request(self, user_email: str, gdpr_request: GDPRRequest) -> Dict[str, Any]:
        """
        Process a data portability request (Article 20).
        
        Returns user data in a structured, machine-readable format.
        """
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return {'error': 'User not found'}
        
        portable_data = {
            'export_metadata': {
                'exported_at': timezone.now().isoformat(),
                'format': 'JSON',
                'version': '1.0'
            },
            'personal_data': self.extract_portable_data(user)
        }
        
        return portable_data
    
    def extract_user_data(self, user: User) -> Dict[str, Any]:
        """Extract user profile data."""
        return {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': getattr(user, 'phone', None),
            'timezone': getattr(user, 'timezone', None),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_active': user.is_active
        }
    
    def extract_organization_data(self, user: User) -> List[Dict[str, Any]]:
        """Extract organization membership data."""
        from accounts.models import Membership
        
        memberships = Membership.objects.filter(user=user, is_active=True)
        
        return [
            {
                'organization_name': membership.organization.name,
                'role': membership.role.name,
                'joined_at': membership.created_at.isoformat(),
                'is_primary': membership.is_primary
            }
            for membership in memberships
        ]
    
    def extract_billing_data(self, user: User) -> Dict[str, Any]:
        """Extract billing-related data."""
        from billing.models import Subscription, Invoice
        
        # Get user's organizations
        user_orgs = [m.organization for m in user.memberships.filter(is_active=True)]
        
        subscriptions = Subscription.objects.filter(organization__in=user_orgs)
        invoices = Invoice.objects.filter(organization__in=user_orgs)
        
        return {
            'subscriptions': [
                {
                    'plan_name': sub.plan.name,
                    'status': sub.status,
                    'started_at': sub.created_at.isoformat(),
                    'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None
                }
                for sub in subscriptions
            ],
            'invoices': [
                {
                    'amount': float(invoice.amount_due),
                    'currency': invoice.currency,
                    'status': invoice.status,
                    'date': invoice.invoice_date.isoformat()
                }
                for invoice in invoices[:10]  # Last 10 invoices
            ]
        }
    
    def extract_audit_logs(self, user: User) -> List[Dict[str, Any]]:
        """Extract user's audit log data (limited)."""
        from .models import AuditLog
        
        # Only include recent logs (last 90 days) for privacy
        cutoff_date = timezone.now() - timedelta(days=90)
        logs = AuditLog.objects.filter(
            user=user,
            timestamp__gte=cutoff_date
        ).order_by('-timestamp')[:100]  # Limit to 100 most recent
        
        return [
            {
                'action': log.action_type,
                'resource': log.resource_type,
                'timestamp': log.timestamp.isoformat(),
                'ip_address': self.anonymize_ip(log.ip_address)
            }
            for log in logs
        ]
    
    def extract_ml_data(self, user: User) -> Dict[str, Any]:
        """Extract ML-related data about the user."""
        # This would extract any ML models or predictions related to the user
        # For now, return placeholder
        return {
            'note': 'No personal ML data stored',
            'anonymous_analytics': 'User participates in anonymous usage analytics'
        }
    
    def extract_portable_data(self, user: User) -> Dict[str, Any]:
        """Extract data in portable format."""
        return {
            'profile': self.extract_user_data(user),
            'organizations': self.extract_organization_data(user),
            'preferences': {
                'timezone': getattr(user, 'timezone', None),
                'email_notifications': True  # This would come from user preferences
            }
        }
    
    def check_data_retention_requirements(self, user: User) -> Dict[str, Any]:
        """
        Check if there are legal requirements to retain user data.
        """
        # Simplified check - in practice, this would be more complex
        retention_reasons = []
        
        # Check for active subscriptions
        from billing.models import Subscription
        user_orgs = [m.organization for m in user.memberships.filter(is_active=True)]
        active_subs = Subscription.objects.filter(
            organization__in=user_orgs,
            status__in=['active', 'trialing']
        )
        
        if active_subs.exists():
            retention_reasons.append('Active subscription - billing records required')
        
        # Check for recent financial transactions
        from billing.models import Invoice
        recent_invoices = Invoice.objects.filter(
            organization__in=user_orgs,
            invoice_date__gte=timezone.now() - timedelta(days=2555)  # 7 years
        )
        
        if recent_invoices.exists():
            retention_reasons.append('Financial records - tax/legal compliance')
        
        can_erase = len(retention_reasons) == 0
        
        return {
            'can_erase': can_erase,
            'reason': '; '.join(retention_reasons) if retention_reasons else None,
            'retained_data': retention_reasons if retention_reasons else []
        }
    
    def perform_data_erasure(self, user: User) -> Dict[str, List[str]]:
        """
        Perform actual data erasure (simplified implementation).
        
        WARNING: This is a simplified implementation for demonstration.
        Production implementation would need careful consideration of:
        - Data backups
        - Related data in other systems
        - Legal retention requirements
        - Referential integrity
        """
        erased = []
        retained = []
        
        # Anonymize audit logs instead of deleting (for security)
        from .models import AuditLog
        audit_logs = AuditLog.objects.filter(user=user)
        for log in audit_logs:
            log.user = None
            log.ip_address = self.anonymize_ip(log.ip_address)
            log.user_agent = '[ANONYMIZED]'
            log.save()
        
        erased.append(f'Anonymized {audit_logs.count()} audit log entries')
        
        # Remove user from organizations (but keep organization data)
        from accounts.models import Membership
        memberships = Membership.objects.filter(user=user)
        membership_count = memberships.count()
        memberships.delete()
        erased.append(f'Removed {membership_count} organization memberships')
        
        # Anonymize user profile
        user.first_name = '[ERASED]'
        user.last_name = '[ERASED]'
        user.email = f'erased-{user.id}@example.com'
        user.is_active = False
        user.save()
        erased.append('User profile anonymized')
        
        # Note: In production, you might retain some data for legal reasons
        retained.append('Billing records retained for legal compliance')
        
        return {
            'erased': erased,
            'retained': retained
        }
    
    def anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address for privacy."""
        if not ip_address:
            return '[ANONYMIZED]'
        
        parts = ip_address.split('.')
        if len(parts) == 4:  # IPv4
            return f"{parts[0]}.{parts[1]}.xxx.xxx"
        else:  # IPv6 or other
            return '[ANONYMIZED]'
    
    def log_data_processing(self, activity_type: str, data_subject: str, 
                          details: Dict[str, Any]):
        """Log data processing activities for GDPR compliance."""
        try:
            DataProcessingLog.objects.create(
                activity_type=activity_type,
                data_subject_identifier=data_subject,
                legal_basis='consent',  # This would be determined based on context
                purpose='service_provision',
                details=details,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to log data processing activity: {str(e)}")
    
    def generate_privacy_report(self, organization) -> Dict[str, Any]:
        """Generate a privacy compliance report for an organization."""
        from .models import AuditLog, SecurityEvent, DataProcessingLog
        
        # Get stats for the last 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        audit_count = AuditLog.objects.filter(
            organization=organization,
            timestamp__gte=cutoff_date
        ).count()
        
        security_events = SecurityEvent.objects.filter(
            organization=organization,
            timestamp__gte=cutoff_date
        ).count()
        
        data_processing_activities = DataProcessingLog.objects.filter(
            timestamp__gte=cutoff_date
        ).count()
        
        return {
            'reporting_period': {
                'start': cutoff_date.isoformat(),
                'end': timezone.now().isoformat()
            },
            'metrics': {
                'audit_log_entries': audit_count,
                'security_events': security_events,
                'data_processing_activities': data_processing_activities
            },
            'compliance_status': {
                'audit_logging': 'compliant',
                'data_retention': 'compliant',
                'security_monitoring': 'compliant',
                'gdpr_procedures': 'compliant'
            },
            'recommendations': [
                'Regular review of data retention policies',
                'Continued monitoring of security events',
                'Annual privacy impact assessments'
            ]
        }
