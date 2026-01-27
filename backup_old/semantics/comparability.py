# src/semantics/comparability.py
"""
ODRL-SA Comparability Predicate

Implements §7 Definition 10: Comparability Predicate

Two constraints are comparable iff ALL of:
1. Same LeftOperand (ℓ₁ = ℓ₂)
2. Analyzable class (both FULL or PARTIAL)
3. Unit-compatible (matching units)
4. Scope-compatible (matching unitOfCount)
5. Temporal-compatible (alignable reference points)

If ANY condition fails, judgment returns UNKNOWN.
This is a SOUNDNESS GUARD, not a limitation.
"""

from typing import Tuple, Optional, Set
from dataclasses import dataclass

from .constraint_types import AtomicConstraint, OperatorType
from .judgment import (
    ConstraintClass, 
    IncomparabilityReason,
    Judgment,
    JudgmentResult
)


# =============================================================================
# TEMPORAL OPERAND SETS (for Refinement B)
# =============================================================================

# Reference-point temporal operands
TEMPORAL_REFERENCE_POINT: Set[str] = {
    "elapsedTime",
    "delayPeriod"
}

# Absolute temporal operands
TEMPORAL_ABSOLUTE: Set[str] = {
    "dateTime"
}

# All temporal operands
TEMPORAL_ALL: Set[str] = TEMPORAL_REFERENCE_POINT | TEMPORAL_ABSOLUTE | {"timeInterval", "meteredTime"}


# =============================================================================
# OPERATOR RESTRICTIONS (Refinement A)
# =============================================================================

# Operands with restricted operators per ODRL spec
OPERATOR_RESTRICTIONS = {
    "timeInterval": {OperatorType.EQ},  # Only eq per spec
    "elapsedTime": {OperatorType.EQ, OperatorType.LT, OperatorType.LTEQ},
    "delayPeriod": {OperatorType.EQ, OperatorType.GT, OperatorType.GTEQ},
}


# =============================================================================
# COMPARABILITY RESULT
# =============================================================================

@dataclass
class ComparabilityResult:
    """Result of checking if two constraints are comparable."""
    
    is_comparable: bool
    """True if constraints can be compared."""
    
    reason: Optional[IncomparabilityReason] = None
    """If not comparable, why."""
    
    message: Optional[str] = None
    """Human-readable explanation."""
    
    def __bool__(self) -> bool:
        return self.is_comparable


# =============================================================================
# CONDITION 1: SAME LEFT OPERAND
# =============================================================================

def check_same_operand(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check Condition 1: Same LeftOperand.
    
    Constraints must have the same LeftOperand to be comparable.
    """
    op1 = _normalize_operand(c1.left_operand)
    op2 = _normalize_operand(c2.left_operand)
    
    if op1 != op2:
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.DIFFERENT_OPERANDS,
            message=f"Different operands: {op1} vs {op2}"
        )
    
    return ComparabilityResult(is_comparable=True)


def _normalize_operand(operand: str) -> str:
    """Normalize operand name by stripping namespace."""
    if '#' in operand:
        return operand.split('#')[-1]
    if '/' in operand:
        return operand.split('/')[-1]
    return operand


# =============================================================================
# CONDITION 2: ANALYZABLE CLASS
# =============================================================================

def check_analyzable_class(
    c1: AtomicConstraint, 
    c2: AtomicConstraint,
    get_class: callable
) -> ComparabilityResult:
    """
    Check Condition 2: Analyzable class.
    
    Both constraints must be FULL or PARTIAL class.
    """
    class1 = get_class(c1)
    class2 = get_class(c2)
    
    if not class1.is_analyzable():
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.NOT_ANALYZABLE,
            message=f"Constraint {c1.id} is {class1.value} (not analyzable)"
        )
    
    if not class2.is_analyzable():
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.NOT_ANALYZABLE,
            message=f"Constraint {c2.id} is {class2.value} (not analyzable)"
        )
    
    return ComparabilityResult(is_comparable=True)


# =============================================================================
# CONDITION 3: UNIT COMPATIBILITY
# =============================================================================

def check_unit_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check Condition 3: Unit-compatible.
    
    Per ODRL-SA §8: No unit conversion. Different units → UNKNOWN.
    """
    unit1 = _normalize_unit(c1.unit)
    unit2 = _normalize_unit(c2.unit)
    
    # Both None → compatible
    if unit1 is None and unit2 is None:
        return ComparabilityResult(is_comparable=True)
    
    # Same unit → compatible
    if unit1 == unit2:
        return ComparabilityResult(is_comparable=True)
    
    # Different units → incomparable
    return ComparabilityResult(
        is_comparable=False,
        reason=IncomparabilityReason.UNIT_MISMATCH,
        message=f"Unit mismatch: {unit1} vs {unit2}"
    )


def _normalize_unit(unit: Optional[str]) -> Optional[str]:
    """Normalize unit URI to local name."""
    if unit is None:
        return None
    if '#' in unit:
        return unit.split('#')[-1]
    if '/' in unit:
        return unit.split('/')[-1]
    return unit


# =============================================================================
# CONDITION 4: SCOPE COMPATIBILITY (unitOfCount)
# =============================================================================

def check_scope_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check Condition 4: Scope-compatible (unitOfCount).
    
    For 'count' operand, unitOfCount must match (perUser, perDevice, etc.)
    """
    op1 = _normalize_operand(c1.left_operand)
    
    # Only applies to count operand
    if op1 != "count":
        return ComparabilityResult(is_comparable=True)
    
    scope1 = c1.unit_of_count
    scope2 = c2.unit_of_count
    
    # Both None → compatible
    if scope1 is None and scope2 is None:
        return ComparabilityResult(is_comparable=True)
    
    # Normalize and compare
    scope1_norm = _normalize_operand(scope1) if scope1 else None
    scope2_norm = _normalize_operand(scope2) if scope2 else None
    
    if scope1_norm == scope2_norm:
        return ComparabilityResult(is_comparable=True)
    
    return ComparabilityResult(
        is_comparable=False,
        reason=IncomparabilityReason.SCOPE_MISMATCH,
        message=f"Scope mismatch: {scope1_norm} vs {scope2_norm}"
    )


# =============================================================================
# CONDITION 5: TEMPORAL COMPATIBILITY (Refinement B)
# =============================================================================

def check_temporal_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check Condition 5: Temporal-compatible.
    
    Implements ODRL-SA §8 Refinement B:
    - delayPeriod only comparable with delayPeriod
    - elapsedTime only comparable with elapsedTime
    - dateTime only comparable with dateTime
    - Cross-temporal comparisons → UNKNOWN
    """
    op1 = _normalize_operand(c1.left_operand)
    op2 = _normalize_operand(c2.left_operand)
    
    # Same operand → always compatible
    if op1 == op2:
        return ComparabilityResult(is_comparable=True)
    
    # Non-temporal operands → compatible
    if op1 not in TEMPORAL_ALL and op2 not in TEMPORAL_ALL:
        return ComparabilityResult(is_comparable=True)
    
    # Cross-temporal: reference-point vs absolute
    if op1 in TEMPORAL_REFERENCE_POINT and op2 in TEMPORAL_ABSOLUTE:
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.TEMPORAL_INCOMPATIBLE,
            message=f"Cannot compare {op1} (reference-point) with {op2} (absolute)"
        )
    
    if op1 in TEMPORAL_ABSOLUTE and op2 in TEMPORAL_REFERENCE_POINT:
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.TEMPORAL_INCOMPATIBLE,
            message=f"Cannot compare {op1} (absolute) with {op2} (reference-point)"
        )
    
    return ComparabilityResult(is_comparable=True)


# =============================================================================
# OPERATOR VALIDITY CHECK (Refinement A)
# =============================================================================

def check_operator_valid(c: AtomicConstraint) -> ComparabilityResult:
    """
    Check operator validity per Refinement A.
    
    Some operands have restricted operators:
    - timeInterval: eq only
    - elapsedTime: eq, lt, lteq only
    - delayPeriod: eq, gt, gteq only
    """
    op = _normalize_operand(c.left_operand)
    
    if op not in OPERATOR_RESTRICTIONS:
        return ComparabilityResult(is_comparable=True)
    
    allowed = OPERATOR_RESTRICTIONS[op]
    if c.operator not in allowed:
        allowed_str = ", ".join(o.value for o in allowed)
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.OPERATOR_INVALID,
            message=f"Operator {c.operator.value} not allowed for {op}. Allowed: {allowed_str}"
        )
    
    return ComparabilityResult(is_comparable=True)


# =============================================================================
# DEFERRED VALUE CHECK
# =============================================================================

def check_not_deferred(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check that neither constraint has a deferred value (rightOperandReference).
    """
    if c1.has_deferred_value():
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.DEFERRED_VALUE,
            message=f"Constraint {c1.id} has rightOperandReference requiring dereferencing"
        )
    
    if c2.has_deferred_value():
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.DEFERRED_VALUE,
            message=f"Constraint {c2.id} has rightOperandReference requiring dereferencing"
        )
    
    return ComparabilityResult(is_comparable=True)


# =============================================================================
# RUNTIME DEPENDENCY CHECK
# =============================================================================

def check_not_runtime(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check that neither constraint requires runtime state (policyUsage, status).
    """
    if c1.has_runtime_dependency():
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.RUNTIME_REQUIRED,
            message=f"Constraint {c1.id} requires runtime state"
        )
    
    if c2.has_runtime_dependency():
        return ComparabilityResult(
            is_comparable=False,
            reason=IncomparabilityReason.RUNTIME_REQUIRED,
            message=f"Constraint {c2.id} requires runtime state"
        )
    
    return ComparabilityResult(is_comparable=True)


# =============================================================================
# MAIN COMPARABILITY FUNCTION (§7 Definition 10)
# =============================================================================

def is_comparable(
    c1: AtomicConstraint, 
    c2: AtomicConstraint,
    get_class: callable
) -> ComparabilityResult:
    """
    Check if two constraints are comparable per ODRL-SA §7 Definition 10.
    
    ALL conditions must pass for constraints to be comparable:
    1. Same LeftOperand
    2. Analyzable class (FULL or PARTIAL)
    3. Unit-compatible
    4. Scope-compatible (unitOfCount for count)
    5. Temporal-compatible (no cross-temporal comparison)
    
    Additionally:
    - Operator must be valid for operand (Refinement A)
    - Neither constraint can have deferred value
    - Neither constraint can require runtime state
    
    Args:
        c1: First constraint
        c2: Second constraint
        get_class: Function to get ConstraintClass for a constraint
        
    Returns:
        ComparabilityResult indicating if comparable and why not if not
    """
    # Check operator validity first
    op_check1 = check_operator_valid(c1)
    if not op_check1:
        return op_check1
    
    op_check2 = check_operator_valid(c2)
    if not op_check2:
        return op_check2
    
    # Check not deferred
    deferred_check = check_not_deferred(c1, c2)
    if not deferred_check:
        return deferred_check
    
    # Check not runtime
    runtime_check = check_not_runtime(c1, c2)
    if not runtime_check:
        return runtime_check
    
    # Condition 1: Same LeftOperand
    same_op_check = check_same_operand(c1, c2)
    if not same_op_check:
        return same_op_check
    
    # Condition 2: Analyzable class
    class_check = check_analyzable_class(c1, c2, get_class)
    if not class_check:
        return class_check
    
    # Condition 3: Unit-compatible
    unit_check = check_unit_compatible(c1, c2)
    if not unit_check:
        return unit_check
    
    # Condition 4: Scope-compatible
    scope_check = check_scope_compatible(c1, c2)
    if not scope_check:
        return scope_check
    
    # Condition 5: Temporal-compatible
    temporal_check = check_temporal_compatible(c1, c2)
    if not temporal_check:
        return temporal_check
    
    # All checks passed
    return ComparabilityResult(is_comparable=True)