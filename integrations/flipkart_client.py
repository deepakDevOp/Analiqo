"""
Flipkart Marketplace API client for marketplace integration.
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import base64
import logging

logger = logging.getLogger(__name__)


class FlipkartMarketplaceClient:
    """
    Client for Flipkart Marketplace API integration.
    """
    
    def __init__(self, credentials: Dict[str, str], sandbox: bool = False):
        """
        Initialize Flipkart Marketplace API client.
        
        Args:
            credentials: Dict containing app_id, app_secret, access_token
            sandbox: Whether to use sandbox environment
        """
        self.credentials = credentials
        self.sandbox = sandbox
        self.base_url = self._get_base_url()
        self.session = requests.Session()
        self.access_token = credentials.get("access_token")
        
        # Set up authentication
        self._setup_authentication()
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL for the environment."""
        if self.sandbox:
            return "https://sandbox-api.flipkart.net"
        return "https://api.flipkart.net"
    
    def _setup_authentication(self):
        """Setup authentication headers for the session."""
        if self.access_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
        else:
            # Use app credentials for basic auth if no access token
            app_id = self.credentials.get("app_id")
            app_secret = self.credentials.get("app_secret")
            
            if app_id and app_secret:
                credentials = f"{app_id}:{app_secret}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                self.session.headers.update({
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                })
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Flipkart Marketplace API.
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Flipkart API request failed: {str(e)}")
            raise
    
    def get_orders(self, start_date: str, end_date: Optional[str] = None, 
                   states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get orders from Flipkart marketplace.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
            states: List of order states to filter (optional)
        """
        params = {
            "filter": json.dumps({
                "orderDate": {
                    "fromDate": start_date,
                    "toDate": end_date or datetime.now().strftime("%Y-%m-%d")
                }
            })
        }
        
        if states:
            params["filter"] = json.dumps({
                **json.loads(params["filter"]),
                "states": states
            })
        
        try:
            response = self._make_request("GET", "/sellers/orders/search", params=params)
            return response.get("orderItems", [])
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            return []
    
    def get_listings(self, sku: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get product listings for the seller.
        
        Args:
            sku: Specific SKU to retrieve (optional)
        """
        endpoint = "/sellers/listings"
        params = {}
        
        if sku:
            params["sku"] = sku
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("listingItems", [])
        except Exception as e:
            logger.error(f"Failed to get listings: {str(e)}")
            return []
    
    def update_listing_price(self, sku: str, selling_price: float, 
                           mrp: Optional[float] = None) -> bool:
        """
        Update the price of a product listing.
        
        Args:
            sku: Seller SKU
            selling_price: New selling price
            mrp: Maximum Retail Price (optional)
        """
        endpoint = "/sellers/listings"
        
        price_data = {
            "sku": sku,
            "sellingPrice": selling_price
        }
        
        if mrp:
            price_data["mrp"] = mrp
        
        data = {
            "listings": [price_data]
        }
        
        try:
            response = self._make_request("PUT", endpoint, data=data)
            return response.get("status") == "success"
        except Exception as e:
            logger.error(f"Failed to update listing price: {str(e)}")
            return False
    
    def update_inventory(self, sku: str, quantity: int, 
                        fulfillment_type: str = "seller") -> bool:
        """
        Update inventory quantity for a product.
        
        Args:
            sku: Seller SKU
            quantity: New inventory quantity
            fulfillment_type: Fulfillment type (seller, flipkart)
        """
        endpoint = "/sellers/listings"
        
        data = {
            "listings": [
                {
                    "sku": sku,
                    "inventory": quantity,
                    "fulfillmentType": fulfillment_type
                }
            ]
        }
        
        try:
            response = self._make_request("PUT", endpoint, data=data)
            return response.get("status") == "success"
        except Exception as e:
            logger.error(f"Failed to update inventory: {str(e)}")
            return False
    
    def get_returns(self, start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get return orders from Flipkart marketplace.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
        """
        params = {
            "filter": json.dumps({
                "postReturnDate": {
                    "fromDate": start_date,
                    "toDate": end_date or datetime.now().strftime("%Y-%m-%d")
                }
            })
        }
        
        try:
            response = self._make_request("GET", "/sellers/returns/search", params=params)
            return response.get("returnItems", [])
        except Exception as e:
            logger.error(f"Failed to get returns: {str(e)}")
            return []
    
    def get_shipments(self, start_date: str, end_date: Optional[str] = None, 
                     states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get shipment details from Flipkart marketplace.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
            states: List of shipment states to filter (optional)
        """
        params = {
            "filter": json.dumps({
                "dispatchAfterDate": start_date,
                "dispatchByDate": end_date or datetime.now().strftime("%Y-%m-%d")
            })
        }
        
        if states:
            params["filter"] = json.dumps({
                **json.loads(params["filter"]),
                "states": states
            })
        
        try:
            response = self._make_request("GET", "/sellers/shipments/search", params=params)
            return response.get("shipments", [])
        except Exception as e:
            logger.error(f"Failed to get shipments: {str(e)}")
            return []
    
    def get_payments(self, start_date: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get payment details from Flipkart marketplace.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
        """
        params = {
            "filter": json.dumps({
                "transactionDate": {
                    "fromDate": start_date,
                    "toDate": end_date or datetime.now().strftime("%Y-%m-%d")
                }
            })
        }
        
        try:
            response = self._make_request("GET", "/sellers/payments/search", params=params)
            return response.get("payments", [])
        except Exception as e:
            logger.error(f"Failed to get payments: {str(e)}")
            return []
    
    def get_listing_quality(self, sku: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get listing quality information.
        
        Args:
            sku: Specific SKU to check (optional)
        """
        endpoint = "/sellers/listings/quality"
        params = {}
        
        if sku:
            params["sku"] = sku
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("qualityErrors", [])
        except Exception as e:
            logger.error(f"Failed to get listing quality: {str(e)}")
            return []
    
    def bulk_listing_update(self, listings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform bulk update of multiple listings.
        
        Args:
            listings_data: List of listing update data
        """
        endpoint = "/sellers/listings"
        
        data = {
            "listings": listings_data
        }
        
        try:
            response = self._make_request("PUT", endpoint, data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to perform bulk listing update: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def validate_credentials(self) -> bool:
        """
        Validate the API credentials by making a test call.
        """
        try:
            # Try to get listings as a test
            listings = self.get_listings()
            return True  # If no exception, credentials are valid
        except Exception as e:
            logger.error(f"Credential validation failed: {str(e)}")
            return False
    
    def get_seller_info(self) -> Dict[str, Any]:
        """
        Get seller account information.
        """
        try:
            response = self._make_request("GET", "/sellers/info")
            return response.get("seller", {})
        except Exception as e:
            logger.error(f"Failed to get seller info: {str(e)}")
            return {}
    
    def get_service_profile(self) -> Dict[str, Any]:
        """
        Get seller service profile information.
        """
        try:
            response = self._make_request("GET", "/sellers/serviceProfile")
            return response.get("serviceProfile", {})
        except Exception as e:
            logger.error(f"Failed to get service profile: {str(e)}")
            return {}
