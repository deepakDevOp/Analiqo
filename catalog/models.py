"""
Product catalog models for managing products and marketplace listings.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import BaseModel, TimeStampedModel


class Category(BaseModel):
    """Product categories across marketplaces."""
    
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Marketplace category mappings
    amazon_category_id = models.CharField(max_length=100, blank=True)
    flipkart_category_id = models.CharField(max_length=100, blank=True)
    
    # Category attributes
    attributes = models.JSONField(default=dict, blank=True)
    
    # SEO and metadata
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        unique_together = ['organization', 'name']
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def full_path(self):
        """Get the full category path."""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Brand(BaseModel):
    """Product brands."""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brand_logos/', blank=True, null=True)
    website = models.URLField(blank=True)
    
    class Meta:
        verbose_name = _('Brand')
        verbose_name_plural = _('Brands')
        unique_together = ['organization', 'name']
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(BaseModel):
    """Core product information."""
    
    # Basic product info
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Identifiers
    sku = models.CharField(max_length=200)  # Internal SKU
    upc = models.CharField(max_length=20, blank=True)
    ean = models.CharField(max_length=20, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    asin = models.CharField(max_length=20, blank=True)  # Amazon ASIN
    
    # Physical attributes
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)  # kg
    dimensions_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # cm
    dimensions_width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)   # cm
    dimensions_height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # cm
    
    # Pricing and costs
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Inventory
    total_inventory = models.PositiveIntegerField(default=0)
    reserved_inventory = models.PositiveIntegerField(default=0)
    
    # Product attributes
    attributes = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        unique_together = ['organization', 'sku']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['asin']),
            models.Index(fields=['upc']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.sku} - {self.title}"
    
    @property
    def available_inventory(self):
        return self.total_inventory - self.reserved_inventory


class Marketplace(models.Model):
    """Marketplace definitions."""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)  # e.g., 'amazon_us', 'flipkart_in'
    country = models.CharField(max_length=2)  # ISO country code
    currency = models.CharField(max_length=3)  # ISO currency code
    
    # API configuration
    api_endpoint = models.URLField()
    sandbox_endpoint = models.URLField(blank=True)
    
    # Fee structure
    referral_fee_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=Decimal('0.15'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))]
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('Marketplace')
        verbose_name_plural = _('Marketplaces')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Listing(BaseModel):
    """Product listings on marketplaces."""
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('pending', _('Pending')),
        ('rejected', _('Rejected')),
        ('suppressed', _('Suppressed')),
    ]
    
    FULFILLMENT_CHOICES = [
        ('fbm', _('Fulfillment by Merchant')),
        ('fba', _('Fulfillment by Amazon')),
        ('fbf', _('Fulfillment by Flipkart')),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='listings')
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE)
    
    # Marketplace identifiers
    marketplace_sku = models.CharField(max_length=200)  # SKU on marketplace
    marketplace_product_id = models.CharField(max_length=100, blank=True)  # ASIN, product ID
    
    # Listing details
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    # Pricing
    current_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Inventory
    quantity = models.PositiveIntegerField(default=0)
    fulfillment_method = models.CharField(max_length=10, choices=FULFILLMENT_CHOICES, default='fbm')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    
    # Buy Box and competitive data
    has_buy_box = models.BooleanField(default=False)
    buy_box_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lowest_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Performance metrics
    sales_rank = models.PositiveIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)
    
    # Listing attributes
    attributes = models.JSONField(default=dict, blank=True)
    
    # Sync tracking
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_errors = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = _('Listing')
        verbose_name_plural = _('Listings')
        unique_together = ['organization', 'marketplace', 'marketplace_sku']
        indexes = [
            models.Index(fields=['marketplace_sku']),
            models.Index(fields=['marketplace_product_id']),
            models.Index(fields=['status']),
            models.Index(fields=['has_buy_box']),
            models.Index(fields=['last_synced_at']),
        ]
    
    def __str__(self):
        return f"{self.marketplace.name} - {self.marketplace_sku}"


class PriceHistory(TimeStampedModel):
    """Historical price tracking."""
    
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='price_history')
    
    # Price data
    price = models.DecimalField(max_digits=10, decimal_places=2)
    buy_box_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lowest_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Competitive data
    competitor_count = models.PositiveIntegerField(default=0)
    
    # Source of the price change
    source = models.CharField(max_length=50)  # 'manual', 'repricing_engine', 'sync'
    
    class Meta:
        verbose_name = _('Price History')
        verbose_name_plural = _('Price History')
        indexes = [
            models.Index(fields=['listing', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.listing} - {self.price} at {self.created_at}"


class Competitor(BaseModel):
    """Competitor tracking."""
    
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='competitors')
    
    # Competitor details
    seller_name = models.CharField(max_length=200)
    seller_id = models.CharField(max_length=100, blank=True)
    
    # Current data
    price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    condition = models.CharField(max_length=50, default='new')
    fulfillment_method = models.CharField(max_length=10, choices=Listing.FULFILLMENT_CHOICES, default='fbm')
    
    # Performance
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    feedback_count = models.PositiveIntegerField(default=0)
    
    # Tracking
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    # Blacklist/whitelist status
    is_blacklisted = models.BooleanField(default=False)
    is_whitelisted = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Competitor')
        verbose_name_plural = _('Competitors')
        unique_together = ['listing', 'seller_id']
        indexes = [
            models.Index(fields=['seller_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_seen_at']),
        ]
    
    def __str__(self):
        return f"{self.seller_name} - {self.listing.marketplace_sku}"


class FeeStructure(BaseModel):
    """Marketplace fee structures."""
    
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE, related_name='fee_structures')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    
    # Fee types
    referral_fee_rate = models.DecimalField(max_digits=5, decimal_places=4)
    variable_closing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    per_item_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # FBA/FBF fees (if applicable)
    fulfillment_fee_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    storage_fee_per_unit_per_month = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Date range
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Fee Structure')
        verbose_name_plural = _('Fee Structures')
        indexes = [
            models.Index(fields=['marketplace', 'effective_from']),
            models.Index(fields=['category', 'effective_from']),
        ]
    
    def __str__(self):
        category_name = self.category.name if self.category else "All Categories"
        return f"{self.marketplace.name} - {category_name}"
    
    def calculate_fees(self, price: Decimal, quantity: int = 1) -> dict:
        """Calculate all fees for a given price and quantity."""
        fees = {}
        
        # Referral fee
        fees['referral_fee'] = price * self.referral_fee_rate * quantity
        
        # Variable closing fee
        fees['closing_fee'] = self.variable_closing_fee * quantity
        
        # Per item fee
        fees['per_item_fee'] = self.per_item_fee * quantity
        
        # Fulfillment fee
        fees['fulfillment_fee'] = self.fulfillment_fee_per_unit * quantity
        
        # Total fees
        fees['total_fees'] = sum(fees.values())
        
        return fees
