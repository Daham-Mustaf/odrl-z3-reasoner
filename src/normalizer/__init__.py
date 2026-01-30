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
    
    # Use enhanced duration parser directly
    from normalizer import parse_duration, ParsedDuration
    parsed = parse_duration("P1DT12H")
    print(parsed.to_seconds())  # 129600.0
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

# Enhanced duration parser (new)
from .duration_parser import (
    # Main functions
    parse_duration,
    duration_to_seconds,
    duration_to_decimal,
    
    # Validation
    is_valid_duration,
    validate_duration_for_elapsed_time,
    
    # Data class
    ParsedDuration,
    
    # Constants
    COMMON_DURATIONS,
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    SECONDS_PER_WEEK,
)

__all__ = [
    # Main API
    "normalize_value",
    "normalize_constraint",
    "get_normalized_value",
    "NormalizationResult",
    "NORMALIZERS",
    "get_normalizer",
    
    # Duration parser
    "parse_duration",
    "duration_to_seconds",
    "duration_to_decimal",
    "is_valid_duration",
    "validate_duration_for_elapsed_time",
    "ParsedDuration",
    "COMMON_DURATIONS",
    "SECONDS_PER_DAY",
    "SECONDS_PER_HOUR",
    "SECONDS_PER_MINUTE",
    "SECONDS_PER_WEEK",
]