# src/grounding/unit/oracle.py
"""
Unit Grounding Oracle for ODRL-SA

Provides unit normalization and compatibility checking based on QUDT standard.
Does NOT perform unit conversion - different units yield UNKNOWN judgment.

Standards supported:
- QUDT (Quantities, Units, Dimensions, and Types) - Primary
- ISO 4217 (Currency codes) - Alias mapping
- DBpedia (Common resources) - Alias mapping

Usage:
    from grounding.unit import UnitOracle, normalize_unit
    
    oracle = UnitOracle()
    
    # Normalize unit
    canonical = oracle.normalize("http://qudt.org/vocab/unit/EUR")  # -> "EUR"
    canonical = oracle.normalize("euro")  # -> "EUR"
    
    # Check compatibility
    compatible = oracle.are_compatible("EUR", "EUR")  # -> True
    compatible = oracle.are_compatible("EUR", "USD")  # -> False
"""

from typing import Optional, Dict, Set, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# UNIT CATEGORIES
# =============================================================================

class UnitCategory(Enum):
    """Categories of units for ODRL constraints."""
    CURRENCY = "currency"
    RESOLUTION = "resolution"
    SIZE_DATA = "size_data"
    SIZE_PHYSICAL = "size_physical"
    TIME = "time"
    UNKNOWN = "unknown"


# =============================================================================
# UNIT INFO
# =============================================================================

@dataclass(frozen=True)
class UnitInfo:
    """Information about a unit."""
    canonical: str
    """Canonical code (e.g., 'EUR', 'DPI')"""
    
    uri: str
    """Full QUDT URI"""
    
    category: UnitCategory
    """Unit category"""
    
    label: str
    """Human-readable label"""
    
    symbol: Optional[str] = None
    """Standard symbol (e.g., '€', 'dpi')"""


# =============================================================================
# UNIT REGISTRY - QUDT BASED
# =============================================================================

# Currency units (ISO 4217 / QUDT)
CURRENCY_UNITS: Dict[str, UnitInfo] = {
    "EUR": UnitInfo("EUR", "http://qudt.org/vocab/unit/EUR", UnitCategory.CURRENCY, "Euro", "€"),
    "USD": UnitInfo("USD", "http://qudt.org/vocab/unit/USD", UnitCategory.CURRENCY, "US Dollar", "$"),
    "GBP": UnitInfo("GBP", "http://qudt.org/vocab/unit/GBP", UnitCategory.CURRENCY, "British Pound", "£"),
    "JPY": UnitInfo("JPY", "http://qudt.org/vocab/unit/JPY", UnitCategory.CURRENCY, "Japanese Yen", "¥"),
    "CHF": UnitInfo("CHF", "http://qudt.org/vocab/unit/CHF", UnitCategory.CURRENCY, "Swiss Franc", "CHF"),
    "CAD": UnitInfo("CAD", "http://qudt.org/vocab/unit/CAD", UnitCategory.CURRENCY, "Canadian Dollar", "C$"),
    "AUD": UnitInfo("AUD", "http://qudt.org/vocab/unit/AUD", UnitCategory.CURRENCY, "Australian Dollar", "A$"),
    "CNY": UnitInfo("CNY", "http://qudt.org/vocab/unit/CNY", UnitCategory.CURRENCY, "Chinese Yuan", "¥"),
    "INR": UnitInfo("INR", "http://qudt.org/vocab/unit/INR", UnitCategory.CURRENCY, "Indian Rupee", "₹"),
    "BRL": UnitInfo("BRL", "http://qudt.org/vocab/unit/BRL", UnitCategory.CURRENCY, "Brazilian Real", "R$"),
}

# Resolution units
RESOLUTION_UNITS: Dict[str, UnitInfo] = {
    "DPI": UnitInfo("DPI", "http://qudt.org/vocab/unit/DPI", UnitCategory.RESOLUTION, "Dots per inch", "dpi"),
    "PPI": UnitInfo("PPI", "http://qudt.org/vocab/unit/PPI", UnitCategory.RESOLUTION, "Pixels per inch", "ppi"),
    "DPCM": UnitInfo("DPCM", "http://qudt.org/vocab/unit/DPCM", UnitCategory.RESOLUTION, "Dots per centimeter", "dpcm"),
}

# Data size units
SIZE_DATA_UNITS: Dict[str, UnitInfo] = {
    "BYTE": UnitInfo("BYTE", "http://qudt.org/vocab/unit/BYTE", UnitCategory.SIZE_DATA, "Byte", "B"),
    "KiloBYTE": UnitInfo("KiloBYTE", "http://qudt.org/vocab/unit/KiloBYTE", UnitCategory.SIZE_DATA, "Kilobyte", "KB"),
    "MegaBYTE": UnitInfo("MegaBYTE", "http://qudt.org/vocab/unit/MegaBYTE", UnitCategory.SIZE_DATA, "Megabyte", "MB"),
    "GigaBYTE": UnitInfo("GigaBYTE", "http://qudt.org/vocab/unit/GigaBYTE", UnitCategory.SIZE_DATA, "Gigabyte", "GB"),
    "TeraBYTE": UnitInfo("TeraBYTE", "http://qudt.org/vocab/unit/TeraBYTE", UnitCategory.SIZE_DATA, "Terabyte", "TB"),
    "BIT": UnitInfo("BIT", "http://qudt.org/vocab/unit/BIT", UnitCategory.SIZE_DATA, "Bit", "b"),
    "KiloBIT": UnitInfo("KiloBIT", "http://qudt.org/vocab/unit/KiloBIT", UnitCategory.SIZE_DATA, "Kilobit", "Kb"),
    "MegaBIT": UnitInfo("MegaBIT", "http://qudt.org/vocab/unit/MegaBIT", UnitCategory.SIZE_DATA, "Megabit", "Mb"),
}

# Physical size units
SIZE_PHYSICAL_UNITS: Dict[str, UnitInfo] = {
    "PIXEL": UnitInfo("PIXEL", "http://qudt.org/vocab/unit/PX", UnitCategory.SIZE_PHYSICAL, "Pixel", "px"),
    "M": UnitInfo("M", "http://qudt.org/vocab/unit/M", UnitCategory.SIZE_PHYSICAL, "Meter", "m"),
    "CM": UnitInfo("CM", "http://qudt.org/vocab/unit/CentiM", UnitCategory.SIZE_PHYSICAL, "Centimeter", "cm"),
    "MM": UnitInfo("MM", "http://qudt.org/vocab/unit/MilliM", UnitCategory.SIZE_PHYSICAL, "Millimeter", "mm"),
    "IN": UnitInfo("IN", "http://qudt.org/vocab/unit/IN", UnitCategory.SIZE_PHYSICAL, "Inch", "in"),
    "PT": UnitInfo("PT", "http://qudt.org/vocab/unit/PT", UnitCategory.SIZE_PHYSICAL, "Point", "pt"),
}

# Time units
TIME_UNITS: Dict[str, UnitInfo] = {
    "SEC": UnitInfo("SEC", "http://qudt.org/vocab/unit/SEC", UnitCategory.TIME, "Second", "s"),
    "MIN": UnitInfo("MIN", "http://qudt.org/vocab/unit/MIN", UnitCategory.TIME, "Minute", "min"),
    "HR": UnitInfo("HR", "http://qudt.org/vocab/unit/HR", UnitCategory.TIME, "Hour", "h"),
    "DAY": UnitInfo("DAY", "http://qudt.org/vocab/unit/DAY", UnitCategory.TIME, "Day", "d"),
    "WK": UnitInfo("WK", "http://qudt.org/vocab/unit/WK", UnitCategory.TIME, "Week", "wk"),
    "MO": UnitInfo("MO", "http://qudt.org/vocab/unit/MO", UnitCategory.TIME, "Month", "mo"),
    "YR": UnitInfo("YR", "http://qudt.org/vocab/unit/YR", UnitCategory.TIME, "Year", "yr"),
}

# Combined registry
UNIT_REGISTRY: Dict[str, UnitInfo] = {
    **CURRENCY_UNITS,
    **RESOLUTION_UNITS,
    **SIZE_DATA_UNITS,
    **SIZE_PHYSICAL_UNITS,
    **TIME_UNITS,
}


# =============================================================================
# UNIT ALIASES
# =============================================================================

UNIT_ALIASES: Dict[str, str] = {
    # ----- Currency Aliases -----
    # ISO 4217 URIs
    "http://iso.org/4217/EUR": "EUR",
    "http://iso.org/4217/USD": "USD",
    "http://iso.org/4217/GBP": "GBP",
    "http://iso.org/4217/JPY": "JPY",
    "http://iso.org/4217/CHF": "CHF",
    
    # DBpedia URIs
    "http://dbpedia.org/resource/Euro": "EUR",
    "http://dbpedia.org/resource/United_States_dollar": "USD",
    "http://dbpedia.org/resource/Pound_sterling": "GBP",
    "http://dbpedia.org/resource/Japanese_yen": "JPY",
    "http://dbpedia.org/resource/Swiss_franc": "CHF",
    
    # Wikidata URIs
    "http://www.wikidata.org/entity/Q4916": "EUR",
    "http://www.wikidata.org/entity/Q4917": "USD",
    "http://www.wikidata.org/entity/Q25224": "GBP",
    
    # Common names (lowercase)
    "euro": "EUR",
    "euros": "EUR",
    "dollar": "USD",
    "dollars": "USD",
    "usd": "USD",
    "pound": "GBP",
    "pounds": "GBP",
    "yen": "JPY",
    "franc": "CHF",
    "francs": "CHF",
    
    # ----- Resolution Aliases -----
    "dpi": "DPI",
    "ppi": "PPI",
    "dpcm": "DPCM",
    "dots per inch": "DPI",
    "pixels per inch": "PPI",
    
    # ----- Data Size Aliases -----
    "byte": "BYTE",
    "bytes": "BYTE",
    "b": "BYTE",
    "kb": "KiloBYTE",
    "kilobyte": "KiloBYTE",
    "kilobytes": "KiloBYTE",
    "mb": "MegaBYTE",
    "megabyte": "MegaBYTE",
    "megabytes": "MegaBYTE",
    "gb": "GigaBYTE",
    "gigabyte": "GigaBYTE",
    "gigabytes": "GigaBYTE",
    "tb": "TeraBYTE",
    "terabyte": "TeraBYTE",
    "terabytes": "TeraBYTE",
    "bit": "BIT",
    "bits": "BIT",
    "kbit": "KiloBIT",
    "kilobit": "KiloBIT",
    "mbit": "MegaBIT",
    "megabit": "MegaBIT",
    
    # ----- Physical Size Aliases -----
    "px": "PIXEL",
    "pixel": "PIXEL",
    "pixels": "PIXEL",
    "meter": "M",
    "meters": "M",
    "metre": "M",
    "metres": "M",
    "centimeter": "CM",
    "centimeters": "CM",
    "centimetre": "CM",
    "cm": "CM",
    "millimeter": "MM",
    "millimeters": "MM",
    "millimetre": "MM",
    "mm": "MM",
    "inch": "IN",
    "inches": "IN",
    "in": "IN",
    "point": "PT",
    "points": "PT",
    "pt": "PT",
    
    # ----- Time Aliases -----
    "s": "SEC",
    "sec": "SEC",
    "second": "SEC",
    "seconds": "SEC",
    "m": "MIN",  # Note: ambiguous with meters, context-dependent
    "min": "MIN",
    "minute": "MIN",
    "minutes": "MIN",
    "h": "HR",
    "hr": "HR",
    "hour": "HR",
    "hours": "HR",
    "d": "DAY",
    "day": "DAY",
    "days": "DAY",
    "wk": "WK",
    "week": "WK",
    "weeks": "WK",
    "mo": "MO",
    "month": "MO",
    "months": "MO",
    "yr": "YR",
    "year": "YR",
    "years": "YR",
}


# =============================================================================
# UNIT ORACLE
# =============================================================================

class UnitOracle:
    """
    Oracle for unit normalization and compatibility checking.
    
    This oracle does NOT perform unit conversion. Constraints with
    different units (after normalization) are considered incomparable,
    resulting in UNKNOWN judgment.
    """
    
    def __init__(self):
        self._registry = UNIT_REGISTRY.copy()
        self._aliases = UNIT_ALIASES.copy()
        self._uri_to_canonical: Dict[str, str] = {}
        
        # Build URI lookup
        for code, info in self._registry.items():
            self._uri_to_canonical[info.uri] = code
            self._uri_to_canonical[info.uri.lower()] = code
    
    def normalize(self, unit: Optional[str]) -> Optional[str]:
        """
        Normalize a unit to its canonical form.
        
        Args:
            unit: Unit string (URI, code, or common name)
            
        Returns:
            Canonical unit code or None if not recognized
        """
        if unit is None:
            return None
        
        unit_str = str(unit).strip()
        
        # Already canonical?
        if unit_str in self._registry:
            return unit_str
        
        # Check aliases (exact match)
        if unit_str in self._aliases:
            return self._aliases[unit_str]
        
        # Check aliases (lowercase)
        unit_lower = unit_str.lower()
        if unit_lower in self._aliases:
            return self._aliases[unit_lower]
        
        # Check URI lookup
        if unit_str in self._uri_to_canonical:
            return self._uri_to_canonical[unit_str]
        if unit_lower in self._uri_to_canonical:
            return self._uri_to_canonical[unit_lower]
        
        # Extract from URI path
        # e.g., "http://qudt.org/vocab/unit/EUR" → "EUR"
        if "/" in unit_str:
            last_part = unit_str.split("/")[-1]
            if last_part in self._registry:
                return last_part
            if last_part in self._aliases:
                return self._aliases[last_part]
            if last_part.lower() in self._aliases:
                return self._aliases[last_part.lower()]
        
        # Extract from URI fragment
        # e.g., "http://example.org/units#EUR" → "EUR"
        if "#" in unit_str:
            fragment = unit_str.split("#")[-1]
            if fragment in self._registry:
                return fragment
            if fragment in self._aliases:
                return self._aliases[fragment]
            if fragment.lower() in self._aliases:
                return self._aliases[fragment.lower()]
        
        # Unknown unit - return as-is (will be treated as unique)
        logger.debug(f"Unknown unit: {unit_str}")
        return unit_str
    
    def get_info(self, unit: str) -> Optional[UnitInfo]:
        """Get detailed information about a unit."""
        canonical = self.normalize(unit)
        return self._registry.get(canonical) if canonical else None
    
    def get_category(self, unit: str) -> UnitCategory:
        """Get the category of a unit."""
        info = self.get_info(unit)
        return info.category if info else UnitCategory.UNKNOWN
    
    def get_uri(self, unit: str) -> Optional[str]:
        """Get the QUDT URI for a unit."""
        info = self.get_info(unit)
        return info.uri if info else None
    
    def are_compatible(self, unit1: Optional[str], unit2: Optional[str]) -> bool:
        """
        Check if two units are compatible (same canonical form).
        
        Returns True only if both units normalize to the same canonical code.
        Returns False if either is None or they differ.
        """
        if unit1 is None or unit2 is None:
            return False
        
        norm1 = self.normalize(unit1)
        norm2 = self.normalize(unit2)
        
        return norm1 == norm2 and norm1 is not None
    
    def are_same_category(self, unit1: str, unit2: str) -> bool:
        """Check if two units are in the same category."""
        cat1 = self.get_category(unit1)
        cat2 = self.get_category(unit2)
        return cat1 == cat2 and cat1 != UnitCategory.UNKNOWN
    
    def list_units(self, category: Optional[UnitCategory] = None) -> List[str]:
        """List all known units, optionally filtered by category."""
        if category is None:
            return list(self._registry.keys())
        return [
            code for code, info in self._registry.items()
            if info.category == category
        ]
    
    def register_alias(self, alias: str, canonical: str):
        """Register a new alias for a canonical unit."""
        if canonical in self._registry:
            self._aliases[alias] = canonical
            self._aliases[alias.lower()] = canonical
        else:
            logger.warning(f"Cannot register alias for unknown unit: {canonical}")
    
    def register_unit(self, info: UnitInfo):
        """Register a new unit."""
        self._registry[info.canonical] = info
        self._uri_to_canonical[info.uri] = info.canonical
        self._uri_to_canonical[info.uri.lower()] = info.canonical


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global oracle instance
_oracle: Optional[UnitOracle] = None


def get_oracle() -> UnitOracle:
    """Get the global unit oracle instance."""
    global _oracle
    if _oracle is None:
        _oracle = UnitOracle()
    return _oracle


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    """Normalize a unit to its canonical form."""
    return get_oracle().normalize(unit)


def are_units_compatible(unit1: Optional[str], unit2: Optional[str]) -> bool:
    """Check if two units are compatible."""
    return get_oracle().are_compatible(unit1, unit2)


def get_unit_info(unit: str) -> Optional[UnitInfo]:
    """Get detailed information about a unit."""
    return get_oracle().get_info(unit)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Unit Oracle Test")
    print("=" * 60)
    
    oracle = UnitOracle()
    
    # Test 1: Currency normalization
    print("\n1. Currency Normalization:")
    currency_tests = [
        "EUR",
        "http://qudt.org/vocab/unit/EUR",
        "http://dbpedia.org/resource/Euro",
        "http://iso.org/4217/EUR",
        "euro",
        "euros",
        "USD",
        "dollar",
    ]
    for unit in currency_tests:
        canonical = oracle.normalize(unit)
        info = oracle.get_info(unit)
        symbol = info.symbol if info else "?"
        print(f"  {unit:45} -> {canonical} ({symbol})")
    
    # Test 2: Resolution normalization
    print("\n2. Resolution Normalization:")
    resolution_tests = ["DPI", "dpi", "dots per inch", "PPI", "ppi"]
    for unit in resolution_tests:
        canonical = oracle.normalize(unit)
        print(f"  {unit:20} -> {canonical}")
    
    # Test 3: Size normalization
    print("\n3. Data Size Normalization:")
    size_tests = ["BYTE", "bytes", "KB", "kilobyte", "MB", "megabytes", "GB"]
    for unit in size_tests:
        canonical = oracle.normalize(unit)
        print(f"  {unit:20} -> {canonical}")
    
    # Test 4: Time normalization
    print("\n4. Time Normalization:")
    time_tests = ["SEC", "seconds", "s", "MIN", "minutes", "HR", "hours"]
    for unit in time_tests:
        canonical = oracle.normalize(unit)
        print(f"  {unit:20} -> {canonical}")
    
    # Test 5: Compatibility
    print("\n5. Compatibility Checks:")
    compat_tests = [
        ("EUR", "EUR", True),
        ("EUR", "euro", True),
        ("http://qudt.org/vocab/unit/EUR", "euro", True),
        ("EUR", "USD", False),
        ("DPI", "PPI", False),
        ("KB", "kilobyte", True),
        ("seconds", "SEC", True),
    ]
    for u1, u2, expected in compat_tests:
        result = oracle.are_compatible(u1, u2)
        status = "OK" if result == expected else "FAIL"
        print(f"  [{status}] {u1} ~ {u2} = {result} (expected {expected})")
    
    # Test 6: Categories
    print("\n6. Unit Categories:")
    for category in UnitCategory:
        if category != UnitCategory.UNKNOWN:
            units = oracle.list_units(category)
            print(f"  {category.value}: {', '.join(units[:5])}{'...' if len(units) > 5 else ''}")
    
    print("\n" + "=" * 60)
    print("Unit Oracle Test Complete!")
    print("=" * 60)