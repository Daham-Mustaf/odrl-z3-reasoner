# src/semantics/types.py
"""
Core type system for ODRL constraint reasoning.
Provides semantic types for all ODRL operands and values.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Dict, Any
from enum import Enum

# ==============================================================================
# VALUE DOMAINS
# ==============================================================================

class ValueDomain(Enum):
    """Semantic domains for ODRL values"""
    NUMERIC = "numeric"
    TEMPORAL = "temporal"
    TEMPORAL_INTERVAL = "temporal_interval"
    MONETARY = "monetary"
    SPATIAL = "spatial"
    CATEGORICAL = "categorical"
    VERSION = "version"
    STRING = "string"
    UNKNOWN = "unknown"

class Z3Sort(Enum):
    """Z3 solver types"""
    INT = "Int"
    REAL = "Real"
    STRING = "String"
    BOOL = "Bool"
    BITVEC = "BitVec"
    ARRAY = "Array"

class Dimension(Enum):
    """Physical/logical dimensions for unit compatibility"""
    TIME = "Time"
    LENGTH = "Length"
    INFORMATION = "Information"
    CURRENCY = "Currency"
    DIMENSIONLESS = "Dimensionless"
    NONE = "None"

# ==============================================================================
# CONSTRAINT TYPES
# ==============================================================================

class ConstraintType(Enum):
    """Types of constraints in ODRL"""
    ATOMIC = "atomic"
    AND = "and"
    OR = "or"
    XONE = "xone"

class OperatorType(Enum):
    """ODRL operators"""
    # Relational
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTEQ = "lteq"
    GT = "gt"
    GTEQ = "gteq"
    
    # Set-based
    IS_ANY_OF = "is_any_of"
    IS_ALL_OF = "is_all_of"
    IS_NONE_OF = "is_none_of"
    
    # Containment
    HAS_PART = "has_part"
    IS_PART_OF = "is_part_of"
    IS_A = "is_a"

class PolicyRuleType(Enum):
    """ODRL rule types"""
    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    DUTY = "duty"

# ==============================================================================
# SEMANTIC METADATA
# ==============================================================================

@dataclass
class SemanticInfo:
    """
    Semantic metadata for a constraint value.
    Guides normalization and Z3 encoding.
    """
    domain: ValueDomain
    dimension: Dimension
    z3_sort: Z3Sort
    base_unit: str
    value_range: Optional[tuple] = None  # (min, max)
    precision: Optional[str] = None      # For temporal values
    
    def __post_init__(self):
        if self.value_range and len(self.value_range) != 2:
            raise ValueError("value_range must be (min, max) tuple")

# ==============================================================================
# NORMALIZED CONSTRAINT
# ==============================================================================

@dataclass
class NormalizedValue:
    """A value after normalization"""
    canonical_value: Union[int, float, str, List]
    original_value: Any
    original_unit: Optional[str]
    canonical_unit: str
    conversion_factor: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AtomicConstraint:
    """A single atomic constraint"""
    id: str
    left_operand: str
    operator: OperatorType
    right_value: NormalizedValue
    semantics: SemanticInfo
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompositeConstraint:
    """A composite constraint (AND/OR/XONE)"""
    id: str
    constraint_type: ConstraintType
    children: List[str]  # IDs of child constraints
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PolicyRule:
    """A policy rule (Permission/Prohibition/Duty)"""
    id: str
    rule_type: PolicyRuleType
    action: str
    constraint_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Policy:
    """Complete ODRL policy"""
    id: str
    rules: List[PolicyRule]
    constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
    metadata: Dict[str, Any] = field(default_factory=dict)

# ==============================================================================
# OPERAND REGISTRY
# ==============================================================================

OPERAND_SEMANTICS: Dict[str, SemanticInfo] = {
    # Numeric - Counts
    'count': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.INT,
        base_unit='seconds_since_epoch',
        value_range=(0, None)
    ),
    
    'percentage': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.REAL,
        base_unit='percent',
        value_range=(0, 100)
    ),
    
    'unitOfCount': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.INT,
        base_unit='none',
        value_range=(1, None)
    ),
    
    # Numeric - Size
    'absoluteSize': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.INFORMATION,
        z3_sort=Z3Sort.INT,
        base_unit='bytes',
        value_range=(0, None)
    ),
    
    'relativeSize': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.REAL,
        base_unit='percent',
        value_range=(0, 100)
    ),
    
    'resolution': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.INT,
        base_unit='pixels',
        value_range=(0, None)
    ),
    
    # Spatial
    'absolutePosition': SemanticInfo(
        domain=ValueDomain.SPATIAL,
        dimension=Dimension.LENGTH,
        z3_sort=Z3Sort.REAL,
        base_unit='meters',
        value_range=(None, None)
    ),
    
    # Temporal - Points in time
    'dateTime': SemanticInfo(
        domain=ValueDomain.TEMPORAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,  
        base_unit='seconds_since_epoch',
        value_range=(0, None)
    ),
    
    'dateTimeAfter': SemanticInfo(
        domain=ValueDomain.TEMPORAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,  
        base_unit='seconds_since_epoch',
        value_range=(0, None)
    ),
    
    'dateTimeBefore': SemanticInfo(
        domain=ValueDomain.TEMPORAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT, 
        base_unit='seconds_since_epoch',
        value_range=(0, None)
    ),
    
    'absoluteTemporalPosition': SemanticInfo(
        domain=ValueDomain.TEMPORAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='unix_timestamp',
        value_range=(0, 2147483647),
        precision='seconds'
    ),
    
    # Temporal - Durations
    'elapsedTime': SemanticInfo(
        domain=ValueDomain.TEMPORAL_INTERVAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds',
        value_range=(0, None),
        precision='seconds'
    ),
    
    'meteredTime': SemanticInfo(
        domain=ValueDomain.TEMPORAL_INTERVAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds',
        value_range=(0, None),
        precision='seconds'
    ),
    
    'delayPeriod': SemanticInfo(
        domain=ValueDomain.TEMPORAL_INTERVAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds',
        value_range=(0, None),
        precision='seconds'
    ),
    
    'timeInterval': SemanticInfo(
        domain=ValueDomain.TEMPORAL_INTERVAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds',
        value_range=(0, None),
        precision='seconds'
    ),
    
    'relativeTemporalPosition': SemanticInfo(
        domain=ValueDomain.TEMPORAL_INTERVAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds',
        value_range=(None, None),  # Can be negative
        precision='seconds'
    ),
    
    # Monetary
    'payAmount': SemanticInfo(
        domain=ValueDomain.MONETARY,
        dimension=Dimension.CURRENCY,
        z3_sort=Z3Sort.INT,
        base_unit='minor_units',  # cents, etc.
        value_range=(0, None)
    ),
    
    # Version
    'version': SemanticInfo(
        domain=ValueDomain.VERSION,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.ARRAY,
        base_unit='semantic_version'
    ),
    
    # Categorical
    'language': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='iso639-1'
    ),
    
    'media': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='mime_type'
    ),
    
    'fileFormat': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='mime_type'
    ),
    
    'purpose': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'industry': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'product': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'recipient': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'systemDevice': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'deliveryChannel': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
}

def get_operand_semantics(operand: str) -> SemanticInfo:
    """Get semantic information for an operand"""
    if operand in OPERAND_SEMANTICS:
        return OPERAND_SEMANTICS[operand]
    
    # Unknown operand - return generic semantics
    return SemanticInfo(
        domain=ValueDomain.UNKNOWN,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='none'
    )