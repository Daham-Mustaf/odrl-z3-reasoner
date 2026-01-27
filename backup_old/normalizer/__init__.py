# src/normalizer/__init__.py
"""
ODRL-SA Normalizer Module

Normalizes constraint values to canonical forms for comparison.

This module is CONFIGURATION-DRIVEN:
- Normalizer names come from config/operands.yaml
- Each operand has a 'normalize' field specifying which normalizer to use

Available Normalizers:
    to_integer          → Convert to Python int
    to_float            → Convert to Python float
    datetime_to_timestamp → Convert ISO datetime to Unix timestamp
    duration_to_seconds → Convert ISO duration (PT1H) to seconds
    to_uri              → Normalize URI strings
    to_coordinates      → Parse spatial coordinates
    none                → No normalization

Usage:
    from normalizer import normalize_value, get_normalized_value
    
    # Normalize a value by operand
    result = normalize_value(80, "percentage")
    print(result.value)  # 80.0
    
    # Get normalized value from constraint
    value = get_normalized_value(constraint)
"""

from .normalizer import (
    # Main API
    normalize_value,
    normalize_constraint,
    get_normalized_value,
    
    # Result type
    NormalizationResult,
    
    # Normalizer registry
    NORMALIZERS,
    get_normalizer,
)

__all__ = [
    "normalize_value",
    "normalize_constraint",
    "get_normalized_value",
    "NormalizationResult",
    "NORMALIZERS",
    "get_normalizer",
]