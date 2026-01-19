# src/semantics/constraint_types.py
"""
Core type system for ODRL constraint reasoning.
Provides semantic types for all ODRL operands and values.

Implementation Plan Alignment:
- Constraint data structures with metadata
- Numeric/temporal SMT encoding support
- Set-based operator support
"""
from dataclasses import dataclass, field
from typing import Optional, List, Union, Dict, Any
from enum import Enum
import json


# ==============================================================================
# DEBUG MODE SUPPORT
# ==============================================================================

_DEBUG_MODE = False

def set_debug_mode(enabled: bool):
    """Enable/disable debug mode globally"""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return _DEBUG_MODE

def debug_print(category: str, message: str, data: Any = None):
    """Print debug information if debug mode is enabled"""
    if _DEBUG_MODE:
        print(f"[DEBUG:{category}] {message}")
        if data is not None:
            if isinstance(data, (dict, list)):
                print(f"         {json.dumps(data, indent=2, default=str)}")
            else:
                print(f"         {data}")


# ==============================================================================
# VALUE DOMAINS
# ==============================================================================

class ValueDomain(Enum):
    """
    Semantic domains for ODRL values.
    
    Maps to constraint categories in Implementation Plan §2.1:
    - NUMERIC: count, percentage, payAmount
    - TEMPORAL: dateTime, elapsedTime, delayPeriod, timeInterval, meteredTime
    - TEMPORAL_INTERVAL: Duration-based temporal constraints
    - MONETARY: payAmount with currency
    - SPATIAL: spatial, spatialCoordinates (Phase 4)
    - CATEGORICAL: language, fileFormat, industry, product, purpose, media
    - POSITIONAL: absolutePosition, absoluteSize, relativePosition, relativeSize
    - REFERENCE: recipient, systemDevice, event, virtualLocation
    - VERSION: version strings
    - STRING: Generic string values
    - UNKNOWN: Fallback for unrecognized operands
    """
    NUMERIC = "numeric"
    TEMPORAL = "temporal"
    TEMPORAL_INTERVAL = "temporal_interval"
    MONETARY = "monetary"
    SPATIAL = "spatial"
    CATEGORICAL = "categorical"
    POSITIONAL = "positional"      
    REFERENCE = "reference"     
    VERSION = "version"
    STRING = "string"
    UNKNOWN = "unknown"


class Z3Sort(Enum):
    """
    Z3 solver types.
    
    Selection based on dataType metadata (Plan §2.3):
    - INT: Integers, counts, timestamps
    - REAL: Percentages, floating point
    - STRING: Categorical values, URIs
    - BOOL: Boolean flags
    - BITVEC: Bit-level operations (rarely used)
    - ARRAY: Multi-valued operands, sets
    """
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
    """
    Types of constraints in ODRL.
    
    Logical operators (Plan §2.2):
    - ATOMIC: Single constraint
    - AND: Conjunction (all must hold)
    - OR: Disjunction (at least one must hold)
    - XONE: Exclusive OR (exactly one must hold)
    - ANDSEQUENCE: Sequential conjunction (preserved structure, no reasoning)
    """
    ATOMIC = "atomic"
    AND = "and"
    OR = "or"
    XONE = "xone"
    ANDSEQUENCE = "andSequence"  # ADD: Preserved, not flattened


class OperatorType(Enum):
    """
    ODRL operators.
    
    Relational Operators (Plan §2.2):
    - Apply to: Numeric, Temporal, Positional
    - Encoding: Direct SMT arithmetic
    
    Set-Based Operators (Plan §2.2):
    - Apply to: Set/Taxonomic, Reference
    - Encoding: Set theory + optional DL
    """
    # Relational (scalar comparison)
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTEQ = "lteq"
    GT = "gt"
    GTEQ = "gteq"
    
    # Set-based (membership/containment)
    IS_ANY_OF = "isAnyOf"
    IS_ALL_OF = "isAllOf"
    IS_NONE_OF = "isNoneOf"
    
    # Taxonomic (hierarchy-aware)
    HAS_PART = "hasPart"
    IS_PART_OF = "isPartOf"
    IS_A = "isA"


class PolicyRuleType(Enum):
    """ODRL rule types"""
    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    DUTY = "duty"
    OBLIGATION = "obligation"  # ADD: Alias for duty in some contexts


# ==============================================================================
# ODRL METADATA (Implementation Plan §2.3)
# ==============================================================================

@dataclass
class ODRLMetadata:
    """
    ODRL constraint metadata as per Implementation Plan §2.3.
    
    These are attached to constraints and used in SMT encoding.
    
    Attributes:
        unit: Measurement unit (URI or string, e.g., "http://dbpedia.org/resource/Minute")
        unit_of_count: Multiplier entity for count-based constraints (LeftOperand reference)
        status: Reference value for comparison baseline
        datatype: rdfs:Datatype annotation (determines SMT sort)
        
    Usage:
        - unit: Attach to numeric variables in SMT for unit conversion
        - unit_of_count: Count-based constraint evaluation (e.g., "per user", "per device")
        - status: Comparison baseline in constraints
        - datatype: Determines Z3 sort (Int, Real, String, DateTime)
    """
    unit: Optional[str] = None
    unit_of_count: Optional[str] = None
    status: Optional[Any] = None
    datatype: Optional[str] = None
    
    # Additional metadata that may appear in ODRL
    operator_reference: Optional[str] = None  # For rightOperandReference
    left_operand_reference: Optional[str] = None  # For leftOperandReference
    
    def __repr__(self) -> str:
        parts = []
        if self.unit:
            parts.append(f"unit={self.unit}")
        if self.unit_of_count:
            parts.append(f"unitOfCount={self.unit_of_count}")
        if self.status:
            parts.append(f"status={self.status}")
        if self.datatype:
            parts.append(f"datatype={self.datatype}")
        return f"ODRLMetadata({', '.join(parts)})" if parts else "ODRLMetadata()"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {}
        if self.unit:
            result['unit'] = self.unit
        if self.unit_of_count:
            result['unitOfCount'] = self.unit_of_count
        if self.status:
            result['status'] = self.status
        if self.datatype:
            result['datatype'] = self.datatype
        if self.operator_reference:
            result['rightOperandReference'] = self.operator_reference
        if self.left_operand_reference:
            result['leftOperandReference'] = self.left_operand_reference
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ODRLMetadata':
        """Create from dictionary"""
        return cls(
            unit=data.get('unit') or data.get('odrl:unit'),
            unit_of_count=data.get('unitOfCount') or data.get('odrl:unitOfCount'),
            status=data.get('status') or data.get('odrl:status'),
            datatype=data.get('datatype') or data.get('@type'),
            operator_reference=data.get('rightOperandReference') or data.get('odrl:rightOperandReference'),
            left_operand_reference=data.get('leftOperandReference') or data.get('odrl:leftOperandReference'),
        )
    
    def is_empty(self) -> bool:
        """Check if metadata has any values"""
        return all(v is None for v in [
            self.unit, self.unit_of_count, self.status, 
            self.datatype, self.operator_reference, self.left_operand_reference
        ])


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
    
    def debug_str(self) -> str:
        """Debug representation"""
        return (f"SemanticInfo(domain={self.domain.value}, "
                f"z3_sort={self.z3_sort.value}, base_unit={self.base_unit})")


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
    
    def debug_str(self) -> str:
        """Debug representation"""
        return (f"NormalizedValue({self.original_value} [{self.original_unit}] "
                f"-> {self.canonical_value} [{self.canonical_unit}])")


@dataclass
class AtomicConstraint:
    """
    A single atomic constraint.
    
    Implementation Plan Alignment:
    - left_operand: LeftOperand URI or name
    - operator: Operator from OperatorType
    - right_value: Normalized value
    - semantics: Domain/sort information
    - odrl_metadata: ODRL-specific metadata (unit, unitOfCount, status, datatype)
    """
    id: str
    left_operand: str
    operator: OperatorType
    right_value: NormalizedValue
    semantics: SemanticInfo
    
    # ODRL metadata (Plan §2.3)
    odrl_metadata: ODRLMetadata = field(default_factory=ODRLMetadata)
    
    # Additional metadata (extensible)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        debug_print("CONSTRAINT", f"Created AtomicConstraint: {self.id}", {
            "left_operand": self.left_operand,
            "operator": self.operator.value if isinstance(self.operator, OperatorType) else self.operator,
            "right_value": str(self.right_value.canonical_value),
            "odrl_metadata": self.odrl_metadata.to_dict() if self.odrl_metadata else {}
        })
    
    def debug_str(self) -> str:
        """Debug representation"""
        op = self.operator.value if isinstance(self.operator, OperatorType) else self.operator
        return f"{self.left_operand} {op} {self.right_value.canonical_value}"
    
    def get_unit(self) -> Optional[str]:
        """Get unit from ODRL metadata or semantics"""
        if self.odrl_metadata and self.odrl_metadata.unit:
            return self.odrl_metadata.unit
        return self.semantics.base_unit if self.semantics else None
    
    def get_datatype(self) -> Optional[str]:
        """Get datatype for SMT sort selection"""
        if self.odrl_metadata and self.odrl_metadata.datatype:
            return self.odrl_metadata.datatype
        return None


@dataclass
class CompositeConstraint:
    """
    A composite constraint (AND/OR/XONE/ANDSEQUENCE).
    
    Note: ANDSEQUENCE is preserved but not flattened (Plan §2.1).
    """
    id: str
    constraint_type: ConstraintType
    children: List[str]  # IDs of child constraints
    
    # ODRL metadata
    odrl_metadata: ODRLMetadata = field(default_factory=ODRLMetadata)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        debug_print("CONSTRAINT", f"Created CompositeConstraint: {self.id}", {
            "type": self.constraint_type.value if isinstance(self.constraint_type, ConstraintType) else self.constraint_type,
            "children": self.children
        })
    
    def is_sequential(self) -> bool:
        """Check if this is a sequential constraint (andSequence)"""
        return self.constraint_type == ConstraintType.ANDSEQUENCE
    
    def debug_str(self) -> str:
        """Debug representation"""
        op = self.constraint_type.value if isinstance(self.constraint_type, ConstraintType) else self.constraint_type
        return f"{op.upper()}({', '.join(self.children)})"


@dataclass
class PolicyRule:
    """
    A policy rule (Permission/Prohibition/Duty).
    
    Actions are symbolic labels used to partition constraint spaces.
    No deontic entailment across action hierarchies.
    """
    id: str
    rule_type: PolicyRuleType
    action: str
    constraint_id: Optional[str] = None
    
    # Target asset/party (optional)
    target: Optional[str] = None
    assigner: Optional[str] = None
    assignee: Optional[str] = None
    
    # ODRL metadata
    odrl_metadata: ODRLMetadata = field(default_factory=ODRLMetadata)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        debug_print("RULE", f"Created PolicyRule: {self.id}", {
            "type": self.rule_type.value if isinstance(self.rule_type, PolicyRuleType) else self.rule_type,
            "action": self.action,
            "constraint_id": self.constraint_id
        })
    
    def debug_str(self) -> str:
        """Debug representation"""
        rt = self.rule_type.value if isinstance(self.rule_type, PolicyRuleType) else self.rule_type
        return f"{rt.upper()}({self.action}) -> {self.constraint_id or 'no constraint'}"


@dataclass
class Policy:
    """
    Complete ODRL policy.
    
    Policies are logical objects, not programs (Plan §1.1).
    """
    id: str
    rules: List[PolicyRule]
    constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
    
    # Policy-level metadata
    odrl_metadata: ODRLMetadata = field(default_factory=ODRLMetadata)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Inheritance relationship
    inherits_from: Optional[str] = None
    
    def __post_init__(self):
        debug_print("POLICY", f"Created Policy: {self.id}", {
            "rules": len(self.rules),
            "constraints": len(self.constraints),
            "inherits_from": self.inherits_from
        })
    
    def get_actions(self) -> set:
        """Get all unique actions in this policy"""
        return {rule.action for rule in self.rules if rule.action}
    
    def get_rules_for_action(self, action: str) -> List[PolicyRule]:
        """Get all rules for a specific action"""
        return [rule for rule in self.rules if rule.action == action]
    
    def get_constraint(self, constraint_id: str) -> Optional[Union[AtomicConstraint, CompositeConstraint]]:
        """Get constraint by ID"""
        return self.constraints.get(constraint_id)
    
    def debug_str(self) -> str:
        """Debug representation"""
        lines = [f"Policy: {self.id}"]
        if self.inherits_from:
            lines.append(f"  inherits: {self.inherits_from}")
        lines.append(f"  rules: {len(self.rules)}")
        for rule in self.rules:
            lines.append(f"    - {rule.debug_str()}")
        lines.append(f"  constraints: {len(self.constraints)}")
        for cid, c in self.constraints.items():
            lines.append(f"    - {c.debug_str()}")
        return '\n'.join(lines)


# ==============================================================================
# OPERAND REGISTRY (Updated with all categories from Plan §2.1)
# ==============================================================================

OPERAND_SEMANTICS: Dict[str, SemanticInfo] = {
    # ─────────────────────────────────────────────────────────────────────────
    # NUMERIC (Plan §2.1: count, percentage, payAmount)
    # ─────────────────────────────────────────────────────────────────────────
    'count': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.INT,
        base_unit='count',
        value_range=(0, None)
    ),
    
    'percentage': SemanticInfo(
        domain=ValueDomain.NUMERIC,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.REAL,
        base_unit='percent',
        value_range=(0, 100)
    ),
    
    'payAmount': SemanticInfo(
        domain=ValueDomain.MONETARY,
        dimension=Dimension.CURRENCY,
        z3_sort=Z3Sort.INT,
        base_unit='minor_units',  # cents, etc.
        value_range=(0, None)
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEMPORAL (Plan §2.1: dateTime, elapsedTime, delayPeriod, timeInterval, meteredTime)
    # ─────────────────────────────────────────────────────────────────────────
    'dateTime': SemanticInfo(
        domain=ValueDomain.TEMPORAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,  
        base_unit='seconds_since_epoch',
        value_range=(0, None),
        precision='seconds'
    ),
    
    'elapsedTime': SemanticInfo(
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
    
    'meteredTime': SemanticInfo(
        domain=ValueDomain.TEMPORAL_INTERVAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds',
        value_range=(0, None),
        precision='seconds'
    ),
    
    # Additional temporal operands
    'absoluteTemporalPosition': SemanticInfo(
        domain=ValueDomain.TEMPORAL,
        dimension=Dimension.TIME,
        z3_sort=Z3Sort.INT,
        base_unit='seconds_since_epoch',
        value_range=(0, 2147483647),
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
    
    # ─────────────────────────────────────────────────────────────────────────
    # SET/TAXONOMIC (Plan §2.1: language, fileFormat, industry, product, purpose, media, deliveryChannel)
    # ─────────────────────────────────────────────────────────────────────────
    'language': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='iso639-1'
    ),
    
    'fileFormat': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='mime_type'
    ),
    
    'media': SemanticInfo(
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
    
    'deliveryChannel': SemanticInfo(
        domain=ValueDomain.CATEGORICAL,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # POSITIONAL (Plan §2.1: absolutePosition, absoluteSize, relativePosition, relativeSize, resolution)
    # ─────────────────────────────────────────────────────────────────────────
    'absolutePosition': SemanticInfo(
        domain=ValueDomain.POSITIONAL,
        dimension=Dimension.LENGTH,
        z3_sort=Z3Sort.REAL,
        base_unit='meters',
        value_range=(None, None)
    ),
    
    'absoluteSize': SemanticInfo(
        domain=ValueDomain.POSITIONAL,
        dimension=Dimension.INFORMATION,
        z3_sort=Z3Sort.INT,
        base_unit='bytes',
        value_range=(0, None)
    ),
    
    'relativePosition': SemanticInfo(
        domain=ValueDomain.POSITIONAL,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.REAL,
        base_unit='percent',
        value_range=(0, 100)
    ),
    
    'relativeSize': SemanticInfo(
        domain=ValueDomain.POSITIONAL,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.REAL,
        base_unit='percent',
        value_range=(0, 100)
    ),
    
    'resolution': SemanticInfo(
        domain=ValueDomain.POSITIONAL,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.INT,
        base_unit='pixels',
        value_range=(0, None)
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # REFERENCE ( recipient, systemDevice, event, virtualLocation)
    # ─────────────────────────────────────────────────────────────────────────
    'recipient': SemanticInfo(
        domain=ValueDomain.REFERENCE,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'systemDevice': SemanticInfo(
        domain=ValueDomain.REFERENCE,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'event': SemanticInfo(
        domain=ValueDomain.REFERENCE,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    'virtualLocation': SemanticInfo(
        domain=ValueDomain.REFERENCE,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # SPATIAL (Optional)
    # ─────────────────────────────────────────────────────────────────────────
    'spatial': SemanticInfo(
        domain=ValueDomain.SPATIAL,
        dimension=Dimension.LENGTH,
        z3_sort=Z3Sort.STRING,  # GeoJSON or WKT string
        base_unit='wgs84'
    ),
    
    'spatialCoordinates': SemanticInfo(
        domain=ValueDomain.SPATIAL,
        dimension=Dimension.LENGTH,
        z3_sort=Z3Sort.ARRAY,  # [lat, lon] or [x, y, z]
        base_unit='wgs84'
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # VERSION
    # ─────────────────────────────────────────────────────────────────────────
    'version': SemanticInfo(
        domain=ValueDomain.VERSION,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.ARRAY,
        base_unit='semantic_version'
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # UNIT OF COUNT (Special - multiplier entity)
    # ─────────────────────────────────────────────────────────────────────────
    'unitOfCount': SemanticInfo(
        domain=ValueDomain.REFERENCE,
        dimension=Dimension.DIMENSIONLESS,
        z3_sort=Z3Sort.STRING,
        base_unit='uri'
    ),
}


def get_operand_semantics(operand: str) -> SemanticInfo:
    """
    Get semantic information for an operand.
    
    Args:
        operand: ODRL leftOperand name (with or without namespace)
        
    Returns:
        SemanticInfo for the operand, or generic UNKNOWN if not found
    """
    # Strip namespace if present
    if ':' in operand:
        operand = operand.split(':')[-1]
    if '/' in operand:
        operand = operand.split('/')[-1]
    
    if operand in OPERAND_SEMANTICS:
        debug_print("SEMANTICS", f"Found semantics for '{operand}'", 
                   OPERAND_SEMANTICS[operand].debug_str())
        return OPERAND_SEMANTICS[operand]
    
    # Unknown operand - return generic semantics
    debug_print("SEMANTICS", f"Unknown operand '{operand}', using default")
    return SemanticInfo(
        domain=ValueDomain.UNKNOWN,
        dimension=Dimension.NONE,
        z3_sort=Z3Sort.STRING,
        base_unit='none'
    )


def get_z3_sort_for_datatype(datatype: Optional[str]) -> Z3Sort:
    """
    Determine Z3 sort based on rdfs:Datatype.
    
    Implementation Plan §2.3: datatype determines SMT sort.
    
    Args:
        datatype: rdfs:Datatype URI or name
        
    Returns:
        Appropriate Z3Sort
    """
    if not datatype:
        return Z3Sort.STRING  # Default
    
    # Normalize datatype
    dt = datatype.lower()
    if '#' in dt:
        dt = dt.split('#')[-1]
    if '/' in dt:
        dt = dt.split('/')[-1]
    
    # Map to Z3 sorts
    INTEGER_TYPES = {'integer', 'int', 'long', 'short', 'byte', 
                     'nonnegativeinteger', 'positiveinteger', 'unsignedint'}
    REAL_TYPES = {'decimal', 'float', 'double', 'real'}
    DATETIME_TYPES = {'datetime', 'date', 'time', 'datetimestamp'}
    BOOLEAN_TYPES = {'boolean', 'bool'}
    
    if dt in INTEGER_TYPES:
        return Z3Sort.INT
    elif dt in REAL_TYPES:
        return Z3Sort.REAL
    elif dt in DATETIME_TYPES:
        return Z3Sort.INT  # Timestamps as integers
    elif dt in BOOLEAN_TYPES:
        return Z3Sort.BOOL
    else:
        return Z3Sort.STRING


# ==============================================================================
# CATEGORY CLASSIFICATION 
# ==============================================================================

def classify_operand(operand: str) -> str:
    """
    Classify operand into category for encoder selection.
    
    Returns:
        Category name: 'numeric', 'temporal', 'set', 'spatial', 'positional', 'reference', 'logical'
    """
    semantics = get_operand_semantics(operand)
    
    if semantics.domain in (ValueDomain.NUMERIC, ValueDomain.MONETARY):
        return 'numeric'
    elif semantics.domain in (ValueDomain.TEMPORAL, ValueDomain.TEMPORAL_INTERVAL):
        return 'temporal'
    elif semantics.domain == ValueDomain.CATEGORICAL:
        return 'set'
    elif semantics.domain == ValueDomain.SPATIAL:
        return 'spatial'
    elif semantics.domain == ValueDomain.POSITIONAL:
        return 'positional'
    elif semantics.domain == ValueDomain.REFERENCE:
        return 'reference'
    else:
        return 'unknown'