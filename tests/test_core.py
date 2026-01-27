# tests/test_core.py
"""
Tests for core module (types, classifier, judgment).
"""

import pytest

from core.types import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
    RightOperand,
    ConstraintMetadata,
    Judgment,
)
from core.classifier import classify_operand, classify_constraint, ClassificationResult
from registry import ConstraintClass


class TestRightOperand:
    """Test RightOperand creation and properties."""
    
    def test_literal_integer(self):
        ro = RightOperand.literal(42)
        assert ro.value == 42
        assert not ro.is_iri
        assert not ro.is_policy_usage
    
    def test_literal_float(self):
        ro = RightOperand.literal(3.14)
        assert ro.value == 3.14
        assert not ro.is_iri
    
    def test_literal_string(self):
        ro = RightOperand.literal("test")
        assert ro.value == "test"
        assert not ro.is_iri
    
    def test_iri(self):
        ro = RightOperand.iri("http://example.org/value")
        assert ro.value == "http://example.org/value"
        assert ro.is_iri
        assert not ro.is_policy_usage
    
    def test_policy_usage(self):
        ro = RightOperand.policy_usage()
        assert ro.is_policy_usage
        assert not ro.is_iri


class TestAtomicConstraint:
    """Test AtomicConstraint creation and string representation."""
    
    def test_basic_creation(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(10)
        )
        assert c.uid == "test"
        assert c.left_operand == "count"
        assert c.operator == OperatorType.LTEQ
        assert c.right_operand.value == 10
    
    def test_str_representation(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.EQ,
            right_operand=RightOperand.literal(5)
        )
        assert str(c) == "count eq 5"
    
    def test_with_metadata(self):
        meta = ConstraintMetadata(unit="http://example.org/EUR")
        c = AtomicConstraint(
            uid="test",
            left_operand="payAmount",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(100),
            metadata=meta
        )
        assert c.unit == "http://example.org/EUR"
    
    def test_unit_shortcut(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="payAmount",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(100),
            metadata=ConstraintMetadata(unit="EUR")
        )
        assert c.unit == "EUR"


class TestCompositeConstraint:
    """Test CompositeConstraint creation."""
    
    def test_and_constraint(self):
        c = CompositeConstraint(
            uid="composite1",
            operator=LogicalOperator.AND,
            operands=["c1", "c2", "c3"]
        )
        assert c.operator == LogicalOperator.AND
        assert len(c.operands) == 3
    
    def test_or_constraint(self):
        c = CompositeConstraint(
            uid="composite2",
            operator=LogicalOperator.OR,
            operands=["c1", "c2"]
        )
        assert c.operator == LogicalOperator.OR
    
    def test_xone_constraint(self):
        c = CompositeConstraint(
            uid="composite3",
            operator=LogicalOperator.XONE,
            operands=["c1", "c2"]
        )
        assert c.operator == LogicalOperator.XONE


class TestOperatorType:
    """Test OperatorType enum."""
    
    def test_comparison_operators(self):
        assert OperatorType.EQ.is_comparison()
        assert OperatorType.NEQ.is_comparison()
        assert OperatorType.LT.is_comparison()
        assert OperatorType.LTEQ.is_comparison()
        assert OperatorType.GT.is_comparison()
        assert OperatorType.GTEQ.is_comparison()
    
    def test_set_operators(self):
        assert OperatorType.IS_A.is_set_based()
        assert OperatorType.IS_ANY_OF.is_set_based()
        assert OperatorType.IS_ALL_OF.is_set_based()
        assert OperatorType.IS_NONE_OF.is_set_based()
        assert OperatorType.HAS_PART.is_set_based()
        assert OperatorType.IS_PART_OF.is_set_based()
    
    def test_operator_values(self):
        """Test operator enum values."""
        assert OperatorType.EQ.value == "eq"
        assert OperatorType.LTEQ.value == "lteq"
        assert OperatorType.GTEQ.value == "gteq"
        assert OperatorType.NEQ.value == "neq"
    
    def test_from_string(self):
        """Test parsing operator from string/URI."""
        assert OperatorType.from_string("http://www.w3.org/ns/odrl/2/eq") == OperatorType.EQ
        assert OperatorType.from_string("lteq") == OperatorType.LTEQ
        assert OperatorType.from_string("gteq") == OperatorType.GTEQ
        assert OperatorType.from_string("isAnyOf") == OperatorType.IS_ANY_OF


class TestClassifier:
    """Test constraint classifier."""
    
    def test_full_operand(self):
        result = classify_operand("count")
        assert result.constraint_class == ConstraintClass.FULL
        assert result.can_analyze
    
    def test_partial_operand(self):
        result = classify_operand("elapsedTime")
        assert result.constraint_class == ConstraintClass.PARTIAL
        assert result.can_analyze
    
    def test_grounded_operand(self):
        result = classify_operand("language")
        assert result.constraint_class == ConstraintClass.GROUNDED
        assert result.oracle_needed == "LanguageOracle"
    
    def test_runtime_operand(self):
        result = classify_operand("meteredTime")
        assert result.constraint_class == ConstraintClass.RUNTIME
        assert not result.can_analyze
    
    def test_unknown_operand(self):
        result = classify_operand("unknownOperand")
        assert result.constraint_class == ConstraintClass.RUNTIME
    
    def test_classify_constraint(self):
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(10)
        )
        result = classify_constraint(c)
        assert result.constraint_class == ConstraintClass.FULL


class TestJudgment:
    """Test Judgment enum."""
    
    def test_judgment_values(self):
        assert Judgment.CONFLICT.value == "CONFLICT"
        assert Judgment.POSSIBLY_COMPATIBLE.value == "POSSIBLY-COMPATIBLE"
        assert Judgment.UNKNOWN.value == "UNKNOWN"
