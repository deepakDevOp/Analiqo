"""
Pytest configuration and fixtures for the repricing platform tests.
"""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Organization, Role, Membership
from billing.models import Plan, Subscription
from pricing_rules.models import PricingStrategy, RuleSet
from catalog.models import Product, Listing
import uuid

User = get_user_model()


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def user():
    """Test user."""
    return User.objects.create_user(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        password='testpass123'
    )


@pytest.fixture
def superuser():
    """Test superuser."""
    return User.objects.create_superuser(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        password='adminpass123'
    )


@pytest.fixture
def organization():
    """Test organization."""
    return Organization.objects.create(
        name='Test Organization',
        email='org@example.com',
        timezone='UTC',
        currency='USD'
    )


@pytest.fixture
def owner_role():
    """Owner role."""
    return Role.objects.create(
        name='Owner',
        description='Organization owner',
        permissions=['*'],
        is_system_role=True
    )


@pytest.fixture
def member_role():
    """Member role."""
    return Role.objects.create(
        name='Member',
        description='Organization member',
        permissions=['view_products', 'manage_products'],
        is_system_role=True
    )


@pytest.fixture
def membership(user, organization, owner_role):
    """Test membership."""
    return Membership.objects.create(
        user=user,
        organization=organization,
        role=owner_role,
        is_active=True,
        is_primary=True
    )


@pytest.fixture
def authenticated_client(client, user, membership):
    """Authenticated client with organization context."""
    client.force_login(user)
    session = client.session
    session['current_organization_id'] = str(membership.organization.id)
    session.save()
    return client


@pytest.fixture
def plan():
    """Test billing plan."""
    return Plan.objects.create(
        name='Test Plan',
        description='Test plan for testing',
        price=29.99,
        currency='USD',
        billing_period='monthly',
        features={
            'max_products': 100,
            'api_calls_limit': 1000,
            'support_level': 'email'
        },
        limits={
            'api_calls': 1000,
            'repricing_runs': 50
        }
    )


@pytest.fixture
def subscription(organization, plan):
    """Test subscription."""
    return Subscription.objects.create(
        organization=organization,
        plan=plan,
        status='active',
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30)
    )


@pytest.fixture
def pricing_strategy(organization):
    """Test pricing strategy."""
    return PricingStrategy.objects.create(
        organization=organization,
        name='Test Strategy',
        description='Test pricing strategy',
        is_active=True,
        is_default=True
    )


@pytest.fixture
def rule_set(pricing_strategy):
    """Test rule set."""
    return RuleSet.objects.create(
        strategy=pricing_strategy,
        name='Test Rules',
        description='Test rule set',
        priority=1,
        is_active=True,
        conditions={
            'marketplace': ['amazon'],
            'category': ['electronics']
        }
    )


@pytest.fixture
def product(organization):
    """Test product."""
    return Product.objects.create(
        organization=organization,
        title='Test Product',
        sku='TEST-SKU-001',
        brand='Test Brand',
        category='Electronics',
        cost=15.00,
        weight=1.5,
        is_active=True
    )


@pytest.fixture
def listing(product):
    """Test listing."""
    return Listing.objects.create(
        organization=product.organization,
        product=product,
        marketplace='amazon',
        marketplace_product_id='ASIN123',
        title='Test Product on Amazon',
        current_price=29.99,
        inventory_quantity=100,
        is_active=True,
        is_buy_box_eligible=True
    )


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    from unittest.mock import Mock
    return Mock()


@pytest.fixture
def mock_stripe():
    """Mock Stripe for testing."""
    from unittest.mock import Mock, patch
    with patch('stripe.Customer') as mock_customer, \
         patch('stripe.Subscription') as mock_subscription, \
         patch('stripe.Invoice') as mock_invoice:
        yield {
            'customer': mock_customer,
            'subscription': mock_subscription,
            'invoice': mock_invoice
        }


@pytest.fixture
def mock_amazon_api():
    """Mock Amazon SP-API for testing."""
    from unittest.mock import Mock, patch
    with patch('integrations.amazon_client.AmazonSPAPIClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Configure mock responses
        mock_instance.get_marketplace_participations.return_value = [
            {'marketplace': {'id': 'ATVPDKIKX0DER', 'name': 'Amazon.com'}}
        ]
        mock_instance.get_orders.return_value = []
        mock_instance.get_listings.return_value = []
        mock_instance.validate_credentials.return_value = True
        
        yield mock_instance


@pytest.fixture
def mock_flipkart_api():
    """Mock Flipkart API for testing."""
    from unittest.mock import Mock, patch
    with patch('integrations.flipkart_client.FlipkartMarketplaceClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Configure mock responses
        mock_instance.get_orders.return_value = []
        mock_instance.get_listings.return_value = []
        mock_instance.validate_credentials.return_value = True
        
        yield mock_instance


@pytest.fixture
def sample_pricing_context():
    """Sample pricing context for testing."""
    from pricing_rules.engine import PricingContext
    from decimal import Decimal
    
    return PricingContext(
        product_id='TEST-001',
        current_price=Decimal('29.99'),
        cost=Decimal('15.00'),
        inventory_level=100,
        competitor_prices=[Decimal('28.99'), Decimal('31.99'), Decimal('30.50')],
        sales_velocity=5.2,
        marketplace='amazon',
        category='electronics',
        brand='test_brand',
        seasonality_factor=1.1,
        demand_score=0.75,
        buy_box_status='won',
        margin_target=0.20
    )


@pytest.fixture
def sample_ml_context():
    """Sample ML pricing context for testing."""
    from pricing_ml.engine import MLPricingContext
    
    return MLPricingContext(
        product_id='TEST-001',
        current_price=29.99,
        cost=15.00,
        inventory_level=100,
        competitor_prices=[28.99, 31.99, 30.50],
        sales_velocity=5.2,
        marketplace='amazon',
        category='electronics',
        brand='test_brand',
        historical_prices=[29.99, 28.50, 30.25, 29.75],
        historical_sales=[10, 12, 8, 15],
        seasonality_factors={'month': 1.1, 'day_of_week': 0.95},
        demand_indicators={'search_volume': 1500, 'conversion_rate': 0.12},
        market_conditions={'competition_level': 0.7, 'demand_trend': 'increasing'}
    )


# Database fixtures
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up test database."""
    with django_db_blocker.unblock():
        # Create default roles
        Role.objects.get_or_create(
            name='Owner',
            defaults={
                'description': 'Organization owner',
                'permissions': ['*'],
                'is_system_role': True
            }
        )
        Role.objects.get_or_create(
            name='Admin',
            defaults={
                'description': 'Administrator',
                'permissions': ['manage_users', 'manage_settings'],
                'is_system_role': True
            }
        )
        Role.objects.get_or_create(
            name='Member',
            defaults={
                'description': 'Regular member',
                'permissions': ['view_products', 'manage_products'],
                'is_system_role': True
            }
        )


# Custom markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external_api: mark test as requiring external API"
    )


# Skip markers based on settings
def pytest_runtest_setup(item):
    """Set up test runs with conditional skipping."""
    import os
    
    # Skip external API tests unless explicitly enabled
    if item.get_closest_marker("external_api"):
        if not os.environ.get("RUN_EXTERNAL_API_TESTS"):
            pytest.skip("External API tests disabled")
    
    # Skip slow tests in fast mode
    if item.get_closest_marker("slow"):
        if os.environ.get("PYTEST_FAST_MODE"):
            pytest.skip("Slow tests disabled in fast mode")
