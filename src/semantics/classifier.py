# src/semantics/classifier.py
"""
ODRL-SA Constraint Classifier

Implements §6 Definition 7: Constraint Analyzability Class

Classifies constraints into:
- FULL: ℓ ∈ Lxsd ∧ v ≠ policyUsage ∧ r = ⊥
- PARTIAL: ℓ ∈ Lref (elapsedTime, delayPeriod)
- GROUNDED: ℓ ∈ Lsem ∨ ⋈ ∈ Oset
- RUNTIME: ℓ ∈ Lrun ∨ v = policyUsage
- DEFERRED: r ≠ ⊥ (rightOperandReference present)
"""

from typing import Set, Dict, Optional
from .constraint_types import AtomicConstraint, OperatorType
from .judgment import ConstraintClass


# =============================================================================
# LEFTOPERAND PARTITIONS (§2 Definition 4)
# =============================================================================

# Lxsd: Self-contained, XSD-grounded (14 operands)
L_XSD: Set[str] = {
    # Numeric (4)
    "count",
    "percentage", 
    "payAmount",
    "resolution",
    # Temporal - Absolute (2)
    "dateTime",
    "timeInterval",
    # Positional - Absolute (4)
    "absolutePosition",
    "absoluteSize",
    "absoluteTemporalPosition",
    "absoluteSpatialPosition",
    # Positional - Relative (4)
    "relativePosition",
    "relativeSize",
    "relativeTemporalPosition",
    "relativeSpatialPosition",
}

# Lref: Reference-point required (2 operands)
L_REF: Set[str] = {
    "elapsedTime",
    "delayPeriod",
}

# Lsem: Semantic grounding required (14 operands)
L_SEM: Set[str] = {
    # Categorical (7)
    "language",
    "fileFormat",
    "media",
    "industry",
    "purpose",
    "product",
    "deliveryChannel",
    # Spatial (2)
    "spatial",
    "spatialCoordinates",
    # Reference (4)
    "recipient",
    "systemDevice",
    "event",
    "virtualLocation",
    # Version (1)
    "version",
}

# Lrun: Runtime-only (1 operand)
L_RUN: Set[str] = {
    "meteredTime",
}

# Complete set (31 operands)
L_ALL: Set[str] = L_XSD | L_REF | L_SEM | L_RUN


# =============================================================================
# OPERATOR SETS
# =============================================================================

# Set-based operators (require semantic grounding)
O_SET: Set[OperatorType] = {
    OperatorType.IS_A,
    OperatorType.HAS_PART,
    OperatorType.IS_PART_OF,
    OperatorType.IS_ALL_OF,
    OperatorType.IS_ANY_OF,
    OperatorType.IS_NONE_OF,
}


# =============================================================================
# CLASSIFICATION FUNCTION (§6 Definition 7)
# =============================================================================

def classify_constraint(constraint: AtomicConstraint) -> ConstraintClass:
    """
    Classify a constraint per ODRL-SA §6 Definition 7.
    
    Classification rules (in order):
    1. DEFERRED: if rightOperandReference ≠ ⊥
    2. RUNTIME: if ℓ ∈ Lrun OR v = policyUsage OR status referenced
    3. GROUNDED: if ℓ ∈ Lsem OR ⋈ ∈ Oset
    4. PARTIAL: if ℓ ∈ Lref
    5. FULL: if ℓ ∈ Lxsd (default for analyzable)
    
    Args:
        constraint: The constraint to classify
        
    Returns:
        ConstraintClass enum value
    """
    operand = _normalize_operand(constraint.left_operand)
    operator = constraint.operator
    
    # Rule 1: DEFERRED if rightOperandReference present
    if constraint.has_deferred_value():
        return ConstraintClass.DEFERRED
    
    # Rule 2: RUNTIME if runtime dependency
    if _is_runtime(constraint, operand):
        return ConstraintClass.RUNTIME
    
    # Rule 3: GROUNDED if semantic operand or set operator
    if _is_grounded(operand, operator):
        return ConstraintClass.GROUNDED
    
    # Rule 4: PARTIAL if reference-point operand
    if operand in L_REF:
        return ConstraintClass.PARTIAL
    
    # Rule 5: FULL if XSD-grounded
    if operand in L_XSD:
        return ConstraintClass.FULL
    
    # Unknown operand - treat as GROUNDED (requires external info)
    return ConstraintClass.GROUNDED


def _normalize_operand(operand: str) -> str:
    """Normalize operand name by stripping namespace."""
    if '#' in operand:
        return operand.split('#')[-1]
    if '/' in operand:
        return operand.split('/')[-1]
    return operand


def _is_runtime(constraint: AtomicConstraint, operand: str) -> bool:
    """Check if constraint requires runtime state."""
    # Runtime-only operand
    if operand in L_RUN:
        return True
    
    # policyUsage as rightOperand
    if constraint.is_policy_usage():
        return True
    
    # status property referenced
    if constraint.has_runtime_dependency():
        return True
    
    return False


def _is_grounded(operand: str, operator: OperatorType) -> bool:
    """Check if constraint requires semantic grounding."""
    # Semantic operand
    if operand in L_SEM:
        return True
    
    # Set-based operator (requires hierarchy/taxonomy)
    if operator in O_SET:
        return True
    
    return False


# =============================================================================
# BATCH CLASSIFICATION
# =============================================================================

def classify_constraints(
    constraints: Dict[str, AtomicConstraint]
) -> Dict[str, ConstraintClass]:
    """
    Classify multiple constraints.
    
    Args:
        constraints: Dictionary of constraint_id -> AtomicConstraint
        
    Returns:
        Dictionary of constraint_id -> ConstraintClass
    """
    return {
        cid: classify_constraint(c)
        for cid, c in constraints.items()
    }


# =============================================================================
# CLASSIFICATION STATISTICS
# =============================================================================

def get_classification_stats(
    classifications: Dict[str, ConstraintClass]
) -> Dict[str, int]:
    """
    Get statistics about constraint classifications.
    
    Returns:
        Dictionary with counts per class
    """
    stats = {cls.value: 0 for cls in ConstraintClass}
    stats['total'] = len(classifications)
    stats['analyzable'] = 0
    
    for cls in classifications.values():
        stats[cls.value] += 1
        if cls.is_analyzable():
            stats['analyzable'] += 1
    
    return stats


# =============================================================================
# PARTITION VERIFICATION
# =============================================================================

def verify_partition() -> bool:
    """
    Verify that the LeftOperand partition is complete and disjoint.
    
    Returns:
        True if partition is valid
    """
    # Check disjointness
    assert L_XSD.isdisjoint(L_REF), "L_XSD and L_REF overlap"
    assert L_XSD.isdisjoint(L_SEM), "L_XSD and L_SEM overlap"
    assert L_XSD.isdisjoint(L_RUN), "L_XSD and L_RUN overlap"
    assert L_REF.isdisjoint(L_SEM), "L_REF and L_SEM overlap"
    assert L_REF.isdisjoint(L_RUN), "L_REF and L_RUN overlap"
    assert L_SEM.isdisjoint(L_RUN), "L_SEM and L_RUN overlap"
    
    # Check counts
    assert len(L_XSD) == 14, f"Expected 14 in L_XSD, got {len(L_XSD)}"
    assert len(L_REF) == 2, f"Expected 2 in L_REF, got {len(L_REF)}"
    assert len(L_SEM) == 14, f"Expected 14 in L_SEM, got {len(L_SEM)}"
    assert len(L_RUN) == 1, f"Expected 1 in L_RUN, got {len(L_RUN)}"
    assert len(L_ALL) == 31, f"Expected 31 total, got {len(L_ALL)}"
    
    return True


# Verify on module load
verify_partition()