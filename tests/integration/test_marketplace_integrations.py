"""
Integration tests for marketplace integrations.
"""

import pytest
from unittest.mock import Mock, patch
from django.test import override_settings

from integrations.services import IntegrationService
from integrations.amazon_client import AmazonSPAPIClient
from integrations.flipkart_client import FlipkartMarketplaceClient
from credentials.models import MarketplaceCredential


@pytest.mark.integration
class TestIntegrationService:
    """Integration tests for the integration service."""
    
    @pytest.mark.django_db
    def test_get_amazon_client_with_valid_credentials(self, organization):
        """Test getting Amazon client with valid credentials."""
        # Create test credentials
        MarketplaceCredential.objects.create(
            organization=organization,
            marketplace='amazon',
            name='Test Amazon Creds',
            status='valid',
            data={
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret',
                'refresh_token': 'test_refresh_token',
                'seller_id': 'test_seller_id'
            }
        )
        
        service = IntegrationService(organization)
        
        with patch('integrations.services.AmazonSPAPIClient') as mock_client:
            client = service.get_amazon_client()
            
            assert client is not None
            mock_client.assert_called_once()
    
    @pytest.mark.django_db
    def test_get_amazon_client_no_credentials(self, organization):
        """Test getting Amazon client with no credentials."""
        service = IntegrationService(organization)
        client = service.get_amazon_client()
        
        assert client is None
    
    @pytest.mark.django_db
    def test_sync_amazon_data_success(self, organization, mock_amazon_api):
        """Test successful Amazon data sync."""
        # Create test credentials
        MarketplaceCredential.objects.create(
            organization=organization,
            marketplace='amazon',
            name='Test Amazon Creds',
            status='valid',
            data={
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret',
                'refresh_token': 'test_refresh_token',
                'seller_id': 'test_seller_id'
            }
        )
        
        service = IntegrationService(organization)
        
        with patch.object(service, 'get_amazon_client', return_value=mock_amazon_api):
            result = service.sync_amazon_data(['marketplaces'])
            
            assert result['marketplaces']['status'] == 'success'
    
    @pytest.mark.django_db
    def test_sync_flipkart_data_success(self, organization, mock_flipkart_api):
        """Test successful Flipkart data sync."""
        # Create test credentials
        MarketplaceCredential.objects.create(
            organization=organization,
            marketplace='flipkart',
            name='Test Flipkart Creds',
            status='valid',
            data={
                'app_id': 'test_app_id',
                'app_secret': 'test_app_secret',
                'access_token': 'test_access_token'
            }
        )
        
        service = IntegrationService(organization)
        
        with patch.object(service, 'get_flipkart_client', return_value=mock_flipkart_api):
            result = service.sync_flipkart_data(['orders'])
            
            assert result['orders']['status'] == 'success'


@pytest.mark.integration
@pytest.mark.external_api
class TestAmazonSPAPIClient:
    """Integration tests for Amazon SP-API client (requires credentials)."""
    
    def test_amazon_client_initialization(self):
        """Test Amazon client initialization."""
        credentials = {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'refresh_token': 'test_token',
            'seller_id': 'test_seller'
        }
        
        client = AmazonSPAPIClient(credentials, sandbox=True)
        
        assert client.credentials == credentials
        assert client.sandbox is True
        assert client.base_url == "https://sandbox.sellingpartnerapi-na.amazon.com"
    
    def test_amazon_client_production_url(self):
        """Test Amazon client with production URL."""
        credentials = {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'refresh_token': 'test_token',
            'seller_id': 'test_seller'
        }
        
        client = AmazonSPAPIClient(credentials, sandbox=False)
        
        assert client.base_url == "https://sellingpartnerapi-na.amazon.com"


@pytest.mark.integration
@pytest.mark.external_api
class TestFlipkartMarketplaceClient:
    """Integration tests for Flipkart Marketplace client."""
    
    def test_flipkart_client_initialization(self):
        """Test Flipkart client initialization."""
        credentials = {
            'app_id': 'test_app_id',
            'app_secret': 'test_app_secret',
            'access_token': 'test_token'
        }
        
        client = FlipkartMarketplaceClient(credentials, sandbox=True)
        
        assert client.credentials == credentials
        assert client.sandbox is True
        assert client.base_url == "https://sandbox-api.flipkart.net"
    
    def test_flipkart_client_production_url(self):
        """Test Flipkart client with production URL."""
        credentials = {
            'app_id': 'test_app_id',
            'app_secret': 'test_app_secret',
            'access_token': 'test_token'
        }
        
        client = FlipkartMarketplaceClient(credentials, sandbox=False)
        
        assert client.base_url == "https://api.flipkart.net"


@pytest.mark.integration
class TestCredentialValidation:
    """Integration tests for credential validation."""
    
    @pytest.mark.django_db
    def test_validate_amazon_credentials_success(self, organization):
        """Test successful Amazon credential validation."""
        from integrations.tasks import validate_api_credentials
        
        # Create test credentials
        credential = MarketplaceCredential.objects.create(
            organization=organization,
            marketplace='amazon',
            name='Test Amazon Creds',
            status='pending',
            data={
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret',
                'refresh_token': 'test_refresh_token',
                'seller_id': 'test_seller_id'
            }
        )
        
        with patch('integrations.amazon_client.AmazonSPAPIClient') as mock_client:
            mock_instance = Mock()
            mock_instance.validate_credentials.return_value = True
            mock_client.return_value = mock_instance
            
            result = validate_api_credentials(str(credential.id))
            
            assert result['status'] == 'valid'
    
    @pytest.mark.django_db
    def test_validate_flipkart_credentials_success(self, organization):
        """Test successful Flipkart credential validation."""
        from integrations.tasks import validate_api_credentials
        
        # Create test credentials
        credential = MarketplaceCredential.objects.create(
            organization=organization,
            marketplace='flipkart',
            name='Test Flipkart Creds',
            status='pending',
            data={
                'app_id': 'test_app_id',
                'app_secret': 'test_app_secret',
                'access_token': 'test_access_token'
            }
        )
        
        with patch('integrations.flipkart_client.FlipkartMarketplaceClient') as mock_client:
            mock_instance = Mock()
            mock_instance.validate_credentials.return_value = True
            mock_client.return_value = mock_instance
            
            result = validate_api_credentials(str(credential.id))
            
            assert result['status'] == 'valid'
