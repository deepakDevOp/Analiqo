"""
Unit tests for the pricing rules engine.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from pricing_rules.engine import PricingRulesEngine, PricingContext, PricingResult
from pricing_rules.models import PricingStrategy, RuleSet, PricingRule, SafetyConstraint


@pytest.mark.unit
class TestPricingRulesEngine:
    """Test cases for the pricing rules engine."""
    
    def test_engine_initialization(self, organization):
        """Test engine initializes correctly."""
        engine = PricingRulesEngine(organization)
        assert engine.organization == organization
        assert engine.rules_cache == {}
        assert engine.safety_constraints_cache == {}
    
    def test_evaluate_pricing_no_strategy(self, organization, sample_pricing_context):
        """Test pricing evaluation when no strategy exists."""
        engine = PricingRulesEngine(organization)
        result = engine.evaluate_pricing(sample_pricing_context)
        
        assert isinstance(result, PricingResult)
        assert result.new_price == sample_pricing_context.current_price
        assert result.confidence == 0.0
        assert "No valid pricing strategy found" in result.reason
        assert not result.safety_checks_passed
    
    def test_evaluate_pricing_with_strategy(self, organization, pricing_strategy, sample_pricing_context):
        """Test pricing evaluation with a strategy."""
        engine = PricingRulesEngine(organization)
        
        with patch.object(engine, '_get_applicable_rules') as mock_rules, \
             patch.object(engine, '_apply_rules') as mock_apply, \
             patch.object(engine, '_apply_safety_constraints') as mock_safety:
            
            mock_rules.return_value = []
            mock_apply.return_value = PricingResult(
                new_price=Decimal('28.99'),
                confidence=0.8,
                reason='Test rule applied',
                rules_applied=['test_rule'],
                safety_checks_passed=True,
                warnings=[],
                metadata={}
            )
            mock_safety.return_value = mock_apply.return_value
            
            result = engine.evaluate_pricing(sample_pricing_context, str(pricing_strategy.id))
            
            assert result.new_price == Decimal('28.99')
            assert result.confidence == 0.8
            assert 'test_rule' in result.rules_applied
    
    def test_get_strategy_by_id(self, organization, pricing_strategy):
        """Test getting strategy by ID."""
        engine = PricingRulesEngine(organization)
        strategy = engine._get_strategy(str(pricing_strategy.id))
        
        assert strategy == pricing_strategy
    
    def test_get_default_strategy(self, organization, pricing_strategy):
        """Test getting default strategy."""
        engine = PricingRulesEngine(organization)
        strategy = engine._get_strategy()
        
        assert strategy == pricing_strategy
    
    def test_evaluate_rule_set_conditions_match(self, organization, rule_set, sample_pricing_context):
        """Test rule set condition evaluation when conditions match."""
        engine = PricingRulesEngine(organization)
        
        # Update rule set conditions to match context
        rule_set.conditions = {
            'marketplace': ['amazon'],
            'category': ['electronics']
        }
        rule_set.save()
        
        result = engine._evaluate_rule_set_conditions(rule_set, sample_pricing_context)
        assert result is True
    
    def test_evaluate_rule_set_conditions_no_match(self, organization, rule_set, sample_pricing_context):
        """Test rule set condition evaluation when conditions don't match."""
        engine = PricingRulesEngine(organization)
        
        # Update rule set conditions to not match context
        rule_set.conditions = {
            'marketplace': ['flipkart'],
            'category': ['books']
        }
        rule_set.save()
        
        result = engine._evaluate_rule_set_conditions(rule_set, sample_pricing_context)
        assert result is False
    
    def test_apply_price_adjustment_percentage_increase(self, organization):
        """Test percentage price increase adjustment."""
        engine = PricingRulesEngine(organization)
        
        new_price = engine._apply_price_adjustment(
            Decimal('100.00'),
            Decimal('10'),  # 10%
            'increase_percentage'
        )
        
        assert new_price == Decimal('110.00')
    
    def test_apply_price_adjustment_percentage_decrease(self, organization):
        """Test percentage price decrease adjustment."""
        engine = PricingRulesEngine(organization)
        
        new_price = engine._apply_price_adjustment(
            Decimal('100.00'),
            Decimal('15'),  # 15%
            'decrease_percentage'
        )
        
        assert new_price == Decimal('85.00')
    
    def test_apply_price_adjustment_amount_increase(self, organization):
        """Test amount price increase adjustment."""
        engine = PricingRulesEngine(organization)
        
        new_price = engine._apply_price_adjustment(
            Decimal('100.00'),
            Decimal('5.50'),
            'increase_amount'
        )
        
        assert new_price == Decimal('105.50')
    
    def test_apply_price_adjustment_set_price(self, organization):
        """Test set price adjustment."""
        engine = PricingRulesEngine(organization)
        
        new_price = engine._apply_price_adjustment(
            Decimal('100.00'),
            Decimal('89.99'),
            'set_price'
        )
        
        assert new_price == Decimal('89.99')
    
    def test_check_safety_constraint_min_margin_pass(self, organization, sample_pricing_context):
        """Test safety constraint check for minimum margin - passing."""
        engine = PricingRulesEngine(organization)
        
        # Create safety constraint
        constraint = SafetyConstraint(
            constraint_type='min_margin',
            threshold=0.15,  # 15% minimum margin
            action='warn'
        )
        
        # Test price that gives 20% margin
        new_price = Decimal('20.00')  # Cost is 15.00, so margin is 25%
        
        result = engine._check_safety_constraint(constraint, new_price, sample_pricing_context)
        
        assert result['passed'] is True
    
    def test_check_safety_constraint_min_margin_fail(self, organization, sample_pricing_context):
        """Test safety constraint check for minimum margin - failing."""
        engine = PricingRulesEngine(organization)
        
        constraint = SafetyConstraint(
            constraint_type='min_margin',
            threshold=0.25,  # 25% minimum margin
            action='adjust'
        )
        
        # Test price that gives 10% margin
        new_price = Decimal('16.67')  # Cost is 15.00, so margin is ~10%
        
        result = engine._check_safety_constraint(constraint, new_price, sample_pricing_context)
        
        assert result['passed'] is False
        assert 'suggested_price' in result
    
    def test_check_safety_constraint_max_price_change(self, organization, sample_pricing_context):
        """Test safety constraint for maximum price change."""
        engine = PricingRulesEngine(organization)
        
        constraint = SafetyConstraint(
            constraint_type='max_price_change',
            threshold=0.10,  # 10% max change
            action='adjust'
        )
        
        # Test price change of 20%
        new_price = Decimal('35.99')  # Current is 29.99, so ~20% increase
        
        result = engine._check_safety_constraint(constraint, new_price, sample_pricing_context)
        
        assert result['passed'] is False
        assert 'suggested_price' in result
    
    def test_simulate_pricing(self, organization, pricing_strategy, sample_pricing_context):
        """Test pricing simulation for multiple contexts."""
        engine = PricingRulesEngine(organization)
        
        contexts = [sample_pricing_context]
        
        with patch.object(engine, 'evaluate_pricing') as mock_evaluate:
            mock_result = PricingResult(
                new_price=Decimal('28.99'),
                confidence=0.8,
                reason='Simulated',
                rules_applied=[],
                safety_checks_passed=True,
                warnings=[],
                metadata={}
            )
            mock_evaluate.return_value = mock_result
            
            results = engine.simulate_pricing(contexts, str(pricing_strategy.id))
            
            assert len(results) == 1
            assert results[0] == mock_result
            mock_evaluate.assert_called_once_with(sample_pricing_context, str(pricing_strategy.id))


@pytest.mark.unit
class TestPricingContext:
    """Test cases for pricing context."""
    
    def test_pricing_context_initialization(self):
        """Test pricing context initializes correctly."""
        context = PricingContext(
            product_id='TEST-001',
            current_price=Decimal('29.99'),
            cost=Decimal('15.00'),
            inventory_level=100,
            competitor_prices=[Decimal('28.99')],
            sales_velocity=5.0,
            marketplace='amazon',
            category='electronics',
            brand='test'
        )
        
        assert context.product_id == 'TEST-001'
        assert context.current_price == Decimal('29.99')
        assert context.cost == Decimal('15.00')
        assert context.inventory_level == 100
        assert context.competitor_prices == [Decimal('28.99')]
        assert context.sales_velocity == 5.0
        assert context.marketplace == 'amazon'
        assert context.category == 'electronics'
        assert context.brand == 'test'
        assert context.custom_attributes == {}
    
    def test_pricing_context_with_custom_attributes(self):
        """Test pricing context with custom attributes."""
        custom_attrs = {'special_promo': True, 'supplier_id': 'SUP-001'}
        
        context = PricingContext(
            product_id='TEST-001',
            current_price=Decimal('29.99'),
            cost=Decimal('15.00'),
            inventory_level=100,
            competitor_prices=[],
            sales_velocity=5.0,
            marketplace='amazon',
            category='electronics',
            brand='test',
            custom_attributes=custom_attrs
        )
        
        assert context.custom_attributes == custom_attrs


@pytest.mark.unit
class TestPricingResult:
    """Test cases for pricing result."""
    
    def test_pricing_result_initialization(self):
        """Test pricing result initializes correctly."""
        result = PricingResult(
            new_price=Decimal('28.99'),
            confidence=0.85,
            reason='Competitor undercut detected',
            rules_applied=['undercut_rule', 'margin_check'],
            safety_checks_passed=True,
            warnings=['High competition detected'],
            metadata={'competitor_count': 5}
        )
        
        assert result.new_price == Decimal('28.99')
        assert result.confidence == 0.85
        assert result.reason == 'Competitor undercut detected'
        assert result.rules_applied == ['undercut_rule', 'margin_check']
        assert result.safety_checks_passed is True
        assert result.warnings == ['High competition detected']
        assert result.metadata == {'competitor_count': 5}
