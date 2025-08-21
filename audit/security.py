"""
Security utilities and monitoring for the repricing platform.
"""

import hashlib
import secrets
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
import logging

from .models import SecurityEvent, ThreatIntelligence

logger = logging.getLogger(__name__)

User = get_user_model()


class SecurityMonitor:
    """
    Security monitoring and threat detection service.
    """
    
    def __init__(self):
        self.threat_indicators = {
            'suspicious_ips': set(),
            'known_bad_user_agents': set(),
            'attack_patterns': []
        }
        self.load_threat_intelligence()
    
    def load_threat_intelligence(self):
        """Load threat intelligence data."""
        try:
            # Load from database
            intel = ThreatIntelligence.objects.filter(is_active=True)
            
            for item in intel:
                if item.indicator_type == 'ip_address':
                    self.threat_indicators['suspicious_ips'].add(item.indicator_value)
                elif item.indicator_type == 'user_agent':
                    self.threat_indicators['known_bad_user_agents'].add(item.indicator_value)
                elif item.indicator_type == 'attack_pattern':
                    self.threat_indicators['attack_patterns'].append(item.indicator_value)
                    
        except Exception as e:
            logger.error(f"Failed to load threat intelligence: {str(e)}")
    
    def analyze_request(self, request, response) -> List[Dict[str, Any]]:
        """
        Analyze a request for security threats.
        
        Returns list of security findings.
        """
        findings = []
        
        # Check IP reputation
        ip_findings = self.check_ip_reputation(request)
        findings.extend(ip_findings)
        
        # Check user agent
        ua_findings = self.check_user_agent(request)
        findings.extend(ua_findings)
        
        # Check for attack patterns
        attack_findings = self.check_attack_patterns(request)
        findings.extend(attack_findings)
        
        # Check for brute force attempts
        brute_force_findings = self.check_brute_force(request, response)
        findings.extend(brute_force_findings)
        
        # Check for data exfiltration
        exfiltration_findings = self.check_data_exfiltration(request, response)
        findings.extend(exfiltration_findings)
        
        return findings
    
    def check_ip_reputation(self, request) -> List[Dict[str, Any]]:
        """Check if request IP is from a known threat source."""
        findings = []
        
        ip_address = self.get_client_ip(request)
        
        # Check against known bad IPs
        if ip_address in self.threat_indicators['suspicious_ips']:
            findings.append({
                'type': 'suspicious_ip',
                'severity': 'high',
                'description': f'Request from known malicious IP: {ip_address}',
                'indicator': ip_address
            })
        
        # Check for Tor exit nodes (simplified check)
        if self.is_tor_exit_node(ip_address):
            findings.append({
                'type': 'tor_usage',
                'severity': 'medium',
                'description': f'Request from Tor exit node: {ip_address}',
                'indicator': ip_address
            })
        
        # Check for excessive requests from single IP
        request_count = self.get_ip_request_count(ip_address)
        if request_count > 1000:  # Threshold
            findings.append({
                'type': 'high_volume_ip',
                'severity': 'medium',
                'description': f'High volume of requests from IP: {ip_address} ({request_count} requests)',
                'indicator': ip_address
            })
        
        return findings
    
    def check_user_agent(self, request) -> List[Dict[str, Any]]:
        """Check user agent for suspicious patterns."""
        findings = []
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check against known bad user agents
        if user_agent in self.threat_indicators['known_bad_user_agents']:
            findings.append({
                'type': 'malicious_user_agent',
                'severity': 'high',
                'description': f'Known malicious user agent detected',
                'indicator': user_agent
            })
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'harvest',
            'python-requests', 'curl', 'wget', 'sqlmap'
        ]
        
        user_agent_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if pattern in user_agent_lower and not self.is_legitimate_bot(user_agent):
                findings.append({
                    'type': 'suspicious_user_agent',
                    'severity': 'medium',
                    'description': f'Suspicious user agent pattern: {pattern}',
                    'indicator': user_agent
                })
                break
        
        # Check for empty or very short user agents
        if len(user_agent) < 10:
            findings.append({
                'type': 'unusual_user_agent',
                'severity': 'low',
                'description': 'Unusually short or empty user agent',
                'indicator': user_agent
            })
        
        return findings
    
    def check_attack_patterns(self, request) -> List[Dict[str, Any]]:
        """Check for common attack patterns in request."""
        findings = []
        
        # SQL Injection patterns
        sql_patterns = [
            'union select', 'or 1=1', 'drop table', 'insert into',
            'delete from', 'update set', 'exec(', 'script>'
        ]
        
        # XSS patterns
        xss_patterns = [
            '<script', 'javascript:', 'onerror=', 'onload=',
            'alert(', 'confirm(', 'prompt('
        ]
        
        # Path traversal patterns
        traversal_patterns = [
            '../', '..\\', '/etc/passwd', '/windows/system32',
            'boot.ini', '.htaccess'
        ]
        
        # Check URL path
        path = request.path.lower()
        query = request.META.get('QUERY_STRING', '').lower()
        
        # Combine all request data for checking
        request_data = f"{path} {query}"
        
        if hasattr(request, 'body'):
            try:
                body = request.body.decode('utf-8', errors='ignore').lower()
                request_data += f" {body}"
            except:
                pass
        
        # Check for SQL injection
        for pattern in sql_patterns:
            if pattern in request_data:
                findings.append({
                    'type': 'sql_injection_attempt',
                    'severity': 'high',
                    'description': f'SQL injection pattern detected: {pattern}',
                    'indicator': pattern
                })
        
        # Check for XSS
        for pattern in xss_patterns:
            if pattern in request_data:
                findings.append({
                    'type': 'xss_attempt',
                    'severity': 'high',
                    'description': f'XSS pattern detected: {pattern}',
                    'indicator': pattern
                })
        
        # Check for path traversal
        for pattern in traversal_patterns:
            if pattern in request_data:
                findings.append({
                    'type': 'path_traversal_attempt',
                    'severity': 'high',
                    'description': f'Path traversal pattern detected: {pattern}',
                    'indicator': pattern
                })
        
        return findings
    
    def check_brute_force(self, request, response) -> List[Dict[str, Any]]:
        """Check for brute force attack patterns."""
        findings = []
        
        # Check for failed login attempts
        if (request.path.startswith('/accounts/login/') and 
            request.method == 'POST' and 
            response.status_code in [400, 401, 403]):
            
            ip_address = self.get_client_ip(request)
            failed_attempts = self.get_failed_login_count(ip_address)
            
            if failed_attempts > 5:  # Threshold
                findings.append({
                    'type': 'brute_force_login',
                    'severity': 'high',
                    'description': f'Multiple failed login attempts from IP: {ip_address} ({failed_attempts} attempts)',
                    'indicator': ip_address
                })
        
        # Check for API brute force
        if request.path.startswith('/api/') and response.status_code == 401:
            ip_address = self.get_client_ip(request)
            api_failures = self.get_api_failure_count(ip_address)
            
            if api_failures > 20:  # Threshold
                findings.append({
                    'type': 'api_brute_force',
                    'severity': 'medium',
                    'description': f'Multiple API authentication failures from IP: {ip_address}',
                    'indicator': ip_address
                })
        
        return findings
    
    def check_data_exfiltration(self, request, response) -> List[Dict[str, Any]]:
        """Check for potential data exfiltration attempts."""
        findings = []
        
        # Large response sizes
        if hasattr(response, 'content') and len(response.content) > 1024 * 1024:  # 1MB
            findings.append({
                'type': 'large_response',
                'severity': 'medium',
                'description': f'Large response size: {len(response.content)} bytes',
                'indicator': str(len(response.content))
            })
        
        # Multiple rapid requests for data endpoints
        if request.path.startswith('/api/') and request.method == 'GET':
            ip_address = self.get_client_ip(request)
            api_requests = self.get_api_request_count(ip_address)
            
            if api_requests > 100:  # Threshold per hour
                findings.append({
                    'type': 'high_volume_api_access',
                    'severity': 'medium',
                    'description': f'High volume API access from IP: {ip_address}',
                    'indicator': ip_address
                })
        
        return findings
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_tor_exit_node(self, ip_address):
        """Check if IP is a Tor exit node (simplified)."""
        # In production, you would use a real Tor exit node list
        return False
    
    def is_legitimate_bot(self, user_agent):
        """Check if user agent belongs to a legitimate bot."""
        legitimate_bots = [
            'Googlebot', 'Bingbot', 'Slurp', 'DuckDuckBot',
            'Baiduspider', 'YandexBot', 'facebookexternalhit'
        ]
        
        for bot in legitimate_bots:
            if bot.lower() in user_agent.lower():
                return True
        
        return False
    
    def get_ip_request_count(self, ip_address):
        """Get request count for IP address in the last hour."""
        cache_key = f"ip_requests_{ip_address}"
        return cache.get(cache_key, 0)
    
    def get_failed_login_count(self, ip_address):
        """Get failed login count for IP address in the last hour."""
        cache_key = f"failed_logins_{ip_address}"
        return cache.get(cache_key, 0)
    
    def get_api_failure_count(self, ip_address):
        """Get API failure count for IP address in the last hour."""
        cache_key = f"api_failures_{ip_address}"
        return cache.get(cache_key, 0)
    
    def get_api_request_count(self, ip_address):
        """Get API request count for IP address in the last hour."""
        cache_key = f"api_requests_{ip_address}"
        return cache.get(cache_key, 0)


class CredentialSecurity:
    """
    Utilities for secure credential handling.
    """
    
    @staticmethod
    def generate_api_key(length=32):
        """Generate a secure API key."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_api_key(api_key):
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key, hashed_key):
        """Verify an API key against its hash."""
        return hashlib.sha256(api_key.encode()).hexdigest() == hashed_key
    
    @staticmethod
    def generate_webhook_secret(length=32):
        """Generate a webhook secret for signature verification."""
        return secrets.token_hex(length)
    
    @staticmethod
    def encrypt_sensitive_data(data, key=None):
        """Encrypt sensitive data for storage."""
        # In production, use proper encryption like Fernet
        # This is a placeholder implementation
        return f"encrypted_{data}"
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data, key=None):
        """Decrypt sensitive data."""
        # In production, use proper decryption
        # This is a placeholder implementation
        if encrypted_data.startswith("encrypted_"):
            return encrypted_data[10:]
        return encrypted_data


class SecurityEventProcessor:
    """
    Process and respond to security events.
    """
    
    def __init__(self):
        self.alert_thresholds = {
            'high': 1,      # Alert immediately
            'medium': 5,    # Alert after 5 events
            'low': 10       # Alert after 10 events
        }
    
    def process_security_findings(self, findings, request, organization=None):
        """Process security findings and create appropriate responses."""
        for finding in findings:
            # Create security event
            self.create_security_event(finding, request, organization)
            
            # Check if we need to alert
            self.check_alert_conditions(finding, organization)
            
            # Apply automatic responses
            self.apply_automatic_responses(finding, request)
    
    def create_security_event(self, finding, request, organization):
        """Create a security event record."""
        try:
            SecurityEvent.objects.create(
                organization=organization,
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                event_type=finding['type'],
                severity=finding['severity'],
                description=finding['description'],
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                request_method=request.method,
                metadata={
                    'indicator': finding.get('indicator', ''),
                    'finding_details': finding
                }
            )
        except Exception as e:
            logger.error(f"Failed to create security event: {str(e)}")
    
    def check_alert_conditions(self, finding, organization):
        """Check if security finding should trigger an alert."""
        severity = finding['severity']
        threshold = self.alert_thresholds.get(severity, 1)
        
        # Count recent similar events
        cutoff_time = timezone.now() - timedelta(hours=1)
        similar_events = SecurityEvent.objects.filter(
            organization=organization,
            event_type=finding['type'],
            timestamp__gte=cutoff_time
        ).count()
        
        if similar_events >= threshold:
            self.send_security_alert(finding, organization, similar_events)
    
    def send_security_alert(self, finding, organization, event_count):
        """Send security alert notification."""
        # In production, this would send emails, Slack messages, etc.
        logger.warning(
            f"Security Alert: {finding['type']} - {finding['description']} "
            f"(Organization: {organization}, Events: {event_count})"
        )
    
    def apply_automatic_responses(self, finding, request):
        """Apply automatic security responses."""
        # Block high-severity threats
        if finding['severity'] == 'high':
            ip_address = self.get_client_ip(request)
            self.temporarily_block_ip(ip_address)
    
    def temporarily_block_ip(self, ip_address, duration_minutes=60):
        """Temporarily block an IP address."""
        cache_key = f"blocked_ip_{ip_address}"
        cache.set(cache_key, True, timeout=duration_minutes * 60)
        
        logger.warning(f"Temporarily blocked IP: {ip_address} for {duration_minutes} minutes")
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def check_password_strength(password):
    """
    Check password strength and return recommendations.
    """
    issues = []
    score = 0
    
    # Length check
    if len(password) < 8:
        issues.append("Password should be at least 8 characters long")
    else:
        score += 1
        
    if len(password) >= 12:
        score += 1
    
    # Character variety checks
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not has_lower:
        issues.append("Include lowercase letters")
    else:
        score += 1
        
    if not has_upper:
        issues.append("Include uppercase letters")
    else:
        score += 1
        
    if not has_digit:
        issues.append("Include numbers")
    else:
        score += 1
        
    if not has_special:
        issues.append("Include special characters")
    else:
        score += 1
    
    # Common password check (simplified)
    common_passwords = ['password', '123456', 'admin', 'login', 'welcome']
    if password.lower() in common_passwords:
        issues.append("Avoid common passwords")
        score = max(0, score - 2)
    
    # Determine strength
    if score >= 5:
        strength = "strong"
    elif score >= 3:
        strength = "medium"
    else:
        strength = "weak"
    
    return {
        'strength': strength,
        'score': score,
        'issues': issues,
        'is_acceptable': score >= 3
    }
