# tests/test_normalizer.py
"""
Tests for normalizer module.
"""

import pytest
from decimal import Decimal
from datetime import timedelta

from normalizer import (
    normalize_value,
    get_normalized_value,
    NormalizationResult,
    NORMALIZERS,
)
from core.constraint_types import AtomicConstraint, OperatorType, RightOperand


class TestNormalizeValue:
    """Test normalize_value function."""
    
    def test_integer_normalization(self):
        """Test integer normalization."""
        result = normalize_value("42", "count")
        assert result.success
        assert result.value == 42
        assert isinstance(result.value, int)
    
    def test_float_normalization(self):
        """Test float normalization."""
        result = normalize_value("3.14", "percentage")
        assert result.success
        assert result.value == 3.14
        assert isinstance(result.value, float)
    
    def test_decimal_normalization(self):
        """Test Decimal input normalization."""
        result = normalize_value(Decimal("99.5"), "percentage")
        assert result.success
        assert result.value == 99.5
        assert isinstance(result.value, float)
    
    def test_datetime_normalization(self):
        """Test datetime string normalization."""
        result = normalize_value("2024-01-01T00:00:00Z", "dateTime")
        assert result.success
        assert isinstance(result.value, int)
        assert result.value > 0
    
    def test_datetime_date_only(self):
        """Test date-only string normalization."""
        result = normalize_value("2024-06-15", "dateTime")
        assert result.success
        assert isinstance(result.value, int)


class TestDurationNormalization:
    """Test ISO 8601 duration normalization."""
    
    def test_seconds(self):
        result = normalize_value("PT1S", "elapsedTime")
        assert result.success
        assert result.value == 1
    
    def test_minutes(self):
        result = normalize_value("PT1M", "elapsedTime")
        assert result.success
        assert result.value == 60
    
    def test_hours(self):
        result = normalize_value("PT1H", "elapsedTime")
        assert result.success
        assert result.value == 3600
    
    def test_days(self):
        result = normalize_value("P1D", "elapsedTime")
        assert result.success
        assert result.value == 86400
    
    def test_combined_duration(self):
        result = normalize_value("PT1H30M", "elapsedTime")
        assert result.success
        assert result.value == 5400  # 1.5 hours
    
    def test_day_and_hours(self):
        result = normalize_value("P1DT12H", "elapsedTime")
        assert result.success
        assert result.value == 129600  # 36 hours
    
    def test_year(self):
        result = normalize_value("P1Y", "elapsedTime")
        assert result.success
        assert result.value == 365 * 24 * 3600
    
    def test_timedelta_input(self):
        """Test timedelta input (from RDFLib)."""
        result = normalize_value(timedelta(hours=2), "elapsedTime")
        assert result.success
        assert result.value == 7200
    
    def test_numeric_passthrough(self):
        """Test numeric values pass through."""
        result = normalize_value(3600, "elapsedTime")
        assert result.success
        assert result.value == 3600


class TestNormalizerRegistry:
    """Test normalizer registry."""
    
    def test_all_normalizers_exist(self):
        """Test that all expected normalizers exist."""
        expected = [
            'to_integer',
            'to_float',
            'datetime_to_timestamp',
            'duration_to_seconds',
            'to_uri',
            'none',
        ]
        for name in expected:
            assert name in NORMALIZERS
    
    def test_normalizer_override(self):
        """Test normalizer override."""
        # Force integer normalization on a percentage value
        result = normalize_value("42.7", "percentage", normalizer_override="to_integer")
        assert result.value == 42
        assert isinstance(result.value, int)


class TestGetNormalizedValue:
    """Test get_normalized_value with constraints."""
    
    def test_basic_constraint(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal("10")
        )
        value = get_normalized_value(c)
        assert value == 10
        assert isinstance(value, int)
    
    def test_decimal_constraint(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="percentage",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(Decimal("75.5"))
        )
        value = get_normalized_value(c)
        assert value == 75.5
        assert isinstance(value, float)
    
    def test_duration_constraint(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="elapsedTime",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(timedelta(hours=1))
        )
        value = get_normalized_value(c)
        assert value == 3600
    
    def test_policy_usage_returns_none(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.policy_usage()
        )
        value = get_normalized_value(c)
        assert value is None


class TestErrorHandling:
    """Test normalization error handling."""
    
    def test_invalid_datetime(self):
        result = normalize_value("not-a-date", "dateTime")
        assert not result.success
        assert result.error is not None
    
    def test_invalid_duration(self):
        result = normalize_value("not-a-duration", "elapsedTime")
        assert not result.success
    
    def test_unknown_operand_uses_none(self):
        """Unknown operands use 'none' normalizer."""
        result = normalize_value("anything", "unknownOperand")
        assert result.success
        assert result.value == "anything"  # Passed through
