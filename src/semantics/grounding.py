# src/semantics/grounding.py
"""
Grounding Requirements for ODRL Operands

Classifies operands by their grounding requirements for static analysis:
- SELF_CONTAINED: Direct Z3 encoding, no external knowledge
- REFERENCE_POINT: Needs temporal anchor (t₀ = policy activation)
- SEMANTIC: Requires external knowledge base
- RUNTIME_ONLY: Cannot be analyzed statically

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0

Summary:
┌─────────────────────────────────────────────────────────────────┐
│  Self-contained (14)  │  Reference point (2)  │  Runtime (1)   │
│  45% - Full analysis  │  6% - Partial         │  3% - None     │
├─────────────────────────────────────────────────────────────────┤
│  Semantic grounding required (14) - 45%                        │
└─────────────────────────────────────────────────────────────────┘
"""

from enum import Enum
from typing import Dict, List, Set, Optional


class GroundingRequirement(Enum):
    """
    Grounding requirement classification for static analysis.
    
    SELF_CONTAINED: Can be fully analyzed with Z3 using XSD type semantics.
                   No external knowledge base required.
                   
    REFERENCE_POINT: Can be partially analyzed with Z3, but requires a
                    temporal reference point (t₀). We use policy activation
                    time as the default.
                    
    SEMANTIC: Requires external semantic knowledge base for complete
             analysis (e.g., LCC for language hierarchy, GeoNames for
             spatial hierarchy).
             
    RUNTIME_ONLY: Cannot be analyzed statically. Requires runtime data
                 (e.g., meteredTime requires cumulative usage tracking).
    """
    SELF_CONTAINED = "self_contained"
    REFERENCE_POINT = "reference_point"
    SEMANTIC = "semantic"
    RUNTIME_ONLY = "runtime_only"


# =============================================================================
# GROUNDING REQUIREMENTS REGISTRY
# =============================================================================

GROUNDING_REQUIREMENTS: Dict[str, GroundingRequirement] = {
    # =========================================================================
    # SELF-CONTAINED (14) - Full static analysis with Z3
    # =========================================================================
    
    # Numeric (4)
    'count': GroundingRequirement.SELF_CONTAINED,
    'percentage': GroundingRequirement.SELF_CONTAINED,
    'payAmount': GroundingRequirement.SELF_CONTAINED,
    'resolution': GroundingRequirement.SELF_CONTAINED,
    
    # Temporal - Absolute (2)
    'dateTime': GroundingRequirement.SELF_CONTAINED,
    'timeInterval': GroundingRequirement.SELF_CONTAINED,
    
    # Positional - Absolute (4)
    'absolutePosition': GroundingRequirement.SELF_CONTAINED,
    'absoluteSize': GroundingRequirement.SELF_CONTAINED,
    'absoluteTemporalPosition': GroundingRequirement.SELF_CONTAINED,
    'absoluteSpatialPosition': GroundingRequirement.SELF_CONTAINED,
    
    # Positional - Relative (4)
    'relativePosition': GroundingRequirement.SELF_CONTAINED,
    'relativeSize': GroundingRequirement.SELF_CONTAINED,
    'relativeTemporalPosition': GroundingRequirement.SELF_CONTAINED,
    'relativeSpatialPosition': GroundingRequirement.SELF_CONTAINED,
    
    # =========================================================================
    # REFERENCE POINT REQUIRED (2) - Partial static analysis
    # =========================================================================
    
    'elapsedTime': GroundingRequirement.REFERENCE_POINT,
    'delayPeriod': GroundingRequirement.REFERENCE_POINT,
    
    # =========================================================================
    # RUNTIME ONLY (1) - Cannot analyze statically
    # =========================================================================
    
    'meteredTime': GroundingRequirement.RUNTIME_ONLY,
    
    # =========================================================================
    # SEMANTIC GROUNDING REQUIRED (14) - Requires external KB
    # =========================================================================
    
    # Categorical (7)
    'language': GroundingRequirement.SEMANTIC,
    'fileFormat': GroundingRequirement.SEMANTIC,
    'media': GroundingRequirement.SEMANTIC,
    'industry': GroundingRequirement.SEMANTIC,
    'purpose': GroundingRequirement.SEMANTIC,
    'product': GroundingRequirement.SEMANTIC,
    'deliveryChannel': GroundingRequirement.SEMANTIC,
    
    # Spatial (2)
    'spatial': GroundingRequirement.SEMANTIC,
    'spatialCoordinates': GroundingRequirement.SEMANTIC,
    
    # Reference (4)
    'recipient': GroundingRequirement.SEMANTIC,
    'systemDevice': GroundingRequirement.SEMANTIC,
    'event': GroundingRequirement.SEMANTIC,
    'virtualLocation': GroundingRequirement.SEMANTIC,
    
    # Version (1)
    'version': GroundingRequirement.SEMANTIC,
}


# =============================================================================
# EXTERNAL KB MAPPING (for semantic operands)
# =============================================================================

EXTERNAL_KB_MAPPING: Dict[str, str] = {
    'language': 'LCC/Lexvo',
    'fileFormat': 'PRONOM/IANA',
    'media': 'Custom taxonomy',
    'industry': 'NAICS/ISIC',
    'purpose': 'DPV (Data Privacy Vocabulary)',
    'product': 'UNSPSC',
    'deliveryChannel': 'Custom taxonomy',
    'spatial': 'GeoNames',
    'spatialCoordinates': 'GeoSPARQL',
    'recipient': 'FOAF/vCard',
    'systemDevice': 'Custom registry',
    'event': 'Schema.org/OWL-Time',
    'virtualLocation': 'DNS/IP geolocation',
    'version': 'SemVer',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_operand_name(operand: str) -> str:
    """Normalize operand name by stripping namespace prefixes."""
    if ':' in operand:
        operand = operand.split(':')[-1]
    if '/' in operand:
        operand = operand.split('/')[-1]
    if '#' in operand:
        operand = operand.split('#')[-1]
    return operand


def get_grounding_requirement(operand: str) -> GroundingRequirement:
    """
    Get the grounding requirement for an operand.
    
    Args:
        operand: Operand name (with or without namespace)
        
    Returns:
        GroundingRequirement enum value.
        Returns SEMANTIC for unknown operands (conservative default).
    """
    name = _normalize_operand_name(operand)
    return GROUNDING_REQUIREMENTS.get(name, GroundingRequirement.SEMANTIC)


def is_self_contained(operand: str) -> bool:
    """
    Check if an operand is self-contained (no external grounding needed).
    
    Args:
        operand: Operand name
        
    Returns:
        True if operand can be fully analyzed with Z3 alone
    """
    return get_grounding_requirement(operand) == GroundingRequirement.SELF_CONTAINED


def is_statically_analyzable(operand: str) -> bool:
    """
    Check if an operand can be statically analyzed (at least partially).
    
    Args:
        operand: Operand name
        
    Returns:
        True if operand can be analyzed statically (self-contained or reference point)
    """
    req = get_grounding_requirement(operand)
    return req in (GroundingRequirement.SELF_CONTAINED, GroundingRequirement.REFERENCE_POINT)


def requires_semantic_grounding(operand: str) -> bool:
    """
    Check if an operand requires external semantic grounding.
    
    Args:
        operand: Operand name
        
    Returns:
        True if operand requires external knowledge base
    """
    return get_grounding_requirement(operand) == GroundingRequirement.SEMANTIC


def is_runtime_only(operand: str) -> bool:
    """
    Check if an operand can only be evaluated at runtime.
    
    Args:
        operand: Operand name
        
    Returns:
        True if operand cannot be statically analyzed
    """
    return get_grounding_requirement(operand) == GroundingRequirement.RUNTIME_ONLY


def get_external_kb(operand: str) -> Optional[str]:
    """
    Get the external knowledge base required for a semantic operand.
    
    Args:
        operand: Operand name
        
    Returns:
        Name of external KB, or None if not semantic
    """
    name = _normalize_operand_name(operand)
    return EXTERNAL_KB_MAPPING.get(name)


# =============================================================================
# SET ACCESSORS
# =============================================================================

def get_self_contained_operands() -> Set[str]:
    """Get set of all self-contained operand names."""
    return {
        name for name, req in GROUNDING_REQUIREMENTS.items()
        if req == GroundingRequirement.SELF_CONTAINED
    }


def get_reference_point_operands() -> Set[str]:
    """Get set of all reference-point operand names."""
    return {
        name for name, req in GROUNDING_REQUIREMENTS.items()
        if req == GroundingRequirement.REFERENCE_POINT
    }


def get_semantic_grounding_operands() -> Set[str]:
    """Get set of all semantic grounding operand names."""
    return {
        name for name, req in GROUNDING_REQUIREMENTS.items()
        if req == GroundingRequirement.SEMANTIC
    }


def get_runtime_only_operands() -> Set[str]:
    """Get set of all runtime-only operand names."""
    return {
        name for name, req in GROUNDING_REQUIREMENTS.items()
        if req == GroundingRequirement.RUNTIME_ONLY
    }


def get_statically_analyzable_operands() -> Set[str]:
    """Get set of all operands that can be statically analyzed."""
    return get_self_contained_operands() | get_reference_point_operands()


# =============================================================================
# STATISTICS
# =============================================================================

def get_grounding_statistics() -> Dict[str, int]:
    """
    Get statistics about grounding requirements.
    
    Returns:
        Dictionary with counts: {requirement_name: count}
    """
    stats = {req.value: 0 for req in GroundingRequirement}
    for req in GROUNDING_REQUIREMENTS.values():
        stats[req.value] += 1
    stats['total'] = len(GROUNDING_REQUIREMENTS)
    stats['statically_analyzable'] = stats['self_contained'] + stats['reference_point']
    return stats


# =============================================================================
# ANALYSIS RESULT TYPES
# =============================================================================

class AnalysisCapability(Enum):
    """Capability level for analyzing a constraint"""
    FULL = "full"           # Complete analysis possible
    PARTIAL = "partial"     # Analysis with assumptions
    SYNTACTIC_ONLY = "syntactic"  # Only syntactic checks
    NOT_POSSIBLE = "not_possible"  # Cannot analyze


def get_analysis_capability(operand: str) -> AnalysisCapability:
    """
    Determine the analysis capability for an operand.
    
    Args:
        operand: Operand name
        
    Returns:
        AnalysisCapability indicating what level of analysis is possible
    """
    req = get_grounding_requirement(operand)
    
    if req == GroundingRequirement.SELF_CONTAINED:
        return AnalysisCapability.FULL
    elif req == GroundingRequirement.REFERENCE_POINT:
        return AnalysisCapability.PARTIAL
    elif req == GroundingRequirement.SEMANTIC:
        return AnalysisCapability.SYNTACTIC_ONLY
    else:  # RUNTIME_ONLY
        return AnalysisCapability.NOT_POSSIBLE


# Verify registry completeness on module load
_self_contained = get_self_contained_operands()
_reference_point = get_reference_point_operands()
_semantic = get_semantic_grounding_operands()
_runtime = get_runtime_only_operands()

assert len(_self_contained) == 14, f"Expected 14 self-contained, got {len(_self_contained)}"
assert len(_reference_point) == 2, f"Expected 2 reference point, got {len(_reference_point)}"
assert len(_runtime) == 1, f"Expected 1 runtime only, got {len(_runtime)}"
assert len(_semantic) == 14, f"Expected 14 semantic, got {len(_semantic)}"
assert len(GROUNDING_REQUIREMENTS) == 31, f"Expected 31 total, got {len(GROUNDING_REQUIREMENTS)}"