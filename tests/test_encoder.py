# tests/test_encoder.py
"""
Tests for encoder module (Z3 SMT encoding).
"""

import pytest
from decimal import Decimal
from datetime import timedelta

from core.constraint_types import AtomicConstraint, OperatorType, RightOperand, Judgment
from encoder import Z3JudgmentEngine, check_consistency


class TestZ3JudgmentEngine:
    """Test Z3JudgmentEngine functionality."""
    
    def test_engine_creation(self):
        """Test engine can be created."""
        engine = Z3JudgmentEngine()
        assert engine is not None
    
    def test_encode_eq_constraint(self):
        """Test encoding equality constraint."""
        engine = Z3JudgmentEngine()
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.EQ,
            right_operand=RightOperand.literal(5)
        )
        formula = engine.encode(c)
        assert formula is not None
    
    def test_encode_lteq_constraint(self):
        """Test encoding less-than-or-equal constraint."""
        engine = Z3JudgmentEngine()
        c = AtomicConstraint(
            uid="test",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(10)
        )
        formula = engine.encode(c)
        assert formula is not None


class TestCheckConsistency:
    """Test constraint consistency checking."""
    
    def test_compatible_constraints(self):
        """Test that compatible constraints are detected."""
        c1 = AtomicConstraint(
            uid="c1",
            left_operand="count",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(5)
        )
        c2 = AtomicConstraint(
            uid="c2",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(10)
        )
        
        judgment, model = check_consistency([c1, c2])
        
        assert judgment == Judgment.POSSIBLY_COMPATIBLE
        assert model is not None
        # Model should have a value between 5 and 10
        assert 'count' in str(model).lower() or len(model) > 0
    
    def test_conflicting_constraints(self):
        """Test that conflicting constraints are detected."""
        c1 = AtomicConstraint(
            uid="c1",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(5)
        )
        c2 = AtomicConstraint(
            uid="c2",
            left_operand="count",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(10)
        )
        
        judgment, model = check_consistency([c1, c2])
        
        assert judgment == Judgment.CONFLICT
        assert model is None
    
    def test_percentage_conflict(self):
        """Test percentage constraint conflict."""
        c1 = AtomicConstraint(
            uid="c1",
            left_operand="percentage",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(80)
        )
        c2 = AtomicConstraint(
            uid="c2",
            left_operand="percentage",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(50)
        )
        
        judgment, model = check_consistency([c1, c2])
        assert judgment == Judgment.CONFLICT
    
    def test_decimal_values(self):
        """Test Decimal value handling."""
        c1 = AtomicConstraint(
            uid="c1",
            left_operand="percentage",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(Decimal("75.5"))
        )
        c2 = AtomicConstraint(
            uid="c2",
            left_operand="percentage",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(Decimal("25"))
        )
        
        judgment, model = check_consistency([c1, c2])
        assert judgment == Judgment.CONFLICT
    
    def test_duration_conflict(self):
        """Test duration constraint conflict."""
        c1 = AtomicConstraint(
            uid="c1",
            left_operand="elapsedTime",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(timedelta(hours=1))
        )
        c2 = AtomicConstraint(
            uid="c2",
            left_operand="elapsedTime",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(timedelta(hours=2))
        )
        
        judgment, model = check_consistency([c1, c2])
        assert judgment == Judgment.CONFLICT
    
    def test_duration_compatible(self):
        """Test compatible duration constraints."""
        c1 = AtomicConstraint(
            uid="c1",
            left_operand="elapsedTime",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(timedelta(minutes=30))
        )
        c2 = AtomicConstraint(
            uid="c2",
            left_operand="elapsedTime",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(timedelta(hours=2))
        )
        
        judgment, model = check_consistency([c1, c2])
        assert judgment == Judgment.POSSIBLY_COMPATIBLE
    
    def test_single_constraint(self):
        """Test single constraint is always compatible."""
        c = AtomicConstraint(
            uid="c1",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(10)
        )
        
        judgment, model = check_consistency([c])
        assert judgment == Judgment.POSSIBLY_COMPATIBLE
    
    def test_empty_constraints(self):
        """Test empty constraint list."""
        judgment, model = check_consistency([])
        assert judgment == Judgment.POSSIBLY_COMPATIBLE


class TestDomainBounds:
    """Test that domain bounds are applied correctly."""
    
    def test_count_non_negative(self):
        """Test that count is non-negative."""
        c = AtomicConstraint(
            uid="c1",
            left_operand="count",
            operator=OperatorType.LT,
            right_operand=RightOperand.literal(0)
        )
        
        judgment, model = check_consistency([c])
        # count < 0 should be unsatisfiable because count >= 0
        assert judgment == Judgment.CONFLICT
    
    def test_percentage_bounded(self):
        """Test that percentage is bounded 0-100."""
        # percentage > 100 should be unsatisfiable
        c = AtomicConstraint(
            uid="c1",
            left_operand="percentage",
            operator=OperatorType.GT,
            right_operand=RightOperand.literal(100)
        )
        
        judgment, model = check_consistency([c])
        assert judgment == Judgment.CONFLICT


class TestVariableManager:
    """Test variable manager functionality."""
    
    def test_same_operand_same_variable(self):
        """Test that same operand uses same variable."""
        engine = Z3JudgmentEngine()
        
        var1 = engine.var_manager.get_variable("count")
        var2 = engine.var_manager.get_variable("count")
        
        assert var1 is var2
    
    def test_different_operands_different_variables(self):
        """Test that different operands use different variables."""
        engine = Z3JudgmentEngine()
        
        var1 = engine.var_manager.get_variable("count")
        var2 = engine.var_manager.get_variable("percentage")
        
        assert var1 is not var2
    
    def test_unit_creates_different_variable(self):
        """Test that different units create different variables."""
        engine = Z3JudgmentEngine()
        
        var1 = engine.var_manager.get_variable("payAmount", unit="EUR")
        var2 = engine.var_manager.get_variable("payAmount", unit="USD")
        
        assert var1 is not var2
