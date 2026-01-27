# src/semantics/durations.py
"""
ISO 8601 Duration Handling for ODRL Constraints

Provides parsing and conversion of ISO 8601 durations to seconds:
- P1D → 86400 seconds
- PT1H30M → 5400 seconds
- P1Y2M3DT4H5M6S → full conversion

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0

Conversion Table:
┌──────────────┬─────────────────────────────────┐
│ XSD Duration │ Seconds                         │
├──────────────┼─────────────────────────────────┤
│ PT1S         │ 1                               │
│ PT1M         │ 60                              │
│ PT1H         │ 3600                            │
│ P1D          │ 86400                           │
│ P1W          │ 604800                          │
│ P1M          │ 2592000 (30 days approx)        │
│ P1Y          │ 31536000 (365 days approx)      │
└──────────────┴─────────────────────────────────┘

Note: Month and year are approximations (30 and 365 days).
For policy analysis, this approximation is acceptable.
"""

import re
from typing import Optional, Dict, Tuple, Union
from dataclasses import dataclass


# =============================================================================
# DURATION CONVERSION CONSTANTS
# =============================================================================

SECONDS_PER_SECOND = 1
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800
SECONDS_PER_MONTH = 2592000    # 30 days (approximation)
SECONDS_PER_YEAR = 31536000    # 365 days (approximation)

DURATION_CONVERSION: Dict[str, int] = {
    'S': SECONDS_PER_SECOND,
    'M': SECONDS_PER_MINUTE,     # In time part (after T)
    'H': SECONDS_PER_HOUR,
    'D': SECONDS_PER_DAY,
    'W': SECONDS_PER_WEEK,
    'MONTH': SECONDS_PER_MONTH,  # M in date part (before T)
    'Y': SECONDS_PER_YEAR,
}


# =============================================================================
# PARSED DURATION
# =============================================================================

@dataclass
class ParsedDuration:
    """
    Parsed ISO 8601 duration components.
    
    Attributes:
        years: Number of years
        months: Number of months
        weeks: Number of weeks
        days: Number of days
        hours: Number of hours
        minutes: Number of minutes
        seconds: Number of seconds (can be fractional)
        negative: Whether duration is negative
    """
    years: float = 0
    months: float = 0
    weeks: float = 0
    days: float = 0
    hours: float = 0
    minutes: float = 0
    seconds: float = 0
    negative: bool = False
    
    def to_seconds(self) -> float:
        """
        Convert to total seconds.
        
        Note: Uses approximations for months (30 days) and years (365 days).
        """
        total = (
            self.years * SECONDS_PER_YEAR +
            self.months * SECONDS_PER_MONTH +
            self.weeks * SECONDS_PER_WEEK +
            self.days * SECONDS_PER_DAY +
            self.hours * SECONDS_PER_HOUR +
            self.minutes * SECONDS_PER_MINUTE +
            self.seconds
        )
        
        if self.negative:
            total = -total
        
        return total
    
    def to_seconds_int(self) -> int:
        """Convert to total seconds as integer (truncated)."""
        return int(self.to_seconds())
    
    def __str__(self) -> str:
        """Convert back to ISO 8601 format."""
        parts = []
        if self.negative:
            parts.append('-')
        parts.append('P')
        
        if self.years:
            parts.append(f"{int(self.years)}Y")
        if self.months:
            parts.append(f"{int(self.months)}M")
        if self.weeks:
            parts.append(f"{int(self.weeks)}W")
        if self.days:
            parts.append(f"{int(self.days)}D")
        
        time_parts = []
        if self.hours:
            time_parts.append(f"{int(self.hours)}H")
        if self.minutes:
            time_parts.append(f"{int(self.minutes)}M")
        if self.seconds:
            if self.seconds == int(self.seconds):
                time_parts.append(f"{int(self.seconds)}S")
            else:
                time_parts.append(f"{self.seconds}S")
        
        if time_parts:
            parts.append('T')
            parts.extend(time_parts)
        
        result = ''.join(str(p) for p in parts)
        return result if result not in ('P', '-P') else 'PT0S'


# =============================================================================
# DURATION PARSING
# =============================================================================

# ISO 8601 duration regex
_DURATION_REGEX = re.compile(
    r'^(?P<sign>-)?P'
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


def parse_iso8601_duration(duration_str: str) -> Optional[ParsedDuration]:
    """
    Parse an ISO 8601 duration string.
    
    Args:
        duration_str: ISO 8601 duration (e.g., 'P1D', 'PT1H30M', 'P1Y2M3DT4H5M6S')
        
    Returns:
        ParsedDuration or None if invalid
        
    Examples:
        >>> parse_iso8601_duration('P1D')
        ParsedDuration(days=1)
        
        >>> parse_iso8601_duration('PT1H30M')
        ParsedDuration(hours=1, minutes=30)
    """
    if not duration_str:
        return None
    
    # Clean up the string
    duration_str = duration_str.strip()
    
    # Handle xsd:duration type annotation
    if '^^' in duration_str:
        duration_str = duration_str.split('^^')[0].strip('"\'')
    
    match = _DURATION_REGEX.match(duration_str)
    
    if not match:
        return None
    
    groups = match.groupdict()
    
    def to_float(value: Optional[str]) -> float:
        return float(value) if value else 0
    
    return ParsedDuration(
        years=to_float(groups.get('years')),
        months=to_float(groups.get('months')),
        weeks=to_float(groups.get('weeks')),
        days=to_float(groups.get('days')),
        hours=to_float(groups.get('hours')),
        minutes=to_float(groups.get('minutes')),
        seconds=to_float(groups.get('seconds')),
        negative=groups.get('sign') == '-'
    )


def duration_to_seconds(duration: Union[str, ParsedDuration]) -> Optional[int]:
    """
    Convert duration to seconds.
    
    Args:
        duration: Duration string or ParsedDuration
        
    Returns:
        Total seconds as integer, or None if invalid
        
    Examples:
        >>> duration_to_seconds('PT1M')
        60
        >>> duration_to_seconds('P1D')
        86400
        >>> duration_to_seconds('P30D')
        2592000
    """
    if isinstance(duration, str):
        parsed = parse_iso8601_duration(duration)
        if parsed is None:
            return None
    else:
        parsed = duration
    
    return parsed.to_seconds_int()


def duration_to_seconds_float(duration: Union[str, ParsedDuration]) -> Optional[float]:
    """
    Convert duration to seconds (preserving fractional seconds).
    
    Args:
        duration: Duration string or ParsedDuration
        
    Returns:
        Total seconds as float, or None if invalid
    """
    if isinstance(duration, str):
        parsed = parse_iso8601_duration(duration)
        if parsed is None:
            return None
    else:
        parsed = duration
    
    return parsed.to_seconds()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def seconds_to_duration(seconds: Union[int, float]) -> str:
    """
    Convert seconds to ISO 8601 duration string.
    
    Args:
        seconds: Number of seconds
        
    Returns:
        ISO 8601 duration string
        
    Examples:
        >>> seconds_to_duration(3600)
        'PT1H'
        >>> seconds_to_duration(86400)
        'P1D'
    """
    negative = seconds < 0
    seconds = abs(int(seconds))
    
    days = seconds // SECONDS_PER_DAY
    seconds %= SECONDS_PER_DAY
    
    hours = seconds // SECONDS_PER_HOUR
    seconds %= SECONDS_PER_HOUR
    
    minutes = seconds // SECONDS_PER_MINUTE
    secs = seconds % SECONDS_PER_MINUTE
    
    parts = []
    if negative:
        parts.append('-')
    parts.append('P')
    
    if days:
        parts.append(f'{days}D')
    
    time_parts = []
    if hours:
        time_parts.append(f'{hours}H')
    if minutes:
        time_parts.append(f'{minutes}M')
    if secs:
        time_parts.append(f'{secs}S')
    
    if time_parts:
        parts.append('T')
        parts.extend(time_parts)
    
    result = ''.join(str(p) for p in parts)
    return result if result not in ('P', '-P') else 'PT0S'


def is_valid_duration(duration_str: str) -> bool:
    """
    Check if a string is a valid ISO 8601 duration.
    
    Args:
        duration_str: String to check
        
    Returns:
        True if valid ISO 8601 duration
    """
    return parse_iso8601_duration(duration_str) is not None


def compare_durations(d1: str, d2: str) -> Optional[int]:
    """
    Compare two ISO 8601 durations.
    
    Args:
        d1: First duration
        d2: Second duration
        
    Returns:
        -1 if d1 < d2, 0 if equal, 1 if d1 > d2
        None if either is invalid
    """
    s1 = duration_to_seconds(d1)
    s2 = duration_to_seconds(d2)
    
    if s1 is None or s2 is None:
        return None
    
    if s1 < s2:
        return -1
    elif s1 > s2:
        return 1
    else:
        return 0


# =============================================================================
# COMMON DURATION CONSTANTS
# =============================================================================

COMMON_DURATIONS: Dict[str, int] = {
    'PT1S': SECONDS_PER_SECOND,
    'PT1M': SECONDS_PER_MINUTE,
    'PT1H': SECONDS_PER_HOUR,
    'P1D': SECONDS_PER_DAY,
    'P1W': SECONDS_PER_WEEK,
    'P30D': SECONDS_PER_MONTH,
    'P1M': SECONDS_PER_MONTH,
    'P1Y': SECONDS_PER_YEAR,
    'P365D': SECONDS_PER_YEAR,
}