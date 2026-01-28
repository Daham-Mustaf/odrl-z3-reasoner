# src/core/classifier.py
"""
ODRL-SA Constraint Classifier

Implements Definition 4 (LeftOperand Partition):

    L = L_xsd ⊎ L_ref ⊎ L_sem ⊎ L_run
    
    where L_sem = L_kb ⊎ L_deref

This module uses the OperandRegistry for classification.
To change the formalism, edit config/operands.yaml - NOT this code!

Classification determines what reasoning strategy to use:
    FULL (L_xsd)     → SMT only, complete analysis
    PARTIAL (L_ref)  → SMT + reference point alignment
    GROUNDED (L_kb)  → SMT + Oracle query
    DEFERRED (L_deref) → Cannot analyze (needs dereferencing)
    RUNTIME (L_run)  → Cannot analyze (needs runtime state)
"""

from typing import Optional, Set
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from registry
from registry import get_registry, ConstraintClass, OperandInfo

# Import types (avoid circular import by using TYPE_CHECKING)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.constraint_types import AtomicConstraint


# =============================================================================
# CLASSIFICATION RESULT
# =============================================================================

@dataclass
class ClassificationResult:
    """Result of classifying a constraint."""
    
    constraint_class: ConstraintClass
    """The classification (FULL, PARTIAL, GROUNDED, DEFERRED, RUNTIME)."""
    
    left_operand: str
    """The LeftOperand that was classified."""
    
    oracle_needed: Optional[str] = None
    """For GROUNDED: which oracle is needed."""
    
    oracle_available: bool = True
    """For GROUNDED: is the oracle implemented?"""
    
    reason: str = ""
    """Human-readable explanation."""
    
    @property
    def can_analyze(self) -> bool:
        """Can we produce a definite judgment (not UNKNOWN)?"""
        if self.constraint_class in {ConstraintClass.FULL, ConstraintClass.PARTIAL}:
            return True
        if self.constraint_class == ConstraintClass.GROUNDED:
            return self.oracle_available
        return False


# =============================================================================
# CLASSIFIER FUNCTIONS
# =============================================================================

def classify_operand(left_operand: str) -> ClassificationResult:
    """
    Classify a LeftOperand according to Definition 4.
    
    Uses the OperandRegistry - no hardcoded sets!
    
    Args:
        left_operand: The ODRL leftOperand (e.g., "count", "language")
        
    Returns:
        ClassificationResult with class and oracle requirements
    """
    registry = get_registry()
    
    # Normalize: extract local name from URI
    op = left_operand
    if '#' in op:
        op = op.split('#')[-1]
    elif '/' in op:
        op = op.split('/')[-1]
    op = op.strip()
    
    # Get operand info from registry
    info = registry.get_operand(op)
    
    if info is None:
        # Unknown operand - treat as RUNTIME (most conservative)
        return ClassificationResult(
            constraint_class=ConstraintClass.RUNTIME,
            left_operand=op,
            reason=f"Unknown LeftOperand '{op}' - treated as RUNTIME"
        )
    
    # Build result based on class
    if info.constraint_class == ConstraintClass.FULL:
        return ClassificationResult(
            constraint_class=ConstraintClass.FULL,
            left_operand=op,
            reason=f"L_xsd: XSD-typed, fully analyzable"
        )
    
    elif info.constraint_class == ConstraintClass.PARTIAL:
        return ClassificationResult(
            constraint_class=ConstraintClass.PARTIAL,
            left_operand=op,
            reason=f"L_ref: Reference-point dependent ({info.reference_point})"
        )
    
    elif info.constraint_class == ConstraintClass.GROUNDED:
        return ClassificationResult(
            constraint_class=ConstraintClass.GROUNDED,
            left_operand=op,
            oracle_needed=info.oracle_name,
            oracle_available=info.oracle_implemented,
            reason=f"L_kb: Requires {info.oracle_name or 'oracle'}"
        )
    
    elif info.constraint_class == ConstraintClass.DEFERRED:
        return ClassificationResult(
            constraint_class=ConstraintClass.DEFERRED,
            left_operand=op,
            reason=f"L_deref: Requires runtime dereferencing"
        )
    
    else:  # RUNTIME
        return ClassificationResult(
            constraint_class=ConstraintClass.RUNTIME,
            left_operand=op,
            reason=f"L_run: Runtime-only"
        )


def classify_constraint(constraint: 'AtomicConstraint') -> ClassificationResult:
    """
    Classify an AtomicConstraint.
    
    The classification depends on:
    1. The LeftOperand (primary factor)
    2. Whether it uses set-based operators (may elevate to GROUNDED)
    3. Whether it has rightOperandReference (elevates to DEFERRED)
    """
    # Check for deferred value
    if constraint.metadata and constraint.metadata.right_operand_reference:
        return ClassificationResult(
            constraint_class=ConstraintClass.DEFERRED,
            left_operand=constraint.left_operand,
            reason="Has rightOperandReference - requires dereferencing"
        )
    
    # Check for policyUsage
    if constraint.right_operand.is_policy_usage:
        return ClassificationResult(
            constraint_class=ConstraintClass.RUNTIME,
            left_operand=constraint.left_operand,
            reason="Uses policyUsage - requires runtime state"
        )
    
    # Classify by LeftOperand
    result = classify_operand(constraint.left_operand)
    
    # Set operators on FULL operands may still need KB for hierarchy
    if result.constraint_class == ConstraintClass.FULL:
        if constraint.operator.is_set_based():
            return ClassificationResult(
                constraint_class=ConstraintClass.GROUNDED,
                left_operand=constraint.left_operand,
                reason=f"Set operator {constraint.operator.value} requires semantic grounding"
            )
    
    return result


# =============================================================================
# CONVENIENCE FUNCTIONS (use registry)
# =============================================================================

def get_full_operands() -> Set[str]:
    """Get all FULL class operands (L_xsd)."""
    return get_registry().get_full_operands()


def get_partial_operands() -> Set[str]:
    """Get all PARTIAL class operands (L_ref)."""
    return get_registry().get_partial_operands()


def get_grounded_operands() -> Set[str]:
    """Get all GROUNDED class operands (L_kb)."""
    return get_registry().get_grounded_operands()


def get_runtime_operands() -> Set[str]:
    """Get all RUNTIME class operands (L_run)."""
    return get_registry().get_runtime_operands()


def get_partition_stats():
    """Get statistics about the LeftOperand partitions."""
    return get_registry().get_statistics()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ODRL-SA Classifier (Registry-Driven)")
    print("=" * 60)
    
    print("\nPartition Statistics:")
    stats = get_partition_stats()
    for name, value in stats.get('class_counts', {}).items():
        total = stats.get('total_operands', 31)
        pct = value / total * 100
        print(f"  {name}: {value} ({pct:.0f}%)")
    
    print("\nSample Classifications:")
    for op in ["count", "dateTime", "elapsedTime", "language", "meteredTime"]:
        result = classify_operand(op)
        oracle_str = f" (oracle: {result.oracle_needed})" if result.oracle_needed else ""
        print(f"  {op}: {result.constraint_class.value}{oracle_str}")