# src/registry/__init__.py
"""
ODRL-SA Registry Module

Provides configuration-driven access to operand and operator information.
This is the SINGLE SOURCE OF TRUTH - all modules should use this registry
instead of hardcoding operand information.

Usage:
    from registry import get_registry, ConstraintClass
    
    registry = get_registry()
    
    # Get operand info
    info = registry.get_operand("count")
    
    # Get class
    cls = registry.get_class("language")  # GROUNDED
    
    # Get all FULL operands
    full_ops = registry.get_full_operands()
    
    # Check if oracle needed
    if registry.needs_oracle("purpose"):
        oracle_name = registry.get_oracle_name("purpose")
"""

from .operand_registry import (
    # Registry
    OperandRegistry,
    get_registry,
    reset_registry,
    
    # Data classes
    OperandInfo,
    OperatorInfo,
    
    # Enums
    ConstraintClass,
    Z3Sort,
)

__all__ = [
    # Registry
    "OperandRegistry",
    "get_registry",
    "reset_registry",
    
    # Data classes
    "OperandInfo",
    "OperatorInfo",
    
    # Enums
    "ConstraintClass",
    "Z3Sort",
]