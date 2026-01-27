#!/usr/bin/env python3
"""
ODRL-SA Test Suite

Tests for the ODRL-SA judgment system integrated into src/semantics/

Run: uv run python -m pytest tests/test_odrl_sa.py -v
"""

import pytest
from typing import List

# Import from src.semantics (your existing structure)
from src.semantics import (
    # NEW: ODRL-SA Formal Components
    Judgment,
    JudgmentResult,
    ConstraintClass,
    IncomparabilityReason,
    TruthValue,
    
    # Classification
    classify_constraint,
    L_XSD,
    L_REF,
    L_SEM,
    L_RUN,
    
    # Comparability
    is_comparable,
    OPERATOR_RESTRICTIONS,
    
    # Oracle
    LanguageOracle,
    SpatialOracle,
    PurposeOracle,
    OracleResult,
    
    # Engine
    JudgmentEngine,
    create_engine,
    Interval,
    
    # Constraint types (existing)
    AtomicConstraint,
    OperatorType,
    RightValue,
    ODRLMetadata,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def make_constraint(
    id: str,
    operand: str,
    operator: OperatorType,
    value,
    unit: str = None,
    unit_of_count: str = None,
    right_operand_reference: str = None
) -> AtomicConstraint:
    """Helper to create constraints easily."""
    metadata = None
    if unit or unit_of_count or right_operand_reference:
        metadata = ODRLMetadata(
            unit=unit,
            unit_of_count=unit_of_count,
            right_operand_reference=right_operand_reference
        )
    
    return AtomicConstraint(
        id=id,
        left_operand=operand,
        operator=operator,
        right_value=RightValue.from_literal(value),
        odrl_metadata=metadata
    )


def make_policy_usage_constraint(id: str, operand: str, operator: OperatorType) -> AtomicConstraint:
    """Create constraint with policyUsage as rightOperand."""
    return AtomicConstraint(
        id=id,
        left_operand=operand,
        operator=operator,
        right_value=RightValue.policy_usage()
    )


# =============================================================================
# TEST: CONSTRAINT CLASSIFICATION (§6)
# =============================================================================

class TestClassification:
    """Test constraint classification per ODRL-SA §6."""
    
    def test_full_classification(self):
        """FULL: ℓ ∈ Lxsd ∧ v ≠ policyUsage ∧ r = ⊥"""
        c = make_constraint("c1", "count", OperatorType.LTEQ, 100)
        assert classify_constraint(c) == ConstraintClass.FULL
        
        c = make_constraint("c2", "percentage", OperatorType.EQ, 50.0)
        assert classify_constraint(c) == ConstraintClass.FULL
        
        c = make_constraint("c3", "dateTime", OperatorType.GT, 1704067200)
        assert classify_constraint(c) == ConstraintClass.FULL
    
    def test_partial_classification(self):
        """PARTIAL: ℓ ∈ Lref (elapsedTime, delayPeriod)"""
        c = make_constraint("c1", "elapsedTime", OperatorType.LTEQ, 3600)
        assert classify_constraint(c) == ConstraintClass.PARTIAL
        
        c = make_constraint("c2", "delayPeriod", OperatorType.GTEQ, 86400)
        assert classify_constraint(c) == ConstraintClass.PARTIAL
    
    def test_grounded_classification(self):
        """GROUNDED: ℓ ∈ Lsem ∨ ⋈ ∈ Oset"""
        c = make_constraint("c1", "language", OperatorType.EQ, "en")
        assert classify_constraint(c) == ConstraintClass.GROUNDED
        
        c = make_constraint("c2", "spatial", OperatorType.EQ, "DE")
        assert classify_constraint(c) == ConstraintClass.GROUNDED
        
        c = make_constraint("c3", "purpose", OperatorType.EQ, "Research")
        assert classify_constraint(c) == ConstraintClass.GROUNDED
    
    def test_runtime_classification(self):
        """RUNTIME: ℓ ∈ Lrun ∨ v = policyUsage"""
        c = make_constraint("c1", "meteredTime", OperatorType.LTEQ, 36000)
        assert classify_constraint(c) == ConstraintClass.RUNTIME
        
        c = make_policy_usage_constraint("c2", "dateTime", OperatorType.GT)
        assert classify_constraint(c) == ConstraintClass.RUNTIME
    
    def test_deferred_classification(self):
        """DEFERRED: r ≠ ⊥ (rightOperandReference present)"""
        c = make_constraint(
            "c1", "count", OperatorType.LTEQ, None,
            right_operand_reference="http://example.org/limits/max-count"
        )
        assert classify_constraint(c) == ConstraintClass.DEFERRED


# =============================================================================
# TEST: COMPARABILITY (§7 Definition 10)
# =============================================================================

class TestComparability:
    """Test comparability predicate per ODRL-SA §7."""
    
    def test_same_operand_required(self):
        """Condition 1: Same LeftOperand"""
        c1 = make_constraint("c1", "count", OperatorType.LTEQ, 100)
        c2 = make_constraint("c2", "percentage", OperatorType.LTEQ, 50)
        
        result = is_comparable(c1, c2, classify_constraint)
        assert not result.is_comparable
        assert result.reason == IncomparabilityReason.DIFFERENT_OPERANDS
    
    def test_unit_compatible_required(self):
        """Condition 3: Unit-compatible"""
        c1 = make_constraint("c1", "payAmount", OperatorType.LTEQ, 100, unit="USD")
        c2 = make_constraint("c2", "payAmount", OperatorType.GTEQ, 50, unit="EUR")
        
        result = is_comparable(c1, c2, classify_constraint)
        assert not result.is_comparable
        assert result.reason == IncomparabilityReason.UNIT_MISMATCH
    
    def test_scope_compatible_required(self):
        """Condition 4: Scope-compatible (unitOfCount)"""
        c1 = make_constraint("c1", "count", OperatorType.LTEQ, 100, unit_of_count="perUser")
        c2 = make_constraint("c2", "count", OperatorType.GTEQ, 50, unit_of_count="perDevice")
        
        result = is_comparable(c1, c2, classify_constraint)
        assert not result.is_comparable
        assert result.reason == IncomparabilityReason.SCOPE_MISMATCH
    
    def test_operator_valid_required(self):
        """Refinement A: timeInterval eq only"""
        c1 = make_constraint("c1", "timeInterval", OperatorType.GT, 3600)
        c2 = make_constraint("c2", "timeInterval", OperatorType.EQ, 7200)
        
        result = is_comparable(c1, c2, classify_constraint)
        assert not result.is_comparable
        assert result.reason == IncomparabilityReason.OPERATOR_INVALID
    
    def test_comparable_constraints(self):
        """Fully comparable constraints pass all checks"""
        c1 = make_constraint("c1", "count", OperatorType.LTEQ, 100)
        c2 = make_constraint("c2", "count", OperatorType.GTEQ, 50)
        
        result = is_comparable(c1, c2, classify_constraint)
        assert result.is_comparable


# =============================================================================
# TEST: FULL CONSTRAINTS (SMT Analysis)
# =============================================================================

class TestFullConstraints:
    """Test FULL constraint analysis with SMT solving."""
    
    @pytest.fixture
    def engine(self):
        return create_engine(with_oracle=False)
    
    def test_conflict_disjoint_ranges(self, engine):
        """Disjoint ranges → CONFLICT"""
        c1 = make_constraint("c1", "count", OperatorType.LTEQ, 10)
        c2 = make_constraint("c2", "count", OperatorType.GTEQ, 20)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.CONFLICT
    
    def test_compatible_overlapping_ranges(self, engine):
        """Overlapping ranges → POSSIBLY_COMPATIBLE"""
        c1 = make_constraint("c1", "count", OperatorType.LTEQ, 100)
        c2 = make_constraint("c2", "count", OperatorType.GTEQ, 50)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.POSSIBLY_COMPATIBLE
        assert result.counterexample is not None
    
    def test_conflict_equality_mismatch(self, engine):
        """eq different values → CONFLICT"""
        c1 = make_constraint("c1", "count", OperatorType.EQ, 10)
        c2 = make_constraint("c2", "count", OperatorType.EQ, 20)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.CONFLICT
    
    def test_compatible_same_equality(self, engine):
        """eq same value → POSSIBLY_COMPATIBLE"""
        c1 = make_constraint("c1", "count", OperatorType.EQ, 10)
        c2 = make_constraint("c2", "count", OperatorType.EQ, 10)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.POSSIBLY_COMPATIBLE
    
    def test_datetime_comparison(self, engine):
        """DateTime as Unix timestamp"""
        c1 = make_constraint("c1", "dateTime", OperatorType.GTEQ, 1704067200)
        c2 = make_constraint("c2", "dateTime", OperatorType.LT, 1704067200)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.CONFLICT


# =============================================================================
# TEST: PARTIAL CONSTRAINTS (Reference Point)
# =============================================================================

class TestPartialConstraints:
    """Test PARTIAL constraint analysis."""
    
    @pytest.fixture
    def engine(self):
        return create_engine(with_oracle=False, enable_partial=True)
    
    def test_elapsed_time_conflict(self, engine):
        """elapsedTime with disjoint ranges → CONFLICT"""
        c1 = make_constraint("c1", "elapsedTime", OperatorType.LTEQ, 3600)
        c2 = make_constraint("c2", "elapsedTime", OperatorType.GTEQ, 7200)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.CONFLICT
    
    def test_elapsed_time_compatible(self, engine):
        """elapsedTime with overlapping ranges → POSSIBLY_COMPATIBLE"""
        c1 = make_constraint("c1", "elapsedTime", OperatorType.LTEQ, 7200)
        c2 = make_constraint("c2", "elapsedTime", OperatorType.GTEQ, 3600)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.POSSIBLY_COMPATIBLE


# =============================================================================
# TEST: GROUNDED CONSTRAINTS (Oracle)
# =============================================================================

class TestGroundedConstraints:
    """Test GROUNDED constraint analysis with oracles."""
    
    def test_language_hierarchy(self):
        """Language oracle: en subsumes en-US"""
        oracle = LanguageOracle()
        
        result = oracle.query("language", OperatorType.IS_A, "en", "en-US")
        assert result == OracleResult.SUBSUMES
        
        result = oracle.query("language", OperatorType.EQ, "de", "fr")
        assert result == OracleResult.DISJOINT
    
    def test_spatial_containment(self):
        """Spatial oracle: EU contains DE"""
        oracle = SpatialOracle()
        
        result = oracle.query("spatial", OperatorType.HAS_PART, "EU", "DE")
        assert result == OracleResult.SUBSUMES
    
    def test_purpose_taxonomy(self):
        """Purpose oracle: Commercial vs NonCommercial"""
        oracle = PurposeOracle()
        
        result = oracle.query("purpose", OperatorType.EQ, "Marketing", "AcademicResearch")
        assert result == OracleResult.DISJOINT
    
    def test_grounded_with_oracle(self):
        """Engine with oracle can judge semantic constraints"""
        engine = create_engine(with_oracle=True)
        
        c1 = make_constraint("c1", "language", OperatorType.EQ, "de")
        c2 = make_constraint("c2", "language", OperatorType.EQ, "fr")
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.CONFLICT
    
    def test_grounded_without_oracle(self):
        """Engine without oracle returns UNKNOWN"""
        engine = create_engine(with_oracle=False)
        
        c1 = make_constraint("c1", "language", OperatorType.EQ, "de")
        c2 = make_constraint("c2", "language", OperatorType.EQ, "fr")
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.UNKNOWN


# =============================================================================
# TEST: RUNTIME CONSTRAINTS
# =============================================================================

class TestRuntimeConstraints:
    """Test RUNTIME constraints (cannot analyze statically)."""
    
    @pytest.fixture
    def engine(self):
        return create_engine()
    
    def test_metered_time_unknown(self, engine):
        """meteredTime → UNKNOWN"""
        c1 = make_constraint("c1", "meteredTime", OperatorType.LTEQ, 3600)
        c2 = make_constraint("c2", "meteredTime", OperatorType.GTEQ, 7200)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.UNKNOWN
    
    def test_policy_usage_unknown(self, engine):
        """policyUsage → UNKNOWN"""
        c1 = make_policy_usage_constraint("c1", "dateTime", OperatorType.GT)
        c2 = make_constraint("c2", "dateTime", OperatorType.LT, 1704067200)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.UNKNOWN


# =============================================================================
# TEST: DEFERRED CONSTRAINTS
# =============================================================================

class TestDeferredConstraints:
    """Test DEFERRED constraints (rightOperandReference)."""
    
    @pytest.fixture
    def engine(self):
        return create_engine()
    
    def test_deferred_unknown(self, engine):
        """rightOperandReference → UNKNOWN"""
        c1 = make_constraint(
            "c1", "count", OperatorType.LTEQ, None,
            right_operand_reference="http://example.org/limits"
        )
        c2 = make_constraint("c2", "count", OperatorType.GTEQ, 50)
        
        result = engine.judge(c1, c2)
        assert result.judgment == Judgment.UNKNOWN


# =============================================================================
# TEST: ABSTRACT DOMAIN
# =============================================================================

class TestAbstractDomain:
    """Test interval abstract domain."""
    
    def test_interval_meet_overlap(self):
        """Overlapping intervals have non-empty meet"""
        i1 = Interval(lo=0, hi=100)
        i2 = Interval(lo=50, hi=150)
        
        result = i1.meet(i2)
        assert not result.is_empty()
        assert result.lo == 50
        assert result.hi == 100
    
    def test_interval_meet_disjoint(self):
        """Disjoint intervals have empty meet (⊥)"""
        i1 = Interval(lo=0, hi=10)
        i2 = Interval(lo=20, hi=30)
        
        result = i1.meet(i2)
        assert result.is_empty()


# =============================================================================
# TEST: THREE-VALUED LOGIC
# =============================================================================

class TestThreeValuedLogic:
    """Test Kleene three-valued logic."""
    
    def test_truth_and(self):
        """Three-valued AND"""
        T, F, U = TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNDEFINED
        
        assert (T & T) == T
        assert (T & F) == F
        assert (T & U) == U
        assert (F & U) == F
    
    def test_truth_or(self):
        """Three-valued OR"""
        T, F, U = TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNDEFINED
        
        assert (T | F) == T
        assert (F | F) == F
        assert (T | U) == T
    
    def test_truth_not(self):
        """Three-valued NOT"""
        T, F, U = TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNDEFINED
        
        assert (~T) == F
        assert (~F) == T
        assert (~U) == U


# =============================================================================
# TEST: BATCH ANALYSIS
# =============================================================================

class TestBatchAnalysis:
    """Test analyzing multiple constraints."""
    
    def test_find_conflicts(self):
        """Find all conflicts in a set of constraints"""
        engine = create_engine(with_oracle=False)
        
        constraints = [
            make_constraint("c1", "count", OperatorType.LTEQ, 10),
            make_constraint("c2", "count", OperatorType.GTEQ, 20),
            make_constraint("c3", "count", OperatorType.EQ, 5),
            make_constraint("c4", "percentage", OperatorType.LTEQ, 50),
        ]
        
        conflicts = engine.find_conflicts(constraints)
        assert len(conflicts) >= 2
        assert all(c.judgment == Judgment.CONFLICT for c in conflicts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])