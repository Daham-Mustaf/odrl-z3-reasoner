# tests/test_registry.py
"""
Tests for registry module (configuration-driven operand registry).
"""

import pytest

from registry import (
    OperandRegistry,
    get_registry,
    reset_registry,
    ConstraintClass,
    Z3Sort,
    OperandInfo,
)


class TestOperandRegistry:
    """Test OperandRegistry functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset registry before each test."""
        reset_registry()
    
    def test_registry_loads(self):
        """Test that registry loads from config."""
        registry = get_registry()
        assert registry is not None
        assert len(registry.get_all_operands()) > 0
    
    def test_operand_count(self):
        """Test that all 31 operands are loaded."""
        registry = get_registry()
        assert len(registry.get_all_operands()) == 31
    
    def test_get_operand_info(self):
        """Test getting operand info."""
        registry = get_registry()
        
        info = registry.get_operand("count")
        assert info is not None
        assert info.name == "count"
        assert info.constraint_class == ConstraintClass.FULL
        assert info.z3_sort == Z3Sort.INT
    
    def test_get_class(self):
        """Test getting operand class."""
        registry = get_registry()
        
        assert registry.get_class("count") == ConstraintClass.FULL
        assert registry.get_class("elapsedTime") == ConstraintClass.PARTIAL
        assert registry.get_class("language") == ConstraintClass.GROUNDED
        assert registry.get_class("meteredTime") == ConstraintClass.RUNTIME
    
    def test_get_domain(self):
        """Test getting operand domain."""
        registry = get_registry()
        
        # count: 0 to infinity
        min_val, max_val = registry.get_domain("count")
        assert min_val == 0
        assert max_val is None
        
        # percentage: 0 to 100
        min_val, max_val = registry.get_domain("percentage")
        assert min_val == 0
        assert max_val == 100
    
    def test_get_normalizer(self):
        """Test getting normalizer name."""
        registry = get_registry()
        
        assert registry.get_normalizer("count") == "to_integer"
        assert registry.get_normalizer("percentage") == "to_float"
        assert registry.get_normalizer("dateTime") == "datetime_to_timestamp"
        assert registry.get_normalizer("elapsedTime") == "duration_to_seconds"
    
    def test_get_oracle_name(self):
        """Test getting oracle name for grounded operands."""
        registry = get_registry()
        
        assert registry.get_oracle_name("language") == "LanguageOracle"
        assert registry.get_oracle_name("purpose") == "PurposeOracle"
        assert registry.get_oracle_name("count") is None
    
    def test_needs_oracle(self):
        """Test needs_oracle check."""
        registry = get_registry()
        
        assert registry.needs_oracle("language")
        assert registry.needs_oracle("purpose")
        assert not registry.needs_oracle("count")
        assert not registry.needs_oracle("elapsedTime")
    
    def test_get_operands_by_class(self):
        """Test getting operands by class."""
        registry = get_registry()
        
        full_ops = registry.get_operands_by_class(ConstraintClass.FULL)
        assert "count" in full_ops
        assert "percentage" in full_ops
        assert "dateTime" in full_ops
        assert len(full_ops) == 14
        
        partial_ops = registry.get_operands_by_class(ConstraintClass.PARTIAL)
        assert "elapsedTime" in partial_ops
        assert "delayPeriod" in partial_ops
        assert len(partial_ops) == 2
        
        grounded_ops = registry.get_operands_by_class(ConstraintClass.GROUNDED)
        assert "language" in grounded_ops
        assert "purpose" in grounded_ops
        assert len(grounded_ops) == 13
    
    def test_uri_normalization(self):
        """Test that URIs are normalized to local names."""
        registry = get_registry()
        
        # Full URI
        info = registry.get_operand("http://www.w3.org/ns/odrl/2/count")
        assert info is not None
        assert info.name == "count"
        
        # Fragment URI
        info = registry.get_operand("count")
        assert info is not None
    
    def test_operator_info(self):
        """Test getting operator info."""
        registry = get_registry()
        
        op = registry.get_operator("eq")
        assert op is not None
        assert op.symbol == "="
        assert op.category == "comparison"
        
        op = registry.get_operator("isA")
        assert op is not None
        assert op.requires_oracle
    
    def test_statistics(self):
        """Test registry statistics."""
        registry = get_registry()
        
        stats = registry.get_statistics()
        assert stats['total_operands'] == 31
        assert stats['class_counts']['FULL'] == 14
        assert stats['class_counts']['PARTIAL'] == 2
        assert stats['class_counts']['GROUNDED'] == 13
        assert stats['class_counts']['RUNTIME'] == 1
