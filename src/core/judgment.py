# src/core/judgment.py
"""
ODRL-SA Judgment Functions

Implements Definition 5 (Judgment) and Definition 6 (Judgment Rules):

Definition 5:
    judge : C × C → {CONFLICT, POSSIBLY-COMPATIBLE, UNKNOWN}

Definition 6 (Rules):
    judge(c₁, c₂) = 
        CONFLICT           if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# = ⊥
        POSSIBLY-COMPATIBLE if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# ≠ ⊥
        UNKNOWN            if ¬comparable(c₁,c₂)

Definition 7 (Comparability):
    comparable(c₁, c₂) ⟺ 
        ℓ₁ = ℓ₂ ∧
        class(c₁), class(c₂) ∈ {FULL, PARTIAL} ∧
        unit-compatible(c₁, c₂) ∧
        scope-compatible(c₁, c₂) ∧
        temporal-compatible(c₁, c₂)
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Any
from enum import Enum, auto

from .constraint_types import (
    AtomicConstraint, 
    Judgment, 
    ConstraintClass,
    OperatorType,
)
from .classifier import classify_constraint, ClassificationResult

# =============================================================================
# UNIT ORACLE INTEGRATION
# =============================================================================

# Try to import unit oracle; fallback to simple string matching if unavailable
try:
    from grounding.unit import are_units_compatible
    UNIT_ORACLE_AVAILABLE = True
except ImportError:
    UNIT_ORACLE_AVAILABLE = False
    
    def are_units_compatible(u1: str, u2: str) -> bool:
        """Fallback: normalize and compare."""
        u1_norm = u1.split('#')[-1].split('/')[-1] if u1 else None
        u2_norm = u2.split('#')[-1].split('/')[-1] if u2 else None
        return u1_norm == u2_norm


# =============================================================================
# COMPARABILITY RESULT
# =============================================================================

class IncomparabilityReason(Enum):
    """Why two constraints cannot be compared."""
    DIFFERENT_OPERANDS = auto()
    NON_ANALYZABLE_CLASS = auto()
    INCOMPATIBLE_UNITS = auto()
    INCOMPATIBLE_SCOPE = auto()
    INCOMPATIBLE_TEMPORAL_REF = auto()
    MISSING_ORACLE = auto()


@dataclass
class ComparabilityResult:
    """Result of checking if two constraints are comparable."""
    comparable: bool
    reason: Optional[IncomparabilityReason] = None
    details: str = ""


# =============================================================================
# COMPARABILITY CHECKS (Definition 7)
# =============================================================================

def check_same_operand(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """Check: ℓ₁ = ℓ₂ (same LeftOperand)."""
    # Normalize operand names
    l1 = c1.left_operand.split('#')[-1].split('/')[-1]
    l2 = c2.left_operand.split('#')[-1].split('/')[-1]
    
    if l1 != l2:
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.DIFFERENT_OPERANDS,
            details=f"Different LeftOperands: {l1} vs {l2}"
        )
    return ComparabilityResult(comparable=True)


def check_analyzable_class(
    class1: ClassificationResult, 
    class2: ClassificationResult
) -> ComparabilityResult:
    """Check: class(c₁), class(c₂) ∈ {FULL, PARTIAL} or both GROUNDED with oracle."""
    
    analyzable = {ConstraintClass.FULL, ConstraintClass.PARTIAL}
    
    # Both FULL or PARTIAL - always comparable
    if class1.constraint_class in analyzable and class2.constraint_class in analyzable:
        return ComparabilityResult(comparable=True)
    
    # Both GROUNDED - comparable if oracle available
    if (class1.constraint_class == ConstraintClass.GROUNDED and 
        class2.constraint_class == ConstraintClass.GROUNDED):
        if class1.oracle_available and class2.oracle_available:
            return ComparabilityResult(comparable=True)
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.MISSING_ORACLE,
            details=f"Oracle not available: {class1.oracle_needed}"
        )
    
    # Mixed or non-analyzable
    return ComparabilityResult(
        comparable=False,
        reason=IncomparabilityReason.NON_ANALYZABLE_CLASS,
        details=f"Classes: {class1.constraint_class.name}, {class2.constraint_class.name}"
    )


def check_unit_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check: unit-compatible(c₁, c₂).
    
    Uses unit oracle for alias resolution (e.g., "euro" → "EUR").
    """
    u1 = c1.unit
    u2 = c2.unit
    
    # Both None - compatible
    if u1 is None and u2 is None:
        return ComparabilityResult(comparable=True)
    
    # One None, one specified - incompatible (ambiguous)
    if (u1 is None) != (u2 is None):
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.INCOMPATIBLE_UNITS,
            details=f"Unit mismatch: {u1} vs {u2}"
        )
    
    # Both specified - use oracle for compatibility check
    # Handles aliases: are_units_compatible("euro", "EUR") → True
    if are_units_compatible(u1, u2):
        return ComparabilityResult(comparable=True)
    
    # Different units (no conversion available)
    return ComparabilityResult(
        comparable=False,
        reason=IncomparabilityReason.INCOMPATIBLE_UNITS,
        details=f"Different units: {u1} vs {u2}"
    )


def check_scope_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """Check: scope-compatible(c₁, c₂) for unitOfCount."""
    s1 = c1.unit_of_count
    s2 = c2.unit_of_count
    
    # Both None - compatible (default scope)
    if s1 is None and s2 is None:
        return ComparabilityResult(comparable=True)
    
    # One None, one specified
    if (s1 is None) != (s2 is None):
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.INCOMPATIBLE_SCOPE,
            details=f"Scope mismatch: {s1} vs {s2}"
        )
    
    # Both specified - must match
    s1_norm = s1.split('#')[-1].split('/')[-1] if s1 else None
    s2_norm = s2.split('#')[-1].split('/')[-1] if s2 else None
    
    if s1_norm != s2_norm:
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.INCOMPATIBLE_SCOPE,
            details=f"Different scopes: {s1} vs {s2}"
        )
    
    return ComparabilityResult(comparable=True)


def check_temporal_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """Check: temporal-compatible(c₁, c₂) for reference point alignment."""
    # Get normalized operand
    l1 = c1.left_operand.split('#')[-1].split('/')[-1]
    l2 = c2.left_operand.split('#')[-1].split('/')[-1]
    
    # Reference-point operands
    ref_point_ops = {"elapsedTime", "delayPeriod"}
    
    # If neither uses reference points - compatible
    if l1 not in ref_point_ops and l2 not in ref_point_ops:
        return ComparabilityResult(comparable=True)
    
    # If both use same reference-point operand - compatible
    # (They share the same reference point)
    if l1 == l2 and l1 in ref_point_ops:
        return ComparabilityResult(comparable=True)
    
    # Mixing reference-point with absolute - incompatible
    # (e.g., elapsedTime vs dateTime)
    return ComparabilityResult(
        comparable=False,
        reason=IncomparabilityReason.INCOMPATIBLE_TEMPORAL_REF,
        details=f"Cannot compare {l1} with {l2}: different temporal references"
    )


def is_comparable(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Full comparability check per Definition 7.
    
    comparable(c₁, c₂) ⟺ 
        ℓ₁ = ℓ₂ ∧
        class(c₁), class(c₂) ∈ {FULL, PARTIAL} ∧
        unit-compatible(c₁, c₂) ∧
        scope-compatible(c₁, c₂) ∧
        temporal-compatible(c₁, c₂)
    """
    # 1. Same LeftOperand
    result = check_same_operand(c1, c2)
    if not result.comparable:
        return result
    
    # 2. Analyzable class
    class1 = classify_constraint(c1)
    class2 = classify_constraint(c2)
    result = check_analyzable_class(class1, class2)
    if not result.comparable:
        return result
    
    # 3. Unit compatible (uses oracle for alias resolution)
    result = check_unit_compatible(c1, c2)
    if not result.comparable:
        return result
    
    # 4. Scope compatible
    result = check_scope_compatible(c1, c2)
    if not result.comparable:
        return result
    
    # 5. Temporal compatible
    result = check_temporal_compatible(c1, c2)
    if not result.comparable:
        return result
    
    return ComparabilityResult(comparable=True)


# =============================================================================
# JUDGMENT RESULT
# =============================================================================

@dataclass
class JudgmentResult:
    """
    Complete judgment result with explanation.
    """
    judgment: Judgment
    """The judgment: CONFLICT, POSSIBLY-COMPATIBLE, or UNKNOWN."""
    
    comparable: bool
    """Were the constraints comparable?"""
    
    incomparability_reason: Optional[IncomparabilityReason] = None
    """If not comparable, why?"""
    
    explanation: str = ""
    """Human-readable explanation."""
    
    counterexample: Optional[Any] = None
    """For POSSIBLY-COMPATIBLE: a satisfying assignment."""
    
    def __str__(self) -> str:
        return f"{self.judgment.value}: {self.explanation}"


# =============================================================================
# JUDGMENT FUNCTION (Definition 5-6)
# =============================================================================

def judge(c1: AtomicConstraint, c2: AtomicConstraint) -> JudgmentResult:
    """
    Main judgment function per Definition 5-6.
    
    judge(c₁, c₂) = 
        CONFLICT           if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# = ⊥
        POSSIBLY-COMPATIBLE if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# ≠ ⊥
        UNKNOWN            if ¬comparable(c₁,c₂)
    
    Note: The abstract interpretation (⟦c⟧#) and meet operation (⊓)
    are implemented in the encoder module. This function delegates
    the actual SMT solving there.
    """
    # Check comparability
    comp_result = is_comparable(c1, c2)
    
    if not comp_result.comparable:
        return JudgmentResult(
            judgment=Judgment.UNKNOWN,
            comparable=False,
            incomparability_reason=comp_result.reason,
            explanation=comp_result.details
        )
    
    # Constraints are comparable - delegate to SMT solver
    # This is a placeholder - actual implementation uses Z3
    # For now, return a result that indicates we need the encoder
    return JudgmentResult(
        judgment=Judgment.UNKNOWN,
        comparable=True,
        explanation="Comparable - needs SMT encoding (implement in encoder module)"
    )


# =============================================================================
# JUDGMENT LATTICE OPERATIONS
# =============================================================================

def judgment_meet(j1: Judgment, j2: Judgment) -> Judgment:
    """
    Meet operation on judgments (most conservative).
    
    CONFLICT ⊓ x = CONFLICT
    UNKNOWN ⊓ POSSIBLY-COMPATIBLE = UNKNOWN
    POSSIBLY-COMPATIBLE ⊓ POSSIBLY-COMPATIBLE = POSSIBLY-COMPATIBLE
    """
    if j1 == Judgment.CONFLICT or j2 == Judgment.CONFLICT:
        return Judgment.CONFLICT
    if j1 == Judgment.UNKNOWN or j2 == Judgment.UNKNOWN:
        return Judgment.UNKNOWN
    return Judgment.POSSIBLY_COMPATIBLE


def judgment_join(j1: Judgment, j2: Judgment) -> Judgment:
    """
    Join operation on judgments (most optimistic).
    
    POSSIBLY-COMPATIBLE ⊔ x = POSSIBLY-COMPATIBLE
    UNKNOWN ⊔ CONFLICT = UNKNOWN
    CONFLICT ⊔ CONFLICT = CONFLICT
    """
    if j1 == Judgment.POSSIBLY_COMPATIBLE or j2 == Judgment.POSSIBLY_COMPATIBLE:
        return Judgment.POSSIBLY_COMPATIBLE
    if j1 == Judgment.UNKNOWN or j2 == Judgment.UNKNOWN:
        return Judgment.UNKNOWN
    return Judgment.CONFLICT