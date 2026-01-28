# src/core/__init__.py
"""
ODRL-SA Core Module

This module contains the core types and functions that implement
the ODRL-SA formal specification exactly.

Types (Definition 1-3):
    - AtomicConstraint: c = (ℓ, ⋈, v, u?, d?, r?, s?)
    - CompositeConstraint: Logical composition
    - OperatorType: O = O_cmp ⊎ O_set
    - LogicalOperator: O_log = {and, or, xone, andSequence}
    - RightOperand: The value v

Classification (Definition 4):
    - ConstraintClass: FULL, PARTIAL, GROUNDED, DEFERRED, RUNTIME
    - classify_constraint(): Determine class of a constraint
    - get_full_operands(), get_partial_operands(), etc.

Judgment (Definition 5-6):
    - Judgment: CONFLICT, POSSIBLY-COMPATIBLE, UNKNOWN
    - judge(): Main judgment function
    - is_comparable(): Comparability predicate

NOTE: Classification uses the OperandRegistry.
      To change the formalism, edit config/operands.yaml - NOT this code!
"""

# Types
from .constraint_types import (
    # Operators
    OperatorType,
    LogicalOperator,
    
    # Values
    RightOperand,
    ConstraintMetadata,
    
    # Constraints
    AtomicConstraint,
    CompositeConstraint,
    Constraint,
    
    # Judgment
    Judgment,
    
    # Utilities
    is_comparison_operator,
    is_set_operator,
)

# Classifier (registry-driven)
from .classifier import (
    classify_operand,
    classify_constraint,
    ClassificationResult,
    
    # Convenience functions (use registry)
    get_full_operands,
    get_partial_operands,
    get_grounded_operands,
    get_runtime_operands,
    get_partition_stats,
)

# Re-export ConstraintClass from registry
from registry import ConstraintClass

# Judgment
from .judgment import (
    judge,
    is_comparable,
    
    # Comparability
    ComparabilityResult,
    IncomparabilityReason,
    check_same_operand,
    check_analyzable_class,
    check_unit_compatible,
    check_scope_compatible,
    check_temporal_compatible,
    
    # Results
    JudgmentResult,
    
    # Lattice operations
    judgment_meet,
    judgment_join,
)

__all__ = [
    # Types
    "OperatorType",
    "LogicalOperator",
    "RightOperand",
    "ConstraintMetadata",
    "AtomicConstraint",
    "CompositeConstraint",
    "Constraint",
    "ConstraintClass",
    "Judgment",
    
    # Classifier
    "classify_operand",
    "classify_constraint",
    "ClassificationResult",
    "get_full_operands",
    "get_partial_operands",
    "get_grounded_operands",
    "get_runtime_operands",
    "get_partition_stats",
    
    # Judgment
    "judge",
    "is_comparable",
    "ComparabilityResult",
    "IncomparabilityReason",
    "JudgmentResult",
    "judgment_meet",
    "judgment_join",
    
    # Utilities
    "is_comparison_operator",
    "is_set_operator",
]