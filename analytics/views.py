"""
Analytics dashboard views for data visualization and reporting.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from datetime import datetime, timedelta
import json

# from .models import AnalyticsReport, Dashboard, Widget
# from accounts.models import Organization
# from catalog.models import Product, Listing
# from billing.models import Subscription


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Main analytics dashboard view."""
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not self.request.organization:
            return redirect('accounts:onboarding')
        
        # Get dashboard metrics
        context.update({
            'overview_metrics': self.get_overview_metrics(),
            'performance_charts': self.get_performance_charts(),
            'top_products': self.get_top_products(),
            'recent_activities': self.get_recent_activities(),
            'alerts': self.get_analytics_alerts(),
        })
        
        return context
    
    def get_overview_metrics(self):
        """Get high-level overview metrics."""
        org = self.request.organization
        
        # Calculate period comparisons
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Mock metrics - replace with actual calculations
        return {
            'total_products': {
                'current': 150,
                'change': '+12%',
                'trend': 'up'
            },
            'active_listings': {
                'current': 140,
                'change': '+8%',
                'trend': 'up'
            },
            'repricing_actions': {
                'current': 45,
                'change': '+25%',
                'trend': 'up'
            },
            'buy_box_win_rate': {
                'current': '68%',
                'change': '+5%',
                'trend': 'up'
            },
            'avg_margin': {
                'current': '18.5%',
                'change': '+2.1%',
                'trend': 'up'
            },
            'revenue_impact': {
                'current': '$12,450',
                'change': '+15%',
                'trend': 'up'
            }
        }
    
    def get_performance_charts(self):
        """Get data for performance charts."""
        # Mock chart data - replace with actual calculations
        return {
            'revenue_trend': {
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                'datasets': [{
                    'label': 'Revenue',
                    'data': [12000, 13500, 11800, 15200, 14100, 16800],
                    'borderColor': 'rgb(59, 130, 246)',
                    'backgroundColor': 'rgba(59, 130, 246, 0.1)'
                }]
            },
            'buy_box_performance': {
                'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                'datasets': [{
                    'label': 'Buy Box Win Rate %',
                    'data': [65, 68, 72, 75],
                    'borderColor': 'rgb(16, 185, 129)',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)'
                }]
            },
            'pricing_actions': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'datasets': [{
                    'label': 'Price Changes',
                    'data': [12, 8, 15, 10, 18, 6, 9],
                    'backgroundColor': 'rgba(245, 158, 11, 0.8)'
                }]
            }
        }
    
    def get_top_products(self):
        """Get top performing products."""
        # Mock data - replace with actual queries
        return [
            {
                'name': 'Premium Wireless Headphones',
                'sku': 'WH-1000XM4',
                'revenue': 2450,
                'margin': '22%',
                'buy_box_rate': '85%',
                'repricing_count': 12
            },
            {
                'name': 'Smart Fitness Watch',
                'sku': 'SW-FIT-PRO',
                'revenue': 1890,
                'margin': '18%',
                'buy_box_rate': '72%',
                'repricing_count': 8
            },
            {
                'name': 'Bluetooth Speaker',
                'sku': 'BT-SPKR-X1',
                'revenue': 1650,
                'margin': '25%',
                'buy_box_rate': '68%',
                'repricing_count': 15
            }
        ]
    
    def get_recent_activities(self):
        """Get recent repricing activities."""
        # Mock data - replace with actual activity logs
        return [
            {
                'timestamp': timezone.now() - timedelta(minutes=15),
                'action': 'Price Decreased',
                'product': 'Wireless Mouse',
                'old_price': 29.99,
                'new_price': 27.99,
                'reason': 'Competitor undercut'
            },
            {
                'timestamp': timezone.now() - timedelta(hours=2),
                'action': 'Price Increased',
                'product': 'USB Cable',
                'old_price': 12.99,
                'new_price': 14.99,
                'reason': 'Demand surge detected'
            },
            {
                'timestamp': timezone.now() - timedelta(hours=4),
                'action': 'Price Optimized',
                'product': 'Phone Case',
                'old_price': 19.99,
                'new_price': 21.99,
                'reason': 'Margin optimization'
            }
        ]
    
    def get_analytics_alerts(self):
        """Get analytics alerts and notifications."""
        # Mock alerts - replace with actual alert system
        return [
            {
                'type': 'warning',
                'title': 'High Competition',
                'message': '5 products facing increased competition',
                'timestamp': timezone.now() - timedelta(hours=1)
            },
            {
                'type': 'success',
                'title': 'Revenue Goal',
                'message': 'Monthly revenue target achieved',
                'timestamp': timezone.now() - timedelta(hours=6)
            },
            {
                'type': 'info',
                'title': 'Market Trend',
                'message': 'Electronics category showing 15% growth',
                'timestamp': timezone.now() - timedelta(days=1)
            }
        ]


class AnalyticsAPIView(LoginRequiredMixin, TemplateView):
    """API endpoints for analytics data."""
    
    def get(self, request, *args, **kwargs):
        chart_type = request.GET.get('chart')
        
        if chart_type == 'revenue_trend':
            return JsonResponse(self.get_revenue_trend_data())
        elif chart_type == 'buy_box_performance':
            return JsonResponse(self.get_buy_box_data())
        elif chart_type == 'category_performance':
            return JsonResponse(self.get_category_data())
        elif chart_type == 'competitor_analysis':
            return JsonResponse(self.get_competitor_data())
        
        return JsonResponse({'error': 'Invalid chart type'}, status=400)
    
    def get_revenue_trend_data(self):
        """Get revenue trend data for charts."""
        # Mock time-series data
        end_date = timezone.now().date()
        dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, -1, -1)]
        
        # Mock revenue data
        import random
        base_revenue = 15000
        revenues = [base_revenue + random.randint(-2000, 3000) for _ in dates]
        
        return {
            'labels': dates,
            'datasets': [{
                'label': 'Daily Revenue',
                'data': revenues,
                'borderColor': 'rgb(59, 130, 246)',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'tension': 0.4
            }]
        }
    
    def get_buy_box_data(self):
        """Get buy box performance data."""
        return {
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            'datasets': [{
                'label': 'Buy Box Win Rate %',
                'data': [65, 68, 72, 75],
                'borderColor': 'rgb(16, 185, 129)',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)'
            }, {
                'label': 'Competition Level',
                'data': [45, 48, 52, 49],
                'borderColor': 'rgb(239, 68, 68)',
                'backgroundColor': 'rgba(239, 68, 68, 0.1)'
            }]
        }
    
    def get_category_data(self):
        """Get category performance data."""
        return {
            'labels': ['Electronics', 'Home & Garden', 'Sports', 'Books', 'Clothing'],
            'datasets': [{
                'label': 'Revenue Distribution',
                'data': [35, 25, 20, 12, 8],
                'backgroundColor': [
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(139, 92, 246, 0.8)'
                ]
            }]
        }
    
    def get_competitor_data(self):
        """Get competitor analysis data."""
        return {
            'labels': ['Product A', 'Product B', 'Product C', 'Product D', 'Product E'],
            'datasets': [{
                'label': 'Our Price',
                'data': [29.99, 45.50, 12.99, 89.99, 24.95],
                'backgroundColor': 'rgba(59, 130, 246, 0.8)'
            }, {
                'label': 'Competitor Avg',
                'data': [31.50, 43.99, 14.50, 92.50, 26.99],
                'backgroundColor': 'rgba(239, 68, 68, 0.8)'
            }]
        }


class ReportsView(LoginRequiredMixin, TemplateView):
    """Analytics reports view."""
    template_name = 'analytics/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context.update({
            'recent_reports': self.get_recent_reports(),
            'report_types': self.get_report_types(),
        })
        
        return context
    
    def get_recent_reports(self):
        """Get list of recent reports."""
        # Mock reports - replace with actual report queries
        return [
            {
                'id': 1,
                'name': 'Weekly Performance Summary',
                'type': 'performance',
                'created_at': timezone.now() - timedelta(days=1),
                'status': 'completed',
                'download_url': '/analytics/reports/1/download/'
            },
            {
                'id': 2,
                'name': 'Competitor Analysis Report',
                'type': 'competition',
                'created_at': timezone.now() - timedelta(days=3),
                'status': 'completed',
                'download_url': '/analytics/reports/2/download/'
            },
            {
                'id': 3,
                'name': 'Monthly Revenue Analysis',
                'type': 'revenue',
                'created_at': timezone.now() - timedelta(days=7),
                'status': 'completed',
                'download_url': '/analytics/reports/3/download/'
            }
        ]
    
    def get_report_types(self):
        """Get available report types."""
        return [
            {
                'id': 'performance',
                'name': 'Performance Report',
                'description': 'Overall pricing and buy box performance metrics',
                'icon': 'chart-line'
            },
            {
                'id': 'competition',
                'name': 'Competitor Analysis',
                'description': 'Detailed analysis of competitor pricing strategies',
                'icon': 'users'
            },
            {
                'id': 'revenue',
                'name': 'Revenue Impact',
                'description': 'Revenue impact analysis from repricing actions',
                'icon': 'dollar-sign'
            },
            {
                'id': 'custom',
                'name': 'Custom Report',
                'description': 'Build custom reports with specific metrics',
                'icon': 'settings'
            }
        ]
