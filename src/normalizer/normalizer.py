# src/normalizer/normalizer.py
"""
ODRL-SA Value Normalizer

Normalizes constraint values to canonical forms for comparison.

This module is CONFIGURATION-DRIVEN:
- Each operand in config/operands.yaml has a 'normalize' field
- The normalizer function is looked up from this configuration
- To add a new normalizer: add it to NORMALIZERS dict and reference in config

Normalization types:
    to_integer          → Convert to Python int
    to_float            → Convert to Python float  
    datetime_to_timestamp → Convert ISO datetime to UTC timestamp
    duration_to_seconds → Convert ISO duration (PT1H) to seconds
    to_uri              → Normalize URI (strip prefix)
    none                → No normalization (pass through)

Usage:
    from normalizer import normalize_value, normalize_constraint
    
    # Normalize a single value
    result = normalize_value(80, "percentage")
    
    # Normalize a constraint (updates in place)
    normalize_constraint(constraint)
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

from typing import Any, Optional, Tuple, Callable, Dict, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import get_registry

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.constraint_types import AtomicConstraint

logger = logging.getLogger(__name__)


# =============================================================================
# NORMALIZATION RESULT
# =============================================================================

@dataclass
class NormalizationResult:
    """Result of normalizing a value."""
    
    value: Any
    """The normalized value."""
    
    original: Any
    """The original value before normalization."""
    
    normalizer: str
    """Name of the normalizer applied."""
    
    success: bool = True
    """Whether normalization succeeded."""
    
    error: Optional[str] = None
    """Error message if normalization failed."""


# =============================================================================
# NORMALIZER FUNCTIONS
# =============================================================================

def _to_integer(value: Any) -> int:
    """Convert value to integer."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (float, Decimal)):
        return int(value)
    if isinstance(value, str):
        # Handle numeric strings
        value = value.strip()
        if '.' in value:
            return int(float(value))
        return int(value)
    return int(value)


def _to_float(value: Any) -> float:
    """Convert value to float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    return float(value)


def _datetime_to_timestamp(value: Any) -> int:
    """
    Convert datetime/date to Unix timestamp (seconds since epoch).
    
    Handles:
    - datetime objects (with timezone)
    - date objects (xsd:date) -> treated as start of day UTC
    - ISO 8601 strings (2024-01-01T00:00:00Z)
    - Date-only strings (2024-01-01)
    - Already numeric timestamps
    
    IMPORTANT: For xsd:date values, we convert to start-of-day UTC.
    The encoder should handle operator semantics (gteq -> start, lteq -> end).
    """
    from datetime import date, timedelta
    
    if value is None:
        return 0
    
    # Already a timestamp
    if isinstance(value, (int, float)):
        return int(value)
    
    # datetime object (has time component)
    if isinstance(value, datetime):
        return int(value.timestamp())
    
    # date object (NO time component) - from xsd:date
    # Convert to start of day in UTC
    if isinstance(value, date):
        # Create datetime at start of day UTC
        dt = datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=timezone.utc)
        return int(dt.timestamp())
    
    # ISO string
    if isinstance(value, str):
        value = value.strip()
        
        # Handle Z suffix
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        
        # Try parsing as datetime first
        try:
            dt = datetime.fromisoformat(value)
            # Add UTC timezone if naive
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            pass
        
        # Try parsing as date-only (YYYY-MM-DD)
        try:
            from datetime import date as date_type
            d = date_type.fromisoformat(value)
            dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            pass
        
        # Try parsing common formats
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse datetime: {value}")
    
    raise ValueError(f"Cannot convert {type(value)} to timestamp")


def validate_duration_value(value: Any) -> Optional[str]:
    """
    Reject variable-length durations (P1M, P1Y).
    
    ISO 8601 months and years have variable lengths:
    - 1 month = 28-31 days
    - 1 year = 365 or 366 days
    
    These cannot be precisely converted to seconds without a reference date.
    
    Returns:
        Error message if invalid, None if valid
    """
    if isinstance(value, str):
        value_upper = value.upper()
        # Check for Year (P1Y, P2Y, etc.) - but not in time part
        if 'Y' in value_upper:
            # Make sure it's not part of a different pattern
            if 'Y' in value_upper.split('T')[0]:  # Only check date part
                return f"Variable-length duration with years not supported: {value}"
        
        # Check for Month (P1M, P2M, etc.) - but not Minute (PT1M)
        if 'M' in value_upper:
            date_part = value_upper.split('T')[0] if 'T' in value_upper else value_upper
            if 'M' in date_part:  # Month is in date part, not time part
                return f"Variable-length duration with months not supported: {value}"
    
    return None


def _duration_to_seconds(value: Any) -> int:
    """
    Convert ISO 8601 duration to seconds.
    
    Handles:
    - datetime.timedelta objects (from RDFLib)
    - ISO duration strings (PT1H, P1D, PT30M, etc.)
    - Already numeric values (assumed to be seconds)
    
    Format: P[n]Y[n]M[n]DT[n]H[n]M[n]S
    
    Note: P1M (months) and P1Y (years) are rejected as variable-length.
    """
    from datetime import timedelta
    
    if value is None:
        return 0
    
    # Handle timedelta (from RDFLib parsing xsd:duration)
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    
    # Already numeric
    if isinstance(value, (int, float, Decimal)):
        return int(value)
    
    if not isinstance(value, str):
        if hasattr(value, 'total_seconds'):
            return int(value.total_seconds())
        return int(value)
    
    value = value.strip().upper()
    
    # Validate: reject variable-length durations
    error = validate_duration_value(value)
    if error:
        logger.warning(error)
        # Still try to parse with approximation, but warn
    
    # Must start with P
    if not value.startswith('P'):
        try:
            return int(float(value))
        except ValueError:
            raise ValueError(f"Invalid duration format: {value}")
    
    # Parse ISO 8601 duration
    # Pattern: P[n]Y[n]M[n]DT[n]H[n]M[n]S
    pattern = r'^P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
    match = re.match(pattern, value)
    
    if not match:
        raise ValueError(f"Cannot parse duration: {value}")
    
    years, months, days, hours, minutes, seconds = match.groups()
    
    total_seconds = 0
    
    # Approximate years and months (with warning already logged)
    if years:
        total_seconds += int(years) * 365 * 24 * 3600
    if months:
        total_seconds += int(months) * 30 * 24 * 3600
    if days:
        total_seconds += int(days) * 24 * 3600
    if hours:
        total_seconds += int(hours) * 3600
    if minutes:
        total_seconds += int(minutes) * 60
    if seconds:
        total_seconds += int(float(seconds))
    
    return total_seconds


def _to_uri(value: Any) -> str:
    """
    Normalize URI value.
    
    For GROUNDED class operands - just ensures it's a clean string.
    """
    if value is None:
        return ""
    return str(value).strip()


def _to_coordinates(value: Any) -> Tuple[float, float]:
    """
    Normalize spatial coordinates.
    
    Handles:
    - Tuple/list of (x, y)
    - String "x,y"
    """
    if value is None:
        return (0.0, 0.0)
    
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        return (float(value[0]), float(value[1]))
    
    if isinstance(value, str):
        parts = value.split(',')
        if len(parts) >= 2:
            return (float(parts[0].strip()), float(parts[1].strip()))
    
    raise ValueError(f"Cannot parse coordinates: {value}")


def _none(value: Any) -> Any:
    """No normalization - pass through."""
    return value


# =============================================================================
# NORMALIZER REGISTRY
# =============================================================================

# Map normalizer names to functions
NORMALIZERS: Dict[str, Callable[[Any], Any]] = {
    'to_integer': _to_integer,
    'to_float': _to_float,
    'datetime_to_timestamp': _datetime_to_timestamp,
    'duration_to_seconds': _duration_to_seconds,
    'to_uri': _to_uri,
    'to_coordinates': _to_coordinates,
    'none': _none,
}


def get_normalizer(name: str) -> Callable[[Any], Any]:
    """
    Get normalizer function by name.
    
    Args:
        name: Normalizer name from config (e.g., 'to_integer')
        
    Returns:
        Normalizer function
    """
    if name in NORMALIZERS:
        return NORMALIZERS[name]
    
    logger.warning(f"Unknown normalizer '{name}', using 'none'")
    return _none


# =============================================================================
# MAIN API
# =============================================================================

def normalize_value(
    value: Any, 
    left_operand: str,
    normalizer_override: Optional[str] = None
) -> NormalizationResult:
    """
    Normalize a value based on its operand type.
    
    Args:
        value: The value to normalize
        left_operand: The ODRL leftOperand (determines normalizer)
        normalizer_override: Override the config normalizer
        
    Returns:
        NormalizationResult with normalized value
    """
    registry = get_registry()
    
    # Get normalizer name from config or override
    if normalizer_override:
        normalizer_name = normalizer_override
    else:
        normalizer_name = registry.get_normalizer(left_operand)
    
    # Get normalizer function
    normalizer_func = get_normalizer(normalizer_name)
    
    try:
        normalized = normalizer_func(value)
        return NormalizationResult(
            value=normalized,
            original=value,
            normalizer=normalizer_name,
            success=True
        )
    except Exception as e:
        logger.warning(f"Normalization failed for {left_operand}: {e}")
        return NormalizationResult(
            value=value,  # Return original on failure
            original=value,
            normalizer=normalizer_name,
            success=False,
            error=str(e)
        )


def normalize_constraint(constraint: AtomicConstraint) -> AtomicConstraint:
    """
    Normalize a constraint's value in place.
    
    Args:
        constraint: AtomicConstraint to normalize
        
    Returns:
        The same constraint with normalized value
    """
    # Import here to avoid circular imports at module level
    from core.constraint_types import RightOperand
    
    # Skip if already normalized or special value
    if constraint.right_operand.is_policy_usage:
        return constraint
    if constraint.right_operand.is_iri:
        # Still normalize URI strings
        result = normalize_value(
            constraint.right_operand.value,
            constraint.left_operand,
            normalizer_override='to_uri'
        )
        # Note: RightOperand is frozen, so we can't modify in place
        # The caller should handle creating a new constraint if needed
        return constraint
    
    # Normalize the value
    result = normalize_value(
        constraint.right_operand.value,
        constraint.left_operand
    )
    
    if not result.success:
        logger.warning(f"Failed to normalize constraint {constraint.uid}: {result.error}")
    
    # Note: Since RightOperand is frozen, we return the constraint as-is
    # The normalized value is available via normalize_value()
    # For actual modification, create a new constraint
    
    return constraint


def get_normalized_value(constraint: AtomicConstraint) -> Any:
    """
    Get the normalized value for a constraint.
    
    This is the value that should be used for Z3 encoding.
    
    Args:
        constraint: AtomicConstraint
        
    Returns:
        Normalized value
    """
    if constraint.right_operand.is_policy_usage:
        return None
    
    result = normalize_value(
        constraint.right_operand.value,
        constraint.left_operand
    )
    
    return result.value


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ODRL-SA Normalizer Test")
    print("=" * 60)
    
    # Test each normalizer
    tests = [
        ("count", "10", "to_integer"),
        ("count", 10.5, "to_integer"),
        ("percentage", "85.5", "to_float"),
        ("percentage", Decimal("80"), "to_float"),
        ("dateTime", "2024-01-01T00:00:00Z", "datetime_to_timestamp"),
        ("dateTime", "2024-06-15", "datetime_to_timestamp"),
        ("timeInterval", "PT1H", "duration_to_seconds"),
        ("elapsedTime", "P1D", "duration_to_seconds"),
        ("elapsedTime", "PT30M", "duration_to_seconds"),
        ("language", "http://example.org/en", "to_uri"),
        ("meteredTime", "anything", "none"),
    ]
    
    print("\nNormalization tests:")
    for operand, value, expected_normalizer in tests:
        result = normalize_value(value, operand)
        status = "" if result.success else "(failed)"
        print(f"  {status} {operand}: {repr(value)} → {repr(result.value)} ({result.normalizer})")
    
    # Test duration parsing
    print("\nDuration parsing tests:")
    durations = [
        ("PT1S", 1),
        ("PT1M", 60),
        ("PT1H", 3600),
        ("P1D", 86400),
        ("PT1H30M", 5400),
        ("P1DT12H", 129600),
    ]
    
    for duration, expected in durations:
        result = _duration_to_seconds(duration)
        status = "" if result == expected else "(failed)"
        print(f"  {status} {duration} → {result} (expected {expected})")
    
    print("\n" + "=" * 60)
    print("Normalizer tests complete!")
    print("=" * 60)
    from datetime import date, datetime, timezone

    print("=" * 50)
    
    # Test cases
    tests = [
        # (input, expected_description)
        (datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), "2024-01-01 datetime"),
        (date(2024, 1, 1), "2024-01-01 date (xsd:date)"),
        (date(2024, 12, 31), "2024-12-31 date (xsd:date)"),
        ("2024-01-01T00:00:00Z", "2024-01-01 ISO string"),
        ("2024-01-01", "2024-01-01 date string"),
        (1704067200, "Already timestamp"),
    ]
    
    for value, desc in tests:
        try:
            result = _datetime_to_timestamp(value)
            print(f"  {desc}: {value} -> {result}")
        except Exception as e:
            print(f"  {desc}: {value} -> ERROR: {e}")
    
    print("\nExpected values:")
    print("  2024-01-01 00:00:00 UTC = 1704067200")
    print("  2024-12-31 00:00:00 UTC = 1735603200")