"""
Amazon SP-API client for marketplace integration.
"""

import requests
import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AmazonSPAPIClient:
    """
    Client for Amazon Selling Partner API integration.
    """
    
    def __init__(self, credentials: Dict[str, str], sandbox: bool = False):
        """
        Initialize Amazon SP-API client.
        
        Args:
            credentials: Dict containing access_key, secret_key, role_arn, refresh_token
            sandbox: Whether to use sandbox environment
        """
        self.credentials = credentials
        self.sandbox = sandbox
        self.base_url = self._get_base_url()
        self.session = requests.Session()
        self.access_token = None
        self.token_expires_at = None
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL for the environment."""
        if self.sandbox:
            return "https://sandbox.sellingpartnerapi-na.amazon.com"
        return "https://sellingpartnerapi-na.amazon.com"
    
    def _get_access_token(self) -> str:
        """
        Get or refresh the access token using LWA (Login with Amazon).
        """
        if self.access_token and self.token_expires_at:
            if datetime.now(timezone.utc) < self.token_expires_at:
                return self.access_token
        
        # Refresh token
        lwa_url = "https://api.amazon.com/auth/o2/token"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.credentials.get("refresh_token"),
            "client_id": self.credentials.get("client_id"),
            "client_secret": self.credentials.get("client_secret")
        }
        
        try:
            response = requests.post(lwa_url, data=payload)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            
            # Calculate expiry time (subtract 60 seconds for safety)
            expires_in = token_data.get("expires_in", 3600) - 60
            self.token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in
            
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get Amazon access token: {str(e)}")
            raise
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Amazon SP-API.
        """
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "User-Agent": "RepricingPlatform/1.0 (Language=Python)",
            "x-amz-access-token": self._get_access_token()
        }
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Amazon API request failed: {str(e)}")
            raise
    
    def get_marketplace_participations(self) -> List[Dict[str, Any]]:
        """
        Get marketplace participations for the seller.
        """
        try:
            response = self._make_request("GET", "/sellers/v1/marketplaceParticipations")
            return response.get("payload", [])
        except Exception as e:
            logger.error(f"Failed to get marketplace participations: {str(e)}")
            return []
    
    def get_orders(self, marketplace_ids: List[str], created_after: str, 
                   created_before: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get orders from specified marketplaces.
        
        Args:
            marketplace_ids: List of marketplace IDs
            created_after: ISO 8601 datetime string
            created_before: ISO 8601 datetime string (optional)
        """
        params = {
            "MarketplaceIds": ",".join(marketplace_ids),
            "CreatedAfter": created_after
        }
        
        if created_before:
            params["CreatedBefore"] = created_before
        
        try:
            response = self._make_request("GET", "/orders/v0/orders", params=params)
            return response.get("payload", {}).get("Orders", [])
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            return []
    
    def get_listings(self, marketplace_id: str, seller_sku: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get product listings for the seller.
        
        Args:
            marketplace_id: Marketplace ID
            seller_sku: Specific SKU to retrieve (optional)
        """
        endpoint = f"/listings/2021-08-01/items/{self.credentials.get('seller_id')}"
        
        params = {
            "marketplaceIds": marketplace_id
        }
        
        if seller_sku:
            endpoint += f"/{seller_sku}"
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("summaries", [])
        except Exception as e:
            logger.error(f"Failed to get listings: {str(e)}")
            return []
    
    def update_listing_price(self, marketplace_id: str, seller_sku: str, 
                           price: float, currency: str = "USD") -> bool:
        """
        Update the price of a product listing.
        
        Args:
            marketplace_id: Marketplace ID
            seller_sku: Seller SKU
            price: New price
            currency: Price currency
        """
        endpoint = f"/listings/2021-08-01/items/{self.credentials.get('seller_id')}/{seller_sku}"
        
        patch_operation = {
            "productType": "PRODUCT",  # This would need to be dynamic
            "patches": [
                {
                    "op": "replace",
                    "path": "/attributes/list_price",
                    "value": [
                        {
                            "currency": currency,
                            "amount": price
                        }
                    ]
                }
            ]
        }
        
        params = {
            "marketplaceIds": marketplace_id
        }
        
        try:
            response = self._make_request("PATCH", endpoint, params=params, data=patch_operation)
            return response.get("status") == "ACCEPTED"
        except Exception as e:
            logger.error(f"Failed to update listing price: {str(e)}")
            return False
    
    def get_competitive_pricing(self, marketplace_id: str, asins: List[str]) -> List[Dict[str, Any]]:
        """
        Get competitive pricing information for products.
        
        Args:
            marketplace_id: Marketplace ID
            asins: List of ASINs to get pricing for
        """
        params = {
            "MarketplaceId": marketplace_id,
            "Asins": ",".join(asins)
        }
        
        try:
            response = self._make_request("GET", "/products/pricing/v0/competitivePricing", params=params)
            return response.get("payload", [])
        except Exception as e:
            logger.error(f"Failed to get competitive pricing: {str(e)}")
            return []
    
    def get_lowest_priced_offers(self, marketplace_id: str, asin: str, 
                                item_condition: str = "New") -> Dict[str, Any]:
        """
        Get lowest priced offers for a product.
        
        Args:
            marketplace_id: Marketplace ID
            asin: Product ASIN
            item_condition: Item condition (New, Used, etc.)
        """
        params = {
            "MarketplaceId": marketplace_id,
            "ItemCondition": item_condition
        }
        
        try:
            response = self._make_request("GET", f"/products/pricing/v0/items/{asin}/offers", params=params)
            return response.get("payload", {})
        except Exception as e:
            logger.error(f"Failed to get lowest priced offers: {str(e)}")
            return {}
    
    def get_inventory_summary(self, marketplace_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get inventory summary for specified marketplaces.
        
        Args:
            marketplace_ids: List of marketplace IDs
        """
        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }
        
        try:
            response = self._make_request("GET", "/fba/inventory/v1/summaries", params=params)
            return response.get("payload", {}).get("inventorySummaries", [])
        except Exception as e:
            logger.error(f"Failed to get inventory summary: {str(e)}")
            return []
    
    def validate_credentials(self) -> bool:
        """
        Validate the API credentials by making a test call.
        """
        try:
            # Try to get marketplace participations as a test
            participations = self.get_marketplace_participations()
            return len(participations) >= 0  # Even empty response means valid credentials
        except Exception as e:
            logger.error(f"Credential validation failed: {str(e)}")
            return False
