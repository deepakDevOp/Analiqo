/**
 * Dashboard JavaScript functionality
 */

window.Dashboard = {
    init: function() {
        this.initMetrics();
        this.initWidgets();
        this.initRefresh();
    },

    initMetrics: function() {
        // Animate metric values on load
        const metricValues = document.querySelectorAll('.metric-value');
        metricValues.forEach(element => {
            const finalValue = parseInt(element.textContent) || 0;
            this.animateValue(element, 0, finalValue, 1000);
        });
    },

    initWidgets: function() {
        // Add loading states and error handling for widgets
        const widgets = document.querySelectorAll('.dashboard-widget');
        widgets.forEach(widget => {
            widget.addEventListener('error', this.handleWidgetError.bind(this));
        });
    },

    initRefresh: function() {
        // Add refresh functionality to widgets
        const refreshButtons = document.querySelectorAll('[data-refresh]');
        refreshButtons.forEach(button => {
            button.addEventListener('click', this.refreshWidget.bind(this));
        });
    },

    animateValue: function(element, start, end, duration) {
        const startTime = performance.now();
        const range = end - start;

        const step = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.floor(start + (range * easeOutQuart));
            
            element.textContent = currentValue.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = end.toLocaleString();
            }
        };

        requestAnimationFrame(step);
    },

    refreshWidget: function(event) {
        const button = event.target;
        const widgetId = button.dataset.refresh;
        const widget = document.querySelector(`[data-widget="${widgetId}"]`);
        
        if (!widget) return;

        this.setLoading(widget, true);
        
        // Simulate refresh (replace with actual API call)
        setTimeout(() => {
            this.setLoading(widget, false);
            this.showNotification('Widget refreshed successfully', 'success');
        }, 1000);
    },

    setLoading: function(element, loading) {
        if (loading) {
            element.classList.add('loading');
        } else {
            element.classList.remove('loading');
        }
    },

    handleWidgetError: function(event) {
        const widget = event.target.closest('.dashboard-widget');
        this.showNotification('Failed to load widget data', 'error');
        this.setLoading(widget, false);
    },

    showNotification: function(message, type = 'info') {
        // Create and show a toast notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    },

    formatNumber: function(number) {
        if (number >= 1000000) {
            return (number / 1000000).toFixed(1) + 'M';
        } else if (number >= 1000) {
            return (number / 1000).toFixed(1) + 'K';
        }
        return number.toString();
    },

    updateMetric: function(metricElement, newValue) {
        const currentValue = parseInt(metricElement.textContent.replace(/[^\d]/g, '')) || 0;
        this.animateValue(metricElement, currentValue, newValue, 800);
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.Dashboard) {
        window.Dashboard.init();
    }
});

// Handle visibility change to pause/resume auto-refresh
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Pause auto-refresh when tab is not visible
        if (window.dashboardRefreshInterval) {
            clearInterval(window.dashboardRefreshInterval);
        }
    } else {
        // Resume auto-refresh when tab becomes visible
        // This would be set up in the main template
    }
}); 