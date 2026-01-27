# src/semantics/oracle.py
"""
ODRL-SA Grounding Oracle Interface

Implements §9 Definition 15: Grounding Oracle Interface

G : Lsem × Oset × V × V → {SUBSUMES, DISJOINT, OVERLAPS, UNKNOWN}

The oracle provides semantic relationships between values in external
knowledge bases (e.g., language hierarchies, geographic containment,
purpose taxonomies).

This module defines:
1. The abstract oracle interface
2. Concrete oracle implementations for common KBs
3. Oracle composition and caching
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Set, Tuple, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .judgment import OracleResult
from .constraint_types import OperatorType


logger = logging.getLogger(__name__)


# =============================================================================
# ORACLE INTERFACE (§9 Definition 15)
# =============================================================================

class GroundingOracle(ABC):
    """
    Abstract interface for semantic grounding oracles.
    
    Oracles provide semantic relationships between values that cannot
    be determined purely from their syntactic representation.
    
    Examples:
    - Language hierarchy: "en" subsumes "en-US"
    - Geographic containment: "Europe" contains "Germany"
    - Purpose taxonomy: "Research" is-a "NonCommercial"
    """
    
    @property
    @abstractmethod
    def supported_operands(self) -> Set[str]:
        """Return set of LeftOperands this oracle can handle."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return oracle name for logging/debugging."""
        pass
    
    @abstractmethod
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        """
        Query the oracle for relationship between two values.
        
        Args:
            operand: The LeftOperand (e.g., "language", "spatial")
            operator: The set operator being used
            value1: First value
            value2: Second value
            
        Returns:
            OracleResult indicating the relationship
        """
        pass
    
    def can_handle(self, operand: str) -> bool:
        """Check if oracle can handle this operand."""
        return self._normalize(operand) in self.supported_operands
    
    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize name by stripping namespace."""
        if '#' in name:
            return name.split('#')[-1]
        if '/' in name:
            return name.split('/')[-1]
        return name


# =============================================================================
# NULL ORACLE (Default - Always returns UNKNOWN)
# =============================================================================

class NullOracle(GroundingOracle):
    """
    Null oracle that always returns UNKNOWN.
    
    Used when no grounding information is available.
    """
    
    @property
    def supported_operands(self) -> Set[str]:
        return set()  # Handles nothing
    
    @property
    def name(self) -> str:
        return "NullOracle"
    
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        return OracleResult.UNKNOWN


# =============================================================================
# LANGUAGE HIERARCHY ORACLE (LCC/BCP47)
# =============================================================================

class LanguageOracle(GroundingOracle):
    """
    Oracle for language hierarchy based on BCP47/LCC.
    
    Handles relationships like:
    - "en" subsumes "en-US", "en-GB", etc.
    - "de" subsumes "de-AT", "de-CH"
    - "zh" subsumes "zh-Hans", "zh-Hant"
    """
    
    @property
    def supported_operands(self) -> Set[str]:
        return {"language"}
    
    @property
    def name(self) -> str:
        return "LanguageOracle"
    
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        v1 = str(value1).lower().strip()
        v2 = str(value2).lower().strip()
        
        # Exact match
        if v1 == v2:
            if operator == OperatorType.IS_A:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        # Check subsumption via prefix matching
        # e.g., "en" subsumes "en-us"
        if v2.startswith(v1 + "-"):
            # v1 is more general than v2
            if operator == OperatorType.IS_A:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        if v1.startswith(v2 + "-"):
            # v2 is more general than v1
            if operator == OperatorType.IS_PART_OF:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        # Different language families
        base1 = v1.split("-")[0]
        base2 = v2.split("-")[0]
        
        if base1 != base2:
            return OracleResult.DISJOINT
        
        # Same base language, different variants
        return OracleResult.OVERLAPS


# =============================================================================
# SPATIAL ORACLE (Geographic Containment)
# =============================================================================

class SpatialOracle(GroundingOracle):
    """
    Oracle for geographic containment.
    
    Uses a simple hierarchy based on ISO 3166 codes.
    For production, would integrate with GeoNames or similar.
    """
    
    # Simple containment hierarchy (country -> regions)
    # Format: parent -> {children}
    CONTAINMENT: Dict[str, Set[str]] = {
        "EU": {"DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL"},
        "EUROPE": {"DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL", "GB", "CH"},
        "DE": {"DE-BY", "DE-NW", "DE-BW", "DE-HE"},
        "US": {"US-CA", "US-NY", "US-TX", "US-FL"},
        "WORLD": {"EU", "EUROPE", "US", "CN", "JP", "ASIA", "AMERICAS"},
    }
    
    @property
    def supported_operands(self) -> Set[str]:
        return {"spatial", "spatialCoordinates"}
    
    @property
    def name(self) -> str:
        return "SpatialOracle"
    
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        v1 = str(value1).upper().strip()
        v2 = str(value2).upper().strip()
        
        # Exact match
        if v1 == v2:
            return OracleResult.OVERLAPS
        
        # Check if v1 contains v2
        if self._contains(v1, v2):
            if operator == OperatorType.HAS_PART:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        # Check if v2 contains v1
        if self._contains(v2, v1):
            if operator == OperatorType.IS_PART_OF:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        # Check if disjoint (no common ancestor)
        if self._are_disjoint(v1, v2):
            return OracleResult.DISJOINT
        
        return OracleResult.UNKNOWN
    
    def _contains(self, parent: str, child: str) -> bool:
        """Check if parent contains child (directly or transitively)."""
        if parent in self.CONTAINMENT:
            children = self.CONTAINMENT[parent]
            if child in children:
                return True
            # Check transitive containment
            for c in children:
                if self._contains(c, child):
                    return True
        return False
    
    def _are_disjoint(self, v1: str, v2: str) -> bool:
        """Check if two regions are definitely disjoint."""
        # Simple heuristic: different top-level regions
        # In production, use proper geographic database
        return False  # Conservative: assume might overlap


# =============================================================================
# PURPOSE TAXONOMY ORACLE (DPV)
# =============================================================================

class PurposeOracle(GroundingOracle):
    """
    Oracle for purpose taxonomy based on DPV (Data Privacy Vocabulary).
    """
    
    # DPV purpose hierarchy (simplified)
    HIERARCHY: Dict[str, Set[str]] = {
        "ServiceProvision": {"PersonalisedService", "RequestedServiceProvision"},
        "Research": {"AcademicResearch", "ScientificResearch", "CommercialResearch"},
        "NonCommercial": {"AcademicResearch", "ScientificResearch", "PersonalUse"},
        "Commercial": {"Marketing", "Advertising", "CommercialResearch", "Profiling"},
        "Marketing": {"DirectMarketing", "Advertising"},
    }
    
    @property
    def supported_operands(self) -> Set[str]:
        return {"purpose"}
    
    @property
    def name(self) -> str:
        return "PurposeOracle"
    
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        v1 = self._normalize_purpose(str(value1))
        v2 = self._normalize_purpose(str(value2))
        
        if v1 == v2:
            return OracleResult.OVERLAPS
        
        # Check hierarchy
        if v1 in self.HIERARCHY and v2 in self.HIERARCHY[v1]:
            if operator == OperatorType.IS_A:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        if v2 in self.HIERARCHY and v1 in self.HIERARCHY[v2]:
            if operator == OperatorType.IS_PART_OF:
                return OracleResult.SUBSUMES
            return OracleResult.OVERLAPS
        
        # Check disjointness
        if self._are_disjoint(v1, v2):
            return OracleResult.DISJOINT
        
        return OracleResult.UNKNOWN
    
    def _normalize_purpose(self, purpose: str) -> str:
        """Normalize purpose URI to local name."""
        if '#' in purpose:
            return purpose.split('#')[-1]
        if '/' in purpose:
            return purpose.split('/')[-1]
        return purpose
    
    def _are_disjoint(self, v1: str, v2: str) -> bool:
        """Check if purposes are definitely disjoint."""
        # Commercial vs NonCommercial
        commercial = {"Marketing", "Advertising", "CommercialResearch", "Profiling", "Commercial"}
        non_commercial = {"AcademicResearch", "ScientificResearch", "PersonalUse", "NonCommercial"}
        
        if v1 in commercial and v2 in non_commercial:
            return True
        if v1 in non_commercial and v2 in commercial:
            return True
        
        return False


# =============================================================================
# COMPOSITE ORACLE (Combines Multiple Oracles)
# =============================================================================

class CompositeOracle(GroundingOracle):
    """
    Combines multiple oracles, routing queries to appropriate one.
    """
    
    def __init__(self, oracles: List[GroundingOracle]):
        self._oracles = oracles
        self._operand_map: Dict[str, GroundingOracle] = {}
        
        # Build operand -> oracle mapping
        for oracle in oracles:
            for operand in oracle.supported_operands:
                self._operand_map[operand] = oracle
    
    @property
    def supported_operands(self) -> Set[str]:
        return set(self._operand_map.keys())
    
    @property
    def name(self) -> str:
        names = [o.name for o in self._oracles]
        return f"CompositeOracle({', '.join(names)})"
    
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        norm_operand = self._normalize(operand)
        
        if norm_operand in self._operand_map:
            oracle = self._operand_map[norm_operand]
            return oracle.query(operand, operator, value1, value2)
        
        return OracleResult.UNKNOWN


# =============================================================================
# CACHING ORACLE WRAPPER
# =============================================================================

class CachingOracle(GroundingOracle):
    """
    Wrapper that caches oracle query results.
    """
    
    def __init__(self, oracle: GroundingOracle):
        self._oracle = oracle
        self._cache: Dict[Tuple, OracleResult] = {}
    
    @property
    def supported_operands(self) -> Set[str]:
        return self._oracle.supported_operands
    
    @property
    def name(self) -> str:
        return f"Cached({self._oracle.name})"
    
    def query(
        self,
        operand: str,
        operator: OperatorType,
        value1: Any,
        value2: Any
    ) -> OracleResult:
        key = (operand, operator, str(value1), str(value2))
        
        if key not in self._cache:
            result = self._oracle.query(operand, operator, value1, value2)
            self._cache[key] = result
        
        return self._cache[key]
    
    def clear_cache(self):
        """Clear the query cache."""
        self._cache.clear()


# =============================================================================
# DEFAULT ORACLE FACTORY
# =============================================================================

def create_default_oracle() -> GroundingOracle:
    """
    Create the default composite oracle with all available oracles.
    """
    oracles = [
        LanguageOracle(),
        SpatialOracle(),
        PurposeOracle(),
    ]
    return CachingOracle(CompositeOracle(oracles))


def create_null_oracle() -> GroundingOracle:
    """Create a null oracle that always returns UNKNOWN."""
    return NullOracle()