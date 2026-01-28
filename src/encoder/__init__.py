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
    - check_consistency(constraints): Check if constraints are consistent
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
    
    # Convenience function
    check_consistency,
)

__all__ = [
    "Z3JudgmentEngine",
    "ConstraintEncoder",
    "CompositeEncoder",
    "Z3VariableManager",
    "DomainBounds",
    "DOMAIN_BOUNDS",
    "check_consistency",
]