# src/semantics/constraint_types.py
"""
ODRL-SA Constraint Types

Complete constraint representation per ODRL-SA §2 Definition 1:

    c = (ℓ, ⋈, v, u?, d?, r?, s?)

Where:
    ℓ = LeftOperand (property being constrained)
    ⋈ = Operator (comparison relation)
    v = RightOperand (value or policyUsage)
    u = Unit (optional unit of measurement)
    d = DataType (optional explicit XSD datatype)
    r = rightOperandReference (optional IRI to dereference)
    s = unitOfCount (optional counting scope)

This module also defines the operator types and logical constraint composition.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Any, Dict
from enum import Enum
from datetime import datetime, timedelta
import re


# =============================================================================
# OPERATOR TYPES (§2 Definition 2-3)
# =============================================================================

class OperatorType(Enum):
    """
    ODRL Operators partitioned into comparison and set-based.
    
    Ōcmp (comparison): eq, neq, lt, lteq, gt, gteq
    Ōset (set-based): isA, hasPart, isPartOf, isAllOf, isAnyOf, isNoneOf
    """
    # Comparison operators (XSD-compatible)
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTEQ = "lteq"
    GT = "gt"
    GTEQ = "gteq"
    
    # Set-based operators (require semantic grounding)
    IS_A = "isA"
    HAS_PART = "hasPart"
    IS_PART_OF = "isPartOf"
    IS_ALL_OF = "isAllOf"
    IS_ANY_OF = "isAnyOf"
    IS_NONE_OF = "isNoneOf"
    
    def is_comparison(self) -> bool:
        """Check if this is a comparison operator."""
        return self in {
            OperatorType.EQ, OperatorType.NEQ,
            OperatorType.LT, OperatorType.LTEQ,
            OperatorType.GT, OperatorType.GTEQ
        }
    
    def is_set_based(self) -> bool:
        """Check if this is a set-based operator."""
        return self in {
            OperatorType.IS_A, OperatorType.HAS_PART, OperatorType.IS_PART_OF,
            OperatorType.IS_ALL_OF, OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF
        }
    
    def is_ordering(self) -> bool:
        """Check if this operator requires ordering (not just equality)."""
        return self in {
            OperatorType.LT, OperatorType.LTEQ,
            OperatorType.GT, OperatorType.GTEQ
        }
    
    @classmethod
    def from_uri(cls, uri: str) -> 'OperatorType':
        """Parse operator from ODRL URI."""
        # Extract local name
        if '#' in uri:
            name = uri.split('#')[-1]
        elif '/' in uri:
            name = uri.split('/')[-1]
        else:
            name = uri
        
        # Normalize and match
        name_lower = name.lower()
        for op in cls:
            if op.value.lower() == name_lower:
                return op
        
        raise ValueError(f"Unknown operator: {uri}")


class LogicalOperatorType(Enum):
    """
    Logical operators for composing constraints (§2 Definition 3).
    
    Ōlog = {and, or, xone, andSequence}
    """
    AND = "and"
    OR = "or"
    XONE = "xone"
    AND_SEQUENCE = "andSequence"
    
    @classmethod
    def from_uri(cls, uri: str) -> 'LogicalOperatorType':
        """Parse logical operator from ODRL URI."""
        if '#' in uri:
            name = uri.split('#')[-1]
        elif '/' in uri:
            name = uri.split('/')[-1]
        else:
            name = uri
        
        name_lower = name.lower()
        for op in cls:
            if op.value.lower() == name_lower:
                return op
        
        raise ValueError(f"Unknown logical operator: {uri}")


# =============================================================================
# Z3 SORT MAPPING
# =============================================================================

class Z3Sort(Enum):
    """Z3 solver sort types for constraint encoding."""
    INT = "Int"
    REAL = "Real"
    STRING = "String"
    BOOL = "Bool"
    ARRAY = "Array"  # For multi-valued operands


# =============================================================================
# RIGHT OPERAND VALUE
# =============================================================================

@dataclass
class RightValue:
    """
    Represents the right operand value of a constraint.
    
    Handles:
    - Literal values (int, float, string, datetime)
    - policyUsage (special runtime reference)
    - IRI references
    - Lists of values (for set operators)
    """
    raw_value: Any
    """Original value as parsed."""
    
    canonical_value: Any
    """Normalized value for comparison."""
    
    datatype: Optional[str] = None
    """XSD datatype URI if specified."""
    
    is_policy_usage: bool = False
    """True if this is the special policyUsage reference."""
    
    is_iri: bool = False
    """True if this is an IRI reference."""
    
    is_list: bool = False
    """True if this is a list of values (for set operators)."""
    
    @classmethod
    def from_literal(cls, value: Any, datatype: Optional[str] = None) -> 'RightValue':
        """Create from a literal value."""
        canonical = cls._canonicalize(value, datatype)
        return cls(
            raw_value=value,
            canonical_value=canonical,
            datatype=datatype,
            is_policy_usage=False,
            is_iri=False,
            is_list=isinstance(value, list)
        )
    
    @classmethod
    def policy_usage(cls) -> 'RightValue':
        """Create the special policyUsage reference."""
        return cls(
            raw_value="policyUsage",
            canonical_value=None,
            datatype=None,
            is_policy_usage=True,
            is_iri=False,
            is_list=False
        )
    
    @classmethod
    def from_iri(cls, iri: str) -> 'RightValue':
        """Create from an IRI reference."""
        return cls(
            raw_value=iri,
            canonical_value=iri,
            datatype="xsd:anyURI",
            is_policy_usage=False,
            is_iri=True,
            is_list=False
        )
    
    @staticmethod
    def _canonicalize(value: Any, datatype: Optional[str]) -> Any:
        """Convert value to canonical form for comparison."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, str):
            # Try to parse as number
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except ValueError:
                pass
            
            # Try to parse as datetime
            if datatype and 'dateTime' in datatype:
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            # Try to parse as duration
            if datatype and 'duration' in datatype:
                return RightValue._parse_duration(value)
            
            return value
        
        if isinstance(value, list):
            return [RightValue._canonicalize(v, datatype) for v in value]
        
        return value
    
    @staticmethod
    def _parse_duration(value: str) -> Optional[int]:
        """Parse ISO 8601 duration to seconds."""
        # Simple pattern for P[n]Y[n]M[n]DT[n]H[n]M[n]S
        pattern = r'P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?'
        match = re.match(pattern, value)
        if not match:
            return None
        
        years, months, days, hours, minutes, seconds = match.groups()
        total_seconds = 0
        
        if years:
            total_seconds += int(years) * 365 * 24 * 3600
        if months:
            total_seconds += int(months) * 30 * 24 * 3600
        if days:
            total_seconds += int(days) * 24 * 3600
        if hours:
            total_seconds += int(hours) * 3600
        if minutes:
            total_seconds += int(minutes) * 60
        if seconds:
            total_seconds += int(seconds)
        
        return total_seconds


# =============================================================================
# ODRL METADATA
# =============================================================================

@dataclass
class ODRLMetadata:
    """
    Additional ODRL constraint properties.
    
    These are the optional fields from the constraint tuple:
    u (unit), d (dataType), r (rightOperandReference), s (unitOfCount)
    """
    unit: Optional[str] = None
    """Unit of measurement (e.g., currency, time unit)."""
    
    datatype: Optional[str] = None
    """Explicit XSD datatype for the rightOperand."""
    
    right_operand_reference: Optional[str] = None
    """IRI to dereference for the actual rightOperand value."""
    
    unit_of_count: Optional[str] = None
    """Counting scope (e.g., perUser, perDevice)."""
    
    status: Optional[str] = None
    """Runtime status reference (if present, constraint is RUNTIME)."""
    
    def has_deferred_value(self) -> bool:
        """Check if value requires dereferencing."""
        return self.right_operand_reference is not None
    
    def has_runtime_dependency(self) -> bool:
        """Check if constraint requires runtime state."""
        return self.status is not None


# =============================================================================
# ATOMIC CONSTRAINT (§2 Definition 1)
# =============================================================================

@dataclass
class AtomicConstraint:
    """
    Complete ODRL atomic constraint per ODRL-SA §2 Definition 1.
    
    c = (ℓ, ⋈, v, u?, d?, r?, s?)
    
    Attributes:
        id: Unique constraint identifier
        left_operand: ℓ - The LeftOperand being constrained
        operator: ⋈ - The comparison operator
        right_value: v - The right operand value
        odrl_metadata: Combined optional fields (u, d, r, s)
        source_rule: The rule (permission/prohibition/duty) this belongs to
        source_policy: The policy this belongs to
    """
    id: str
    """Unique identifier for this constraint."""
    
    left_operand: str
    """LeftOperand being constrained (e.g., 'count', 'dateTime')."""
    
    operator: OperatorType
    """Comparison operator."""
    
    right_value: RightValue
    """Right operand value."""
    
    odrl_metadata: Optional[ODRLMetadata] = None
    """Optional ODRL metadata (unit, datatype, reference, unitOfCount)."""
    
    source_rule: Optional[str] = None
    """The rule ID this constraint belongs to."""
    
    source_policy: Optional[str] = None
    """The policy ID this constraint belongs to."""
    
    # Convenience accessors
    @property
    def unit(self) -> Optional[str]:
        """Get unit from metadata."""
        return self.odrl_metadata.unit if self.odrl_metadata else None
    
    @property
    def datatype(self) -> Optional[str]:
        """Get datatype from metadata."""
        return self.odrl_metadata.datatype if self.odrl_metadata else None
    
    @property
    def right_operand_reference(self) -> Optional[str]:
        """Get rightOperandReference from metadata."""
        return self.odrl_metadata.right_operand_reference if self.odrl_metadata else None
    
    @property
    def unit_of_count(self) -> Optional[str]:
        """Get unitOfCount from metadata."""
        return self.odrl_metadata.unit_of_count if self.odrl_metadata else None
    
    def is_policy_usage(self) -> bool:
        """Check if this constraint uses policyUsage as rightOperand."""
        return self.right_value.is_policy_usage
    
    def has_deferred_value(self) -> bool:
        """Check if value requires dereferencing."""
        return (self.odrl_metadata is not None and 
                self.odrl_metadata.has_deferred_value())
    
    def has_runtime_dependency(self) -> bool:
        """Check if constraint requires runtime state."""
        return (self.is_policy_usage() or 
                (self.odrl_metadata is not None and 
                 self.odrl_metadata.has_runtime_dependency()))
    
    def __str__(self) -> str:
        op_str = self.operator.value
        val_str = str(self.right_value.canonical_value)
        unit_str = f" ({self.unit})" if self.unit else ""
        return f"{self.left_operand} {op_str} {val_str}{unit_str}"


# =============================================================================
# COMPOSITE CONSTRAINT (Logical Composition)
# =============================================================================

@dataclass
class CompositeConstraint:
    """
    Logical composition of constraints.
    
    Supports: and, or, xone, andSequence
    """
    id: str
    """Unique identifier for this composite constraint."""
    
    operator: LogicalOperatorType
    """Logical operator (and, or, xone, andSequence)."""
    
    operands: List[str]
    """List of constraint IDs being composed."""
    
    source_rule: Optional[str] = None
    """The rule ID this constraint belongs to."""
    
    source_policy: Optional[str] = None
    """The policy ID this constraint belongs to."""
    
    def is_and(self) -> bool:
        return self.operator == LogicalOperatorType.AND
    
    def is_or(self) -> bool:
        return self.operator == LogicalOperatorType.OR
    
    def is_xone(self) -> bool:
        return self.operator == LogicalOperatorType.XONE
    
    def is_and_sequence(self) -> bool:
        return self.operator == LogicalOperatorType.AND_SEQUENCE
    
    def __str__(self) -> str:
        return f"{self.operator.value}({', '.join(self.operands)})"


# =============================================================================
# CONSTRAINT TYPE ALIAS
# =============================================================================

Constraint = Union[AtomicConstraint, CompositeConstraint]


# =============================================================================
# VALUE DOMAIN (for abstract interpretation)
# =============================================================================

@dataclass
class ValueDomain:
    """
    Abstract domain for a LeftOperand.
    
    Defines the valid range of values for abstract interpretation.
    """
    z3_sort: Z3Sort
    """Z3 sort for this operand."""
    
    min_value: Optional[float] = None
    """Minimum value (None = unbounded below)."""
    
    max_value: Optional[float] = None
    """Maximum value (None = unbounded above)."""
    
    is_integer: bool = False
    """True if values must be integers."""
    
    def contains(self, value: Any) -> bool:
        """Check if value is within domain bounds."""
        if value is None:
            return False
        
        try:
            num_val = float(value)
        except (TypeError, ValueError):
            return True  # Non-numeric values pass domain check
        
        if self.min_value is not None and num_val < self.min_value:
            return False
        if self.max_value is not None and num_val > self.max_value:
            return False
        
        if self.is_integer and not float(num_val).is_integer():
            return False
        
        return True