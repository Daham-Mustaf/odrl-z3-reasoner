# src/normalizer/duration_parser.py
"""
ISO 8601 Duration Parser for ODRL-SA

Parses xsd:duration values (e.g., "P30D", "PT60M", "P1Y2M3DT4H5M6S")
and converts to seconds for SMT encoding.

Used by: elapsedTime, delayPeriod, timeInterval
Reference: https://www.w3.org/TR/xmlschema11-2/#duration
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONVERSION CONSTANTS
# =============================================================================

# Exact conversions
SECONDS_PER_SECOND = 1
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800

# Average conversions (for months/years)
# Using average month = 30.436875 days (365.2425 / 12)
# Using average year = 365.2425 days (Gregorian calendar)
SECONDS_PER_MONTH_AVG = 2629746    # ~30.44 days
SECONDS_PER_YEAR_AVG = 31556952    # ~365.25 days


# =============================================================================
# PARSED DURATION
# =============================================================================

@dataclass
class ParsedDuration:
    """Represents a parsed ISO 8601 duration."""
    
    years: float = 0
    months: float = 0
    days: float = 0
    hours: float = 0
    minutes: float = 0
    seconds: float = 0
    negative: bool = False
    
    def to_seconds(self) -> float:
        """
        Convert duration to total seconds.
        
        Note: Months and years use average lengths, which may introduce
        slight imprecision for durations involving these components.
        """
        total = (
            self.years * SECONDS_PER_YEAR_AVG +
            self.months * SECONDS_PER_MONTH_AVG +
            self.days * SECONDS_PER_DAY +
            self.hours * SECONDS_PER_HOUR +
            self.minutes * SECONDS_PER_MINUTE +
            self.seconds
        )
        return -total if self.negative else total
    
    def to_seconds_decimal(self) -> Decimal:
        """Convert to Decimal for precise SMT encoding."""
        return Decimal(str(self.to_seconds()))
    
    def has_variable_components(self) -> bool:
        """Check if duration has month/year (variable length) components."""
        return self.years > 0 or self.months > 0
    
    def is_zero(self) -> bool:
        """Check if duration is zero."""
        return (
            self.years == 0 and
            self.months == 0 and
            self.days == 0 and
            self.hours == 0 and
            self.minutes == 0 and
            self.seconds == 0
        )
    
    def __str__(self) -> str:
        """Reconstruct ISO 8601 string."""
        parts = []
        if self.negative:
            parts.append("-")
        parts.append("P")
        
        if self.years:
            parts.append(f"{self.years}Y")
        if self.months:
            parts.append(f"{self.months}M")
        if self.days:
            parts.append(f"{self.days}D")
        
        time_parts = []
        if self.hours:
            time_parts.append(f"{self.hours}H")
        if self.minutes:
            time_parts.append(f"{self.minutes}M")
        if self.seconds:
            time_parts.append(f"{self.seconds}S")
        
        if time_parts:
            parts.append("T")
            parts.extend(time_parts)
        
        result = "".join(parts)
        return result if result != "P" else "PT0S"


# =============================================================================
# DURATION PARSER
# =============================================================================

# ISO 8601 duration regex
# Handles: P[n]Y[n]M[n]DT[n]H[n]M[n]S
# Also handles: P[n]W (weeks)
DURATION_PATTERN = re.compile(
    r'^(?P<negative>-)?P'
    r'(?:(?P<years>\d+(?:\.\d+)?)Y)?'
    r'(?:(?P<months>\d+(?:\.\d+)?)M)?'
    r'(?:(?P<weeks>\d+(?:\.\d+)?)W)?'
    r'(?:(?P<days>\d+(?:\.\d+)?)D)?'
    r'(?:T'
    r'(?:(?P<hours>\d+(?:\.\d+)?)H)?'
    r'(?:(?P<minutes>\d+(?:\.\d+)?)M)?'
    r'(?:(?P<seconds>\d+(?:\.\d+)?)S)?'
    r')?$',
    re.IGNORECASE
)


def parse_duration(duration_str: str) -> Optional[ParsedDuration]:
    """
    Parse an ISO 8601 duration string.
    
    Args:
        duration_str: Duration string (e.g., "P30D", "PT60M", "P1Y2M3DT4H5M6S")
        
    Returns:
        ParsedDuration object, or None if parsing fails
        
    Examples:
        >>> parse_duration("PT60M")
        ParsedDuration(minutes=60)  # 3600 seconds
        
        >>> parse_duration("P30D")
        ParsedDuration(days=30)  # 2592000 seconds
        
        >>> parse_duration("P1Y2M3DT4H5M6S")
        ParsedDuration(years=1, months=2, days=3, hours=4, minutes=5, seconds=6)
        
        >>> parse_duration("P1W")
        ParsedDuration(days=7)  # Weeks converted to days
    """
    if not duration_str:
        return None
    
    # Strip whitespace
    duration_str = duration_str.strip()
    
    # Handle string types from RDF
    if hasattr(duration_str, 'toPython'):
        duration_str = str(duration_str)
    
    match = DURATION_PATTERN.match(duration_str)
    if not match:
        logger.warning(f"Invalid duration format: {duration_str}")
        return None
    
    groups = match.groupdict()
    
    # Convert weeks to days if present
    weeks = float(groups.get('weeks') or 0)
    days = float(groups.get('days') or 0) + (weeks * 7)
    
    return ParsedDuration(
        years=float(groups.get('years') or 0),
        months=float(groups.get('months') or 0),
        days=days,
        hours=float(groups.get('hours') or 0),
        minutes=float(groups.get('minutes') or 0),
        seconds=float(groups.get('seconds') or 0),
        negative=groups.get('negative') == '-'
    )


def duration_to_seconds(duration_str: str) -> Optional[float]:
    """
    Convert duration string directly to seconds.
    
    Convenience function for simple use cases.
    
    Args:
        duration_str: ISO 8601 duration string
        
    Returns:
        Total seconds as float, or None if parsing fails
        
    Examples:
        >>> duration_to_seconds("PT60M")
        3600.0
        
        >>> duration_to_seconds("P30D")
        2592000.0
        
        >>> duration_to_seconds("PT1H30M")
        5400.0
    """
    parsed = parse_duration(duration_str)
    if parsed is None:
        return None
    return parsed.to_seconds()


def duration_to_decimal(duration_str: str) -> Optional[Decimal]:
    """
    Convert duration string to Decimal seconds.
    
    Use this for SMT encoding to preserve precision.
    """
    parsed = parse_duration(duration_str)
    if parsed is None:
        return None
    return parsed.to_seconds_decimal()


# =============================================================================
# VALIDATION
# =============================================================================

def is_valid_duration(duration_str: str) -> bool:
    """Check if string is a valid ISO 8601 duration."""
    return parse_duration(duration_str) is not None


def validate_duration_for_elapsed_time(duration_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate duration for elapsedTime operand.
    
    Returns:
        (is_valid, warning_message)
        
    Warnings issued for:
        - Zero duration (meaningless for elapsedTime)
        - Negative duration (invalid for elapsedTime)
        - Variable-length components (months/years use averages)
    """
    parsed = parse_duration(duration_str)
    
    if parsed is None:
        return (False, f"Invalid duration format: {duration_str}")
    
    if parsed.negative:
        return (False, "Negative duration is invalid for elapsedTime")
    
    if parsed.is_zero():
        return (False, "Zero duration is meaningless for elapsedTime")
    
    if parsed.has_variable_components():
        return (True, f"Duration contains months/years which have variable lengths. "
                      f"Using average: {parsed.to_seconds()} seconds")
    
    return (True, None)


# =============================================================================
# COMMON DURATION EXAMPLES
# =============================================================================

COMMON_DURATIONS = {
    # Minutes
    "PT1M": 60,
    "PT5M": 300,
    "PT10M": 600,
    "PT15M": 900,
    "PT30M": 1800,
    "PT60M": 3600,
    
    # Hours
    "PT1H": 3600,
    "PT2H": 7200,
    "PT12H": 43200,
    "PT24H": 86400,
    
    # Days
    "P1D": 86400,
    "P7D": 604800,
    "P14D": 1209600,
    "P30D": 2592000,
    "P90D": 7776000,
    "P365D": 31536000,
    
    # Weeks
    "P1W": 604800,
    "P2W": 1209600,
    "P4W": 2419200,
    
    # Mixed
    "PT1H30M": 5400,
    "P1DT12H": 129600,
    "P7DT0H": 604800,
}


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Duration Parser Test")
    print("=" * 60)
    
    test_cases = [
        # Basic cases
        ("PT60M", 3600),
        ("PT1H", 3600),
        ("P30D", 2592000),
        ("P1W", 604800),
        
        # Complex cases
        ("P1Y2M3DT4H5M6S", None),  # Has variable components
        ("PT1H30M", 5400),
        ("P1DT12H", 129600),
        
        # Edge cases
        ("PT0S", 0),
        ("P0D", 0),
        ("-P1D", -86400),
        
        # Invalid cases
        ("invalid", None),
        ("60M", None),  # Missing P
        ("", None),
    ]
    
    print("\nParsing Tests:")
    print("-" * 60)
    
    for duration_str, expected in test_cases:
        result = duration_to_seconds(duration_str)
        
        if expected is None:
            status = "✓" if result is not None else "✗"
            print(f"  {status} {duration_str:20} → {result}")
        else:
            status = "✓" if result == expected else "✗"
            print(f"  {status} {duration_str:20} → {result} (expected: {expected})")
    
    print("\n" + "=" * 60)
    print("Validation Tests:")
    print("-" * 60)
    
    validation_cases = [
        "PT60M",      # Valid
        "P30D",       # Valid
        "P1M",        # Warning (variable month)
        "P1Y",        # Warning (variable year)
        "PT0S",       # Invalid (zero)
        "-P1D",       # Invalid (negative)
    ]
    
    for dur in validation_cases:
        valid, warning = validate_duration_for_elapsed_time(dur)
        status = "✓" if valid else "✗"
        msg = warning if warning else "OK"
        print(f"  {status} {dur:10} → {msg[:50]}")
    
    print("\n" + "=" * 60)