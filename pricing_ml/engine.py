"""
Machine learning pricing engine for advanced price optimization.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import joblib
import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import xgboost as xgb

from .models import MLModel, ModelPrediction, FeatureStore, TrainingJob

logger = logging.getLogger(__name__)


@dataclass
class MLPricingContext:
    """Context for ML pricing prediction."""
    product_id: str
    current_price: float
    cost: float
    inventory_level: int
    competitor_prices: List[float]
    sales_velocity: float
    marketplace: str
    category: str
    brand: str
    historical_prices: List[float]
    historical_sales: List[int]
    seasonality_factors: Dict[str, float]
    demand_indicators: Dict[str, float]
    market_conditions: Dict[str, float]
    custom_features: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_features is None:
            self.custom_features = {}


@dataclass
class MLPricingResult:
    """Result of ML pricing prediction."""
    predicted_price: float
    confidence: float
    model_type: str
    model_version: str
    feature_importance: Dict[str, float]
    prediction_metadata: Dict[str, Any]


class MLPricingEngine:
    """
    Machine learning pricing engine using various algorithms.
    """
    
    def __init__(self, organization):
        self.organization = organization
        self.models_cache = {}
        self.scalers_cache = {}
        self.feature_store = FeatureStoreManager(organization)
    
    def predict_optimal_price(self, context: MLPricingContext, 
                            model_type: str = 'price_optimization') -> MLPricingResult:
        """
        Predict optimal price using ML models.
        
        Args:
            context: ML pricing context with product and market data
            model_type: Type of ML model to use
        
        Returns:
            MLPricingResult with predicted price and metadata
        """
        try:
            # Get the model
            model = self._get_model(model_type)
            if not model:
                raise ValueError(f"No active model found for type: {model_type}")
            
            # Prepare features
            features = self._prepare_features(context, model)
            
            # Make prediction
            prediction, confidence = self._make_prediction(model, features)
            
            # Get feature importance
            feature_importance = self._get_feature_importance(model, features)
            
            # Log prediction
            self._log_prediction(model, context, prediction, confidence, features)
            
            return MLPricingResult(
                predicted_price=prediction,
                confidence=confidence,
                model_type=model.model_type,
                model_version=model.version,
                feature_importance=feature_importance,
                prediction_metadata={
                    'features_used': list(features.keys()),
                    'model_id': str(model.id),
                    'prediction_timestamp': timezone.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"ML pricing prediction failed: {str(e)}")
            raise
    
    def predict_demand(self, context: MLPricingContext, price_points: List[float]) -> List[float]:
        """
        Predict demand at different price points using demand forecasting model.
        
        Args:
            context: ML pricing context
            price_points: List of prices to predict demand for
        
        Returns:
            List of predicted demand values corresponding to price points
        """
        model = self._get_model('demand_forecasting')
        if not model:
            raise ValueError("No demand forecasting model available")
        
        demand_predictions = []
        
        for price in price_points:
            # Create context with the new price
            demand_context = MLPricingContext(
                product_id=context.product_id,
                current_price=price,  # Use the test price
                cost=context.cost,
                inventory_level=context.inventory_level,
                competitor_prices=context.competitor_prices,
                sales_velocity=context.sales_velocity,
                marketplace=context.marketplace,
                category=context.category,
                brand=context.brand,
                historical_prices=context.historical_prices,
                historical_sales=context.historical_sales,
                seasonality_factors=context.seasonality_factors,
                demand_indicators=context.demand_indicators,
                market_conditions=context.market_conditions,
                custom_features=context.custom_features
            )
            
            features = self._prepare_features(demand_context, model)
            demand, _ = self._make_prediction(model, features)
            demand_predictions.append(max(0, demand))  # Ensure non-negative demand
        
        return demand_predictions
    
    def predict_buy_box_probability(self, context: MLPricingContext, price: float) -> float:
        """
        Predict probability of winning buy box at given price.
        
        Args:
            context: ML pricing context
            price: Price to test
        
        Returns:
            Probability of winning buy box (0-1)
        """
        model = self._get_model('buy_box_prediction')
        if not model:
            return 0.5  # Default probability if no model
        
        # Create context with the test price
        test_context = MLPricingContext(
            product_id=context.product_id,
            current_price=price,
            cost=context.cost,
            inventory_level=context.inventory_level,
            competitor_prices=context.competitor_prices,
            sales_velocity=context.sales_velocity,
            marketplace=context.marketplace,
            category=context.category,
            brand=context.brand,
            historical_prices=context.historical_prices,
            historical_sales=context.historical_sales,
            seasonality_factors=context.seasonality_factors,
            demand_indicators=context.demand_indicators,
            market_conditions=context.market_conditions,
            custom_features=context.custom_features
        )
        
        features = self._prepare_features(test_context, model)
        probability, _ = self._make_prediction(model, features)
        
        return max(0.0, min(1.0, probability))  # Clamp to [0, 1]
    
    def optimize_price_with_constraints(self, context: MLPricingContext, 
                                      min_price: float, max_price: float,
                                      min_margin: float = 0.1) -> MLPricingResult:
        """
        Find optimal price within constraints using ML models.
        
        Args:
            context: ML pricing context
            min_price: Minimum allowed price
            max_price: Maximum allowed price
            min_margin: Minimum required margin
        
        Returns:
            MLPricingResult with optimized price
        """
        # Ensure minimum price respects margin constraint
        min_price_for_margin = context.cost / (1 - min_margin)
        effective_min_price = max(min_price, min_price_for_margin)
        
        if effective_min_price > max_price:
            raise ValueError("Cannot satisfy margin constraint within price range")
        
        # Generate price candidates
        price_candidates = np.linspace(effective_min_price, max_price, 20)
        
        best_price = effective_min_price
        best_score = float('-inf')
        best_result = None
        
        for price in price_candidates:
            try:
                # Predict demand at this price
                demand = self.predict_demand(context, [price])[0]
                
                # Predict buy box probability
                buy_box_prob = self.predict_buy_box_probability(context, price)
                
                # Calculate expected revenue and profit
                expected_sales = demand * buy_box_prob
                revenue = price * expected_sales
                profit = (price - context.cost) * expected_sales
                margin = (price - context.cost) / price
                
                # Composite score (can be customized)
                score = profit * 0.6 + revenue * 0.3 + buy_box_prob * 100 * 0.1
                
                if score > best_score:
                    best_score = score
                    best_price = price
                    best_result = MLPricingResult(
                        predicted_price=price,
                        confidence=buy_box_prob,  # Use buy box prob as confidence proxy
                        model_type='price_optimization',
                        model_version='ensemble',
                        feature_importance={},
                        prediction_metadata={
                            'expected_demand': demand,
                            'expected_sales': expected_sales,
                            'expected_revenue': revenue,
                            'expected_profit': profit,
                            'margin': margin,
                            'buy_box_probability': buy_box_prob,
                            'optimization_score': score
                        }
                    )
                    
            except Exception as e:
                logger.warning(f"Error evaluating price {price}: {str(e)}")
                continue
        
        if best_result is None:
            # Fallback to simple prediction
            return self.predict_optimal_price(context)
        
        return best_result
    
    def _get_model(self, model_type: str) -> Optional[MLModel]:
        """Get active ML model for the given type."""
        cache_key = f"{self.organization.id}_{model_type}"
        
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]
        
        try:
            model = MLModel.objects.get(
                organization=self.organization,
                model_type=model_type,
                status='active',
                is_default=True
            )
            
            # Load the actual model artifact
            if model.model_file_path and Path(model.model_file_path).exists():
                model.sklearn_model = joblib.load(model.model_file_path)
                self.models_cache[cache_key] = model
                return model
            else:
                logger.warning(f"Model file not found: {model.model_file_path}")
                return None
                
        except MLModel.DoesNotExist:
            logger.warning(f"No active model found for type: {model_type}")
            return None
    
    def _prepare_features(self, context: MLPricingContext, model: MLModel) -> Dict[str, float]:
        """Prepare features for ML model prediction."""
        features = {}
        
        # Basic features
        features.update({
            'current_price': context.current_price,
            'cost': context.cost,
            'margin': (context.current_price - context.cost) / context.current_price if context.current_price > 0 else 0,
            'inventory_level': context.inventory_level,
            'sales_velocity': context.sales_velocity,
        })
        
        # Competitor features
        if context.competitor_prices:
            features.update({
                'competitor_min_price': min(context.competitor_prices),
                'competitor_max_price': max(context.competitor_prices),
                'competitor_avg_price': sum(context.competitor_prices) / len(context.competitor_prices),
                'competitor_count': len(context.competitor_prices),
                'price_rank': sum(1 for p in context.competitor_prices if p < context.current_price) + 1,
                'price_percentile': (sum(1 for p in context.competitor_prices if p < context.current_price) / len(context.competitor_prices)) if context.competitor_prices else 0.5,
            })
        else:
            features.update({
                'competitor_min_price': 0,
                'competitor_max_price': 0,
                'competitor_avg_price': 0,
                'competitor_count': 0,
                'price_rank': 1,
                'price_percentile': 0.5,
            })
        
        # Historical features
        if context.historical_prices:
            features.update({
                'price_trend': (context.historical_prices[-1] - context.historical_prices[0]) / len(context.historical_prices) if len(context.historical_prices) > 1 else 0,
                'price_volatility': np.std(context.historical_prices) if len(context.historical_prices) > 1 else 0,
                'avg_historical_price': np.mean(context.historical_prices),
            })
        
        if context.historical_sales:
            features.update({
                'sales_trend': (context.historical_sales[-1] - context.historical_sales[0]) / len(context.historical_sales) if len(context.historical_sales) > 1 else 0,
                'sales_volatility': np.std(context.historical_sales) if len(context.historical_sales) > 1 else 0,
                'avg_historical_sales': np.mean(context.historical_sales),
            })
        
        # Categorical features (one-hot encoded)
        features[f'marketplace_{context.marketplace}'] = 1
        features[f'category_{context.category}'] = 1
        features[f'brand_{context.brand}'] = 1
        
        # Seasonality features
        features.update(context.seasonality_factors)
        
        # Demand indicators
        features.update(context.demand_indicators)
        
        # Market conditions
        features.update(context.market_conditions)
        
        # Custom features
        features.update(context.custom_features)
        
        # Filter features to only include those expected by the model
        model_features = model.features
        filtered_features = {k: v for k, v in features.items() if k in model_features}
        
        # Add missing features with default values
        for feature in model_features:
            if feature not in filtered_features:
                filtered_features[feature] = 0.0
        
        return filtered_features
    
    def _make_prediction(self, model: MLModel, features: Dict[str, float]) -> Tuple[float, float]:
        """Make prediction using the model."""
        if not hasattr(model, 'sklearn_model'):
            raise ValueError("Model not loaded")
        
        # Convert features to array in correct order
        feature_array = np.array([[features[f] for f in model.features]])
        
        # Make prediction
        prediction = model.sklearn_model.predict(feature_array)[0]
        
        # Calculate confidence (this is a simplified approach)
        # In practice, you might use prediction intervals or ensemble variance
        confidence = 0.8  # Default confidence
        
        if hasattr(model.sklearn_model, 'predict_proba'):
            # For classification models
            probabilities = model.sklearn_model.predict_proba(feature_array)[0]
            confidence = max(probabilities)
        elif hasattr(model.sklearn_model, 'estimators_'):
            # For ensemble models, use variance of individual predictions
            individual_predictions = [estimator.predict(feature_array)[0] 
                                    for estimator in model.sklearn_model.estimators_]
            variance = np.var(individual_predictions)
            confidence = max(0.1, min(0.99, 1.0 - (variance / (prediction ** 2)) if prediction != 0 else 0.1))
        
        return float(prediction), float(confidence)
    
    def _get_feature_importance(self, model: MLModel, features: Dict[str, float]) -> Dict[str, float]:
        """Get feature importance from the model."""
        if not hasattr(model, 'sklearn_model') or not hasattr(model.sklearn_model, 'feature_importances_'):
            return {}
        
        importances = model.sklearn_model.feature_importances_
        return dict(zip(model.features, importances))
    
    def _log_prediction(self, model: MLModel, context: MLPricingContext, 
                       prediction: float, confidence: float, features: Dict[str, float]):
        """Log prediction for audit and analysis."""
        try:
            ModelPrediction.objects.create(
                organization=self.organization,
                model=model,
                product_id=context.product_id,
                marketplace=context.marketplace,
                input_features=features,
                prediction_value=prediction,
                confidence_score=confidence,
                model_version=model.version,
                metadata={
                    'context_features_count': len(features),
                    'competitor_prices_count': len(context.competitor_prices),
                    'historical_data_points': len(context.historical_prices) + len(context.historical_sales)
                }
            )
        except Exception as e:
            logger.error(f"Failed to log prediction: {str(e)}")


class FeatureStoreManager:
    """
    Manager for feature store operations.
    """
    
    def __init__(self, organization):
        self.organization = organization
    
    def get_features(self, product_id: str, marketplace: str, 
                    feature_groups: List[str] = None) -> Dict[str, float]:
        """
        Get features for a product from the feature store.
        
        Args:
            product_id: Product identifier
            marketplace: Marketplace name
            feature_groups: List of feature groups to retrieve
        
        Returns:
            Dictionary of features
        """
        # This would typically query a feature store database or API
        # For now, return mock features
        
        features = {}
        
        if not feature_groups:
            feature_groups = ['pricing', 'demand', 'competition', 'seasonality']
        
        for group in feature_groups:
            group_features = self._get_feature_group(product_id, marketplace, group)
            features.update(group_features)
        
        return features
    
    def _get_feature_group(self, product_id: str, marketplace: str, group: str) -> Dict[str, float]:
        """Get features for a specific group."""
        # Mock implementation - in practice, this would query actual feature store
        
        if group == 'pricing':
            return {
                'price_7d_avg': 25.99,
                'price_30d_avg': 26.50,
                'price_trend_7d': -0.02,
                'price_volatility_7d': 1.2,
            }
        
        elif group == 'demand':
            return {
                'demand_score': 0.75,
                'search_volume': 1500,
                'conversion_rate': 0.12,
                'pageviews_7d': 850,
            }
        
        elif group == 'competition':
            return {
                'competitor_count': 15,
                'avg_competitor_price': 24.99,
                'price_position': 0.6,
                'buy_box_share_7d': 0.35,
            }
        
        elif group == 'seasonality':
            return {
                'seasonal_index': 1.1,
                'day_of_week_factor': 0.95,
                'month_factor': 1.05,
                'holiday_proximity': 0.0,
            }
        
        return {}
    
    def update_features(self, product_id: str, marketplace: str, 
                       features: Dict[str, float]):
        """Update features in the feature store."""
        # In practice, this would update the feature store
        pass
