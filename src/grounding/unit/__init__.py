"""
Unit Grounding Module for ODRL-SA

Provides semantic unit normalization and compatibility checking based on QUDT ontology.

Architecture:
- UnitOracle: Main interface for unit operations
- UnitSource: Abstract interface for unit data sources
  - SPARQLUnitSource: Fetches from QUDT SPARQL endpoint
  - RDFFileUnitSource: Loads from local RDF/TTL files
  - JSONCacheUnitSource: Uses cached JSON (for offline operation)
  - CompositeUnitSource: Chains multiple sources with fallback

Design Principles:
- Semantic mappings via ontology, not hardcoding
- No unit conversion (preserves soundness)
- Open-world: unknown units treated as unique symbols
- Different units after normalization → UNKNOWN judgment

Usage:
    from grounding.unit import UnitOracle, normalize_unit, are_units_compatible
    
    # Simple usage (uses default bootstrap cache)
    canonical = normalize_unit("http://qudt.org/vocab/unit/EUR")  # -> "EUR"
    canonical = normalize_unit("euro")  # -> "EUR"
    compatible = are_units_compatible("EUR", "EUR")  # -> True
    
    # Advanced usage with SPARQL
    oracle = UnitOracle(use_sparql=True)
    info = oracle.get_info("EUR")
    
    # With custom cache
    from pathlib import Path
    oracle = UnitOracle(cache_file=Path("my_cache.json"))
"""

from pathlib import Path
from typing import Optional

from .oracle import (
    # Core classes
    UnitOracle,
    UnitInfo,
    UnitCategory,
    
    # Source implementations
    UnitSource,
    SPARQLUnitSource,
    RDFFileUnitSource,
    JSONCacheUnitSource,
    CompositeUnitSource,
    
    # Convenience functions
    normalize_unit,
    are_units_compatible,
    get_unit_info,
    get_oracle,
    configure_oracle,
    
    # Cache generation
    generate_bootstrap_cache,
)

# Default bootstrap cache location (relative to this module)
_MODULE_DIR = Path(__file__).parent
_DEFAULT_CACHE = _MODULE_DIR / "bootstrap_cache.json"


def _init_default_oracle():
    """Initialize the default oracle with bootstrap cache."""
    if _DEFAULT_CACHE.exists():
        configure_oracle(cache_file=_DEFAULT_CACHE)


# Initialize on import
_init_default_oracle()


__all__ = [
    # Core classes
    "UnitOracle",
    "UnitInfo", 
    "UnitCategory",
    
    # Source implementations
    "UnitSource",
    "SPARQLUnitSource",
    "RDFFileUnitSource",
    "JSONCacheUnitSource",
    "CompositeUnitSource",
    
    # Convenience functions
    "normalize_unit",
    "are_units_compatible",
    "get_unit_info",
    "get_oracle",
    "configure_oracle",
    
    # Cache generation
    "generate_bootstrap_cache",
]