# src/grounding/oracle_registry.py
"""
Oracle Registry for ODRL-SA

Provides a unified interface for all grounding oracles (unit, language, purpose, etc.)
with safe fallbacks when oracles are unavailable.

Design Principles:
1. SAFE: Missing oracles don't break the system
2. EXTENSIBLE: Easy to add new oracles
3. CONSISTENT: All oracles have same interface pattern
4. MINIMAL COUPLING: Encoder doesn't need to know oracle details

Usage:
    from grounding.oracle_registry import OracleRegistry
    
    registry = OracleRegistry()
    
    # Normalize a unit
    normalized = registry.normalize("unit", "euro")  # -> "EUR"
    
    # Check if oracle is available
    if registry.has_oracle("language"):
        descendants = registry.get_descendants("language", "en")
"""

from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ORACLE TYPES
# =============================================================================

class OracleType(Enum):
    """Types of grounding oracles."""
    UNIT = "unit"           # QUDT units (EUR, DPI, KB)
    LANGUAGE = "language"   # BCP47 language tags
    PURPOSE = "purpose"     # DPV purposes
    FILE_FORMAT = "fileFormat"  # IANA media types
    SPATIAL = "spatial"     # GeoNames locations
    INDUSTRY = "industry"   # Industry codes
    RECIPIENT = "recipient" # Recipient types
    EVENT = "event"         # Event types
    MEDIA = "media"         # Media types
    PRODUCT = "product"     # Product types
    DELIVERY_CHANNEL = "deliveryChannel"  # Delivery channels
    SYSTEM_DEVICE = "systemDevice"  # System/device types
    VERSION = "version"     # Version strings


# =============================================================================
# ORACLE INTERFACE
# =============================================================================

@dataclass
class OracleInfo:
    """Information about an oracle."""
    oracle_type: OracleType
    name: str
    normalize_fn: Callable[[str], Optional[str]]
    is_descendant_fn: Optional[Callable[[str, str], bool]] = None
    get_descendants_fn: Optional[Callable[[str], Set[str]]] = None
    are_compatible_fn: Optional[Callable[[str, str], bool]] = None


# =============================================================================
# ORACLE REGISTRY
# =============================================================================

class OracleRegistry:
    """
    Central registry for all grounding oracles.
    
    Provides safe access to oracles with automatic fallbacks.
    """
    
    _instance: Optional['OracleRegistry'] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._oracles: Dict[str, OracleInfo] = {}
        self._load_oracles()
        self._initialized = True
    
    def _load_oracles(self):
        """Load all available oracles."""
        # Try to load each oracle type
        self._try_load_unit_oracle()
        self._try_load_language_oracle()
        self._try_load_purpose_oracle()
        self._try_load_file_format_oracle()
        self._try_load_spatial_oracle()
        
        logger.info(f"Loaded {len(self._oracles)} oracles: {list(self._oracles.keys())}")
    
    # =========================================================================
    # ORACLE LOADERS (Safe - each has try/except)
    # =========================================================================
    
    def _try_load_unit_oracle(self):
        """Try to load unit oracle."""
        try:
            from grounding.unit import normalize_unit, are_units_compatible
            
            self._oracles["unit"] = OracleInfo(
                oracle_type=OracleType.UNIT,
                name="QUDT Unit Oracle",
                normalize_fn=normalize_unit,
                are_compatible_fn=are_units_compatible,
            )
            logger.debug("Loaded unit oracle")
        except ImportError as e:
            logger.debug(f"Unit oracle not available: {e}")
    
    def _try_load_language_oracle(self):
        """Try to load language oracle."""
        try:
            from grounding.language import (
                normalize_language, 
                is_language_descendant,
                get_language_descendants
            )
            
            self._oracles["language"] = OracleInfo(
                oracle_type=OracleType.LANGUAGE,
                name="BCP47 Language Oracle",
                normalize_fn=normalize_language,
                is_descendant_fn=is_language_descendant,
                get_descendants_fn=get_language_descendants,
            )
            logger.debug("Loaded language oracle")
        except ImportError as e:
            logger.debug(f"Language oracle not available: {e}")
    
    def _try_load_purpose_oracle(self):
        """Try to load purpose oracle."""
        try:
            from grounding.purpose import (
                normalize_purpose,
                is_purpose_descendant,
                get_purpose_descendants
            )
            
            self._oracles["purpose"] = OracleInfo(
                oracle_type=OracleType.PURPOSE,
                name="DPV Purpose Oracle",
                normalize_fn=normalize_purpose,
                is_descendant_fn=is_purpose_descendant,
                get_descendants_fn=get_purpose_descendants,
            )
            logger.debug("Loaded purpose oracle")
        except ImportError as e:
            logger.debug(f"Purpose oracle not available: {e}")
    
    def _try_load_file_format_oracle(self):
        """Try to load file format oracle."""
        try:
            from grounding.file_format import normalize_file_format
            
            self._oracles["fileFormat"] = OracleInfo(
                oracle_type=OracleType.FILE_FORMAT,
                name="IANA Media Type Oracle",
                normalize_fn=normalize_file_format,
            )
            logger.debug("Loaded file format oracle")
        except ImportError as e:
            logger.debug(f"File format oracle not available: {e}")
    
    def _try_load_spatial_oracle(self):
        """Try to load spatial oracle."""
        try:
            from grounding.spatial import (
                normalize_spatial,
                is_spatial_descendant,
                get_spatial_descendants
            )
            
            self._oracles["spatial"] = OracleInfo(
                oracle_type=OracleType.SPATIAL,
                name="GeoNames Spatial Oracle",
                normalize_fn=normalize_spatial,
                is_descendant_fn=is_spatial_descendant,
                get_descendants_fn=get_spatial_descendants,
            )
            logger.debug("Loaded spatial oracle")
        except ImportError as e:
            logger.debug(f"Spatial oracle not available: {e}")
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def has_oracle(self, oracle_type: str) -> bool:
        """Check if an oracle is available."""
        return oracle_type in self._oracles
    
    def list_oracles(self) -> List[str]:
        """List available oracle types."""
        return list(self._oracles.keys())
    
    def normalize(self, oracle_type: str, value: str) -> str:
        """
        Normalize a value using the appropriate oracle.
        
        Falls back to simple IRI extraction if oracle unavailable.
        """
        if value is None:
            return "default"
        
        if oracle_type in self._oracles:
            oracle = self._oracles[oracle_type]
            try:
                result = oracle.normalize_fn(value)
                return result if result else value
            except Exception as e:
                logger.warning(f"Oracle normalization failed: {e}")
                return self._fallback_normalize(value)
        
        return self._fallback_normalize(value)
    
    def is_descendant(self, oracle_type: str, child: str, parent: str) -> Optional[bool]:
        """
        Check if child is a descendant of parent in the hierarchy.
        
        Returns None if oracle unavailable or doesn't support hierarchies.
        """
        if oracle_type not in self._oracles:
            return None
        
        oracle = self._oracles[oracle_type]
        if oracle.is_descendant_fn is None:
            return None
        
        try:
            return oracle.is_descendant_fn(child, parent)
        except Exception as e:
            logger.warning(f"Oracle descendant check failed: {e}")
            return None
    
    def get_descendants(self, oracle_type: str, value: str) -> Optional[Set[str]]:
        """
        Get all descendants of a value in the hierarchy.
        
        Returns None if oracle unavailable or doesn't support hierarchies.
        """
        if oracle_type not in self._oracles:
            return None
        
        oracle = self._oracles[oracle_type]
        if oracle.get_descendants_fn is None:
            return None
        
        try:
            return oracle.get_descendants_fn(value)
        except Exception as e:
            logger.warning(f"Oracle get_descendants failed: {e}")
            return None
    
    def are_compatible(self, oracle_type: str, v1: str, v2: str) -> bool:
        """
        Check if two values are compatible (same after normalization).
        
        Falls back to string comparison if oracle unavailable.
        """
        if oracle_type in self._oracles:
            oracle = self._oracles[oracle_type]
            if oracle.are_compatible_fn:
                try:
                    return oracle.are_compatible_fn(v1, v2)
                except Exception:
                    pass
        
        # Fallback: normalize and compare
        n1 = self.normalize(oracle_type, v1)
        n2 = self.normalize(oracle_type, v2)
        return n1 == n2
    
    def _fallback_normalize(self, value: str) -> str:
        """Fallback normalization: extract local name from IRI."""
        if value is None:
            return "default"
        value = str(value)
        if '/' in value:
            return value.split('/')[-1]
        if '#' in value:
            return value.split('#')[-1]
        return value


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_registry: Optional[OracleRegistry] = None


def get_registry() -> OracleRegistry:
    """Get the global oracle registry."""
    global _registry
    if _registry is None:
        _registry = OracleRegistry()
    return _registry


def normalize_value(oracle_type: str, value: str) -> str:
    """Normalize a value using the appropriate oracle."""
    return get_registry().normalize(oracle_type, value)


def has_oracle(oracle_type: str) -> bool:
    """Check if an oracle is available."""
    return get_registry().has_oracle(oracle_type)


# =============================================================================
# OPERAND TO ORACLE MAPPING
# =============================================================================

# Map LeftOperands to their oracle types
OPERAND_ORACLE_MAP: Dict[str, str] = {
    # Unit-dependent operands
    "payAmount": "unit",
    "resolution": "unit",
    "absolutePosition": "unit",
    "absoluteSize": "unit",
    "absoluteTemporalPosition": "unit",
    "absoluteSpatialPosition": "unit",
    
    # Semantic operands
    "language": "language",
    "purpose": "purpose",
    "fileFormat": "fileFormat",
    "spatial": "spatial",
    "industry": "industry",
    "recipient": "recipient",
    "event": "event",
    "media": "media",
    "product": "product",
    "deliveryChannel": "deliveryChannel",
    "systemDevice": "systemDevice",
    "version": "version",
}


def get_oracle_type_for_operand(operand: str) -> Optional[str]:
    """Get the oracle type for a LeftOperand."""
    # Normalize operand name
    if '/' in operand:
        operand = operand.split('/')[-1]
    if '#' in operand:
        operand = operand.split('#')[-1]
    
    return OPERAND_ORACLE_MAP.get(operand)


def normalize_for_operand(operand: str, value: str) -> str:
    """Normalize a value based on its operand type."""
    oracle_type = get_oracle_type_for_operand(operand)
    if oracle_type:
        return get_registry().normalize(oracle_type, value)
    return get_registry()._fallback_normalize(value)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Oracle Registry Test")
    print("=" * 60)
    
    registry = get_registry()
    
    print(f"\nAvailable oracles: {registry.list_oracles()}")
    
    # Test unit normalization
    print("\n1. Unit Normalization:")
    for unit in ["EUR", "euro", "http://qudt.org/vocab/unit/EUR", "USD"]:
        normalized = registry.normalize("unit", unit)
        print(f"   {unit:40} → {normalized}")
    
    # Test fallback for unavailable oracle
    print("\n2. Fallback (unknown oracle):")
    for value in ["http://example.org/foo/bar", "test#fragment"]:
        normalized = registry.normalize("unknown_oracle", value)
        print(f"   {value:40} → {normalized}")
    
    # Test operand mapping
    print("\n3. Operand → Oracle Mapping:")
    for operand in ["payAmount", "language", "purpose", "count"]:
        oracle_type = get_oracle_type_for_operand(operand)
        print(f"   {operand:20} → {oracle_type or '(no oracle)'}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
