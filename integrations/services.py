"""
Integration services for marketplace clients.
"""

from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db import transaction
import logging

from .amazon_client import AmazonSPAPIClient
from .flipkart_client import FlipkartMarketplaceClient
from .models import SyncJob, MarketplaceData
from credentials.models import MarketplaceCredential

logger = logging.getLogger(__name__)


class IntegrationService:
    """
    Service for managing marketplace integrations.
    """
    
    def __init__(self, organization):
        self.organization = organization
    
    def get_amazon_client(self, sandbox: bool = False) -> Optional[AmazonSPAPIClient]:
        """
        Get configured Amazon SP-API client for the organization.
        """
        try:
            credential = MarketplaceCredential.objects.get(
                organization=self.organization,
                marketplace='amazon',
                status='valid'
            )
            
            credentials = {
                'client_id': credential.data.get('client_id'),
                'client_secret': credential.data.get('client_secret'),
                'refresh_token': credential.data.get('refresh_token'),
                'access_key': credential.data.get('access_key'),
                'secret_key': credential.data.get('secret_key'),
                'role_arn': credential.data.get('role_arn'),
                'seller_id': credential.data.get('seller_id')
            }
            
            return AmazonSPAPIClient(credentials, sandbox=sandbox)
            
        except MarketplaceCredential.DoesNotExist:
            logger.warning(f"No valid Amazon credentials found for organization {self.organization.id}")
            return None
        except Exception as e:
            logger.error(f"Failed to create Amazon client: {str(e)}")
            return None
    
    def get_flipkart_client(self, sandbox: bool = False) -> Optional[FlipkartMarketplaceClient]:
        """
        Get configured Flipkart Marketplace API client for the organization.
        """
        try:
            credential = MarketplaceCredential.objects.get(
                organization=self.organization,
                marketplace='flipkart',
                status='valid'
            )
            
            credentials = {
                'app_id': credential.data.get('app_id'),
                'app_secret': credential.data.get('app_secret'),
                'access_token': credential.data.get('access_token')
            }
            
            return FlipkartMarketplaceClient(credentials, sandbox=sandbox)
            
        except MarketplaceCredential.DoesNotExist:
            logger.warning(f"No valid Flipkart credentials found for organization {self.organization.id}")
            return None
        except Exception as e:
            logger.error(f"Failed to create Flipkart client: {str(e)}")
            return None
    
    def sync_amazon_data(self, data_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync data from Amazon SP-API.
        
        Args:
            data_types: List of data types to sync (orders, listings, inventory, etc.)
        """
        client = self.get_amazon_client()
        if not client:
            return {"status": "error", "message": "No valid Amazon credentials"}
        
        if data_types is None:
            data_types = ['marketplaces', 'orders', 'listings', 'inventory']
        
        results = {}
        
        try:
            with transaction.atomic():
                sync_job = SyncJob.objects.create(
                    organization=self.organization,
                    job_type='amazon_sync',
                    marketplace='amazon',
                    status='running',
                    started_at=timezone.now()
                )
                
                for data_type in data_types:
                    try:
                        result = self._sync_amazon_data_type(client, data_type)
                        results[data_type] = result
                    except Exception as e:
                        logger.error(f"Failed to sync Amazon {data_type}: {str(e)}")
                        results[data_type] = {"status": "error", "message": str(e)}
                
                sync_job.status = 'completed'
                sync_job.completed_at = timezone.now()
                sync_job.save()
                
        except Exception as e:
            logger.error(f"Amazon sync failed: {str(e)}")
            if 'sync_job' in locals():
                sync_job.status = 'failed'
                sync_job.error_message = str(e)
                sync_job.completed_at = timezone.now()
                sync_job.save()
            results = {"status": "error", "message": str(e)}
        
        return results
    
    def _sync_amazon_data_type(self, client: AmazonSPAPIClient, data_type: str) -> Dict[str, Any]:
        """
        Sync specific data type from Amazon.
        """
        if data_type == 'marketplaces':
            return self._sync_amazon_marketplaces(client)
        elif data_type == 'orders':
            return self._sync_amazon_orders(client)
        elif data_type == 'listings':
            return self._sync_amazon_listings(client)
        elif data_type == 'inventory':
            return self._sync_amazon_inventory(client)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def _sync_amazon_marketplaces(self, client: AmazonSPAPIClient) -> Dict[str, Any]:
        """Sync marketplace participations from Amazon."""
        participations = client.get_marketplace_participations()
        
        for participation in participations:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='amazon',
                data_type='marketplace',
                external_id=participation.get('marketplace', {}).get('id'),
                defaults={
                    'data': participation,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(participations)}
    
    def _sync_amazon_orders(self, client: AmazonSPAPIClient) -> Dict[str, Any]:
        """Sync orders from Amazon."""
        # Get marketplace IDs
        marketplaces = MarketplaceData.objects.filter(
            organization=self.organization,
            marketplace='amazon',
            data_type='marketplace'
        )
        
        marketplace_ids = [mp.external_id for mp in marketplaces]
        
        if not marketplace_ids:
            return {"status": "error", "message": "No marketplaces found"}
        
        # Get orders from last 7 days
        created_after = (timezone.now() - timezone.timedelta(days=7)).isoformat()
        orders = client.get_orders(marketplace_ids, created_after)
        
        for order in orders:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='amazon',
                data_type='order',
                external_id=order.get('AmazonOrderId'),
                defaults={
                    'data': order,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(orders)}
    
    def _sync_amazon_listings(self, client: AmazonSPAPIClient) -> Dict[str, Any]:
        """Sync listings from Amazon."""
        # Get marketplace IDs
        marketplaces = MarketplaceData.objects.filter(
            organization=self.organization,
            marketplace='amazon',
            data_type='marketplace'
        )
        
        total_listings = 0
        
        for marketplace in marketplaces:
            marketplace_id = marketplace.external_id
            listings = client.get_listings(marketplace_id)
            
            for listing in listings:
                MarketplaceData.objects.update_or_create(
                    organization=self.organization,
                    marketplace='amazon',
                    data_type='listing',
                    external_id=listing.get('sku'),
                    defaults={
                        'data': listing,
                        'updated_at': timezone.now()
                    }
                )
                total_listings += 1
        
        return {"status": "success", "count": total_listings}
    
    def _sync_amazon_inventory(self, client: AmazonSPAPIClient) -> Dict[str, Any]:
        """Sync inventory from Amazon."""
        # Get marketplace IDs
        marketplaces = MarketplaceData.objects.filter(
            organization=self.organization,
            marketplace='amazon',
            data_type='marketplace'
        )
        
        marketplace_ids = [mp.external_id for mp in marketplaces]
        
        if not marketplace_ids:
            return {"status": "error", "message": "No marketplaces found"}
        
        inventory_summaries = client.get_inventory_summary(marketplace_ids)
        
        for summary in inventory_summaries:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='amazon',
                data_type='inventory',
                external_id=summary.get('sellerSku'),
                defaults={
                    'data': summary,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(inventory_summaries)}
    
    def sync_flipkart_data(self, data_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync data from Flipkart Marketplace API.
        
        Args:
            data_types: List of data types to sync (orders, listings, returns, etc.)
        """
        client = self.get_flipkart_client()
        if not client:
            return {"status": "error", "message": "No valid Flipkart credentials"}
        
        if data_types is None:
            data_types = ['orders', 'listings', 'returns', 'shipments']
        
        results = {}
        
        try:
            with transaction.atomic():
                sync_job = SyncJob.objects.create(
                    organization=self.organization,
                    job_type='flipkart_sync',
                    marketplace='flipkart',
                    status='running',
                    started_at=timezone.now()
                )
                
                for data_type in data_types:
                    try:
                        result = self._sync_flipkart_data_type(client, data_type)
                        results[data_type] = result
                    except Exception as e:
                        logger.error(f"Failed to sync Flipkart {data_type}: {str(e)}")
                        results[data_type] = {"status": "error", "message": str(e)}
                
                sync_job.status = 'completed'
                sync_job.completed_at = timezone.now()
                sync_job.save()
                
        except Exception as e:
            logger.error(f"Flipkart sync failed: {str(e)}")
            if 'sync_job' in locals():
                sync_job.status = 'failed'
                sync_job.error_message = str(e)
                sync_job.completed_at = timezone.now()
                sync_job.save()
            results = {"status": "error", "message": str(e)}
        
        return results
    
    def _sync_flipkart_data_type(self, client: FlipkartMarketplaceClient, data_type: str) -> Dict[str, Any]:
        """
        Sync specific data type from Flipkart.
        """
        if data_type == 'orders':
            return self._sync_flipkart_orders(client)
        elif data_type == 'listings':
            return self._sync_flipkart_listings(client)
        elif data_type == 'returns':
            return self._sync_flipkart_returns(client)
        elif data_type == 'shipments':
            return self._sync_flipkart_shipments(client)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def _sync_flipkart_orders(self, client: FlipkartMarketplaceClient) -> Dict[str, Any]:
        """Sync orders from Flipkart."""
        # Get orders from last 7 days
        start_date = (timezone.now() - timezone.timedelta(days=7)).strftime("%Y-%m-%d")
        orders = client.get_orders(start_date)
        
        for order in orders:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='flipkart',
                data_type='order',
                external_id=order.get('orderId'),
                defaults={
                    'data': order,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(orders)}
    
    def _sync_flipkart_listings(self, client: FlipkartMarketplaceClient) -> Dict[str, Any]:
        """Sync listings from Flipkart."""
        listings = client.get_listings()
        
        for listing in listings:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='flipkart',
                data_type='listing',
                external_id=listing.get('sku'),
                defaults={
                    'data': listing,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(listings)}
    
    def _sync_flipkart_returns(self, client: FlipkartMarketplaceClient) -> Dict[str, Any]:
        """Sync returns from Flipkart."""
        # Get returns from last 30 days
        start_date = (timezone.now() - timezone.timedelta(days=30)).strftime("%Y-%m-%d")
        returns = client.get_returns(start_date)
        
        for return_item in returns:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='flipkart',
                data_type='return',
                external_id=return_item.get('returnId'),
                defaults={
                    'data': return_item,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(returns)}
    
    def _sync_flipkart_shipments(self, client: FlipkartMarketplaceClient) -> Dict[str, Any]:
        """Sync shipments from Flipkart."""
        # Get shipments from last 7 days
        start_date = (timezone.now() - timezone.timedelta(days=7)).strftime("%Y-%m-%d")
        shipments = client.get_shipments(start_date)
        
        for shipment in shipments:
            MarketplaceData.objects.update_or_create(
                organization=self.organization,
                marketplace='flipkart',
                data_type='shipment',
                external_id=shipment.get('shipmentId'),
                defaults={
                    'data': shipment,
                    'updated_at': timezone.now()
                }
            )
        
        return {"status": "success", "count": len(shipments)}
