# src/semantics/units.py
"""
Unit Handling for ODRL Constraints

Provides unit registry and compatibility checking:
- No unit conversion (different units = INCOMPARABLE)
- Unit category classification
- Common unit URI normalization

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0

Design Decision:
> Constraints with different units are treated as INCOMPARABLE.
> The engine reports a warning and cannot determine conflict/refinement.
> This maintains soundness while avoiding conversion complexity.
"""

from enum import Enum
from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass


class UnitCategory(Enum):
    """Categories of measurement units"""
    CURRENCY = "currency"
    TIME = "time"
    RESOLUTION = "resolution"
    SIZE = "size"
    COUNT = "count"
    PERCENTAGE = "percentage"
    DIMENSIONLESS = "dimensionless"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UnitInfo:
    """
    Information about a unit.
    
    Attributes:
        name: Human-readable name
        category: Unit category
        symbol: Short symbol (e.g., 'EUR', 's', 'DPI')
        uris: Known URIs for this unit
    """
    name: str
    category: UnitCategory
    symbol: str
    uris: Tuple[str, ...]


# =============================================================================
# UNIT REGISTRY
# =============================================================================

UNIT_REGISTRY: Dict[str, UnitInfo] = {
    # =========================================================================
    # CURRENCY
    # =========================================================================
    
    'EUR': UnitInfo(
        name='Euro',
        category=UnitCategory.CURRENCY,
        symbol='EUR',
        uris=(
            'http://dbpedia.org/resource/Euro',
            'https://dbpedia.org/resource/Euro',
            'http://www.wikidata.org/entity/Q4916',
        )
    ),
    
    'USD': UnitInfo(
        name='US Dollar',
        category=UnitCategory.CURRENCY,
        symbol='USD',
        uris=(
            'http://dbpedia.org/resource/US_Dollar',
            'http://dbpedia.org/resource/United_States_dollar',
            'https://dbpedia.org/resource/United_States_dollar',
            'http://www.wikidata.org/entity/Q4917',
        )
    ),
    
    'GBP': UnitInfo(
        name='British Pound',
        category=UnitCategory.CURRENCY,
        symbol='GBP',
        uris=(
            'http://dbpedia.org/resource/Pound_sterling',
            'https://dbpedia.org/resource/Pound_sterling',
            'http://www.wikidata.org/entity/Q25224',
        )
    ),
    
    'JPY': UnitInfo(
        name='Japanese Yen',
        category=UnitCategory.CURRENCY,
        symbol='JPY',
        uris=(
            'http://dbpedia.org/resource/Japanese_yen',
            'https://dbpedia.org/resource/Japanese_yen',
        )
    ),
    
    'CHF': UnitInfo(
        name='Swiss Franc',
        category=UnitCategory.CURRENCY,
        symbol='CHF',
        uris=(
            'http://dbpedia.org/resource/Swiss_franc',
            'https://dbpedia.org/resource/Swiss_franc',
        )
    ),
    
    # =========================================================================
    # TIME
    # =========================================================================
    
    'second': UnitInfo(
        name='Second',
        category=UnitCategory.TIME,
        symbol='s',
        uris=(
            'http://dbpedia.org/resource/Second',
            'https://dbpedia.org/resource/Second',
            'http://qudt.org/vocab/unit/SEC',
        )
    ),
    
    'minute': UnitInfo(
        name='Minute',
        category=UnitCategory.TIME,
        symbol='min',
        uris=(
            'http://dbpedia.org/resource/Minute',
            'https://dbpedia.org/resource/Minute',
            'http://qudt.org/vocab/unit/MIN',
        )
    ),
    
    'hour': UnitInfo(
        name='Hour',
        category=UnitCategory.TIME,
        symbol='h',
        uris=(
            'http://dbpedia.org/resource/Hour',
            'https://dbpedia.org/resource/Hour',
            'http://qudt.org/vocab/unit/HR',
        )
    ),
    
    'day': UnitInfo(
        name='Day',
        category=UnitCategory.TIME,
        symbol='d',
        uris=(
            'http://dbpedia.org/resource/Day',
            'https://dbpedia.org/resource/Day',
            'http://qudt.org/vocab/unit/DAY',
        )
    ),
    
    # =========================================================================
    # RESOLUTION
    # =========================================================================
    
    'DPI': UnitInfo(
        name='Dots per inch',
        category=UnitCategory.RESOLUTION,
        symbol='DPI',
        uris=(
            'http://dbpedia.org/resource/Dots_per_inch',
            'https://dbpedia.org/resource/Dots_per_inch',
        )
    ),
    
    'PPI': UnitInfo(
        name='Pixels per inch',
        category=UnitCategory.RESOLUTION,
        symbol='PPI',
        uris=(
            'http://dbpedia.org/resource/Pixels_per_inch',
            'https://dbpedia.org/resource/Pixels_per_inch',
        )
    ),
    
    # =========================================================================
    # SIZE (Information)
    # =========================================================================
    
    'byte': UnitInfo(
        name='Byte',
        category=UnitCategory.SIZE,
        symbol='B',
        uris=(
            'http://dbpedia.org/resource/Byte',
            'https://dbpedia.org/resource/Byte',
            'http://qudt.org/vocab/unit/BYTE',
        )
    ),
    
    'kilobyte': UnitInfo(
        name='Kilobyte',
        category=UnitCategory.SIZE,
        symbol='KB',
        uris=(
            'http://dbpedia.org/resource/Kilobyte',
            'https://dbpedia.org/resource/Kilobyte',
        )
    ),
    
    'megabyte': UnitInfo(
        name='Megabyte',
        category=UnitCategory.SIZE,
        symbol='MB',
        uris=(
            'http://dbpedia.org/resource/Megabyte',
            'https://dbpedia.org/resource/Megabyte',
        )
    ),
    
    'gigabyte': UnitInfo(
        name='Gigabyte',
        category=UnitCategory.SIZE,
        symbol='GB',
        uris=(
            'http://dbpedia.org/resource/Gigabyte',
            'https://dbpedia.org/resource/Gigabyte',
        )
    ),
    
    # =========================================================================
    # DIMENSIONLESS
    # =========================================================================
    
    'percent': UnitInfo(
        name='Percent',
        category=UnitCategory.PERCENTAGE,
        symbol='%',
        uris=(
            'http://dbpedia.org/resource/Percentage',
            'http://qudt.org/vocab/unit/PERCENT',
        )
    ),
    
    'count': UnitInfo(
        name='Count',
        category=UnitCategory.COUNT,
        symbol='',
        uris=()
    ),
}


# Build reverse lookup: URI -> unit name
_URI_TO_UNIT: Dict[str, str] = {}
for unit_name, unit_info in UNIT_REGISTRY.items():
    for uri in unit_info.uris:
        _URI_TO_UNIT[uri] = unit_name
        # Also add lowercase version
        _URI_TO_UNIT[uri.lower()] = unit_name


# =============================================================================
# UNIT COMPATIBILITY
# =============================================================================

class UnitIncompatibleError(Exception):
    """Raised when units are incompatible for comparison"""
    
    def __init__(self, unit1: str, unit2: str):
        self.unit1 = unit1
        self.unit2 = unit2
        super().__init__(
            f"Units are incompatible: '{unit1}' vs '{unit2}'. "
            "Cannot determine conflict/refinement relationship."
        )


def normalize_unit_uri(unit: Optional[str]) -> Optional[str]:
    """
    Normalize a unit URI or string to a canonical form.
    
    Args:
        unit: Unit URI, name, or symbol
        
    Returns:
        Normalized unit name, or None if not recognized
    """
    if unit is None:
        return None
    
    # Check if it's a known URI
    if unit in _URI_TO_UNIT:
        return _URI_TO_UNIT[unit]
    if unit.lower() in _URI_TO_UNIT:
        return _URI_TO_UNIT[unit.lower()]
    
    # Check if it's a unit name or symbol
    if unit in UNIT_REGISTRY:
        return unit
    
    # Try lowercase
    unit_lower = unit.lower()
    if unit_lower in UNIT_REGISTRY:
        return unit_lower
    
    # Check symbols
    for name, info in UNIT_REGISTRY.items():
        if info.symbol.lower() == unit_lower:
            return name
    
    # Try extracting from URI
    if '/' in unit:
        last_part = unit.split('/')[-1]
        if last_part in UNIT_REGISTRY:
            return last_part
        # Try converting underscores
        cleaned = last_part.replace('_', ' ').lower()
        for name, info in UNIT_REGISTRY.items():
            if info.name.lower() == cleaned:
                return name
    
    return None


def get_unit_category(unit: Optional[str]) -> UnitCategory:
    """
    Get the category of a unit.
    
    Args:
        unit: Unit URI, name, or symbol
        
    Returns:
        UnitCategory
    """
    if unit is None:
        return UnitCategory.UNKNOWN
    
    normalized = normalize_unit_uri(unit)
    if normalized and normalized in UNIT_REGISTRY:
        return UNIT_REGISTRY[normalized].category
    
    return UnitCategory.UNKNOWN


def are_units_compatible(unit1: Optional[str], unit2: Optional[str]) -> bool:
    """
    Check if two units are compatible for comparison.
    
    Design decision: Units must be IDENTICAL (after normalization) to be
    compatible. Different units (even in same category) are INCOMPARABLE.
    
    Args:
        unit1: First unit
        unit2: Second unit
        
    Returns:
        True if units are compatible (same unit or both None)
    """
    # Both None = compatible (unspecified)
    if unit1 is None and unit2 is None:
        return True
    
    # One None, one specified = incompatible (conservative)
    if unit1 is None or unit2 is None:
        return False
    
    # Normalize both
    norm1 = normalize_unit_uri(unit1)
    norm2 = normalize_unit_uri(unit2)
    
    # If either couldn't be normalized, compare raw strings
    if norm1 is None:
        norm1 = unit1
    if norm2 is None:
        norm2 = unit2
    
    # Must be exactly the same
    return norm1 == norm2


def check_unit_compatibility(unit1: Optional[str], unit2: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Check unit compatibility and return detailed result.
    
    Args:
        unit1: First unit
        unit2: Second unit
        
    Returns:
        Tuple of (is_compatible, warning_message)
        warning_message is None if compatible
    """
    if are_units_compatible(unit1, unit2):
        return (True, None)
    
    norm1 = normalize_unit_uri(unit1) or unit1
    norm2 = normalize_unit_uri(unit2) or unit2
    
    warning = (
        f"Unit mismatch: '{norm1}' vs '{norm2}'. "
        "Constraints with different units are INCOMPARABLE. "
        "Cannot determine conflict/refinement relationship."
    )
    
    return (False, warning)


def assert_units_compatible(unit1: Optional[str], unit2: Optional[str]) -> None:
    """
    Assert that units are compatible, raising UnitIncompatibleError if not.
    
    Args:
        unit1: First unit
        unit2: Second unit
        
    Raises:
        UnitIncompatibleError: If units are incompatible
    """
    if not are_units_compatible(unit1, unit2):
        raise UnitIncompatibleError(
            normalize_unit_uri(unit1) or str(unit1),
            normalize_unit_uri(unit2) or str(unit2)
        )


# =============================================================================
# UNIT OF COUNT (Special handling)
# =============================================================================

class UnitOfCount(Enum):
    """
    ODRL unitOfCount values.
    
    These define how counts are partitioned (per user, per device, etc.)
    """
    PER_USER = "perUser"
    PER_DEVICE = "perDevice"
    PER_ORGANIZATION = "perOrganization"
    PER_SESSION = "perSession"
    TOTAL = "total"  # Default


UNIT_OF_COUNT_URIS: Dict[str, UnitOfCount] = {
    'http://www.w3.org/ns/odrl/2/perUser': UnitOfCount.PER_USER,
    'odrl:perUser': UnitOfCount.PER_USER,
    'perUser': UnitOfCount.PER_USER,
    
    'http://www.w3.org/ns/odrl/2/perDevice': UnitOfCount.PER_DEVICE,
    'odrl:perDevice': UnitOfCount.PER_DEVICE,
    'perDevice': UnitOfCount.PER_DEVICE,
    
    'http://www.w3.org/ns/odrl/2/perOrganization': UnitOfCount.PER_ORGANIZATION,
    'odrl:perOrganization': UnitOfCount.PER_ORGANIZATION,
    'perOrganization': UnitOfCount.PER_ORGANIZATION,
    
    'http://www.w3.org/ns/odrl/2/perSession': UnitOfCount.PER_SESSION,
    'odrl:perSession': UnitOfCount.PER_SESSION,
    'perSession': UnitOfCount.PER_SESSION,
}


def parse_unit_of_count(value: Optional[str]) -> UnitOfCount:
    """
    Parse unitOfCount value.
    
    Args:
        value: URI or name of unitOfCount
        
    Returns:
        UnitOfCount enum value (defaults to TOTAL)
    """
    if value is None:
        return UnitOfCount.TOTAL
    
    return UNIT_OF_COUNT_URIS.get(value, UnitOfCount.TOTAL)


def are_unit_of_count_compatible(uoc1: Optional[str], uoc2: Optional[str]) -> bool:
    """
    Check if two unitOfCount values are compatible.
    
    Same rule: must be identical to be compatible.
    """
    parsed1 = parse_unit_of_count(uoc1)
    parsed2 = parse_unit_of_count(uoc2)
    return parsed1 == parsed2


# =============================================================================
# VALUE NORMALIZER (for backwards compatibility)
# =============================================================================

# Unit conversion factors
TEMPORAL_CONVERSIONS = {
    'seconds': 1,
    'second': 1,
    's': 1,
    'minutes': 60,
    'minute': 60,
    'min': 60,
    'm': 60,
    'hours': 3600,
    'hour': 3600,
    'h': 3600,
    'days': 86400,
    'day': 86400,
    'd': 86400,
    'weeks': 604800,
    'week': 604800,
    'w': 604800,
}

SIZE_CONVERSIONS = {
    'bytes': 1,
    'byte': 1,
    'b': 1,
    'kb': 1000,
    'kilobyte': 1000,
    'kilobytes': 1000,
    'mb': 1000000,
    'megabyte': 1000000,
    'megabytes': 1000000,
    'gb': 1000000000,
    'gigabyte': 1000000000,
    'gigabytes': 1000000000,
    'kib': 1024,
    'mib': 1048576,
    'gib': 1073741824,
}


class ValueNormalizer:
    """
    Value normalizer for constraint values.
    
    Handles unit conversion and normalization based on operand semantics.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def normalize(self, value, operand: str, unit: Optional[str], 
                  semantics) -> tuple:
        """
        Normalize a value based on operand semantics.
        
        Args:
            value: The value to normalize
            operand: The operand name
            unit: The unit (if any)
            semantics: SemanticInfo for the operand
            
        Returns:
            Tuple of (canonical_value, canonical_unit, metadata_dict)
        """
        metadata = {}
        
        # Get canonical unit
        canonical_unit = semantics.base_unit if semantics else 'none'
        canonical_value = value
        
        # Handle unit normalization
        if unit:
            normalized_unit = normalize_unit_uri(unit)
            if normalized_unit:
                metadata['original_unit'] = unit
                metadata['normalized_unit'] = normalized_unit
        
        # Handle temporal values (durations)
        if semantics and hasattr(semantics, 'domain'):
            domain_val = semantics.domain.value if hasattr(semantics.domain, 'value') else str(semantics.domain)
            if domain_val in ('temporal', 'temporal_interval'):
                # Check if value is ISO 8601 duration
                from .durations import duration_to_seconds, is_valid_duration
                
                if isinstance(value, str) and is_valid_duration(value):
                    seconds = duration_to_seconds(value)
                    if seconds is not None:
                        metadata['original_duration'] = value
                        metadata['conversion_factor'] = seconds
                        return (seconds, 'seconds', metadata)
                
                # Check if unit specifies time conversion
                if unit:
                    unit_lower = unit.lower()
                    if unit_lower in TEMPORAL_CONVERSIONS:
                        factor = TEMPORAL_CONVERSIONS[unit_lower]
                        canonical_value = value * factor
                        metadata['conversion_factor'] = factor
                        return (canonical_value, 'seconds', metadata)
        
        # Handle size values
        if semantics and hasattr(semantics, 'domain'):
            domain_val = semantics.domain.value if hasattr(semantics.domain, 'value') else str(semantics.domain)
            if domain_val == 'positional' and operand in ('absoluteSize',):
                if unit:
                    unit_lower = unit.lower()
                    if unit_lower in SIZE_CONVERSIONS:
                        factor = SIZE_CONVERSIONS[unit_lower]
                        canonical_value = value * factor
                        metadata['conversion_factor'] = factor
                        return (int(canonical_value), 'bytes', metadata)
        
        # Handle monetary values
        if semantics and hasattr(semantics, 'domain'):
            domain_val = semantics.domain.value if hasattr(semantics.domain, 'value') else str(semantics.domain)
            if domain_val == 'monetary':
                # Extract currency from unit
                if unit:
                    currency = normalize_unit_uri(unit)
                    if currency:
                        metadata['currency'] = currency
                        canonical_unit = currency
                        # Convert to minor units (cents)
                        if isinstance(value, float):
                            canonical_value = int(round(value * 100))
                            metadata['conversion_factor'] = 100
                            return (canonical_value, canonical_unit, metadata)
        
        # Handle numeric values
        if isinstance(value, (int, float)):
            canonical_value = value
        elif isinstance(value, str):
            # Try to parse as number
            try:
                if '.' in value:
                    canonical_value = float(value)
                else:
                    canonical_value = int(value)
            except ValueError:
                canonical_value = value
        
        return (canonical_value, canonical_unit, metadata)


def get_value_normalizer(debug: bool = False) -> ValueNormalizer:
    """
    Get a value normalizer instance.
    
    Args:
        debug: Enable debug output
        
    Returns:
        ValueNormalizer instance
    """
    return ValueNormalizer(debug=debug)


# =============================================================================
# STATISTICS
# =============================================================================

def get_unit_statistics() -> Dict[str, int]:
    """Get statistics about the unit registry."""
    stats = {'total': len(UNIT_REGISTRY)}
    
    for category in UnitCategory:
        count = sum(
            1 for info in UNIT_REGISTRY.values()
            if info.category == category
        )
        if count > 0:
            stats[category.value] = count
    
    return stats


def get_units_by_category(category: UnitCategory) -> Set[str]:
    """Get all unit names in a category."""
    return {
        name for name, info in UNIT_REGISTRY.items()
        if info.category == category
    }