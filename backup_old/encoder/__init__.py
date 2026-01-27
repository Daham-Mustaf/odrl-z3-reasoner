# src/encoder/__init__.py
"""
ODRL-SA Encoder Module

Provides Z3 SMT encoding for ODRL constraints.

Main Components:
    - Z3JudgmentEngine: SMT-based judgment engine
    - ConstraintEncoder: Encodes atomic constraints
    - CompositeEncoder: Encodes logical compositions
    - Z3VariableManager: Manages Z3 variables

Convenience Functions:
    - judge_constraints(c1, c2): Judge two constraints
    - check_consistency(constraints): Check if constraints are consistent

Domain Bounds:
    - DOMAIN_BOUNDS: Maps LeftOperands to their valid ranges
"""

from .z3_encoder import (
    # Engine
    Z3JudgmentEngine,
    
    # Encoders
    ConstraintEncoder,
    CompositeEncoder,
    Z3VariableManager,
    
    # Domain
    DomainBounds,
    DOMAIN_BOUNDS,
    
    # Convenience functions
    judge_constraints,
    check_consistency,
)

__all__ = [
    "Z3JudgmentEngine",
    "ConstraintEncoder",
    "CompositeEncoder",
    "Z3VariableManager",
    "DomainBounds",
    "DOMAIN_BOUNDS",
    "judge_constraints",
    "check_consistency",
]