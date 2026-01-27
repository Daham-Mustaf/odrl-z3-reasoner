# src/semantics/operand_registry.py
"""
Complete ODRL LeftOperand Registry

Defines all 31 ODRL leftOperands with:
- Semantic category
- XSD type mapping
- Z3 sort
- Domain bounds
- Grounding requirements
- Unit handling

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0

Summary:
- Self-contained (14): Full static analysis with Z3
- Reference point (3): Partial static analysis
- Semantic grounding (14): Requires external KB
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum


class OperandCategory(Enum):
    """
    Categories of ODRL leftOperands.
    
    Used for encoder selection and validation.
    """
    NUMERIC = "numeric"
    TEMPORAL = "temporal"
    TEMPORAL_DURATION = "temporal_duration"
    POSITIONAL_ABSOLUTE = "positional_absolute"
    POSITIONAL_RELATIVE = "positional_relative"
    CATEGORICAL = "categorical"
    SPATIAL = "spatial"
    REFERENCE = "reference"
    VERSION = "version"


class XSDType(Enum):
    """XSD datatypes for ODRL values"""
    INTEGER = "xsd:integer"
    DECIMAL = "xsd:decimal"
    DATETIME = "xsd:dateTime"
    DATE = "xsd:date"
    DURATION = "xsd:duration"
    STRING = "xsd:string"
    ANYURI = "xsd:anyURI"
    BOOLEAN = "xsd:boolean"


class Z3SortType(Enum):
    """Z3 solver sort types"""
    INT = "Int"
    REAL = "Real"
    STRING = "String"
    BOOL = "Bool"
    ARRAY = "Array"


class GroundingType(Enum):
    """Grounding requirement classification"""
    SELF_CONTAINED = "self_contained"
    REFERENCE_POINT = "reference_point"
    SEMANTIC = "semantic"
    RUNTIME_ONLY = "runtime_only"


@dataclass(frozen=True)
class OperandInfo:
    """
    Complete information for an ODRL leftOperand.
    
    Attributes:
        name: Operand name (e.g., 'count', 'dateTime')
        category: Semantic category
        xsd_type: XSD datatype
        z3_sort: Z3 solver sort
        domain_min: Minimum value (None = unbounded)
        domain_max: Maximum value (None = unbounded)
        unit_required: Whether unit is required
        default_unit: Default unit if not specified
        grounding: Grounding requirement
        description: Human-readable description
        reference_point: For duration operands, what t₀ refers to
        external_kb: For semantic operands, which KB is needed
    """
    name: str
    category: OperandCategory
    xsd_type: XSDType
    z3_sort: Z3SortType
    domain_min: Optional[float] = None
    domain_max: Optional[float] = None
    unit_required: bool = False
    default_unit: Optional[str] = None
    grounding: GroundingType = GroundingType.SELF_CONTAINED
    description: str = ""
    reference_point: Optional[str] = None
    external_kb: Optional[str] = None
    
    @property
    def has_bounded_domain(self) -> bool:
        """Check if operand has bounded domain"""
        return self.domain_min is not None or self.domain_max is not None
    
    @property
    def is_self_contained(self) -> bool:
        """Check if operand is self-contained (no external grounding)"""
        return self.grounding == GroundingType.SELF_CONTAINED
    
    @property
    def is_statically_analyzable(self) -> bool:
        """Check if operand can be statically analyzed"""
        return self.grounding in (GroundingType.SELF_CONTAINED, GroundingType.REFERENCE_POINT)


# =============================================================================
# COMPLETE OPERAND REGISTRY (31 operands)
# =============================================================================

OPERAND_REGISTRY: Dict[str, OperandInfo] = {
    
    # =========================================================================
    # NUMERIC (4) - Self-contained
    # =========================================================================
    
    'count': OperandInfo(
        name='count',
        category=OperandCategory.NUMERIC,
        xsd_type=XSDType.INTEGER,
        z3_sort=Z3SortType.INT,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit=None,
        grounding=GroundingType.SELF_CONTAINED,
        description="A numeric count value. Uses unitOfCount for semantics (perUser, perDevice, etc.)"
    ),
    
    'percentage': OperandInfo(
        name='percentage',
        category=OperandCategory.NUMERIC,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=100,
        unit_required=False,
        default_unit='percent',
        grounding=GroundingType.SELF_CONTAINED,
        description="A percentage value between 0 and 100"
    ),
    
    'payAmount': OperandInfo(
        name='payAmount',
        category=OperandCategory.NUMERIC,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=None,
        unit_required=True,
        default_unit=None,
        grounding=GroundingType.SELF_CONTAINED,
        description="A monetary payment amount. Requires unit (currency). No conversion between currencies."
    ),
    
    'resolution': OperandInfo(
        name='resolution',
        category=OperandCategory.NUMERIC,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=None,
        unit_required=True,
        default_unit='dpi',
        grounding=GroundingType.SELF_CONTAINED,
        description="Image/display resolution. Requires unit (DPI, PPI). No conversion between units."
    ),
    
    # =========================================================================
    # TEMPORAL - Absolute (2) - Self-contained
    # =========================================================================
    
    'dateTime': OperandInfo(
        name='dateTime',
        category=OperandCategory.TEMPORAL,
        xsd_type=XSDType.DATETIME,
        z3_sort=Z3SortType.INT,
        domain_min=None,
        domain_max=None,
        unit_required=False,
        default_unit='seconds_since_epoch',
        grounding=GroundingType.SELF_CONTAINED,
        description="An absolute point in time (ISO 8601). Encoded as Unix timestamp."
    ),
    
    'timeInterval': OperandInfo(
        name='timeInterval',
        category=OperandCategory.TEMPORAL_DURATION,
        xsd_type=XSDType.DURATION,
        z3_sort=Z3SortType.INT,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='seconds',
        grounding=GroundingType.SELF_CONTAINED,
        description="A duration of time (ISO 8601 duration). Encoded as seconds."
    ),
    
    # =========================================================================
    # TEMPORAL - Duration (3) - Reference point required
    # =========================================================================
    
    'elapsedTime': OperandInfo(
        name='elapsedTime',
        category=OperandCategory.TEMPORAL_DURATION,
        xsd_type=XSDType.DURATION,
        z3_sort=Z3SortType.INT,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='seconds',
        grounding=GroundingType.REFERENCE_POINT,
        description="Time elapsed since policy activation",
        reference_point="policy_activation_time"
    ),
    
    'delayPeriod': OperandInfo(
        name='delayPeriod',
        category=OperandCategory.TEMPORAL_DURATION,
        xsd_type=XSDType.DURATION,
        z3_sort=Z3SortType.INT,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='seconds',
        grounding=GroundingType.REFERENCE_POINT,
        description="Delay period before action is allowed",
        reference_point="policy_activation_time"
    ),
    
    'meteredTime': OperandInfo(
        name='meteredTime',
        category=OperandCategory.TEMPORAL_DURATION,
        xsd_type=XSDType.DURATION,
        z3_sort=Z3SortType.INT,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='seconds',
        grounding=GroundingType.RUNTIME_ONLY,
        description="Cumulative active usage time. Cannot be statically analyzed.",
        reference_point="cumulative_usage"
    ),
    
    # =========================================================================
    # POSITIONAL - Absolute (4) - Self-contained
    # =========================================================================
    
    'absolutePosition': OperandInfo(
        name='absolutePosition',
        category=OperandCategory.POSITIONAL_ABSOLUTE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='seconds',  # For temporal media; bytes for files
        grounding=GroundingType.SELF_CONTAINED,
        description="Absolute offset position in media (seconds or bytes)"
    ),
    
    'absoluteSize': OperandInfo(
        name='absoluteSize',
        category=OperandCategory.POSITIONAL_ABSOLUTE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='bytes',
        grounding=GroundingType.SELF_CONTAINED,
        description="Absolute size/dimension (bytes or pixels)"
    ),
    
    'absoluteTemporalPosition': OperandInfo(
        name='absoluteTemporalPosition',
        category=OperandCategory.POSITIONAL_ABSOLUTE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='seconds',
        grounding=GroundingType.SELF_CONTAINED,
        description="Absolute time offset in media (seconds)"
    ),
    
    'absoluteSpatialPosition': OperandInfo(
        name='absoluteSpatialPosition',
        category=OperandCategory.POSITIONAL_ABSOLUTE,
        xsd_type=XSDType.STRING,  # Complex: "x,y" or structured
        z3_sort=Z3SortType.STRING,
        domain_min=0,
        domain_max=None,
        unit_required=False,
        default_unit='pixels',
        grounding=GroundingType.SELF_CONTAINED,
        description="Absolute x,y position in visual media (pixels)"
    ),
    
    # =========================================================================
    # POSITIONAL - Relative (4) - Self-contained
    # =========================================================================
    
    'relativePosition': OperandInfo(
        name='relativePosition',
        category=OperandCategory.POSITIONAL_RELATIVE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=100,
        unit_required=False,
        default_unit='percent',
        grounding=GroundingType.SELF_CONTAINED,
        description="Relative offset position (0-100%)"
    ),
    
    'relativeSize': OperandInfo(
        name='relativeSize',
        category=OperandCategory.POSITIONAL_RELATIVE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=100,
        unit_required=False,
        default_unit='percent',
        grounding=GroundingType.SELF_CONTAINED,
        description="Relative size/dimension (0-100%)"
    ),
    
    'relativeTemporalPosition': OperandInfo(
        name='relativeTemporalPosition',
        category=OperandCategory.POSITIONAL_RELATIVE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=100,
        unit_required=False,
        default_unit='percent',
        grounding=GroundingType.SELF_CONTAINED,
        description="Relative time position in media (0-100%)"
    ),
    
    'relativeSpatialPosition': OperandInfo(
        name='relativeSpatialPosition',
        category=OperandCategory.POSITIONAL_RELATIVE,
        xsd_type=XSDType.DECIMAL,
        z3_sort=Z3SortType.REAL,
        domain_min=0,
        domain_max=100,
        unit_required=False,
        default_unit='percent',
        grounding=GroundingType.SELF_CONTAINED,
        description="Relative x,y position in visual media (0-100%)"
    ),
    
    # =========================================================================
    # CATEGORICAL (7) - Semantic grounding required
    # =========================================================================
    
    'language': OperandInfo(
        name='language',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Natural language (BCP47 tag). Requires LCC/Lexvo for hierarchy.",
        external_kb="LCC/Lexvo"
    ),
    
    'fileFormat': OperandInfo(
        name='fileFormat',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="File format (MIME type). Requires PRONOM/IANA for hierarchy.",
        external_kb="PRONOM/IANA"
    ),
    
    'media': OperandInfo(
        name='media',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Media category (NOT IANA MediaType). Requires custom taxonomy.",
        external_kb="Custom taxonomy"
    ),
    
    'industry': OperandInfo(
        name='industry',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Industry sector. Requires NAICS/ISIC for hierarchy.",
        external_kb="NAICS/ISIC"
    ),
    
    'purpose': OperandInfo(
        name='purpose',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.ANYURI,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Purpose of use. Requires DPV for hierarchy.",
        external_kb="DPV"
    ),
    
    'product': OperandInfo(
        name='product',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.ANYURI,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Product category. Requires UNSPSC for hierarchy.",
        external_kb="UNSPSC"
    ),
    
    'deliveryChannel': OperandInfo(
        name='deliveryChannel',
        category=OperandCategory.CATEGORICAL,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Delivery channel. Requires custom taxonomy.",
        external_kb="Custom taxonomy"
    ),
    
    # =========================================================================
    # SPATIAL (2) - Semantic grounding required
    # =========================================================================
    
    'spatial': OperandInfo(
        name='spatial',
        category=OperandCategory.SPATIAL,
        xsd_type=XSDType.ANYURI,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Named geographic region. Requires GeoNames for hierarchy.",
        external_kb="GeoNames"
    ),
    
    'spatialCoordinates': OperandInfo(
        name='spatialCoordinates',
        category=OperandCategory.SPATIAL,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Geographic coordinates. Requires GeoSPARQL for reasoning.",
        external_kb="GeoSPARQL"
    ),
    
    # =========================================================================
    # REFERENCE (4) - Semantic grounding required
    # =========================================================================
    
    'recipient': OperandInfo(
        name='recipient',
        category=OperandCategory.REFERENCE,
        xsd_type=XSDType.ANYURI,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Party receiving the asset. Requires FOAF/vCard.",
        external_kb="FOAF/vCard"
    ),
    
    'systemDevice': OperandInfo(
        name='systemDevice',
        category=OperandCategory.REFERENCE,
        xsd_type=XSDType.ANYURI,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Computing system/device. Requires custom registry.",
        external_kb="Custom registry"
    ),
    
    'event': OperandInfo(
        name='event',
        category=OperandCategory.REFERENCE,
        xsd_type=XSDType.ANYURI,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="An identified event. Requires Schema.org/OWL-Time.",
        external_kb="Schema.org/OWL-Time"
    ),
    
    'virtualLocation': OperandInfo(
        name='virtualLocation',
        category=OperandCategory.REFERENCE,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Internet domain or IP address. Requires DNS/IP geolocation.",
        external_kb="DNS/IP geolocation"
    ),
    
    # =========================================================================
    # VERSION (1) - Semantic grounding required
    # =========================================================================
    
    'version': OperandInfo(
        name='version',
        category=OperandCategory.VERSION,
        xsd_type=XSDType.STRING,
        z3_sort=Z3SortType.STRING,
        grounding=GroundingType.SEMANTIC,
        description="Version string. Requires SemVer or custom parsing.",
        external_kb="SemVer"
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_operand_name(operand: str) -> str:
    """
    Normalize operand name by stripping namespace prefixes.
    
    Args:
        operand: Operand name with optional namespace
        
    Returns:
        Normalized operand name
    """
    # Strip common prefixes
    if ':' in operand:
        operand = operand.split(':')[-1]
    if '/' in operand:
        operand = operand.split('/')[-1]
    if '#' in operand:
        operand = operand.split('#')[-1]
    return operand


def get_operand_info(operand: str) -> Optional[OperandInfo]:
    """
    Get complete information for an operand.
    
    Args:
        operand: Operand name (with or without namespace)
        
    Returns:
        OperandInfo or None if not found
    """
    name = _normalize_operand_name(operand)
    return OPERAND_REGISTRY.get(name)


def get_all_operands() -> List[str]:
    """Get list of all registered operand names"""
    return list(OPERAND_REGISTRY.keys())


def get_operands_by_category(category: OperandCategory) -> List[OperandInfo]:
    """
    Get all operands in a specific category.
    
    Args:
        category: The category to filter by
        
    Returns:
        List of OperandInfo for operands in that category
    """
    return [
        info for info in OPERAND_REGISTRY.values()
        if info.category == category
    ]


def get_operands_by_grounding(grounding: GroundingType) -> List[OperandInfo]:
    """
    Get all operands with a specific grounding requirement.
    
    Args:
        grounding: The grounding type to filter by
        
    Returns:
        List of OperandInfo for operands with that grounding
    """
    return [
        info for info in OPERAND_REGISTRY.values()
        if info.grounding == grounding
    ]


# =============================================================================
# STATISTICS
# =============================================================================

def get_registry_statistics() -> Dict[str, Any]:
    """
    Get statistics about the operand registry.
    
    Returns:
        Dictionary with counts by category and grounding
    """
    stats = {
        'total': len(OPERAND_REGISTRY),
        'by_category': {},
        'by_grounding': {},
    }
    
    for category in OperandCategory:
        count = len(get_operands_by_category(category))
        if count > 0:
            stats['by_category'][category.value] = count
    
    for grounding in GroundingType:
        count = len(get_operands_by_grounding(grounding))
        if count > 0:
            stats['by_grounding'][grounding.value] = count
    
    return stats


# Verify registry completeness on module load
_stats = get_registry_statistics()
assert _stats['total'] == 31, f"Expected 31 operands, got {_stats['total']}"
assert _stats['by_grounding'].get('self_contained', 0) == 14, "Expected 14 self-contained"
assert _stats['by_grounding'].get('reference_point', 0) == 2, "Expected 2 reference_point"
assert _stats['by_grounding'].get('runtime_only', 0) == 1, "Expected 1 runtime_only"
assert _stats['by_grounding'].get('semantic', 0) == 14, "Expected 14 semantic"