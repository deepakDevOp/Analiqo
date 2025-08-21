"""
Pricing rules engine for dynamic price optimization.
"""

from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging

from django.db.models import Q
from .models import PricingStrategy, RuleSet, PricingRule, SafetyConstraint, RuleExecution

logger = logging.getLogger(__name__)


@dataclass
class PricingContext:
    """Context for pricing rule evaluation."""
    product_id: str
    current_price: Decimal
    cost: Decimal
    inventory_level: int
    competitor_prices: List[Decimal]
    sales_velocity: float
    marketplace: str
    category: str
    brand: str
    seasonality_factor: float = 1.0
    demand_score: float = 1.0
    buy_box_status: str = 'unknown'
    margin_target: float = 0.2
    custom_attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_attributes is None:
            self.custom_attributes = {}


@dataclass
class PricingResult:
    """Result of pricing rule evaluation."""
    new_price: Decimal
    confidence: float
    reason: str
    rules_applied: List[str]
    safety_checks_passed: bool
    warnings: List[str]
    metadata: Dict[str, Any]


class PricingRulesEngine:
    """
    Main pricing rules engine that evaluates strategies and applies rules.
    """
    
    def __init__(self, organization):
        self.organization = organization
        self.rules_cache = {}
        self.safety_constraints_cache = {}
    
    def evaluate_pricing(self, context: PricingContext, strategy_id: Optional[str] = None) -> PricingResult:
        """
        Evaluate pricing for a product using the specified strategy or default strategy.
        
        Args:
            context: Pricing context with product and market data
            strategy_id: Optional strategy ID to use; defaults to organization's default
        
        Returns:
            PricingResult with new price and metadata
        """
        try:
            # Get pricing strategy
            strategy = self._get_strategy(strategy_id)
            if not strategy:
                return PricingResult(
                    new_price=context.current_price,
                    confidence=0.0,
                    reason="No valid pricing strategy found",
                    rules_applied=[],
                    safety_checks_passed=False,
                    warnings=["No pricing strategy available"],
                    metadata={}
                )
            
            # Get applicable rules for this strategy
            rules = self._get_applicable_rules(strategy, context)
            
            # Apply rules in priority order
            pricing_result = self._apply_rules(rules, context, strategy)
            
            # Apply safety constraints
            final_result = self._apply_safety_constraints(pricing_result, context, strategy)
            
            # Log rule execution
            self._log_execution(strategy, final_result, context)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Pricing evaluation failed: {str(e)}")
            return PricingResult(
                new_price=context.current_price,
                confidence=0.0,
                reason=f"Error during pricing evaluation: {str(e)}",
                rules_applied=[],
                safety_checks_passed=False,
                warnings=[f"Evaluation error: {str(e)}"],
                metadata={}
            )
    
    def _get_strategy(self, strategy_id: Optional[str] = None) -> Optional[PricingStrategy]:
        """Get pricing strategy by ID or default strategy."""
        try:
            if strategy_id:
                return PricingStrategy.objects.get(
                    id=strategy_id,
                    organization=self.organization,
                    is_active=True
                )
            else:
                # Get default strategy
                return PricingStrategy.objects.filter(
                    organization=self.organization,
                    is_active=True,
                    is_default=True
                ).first()
        except PricingStrategy.DoesNotExist:
            return None
    
    def _get_applicable_rules(self, strategy: PricingStrategy, context: PricingContext) -> List[PricingRule]:
        """Get rules applicable to the given context."""
        # Get all rule sets for this strategy
        rule_sets = RuleSet.objects.filter(
            strategy=strategy,
            is_active=True
        ).prefetch_related('rules')
        
        applicable_rules = []
        
        for rule_set in rule_sets:
            # Check if rule set conditions match context
            if self._evaluate_rule_set_conditions(rule_set, context):
                # Add all active rules from this rule set
                rules = rule_set.rules.filter(is_active=True).order_by('priority')
                applicable_rules.extend(rules)
        
        # Sort by priority (lower number = higher priority)
        return sorted(applicable_rules, key=lambda r: r.priority)
    
    def _evaluate_rule_set_conditions(self, rule_set: RuleSet, context: PricingContext) -> bool:
        """Check if rule set conditions match the context."""
        conditions = rule_set.conditions
        
        if not conditions:
            return True  # No conditions means always applicable
        
        # Check marketplace
        if 'marketplace' in conditions:
            if context.marketplace not in conditions['marketplace']:
                return False
        
        # Check category
        if 'category' in conditions:
            if context.category not in conditions['category']:
                return False
        
        # Check brand
        if 'brand' in conditions:
            if context.brand not in conditions['brand']:
                return False
        
        # Check inventory level
        if 'inventory_min' in conditions:
            if context.inventory_level < conditions['inventory_min']:
                return False
        
        if 'inventory_max' in conditions:
            if context.inventory_level > conditions['inventory_max']:
                return False
        
        # Check price range
        if 'price_min' in conditions:
            if context.current_price < Decimal(str(conditions['price_min'])):
                return False
        
        if 'price_max' in conditions:
            if context.current_price > Decimal(str(conditions['price_max'])):
                return False
        
        return True
    
    def _apply_rules(self, rules: List[PricingRule], context: PricingContext, 
                    strategy: PricingStrategy) -> PricingResult:
        """Apply pricing rules to calculate new price."""
        new_price = context.current_price
        rules_applied = []
        warnings = []
        confidence = 1.0
        reasons = []
        metadata = {}
        
        for rule in rules:
            try:
                # Evaluate rule condition
                if self._evaluate_rule_condition(rule, context):
                    # Apply rule action
                    price_adjustment = self._calculate_rule_adjustment(rule, context)
                    
                    if price_adjustment != 0:
                        old_price = new_price
                        new_price = self._apply_price_adjustment(new_price, price_adjustment, rule.action_type)
                        
                        rules_applied.append(rule.name)
                        reasons.append(f"{rule.name}: {rule.action_type} {price_adjustment}")
                        
                        # Adjust confidence based on rule weight
                        rule_weight = rule.metadata.get('weight', 1.0) if rule.metadata else 1.0
                        confidence *= rule_weight
                        
                        logger.info(f"Applied rule '{rule.name}': {old_price} -> {new_price}")
                
            except Exception as e:
                logger.error(f"Error applying rule '{rule.name}': {str(e)}")
                warnings.append(f"Rule '{rule.name}' failed: {str(e)}")
        
        return PricingResult(
            new_price=new_price,
            confidence=min(confidence, 1.0),
            reason="; ".join(reasons) if reasons else "No rules applied",
            rules_applied=rules_applied,
            safety_checks_passed=True,  # Will be validated separately
            warnings=warnings,
            metadata=metadata
        )
    
    def _evaluate_rule_condition(self, rule: PricingRule, context: PricingContext) -> bool:
        """Evaluate if rule condition matches the context."""
        condition = rule.condition
        
        if not condition:
            return True  # No condition means always true
        
        try:
            # Build evaluation context
            eval_context = {
                'current_price': float(context.current_price),
                'cost': float(context.cost),
                'inventory': context.inventory_level,
                'competitor_min': float(min(context.competitor_prices)) if context.competitor_prices else 0,
                'competitor_max': float(max(context.competitor_prices)) if context.competitor_prices else 0,
                'competitor_avg': float(sum(context.competitor_prices) / len(context.competitor_prices)) if context.competitor_prices else 0,
                'sales_velocity': context.sales_velocity,
                'seasonality': context.seasonality_factor,
                'demand_score': context.demand_score,
                'margin_current': float((context.current_price - context.cost) / context.current_price) if context.current_price > 0 else 0,
                'margin_target': context.margin_target,
                'buy_box': context.buy_box_status == 'won',
            }
            
            # Add custom attributes
            eval_context.update(context.custom_attributes)
            
            # Evaluate condition as Python expression
            # Note: In production, use a safer expression evaluator
            return eval(condition, {"__builtins__": {}}, eval_context)
            
        except Exception as e:
            logger.error(f"Error evaluating rule condition '{condition}': {str(e)}")
            return False
    
    def _calculate_rule_adjustment(self, rule: PricingRule, context: PricingContext) -> Decimal:
        """Calculate price adjustment from rule action."""
        action_value = rule.action_value
        
        if not action_value:
            return Decimal('0')
        
        try:
            # Build evaluation context for action value
            eval_context = {
                'current_price': float(context.current_price),
                'cost': float(context.cost),
                'inventory': context.inventory_level,
                'competitor_min': float(min(context.competitor_prices)) if context.competitor_prices else 0,
                'competitor_max': float(max(context.competitor_prices)) if context.competitor_prices else 0,
                'competitor_avg': float(sum(context.competitor_prices) / len(context.competitor_prices)) if context.competitor_prices else 0,
                'sales_velocity': context.sales_velocity,
                'seasonality': context.seasonality_factor,
                'demand_score': context.demand_score,
            }
            
            # Evaluate action value as Python expression
            result = eval(action_value, {"__builtins__": {}}, eval_context)
            return Decimal(str(result))
            
        except Exception as e:
            logger.error(f"Error calculating rule adjustment '{action_value}': {str(e)}")
            return Decimal('0')
    
    def _apply_price_adjustment(self, current_price: Decimal, adjustment: Decimal, 
                              action_type: str) -> Decimal:
        """Apply price adjustment based on action type."""
        if action_type == 'increase_percentage':
            return current_price * (1 + adjustment / 100)
        elif action_type == 'decrease_percentage':
            return current_price * (1 - adjustment / 100)
        elif action_type == 'increase_amount':
            return current_price + adjustment
        elif action_type == 'decrease_amount':
            return current_price - adjustment
        elif action_type == 'set_price':
            return adjustment
        elif action_type == 'match_competitor':
            # Use adjustment as competitor price
            return adjustment
        elif action_type == 'undercut_competitor':
            # Adjustment should be the competitor price, undercut by small amount
            return adjustment * Decimal('0.99')  # 1% undercut
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return current_price
    
    def _apply_safety_constraints(self, result: PricingResult, context: PricingContext, 
                                strategy: PricingStrategy) -> PricingResult:
        """Apply safety constraints to the pricing result."""
        constraints = SafetyConstraint.objects.filter(
            strategy=strategy,
            is_active=True
        )
        
        new_price = result.new_price
        warnings = list(result.warnings)
        safety_passed = True
        
        for constraint in constraints:
            constraint_result = self._check_safety_constraint(constraint, new_price, context)
            
            if not constraint_result['passed']:
                safety_passed = False
                
                if constraint.action == 'block':
                    # Revert to original price
                    new_price = context.current_price
                    warnings.append(f"Safety constraint '{constraint.name}' blocked price change")
                    
                elif constraint.action == 'adjust':
                    # Apply suggested adjustment
                    if 'suggested_price' in constraint_result:
                        new_price = constraint_result['suggested_price']
                        warnings.append(f"Safety constraint '{constraint.name}' adjusted price")
                
                elif constraint.action == 'warn':
                    # Just add warning but allow price
                    warnings.append(f"Safety constraint '{constraint.name}' warning: {constraint_result['message']}")
        
        return PricingResult(
            new_price=new_price,
            confidence=result.confidence,
            reason=result.reason,
            rules_applied=result.rules_applied,
            safety_checks_passed=safety_passed,
            warnings=warnings,
            metadata=result.metadata
        )
    
    def _check_safety_constraint(self, constraint: SafetyConstraint, new_price: Decimal, 
                               context: PricingContext) -> Dict[str, Any]:
        """Check if price violates safety constraint."""
        constraint_type = constraint.constraint_type
        
        if constraint_type == 'min_margin':
            threshold = Decimal(str(constraint.threshold))
            margin = (new_price - context.cost) / new_price if new_price > 0 else 0
            
            if margin < threshold:
                # Calculate minimum price for required margin
                min_price = context.cost / (1 - threshold)
                return {
                    'passed': False,
                    'message': f"Margin {margin:.2%} below minimum {threshold:.2%}",
                    'suggested_price': min_price
                }
        
        elif constraint_type == 'max_price_change':
            threshold = Decimal(str(constraint.threshold))
            price_change = abs(new_price - context.current_price) / context.current_price
            
            if price_change > threshold:
                # Limit price change to threshold
                max_change = context.current_price * threshold
                if new_price > context.current_price:
                    suggested_price = context.current_price + max_change
                else:
                    suggested_price = context.current_price - max_change
                
                return {
                    'passed': False,
                    'message': f"Price change {price_change:.2%} exceeds maximum {threshold:.2%}",
                    'suggested_price': suggested_price
                }
        
        elif constraint_type == 'min_price':
            threshold = Decimal(str(constraint.threshold))
            
            if new_price < threshold:
                return {
                    'passed': False,
                    'message': f"Price {new_price} below minimum {threshold}",
                    'suggested_price': threshold
                }
        
        elif constraint_type == 'max_price':
            threshold = Decimal(str(constraint.threshold))
            
            if new_price > threshold:
                return {
                    'passed': False,
                    'message': f"Price {new_price} above maximum {threshold}",
                    'suggested_price': threshold
                }
        
        return {'passed': True, 'message': 'Constraint satisfied'}
    
    def _log_execution(self, strategy: PricingStrategy, result: PricingResult, 
                      context: PricingContext):
        """Log rule execution for audit and analysis."""
        try:
            RuleExecution.objects.create(
                organization=self.organization,
                strategy=strategy,
                product_id=context.product_id,
                marketplace=context.marketplace,
                original_price=context.current_price,
                calculated_price=result.new_price,
                confidence_score=result.confidence,
                rules_applied=result.rules_applied,
                safety_checks_passed=result.safety_checks_passed,
                warnings=result.warnings,
                reason=result.reason,
                context_data={
                    'inventory_level': context.inventory_level,
                    'competitor_prices': [float(p) for p in context.competitor_prices],
                    'sales_velocity': context.sales_velocity,
                    'buy_box_status': context.buy_box_status,
                    'seasonality_factor': context.seasonality_factor,
                    'demand_score': context.demand_score
                }
            )
        except Exception as e:
            logger.error(f"Failed to log rule execution: {str(e)}")
    
    def simulate_pricing(self, contexts: List[PricingContext], 
                        strategy_id: Optional[str] = None) -> List[PricingResult]:
        """
        Simulate pricing for multiple products without applying changes.
        
        Args:
            contexts: List of pricing contexts to simulate
            strategy_id: Optional strategy ID to use
        
        Returns:
            List of pricing results
        """
        results = []
        
        for context in contexts:
            result = self.evaluate_pricing(context, strategy_id)
            results.append(result)
        
        return results
