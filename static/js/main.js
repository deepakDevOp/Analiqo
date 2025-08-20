// Main JavaScript for Repricing Platform

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // CSRF token setup for AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (csrfToken) {
        // Set up CSRF for all AJAX requests
        document.addEventListener('up:request-loaded', function(event) {
            if (event.request.method !== 'GET') {
                event.request.headers['X-CSRFToken'] = csrfToken;
            }
        });
    }

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-danger)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Loading states for forms
    document.addEventListener('submit', function(event) {
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn && !submitBtn.disabled) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>' + submitBtn.textContent;
            
            // Re-enable after 10 seconds as fallback
            setTimeout(function() {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.textContent.replace(/^.*<\/span>/, '');
            }, 10000);
        }
    });

    // Auto-refresh components with Unpoly
    const autoRefreshElements = document.querySelectorAll('[data-auto-refresh]');
    autoRefreshElements.forEach(function(element) {
        const interval = parseInt(element.dataset.autoRefresh) || 30000; // Default 30 seconds
        setInterval(function() {
            up.reload(element);
        }, interval);
    });

    // Confirm dialogs for dangerous actions
    document.addEventListener('click', function(event) {
        const target = event.target.closest('[data-confirm]');
        if (target) {
            const message = target.dataset.confirm;
            if (!confirm(message)) {
                event.preventDefault();
                event.stopPropagation();
            }
        }
    });

    // Price formatting
    function formatPrice(input) {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            input.value = value.toFixed(2);
        }
    }

    document.querySelectorAll('.price-input').forEach(function(input) {
        input.addEventListener('blur', function() {
            formatPrice(this);
        });
    });

    // Percentage formatting
    function formatPercentage(input) {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            input.value = Math.max(0, Math.min(100, value)).toFixed(1);
        }
    }

    document.querySelectorAll('.percentage-input').forEach(function(input) {
        input.addEventListener('blur', function() {
            formatPercentage(this);
        });
    });

    // Real-time search with debouncing
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = function() {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    document.querySelectorAll('[data-live-search]').forEach(function(input) {
        const searchFunction = debounce(function(event) {
            const form = input.closest('form');
            if (form) {
                up.submit(form);
            }
        }, 300);

        input.addEventListener('input', searchFunction);
    });

    // Copy to clipboard functionality
    document.addEventListener('click', function(event) {
        const copyBtn = event.target.closest('[data-copy]');
        if (copyBtn) {
            event.preventDefault();
            const text = copyBtn.dataset.copy;
            navigator.clipboard.writeText(text).then(function() {
                // Show feedback
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('btn-success');
                
                setTimeout(function() {
                    copyBtn.textContent = originalText;
                    copyBtn.classList.remove('btn-success');
                }, 2000);
            });
        }
    });

    // Theme toggle
    const themeToggle = document.querySelector('#theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });

        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-bs-theme', savedTheme);
        }
    }

    // Chart helpers
    window.chartColors = {
        primary: 'rgb(0, 102, 204)',
        success: 'rgb(25, 135, 84)',
        danger: 'rgb(220, 53, 69)',
        warning: 'rgb(255, 193, 7)',
        info: 'rgb(13, 202, 240)',
        secondary: 'rgb(108, 117, 125)'
    };

    // Notification helpers
    window.showNotification = function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);

        // Auto-hide after 5 seconds
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    };

    // Form validation helpers
    window.validateForm = function(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(function(input) {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });

        return isValid;
    };

    // Number formatting helpers
    window.formatNumber = function(number, decimals = 0) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(number);
    };

    window.formatCurrency = function(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    };

    window.formatPercentage = function(value, decimals = 1) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(value / 100);
    };

    // Date formatting helpers
    window.formatDate = function(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };
        return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
    };

    window.formatDateTime = function(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
    };

    // API helpers
    window.apiCall = async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        };

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    };

    // Initialize custom components
    initializeDataTables();
    initializeCharts();
});

// DataTables initialization
function initializeDataTables() {
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(function(table) {
        // Custom DataTable initialization would go here
        // For now, we'll use simple sorting
        enableTableSorting(table);
    });
}

// Simple table sorting
function enableTableSorting(table) {
    const headers = table.querySelectorAll('th[data-sortable]');
    headers.forEach(function(header, index) {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            sortTable(table, index);
        });
    });
}

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAscending = table.dataset.sortDirection !== 'asc';
    
    rows.sort(function(a, b) {
        const aVal = a.cells[column].textContent.trim();
        const bVal = b.cells[column].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
        const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // String comparison
        return isAscending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    // Update table
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
    
    table.dataset.sortDirection = isAscending ? 'asc' : 'desc';
    
    // Update header indicators
    table.querySelectorAll('th').forEach(function(th) {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const header = table.querySelectorAll('th')[column];
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
}

// Chart initialization placeholder
function initializeCharts() {
    // Chart.js or other charting library initialization would go here
    console.log('Charts initialized');
}
