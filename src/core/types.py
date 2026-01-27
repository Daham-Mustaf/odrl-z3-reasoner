# src/core/types.py
"""
ODRL-SA Core Types

Implements the formal specification exactly:

Definition 1 (Constraint):
    c = (ℓ, ⋈, v, u?, d?, r?, s?)

Definition 2 (Operators):
    O = O_cmp ⊎ O_set
    O_cmp = {eq, neq, lt, lteq, gt, gteq}
    O_set = {isA, hasPart, isPartOf, isAllOf, isAnyOf, isNoneOf}

Definition 3 (Logical Operators):
    O_log = {and, or, xone, andSequence}

This module contains ONLY the core type definitions.
No parsing, no encoding, no judgment logic.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Any
from enum import Enum, auto
from datetime import datetime
import re


# =============================================================================
# OPERATORS (Definition 2)
# =============================================================================

class OperatorType(Enum):
    """
    ODRL Operators: O = O_cmp ⊎ O_set
    
    O_cmp (comparison): XSD-compatible, work on ordered domains
    O_set (set-based): Require semantic grounding/KB
    """
    # O_cmp: Comparison operators
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTEQ = "lteq"
    GT = "gt"
    GTEQ = "gteq"
    
    # O_set: Set-based operators
    IS_A = "isA"
    HAS_PART = "hasPart"
    IS_PART_OF = "isPartOf"
    IS_ALL_OF = "isAllOf"
    IS_ANY_OF = "isAnyOf"
    IS_NONE_OF = "isNoneOf"
    
    def is_comparison(self) -> bool:
        """Check if operator is in O_cmp."""
        return self in _O_CMP
    
    def is_set_based(self) -> bool:
        """Check if operator is in O_set."""
        return self in _O_SET
    
    @classmethod
    def from_string(cls, s: str) -> 'OperatorType':
        """Parse operator from string (handles URIs)."""
        # Extract local name from URI
        if '#' in s:
            s = s.split('#')[-1]
        elif '/' in s:
            s = s.split('/')[-1]
        
        s_lower = s.lower()
        for op in cls:
            if op.value.lower() == s_lower:
                return op
        raise ValueError(f"Unknown operator: {s}")


# Operator partitions
_O_CMP = {
    OperatorType.EQ, OperatorType.NEQ,
    OperatorType.LT, OperatorType.LTEQ,
    OperatorType.GT, OperatorType.GTEQ
}

_O_SET = {
    OperatorType.IS_A, OperatorType.HAS_PART, OperatorType.IS_PART_OF,
    OperatorType.IS_ALL_OF, OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF
}


class LogicalOperator(Enum):
    """
    Logical operators for constraint composition (Definition 3).
    O_log = {and, or, xone, andSequence}
    """
    AND = "and"
    OR = "or"
    XONE = "xone"
    AND_SEQUENCE = "andSequence"
    
    @classmethod
    def from_string(cls, s: str) -> 'LogicalOperator':
        """Parse logical operator from string."""
        if '#' in s:
            s = s.split('#')[-1]
        elif '/' in s:
            s = s.split('/')[-1]
        
        s_lower = s.lower()
        for op in cls:
            if op.value.lower() == s_lower:
                return op
        raise ValueError(f"Unknown logical operator: {s}")


# =============================================================================
# RIGHT OPERAND VALUE
# =============================================================================

@dataclass(frozen=True)
class RightOperand:
    """
    The right operand value v in constraint c = (ℓ, ⋈, v, ...)
    
    Can be:
    - A literal value (int, float, string, datetime)
    - A list of values (for set operators)
    - The special 'policyUsage' reference
    - An IRI reference
    """
    value: Any
    """The actual value (canonical form)."""
    
    datatype: Optional[str] = None
    """XSD datatype if specified."""
    
    is_list: bool = False
    """True if value is a list (for set operators)."""
    
    is_policy_usage: bool = False
    """True if this is the special policyUsage reference."""
    
    is_iri: bool = False
    """True if this is an IRI reference."""
    
    @classmethod
    def literal(cls, value: Any, datatype: Optional[str] = None) -> 'RightOperand':
        """Create from a literal value."""
        canonical = cls._canonicalize(value, datatype)
        return cls(
            value=canonical,
            datatype=datatype,
            is_list=isinstance(value, (list, tuple, set))
        )
    
    @classmethod
    def policy_usage(cls) -> 'RightOperand':
        """Create the special policyUsage reference."""
        return cls(value=None, is_policy_usage=True)
    
    @classmethod
    def iri(cls, uri: str) -> 'RightOperand':
        """Create from an IRI."""
        return cls(value=uri, is_iri=True)
    
    @staticmethod
    def _canonicalize(value: Any, datatype: Optional[str]) -> Any:
        """Convert to canonical form."""
        if value is None:
            return None
        
        if isinstance(value, (list, tuple, set)):
            return tuple(RightOperand._canonicalize(v, datatype) for v in value)
        
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, str):
            # Try numeric
            try:
                return int(value) if '.' not in value else float(value)
            except ValueError:
                pass
            
            # Try datetime
            if datatype and 'dateTime' in datatype:
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            return value
        
        return value


# =============================================================================
# CONSTRAINT METADATA
# =============================================================================

@dataclass(frozen=True)
class ConstraintMetadata:
    """
    Optional constraint fields: (u?, d?, r?, s?)
    
    u = unit (measurement unit)
    d = dataType (explicit XSD type)
    r = rightOperandReference (IRI to dereference)
    s = unitOfCount (counting scope)
    """
    unit: Optional[str] = None
    datatype: Optional[str] = None
    right_operand_reference: Optional[str] = None
    unit_of_count: Optional[str] = None


# =============================================================================
# ATOMIC CONSTRAINT (Definition 1)
# =============================================================================

@dataclass(frozen=True)
class AtomicConstraint:
    """
    ODRL Atomic Constraint per Definition 1:
    
        c = (ℓ, ⋈, v, u?, d?, r?, s?)
    
    Where:
        ℓ = left_operand (property being constrained)
        ⋈ = operator (comparison relation)
        v = right_operand (value)
        u?, d?, r?, s? = metadata (optional fields)
    
    Immutable (frozen) for use as dict keys and in sets.
    """
    uid: str
    """Unique identifier."""
    
    left_operand: str
    """ℓ - The LeftOperand being constrained."""
    
    operator: OperatorType
    """⋈ - The comparison operator."""
    
    right_operand: RightOperand
    """v - The right operand value."""
    
    metadata: ConstraintMetadata = field(default_factory=ConstraintMetadata)
    """Optional fields (u, d, r, s)."""
    
    # Convenience properties
    @property
    def unit(self) -> Optional[str]:
        return self.metadata.unit
    
    @property
    def datatype(self) -> Optional[str]:
        return self.metadata.datatype
    
    @property
    def unit_of_count(self) -> Optional[str]:
        return self.metadata.unit_of_count
    
    def __str__(self) -> str:
        unit_str = f" [{self.unit}]" if self.unit else ""
        return f"{self.left_operand} {self.operator.value} {self.right_operand.value}{unit_str}"


# =============================================================================
# COMPOSITE CONSTRAINT
# =============================================================================

@dataclass(frozen=True)
class CompositeConstraint:
    """
    Logical composition of constraints.
    
    Semantics (Definition 3):
        and(c₁, ..., cₙ)      ≡ ⋀ᵢ cᵢ
        or(c₁, ..., cₙ)       ≡ ⋁ᵢ cᵢ
        xone(c₁, ..., cₙ)     ≡ Σᵢ⟦cᵢ⟧ = 1
        andSequence(c₁, ..., cₙ) ≡ ∃ t₁ < t₂ < ... < tₙ
    """
    uid: str
    """Unique identifier."""
    
    operator: LogicalOperator
    """Logical operator (and, or, xone, andSequence)."""
    
    operands: tuple
    """Tuple of constraint UIDs or nested constraints."""
    
    def __str__(self) -> str:
        return f"{self.operator.value}({', '.join(str(o) for o in self.operands)})"


# =============================================================================
# TYPE ALIAS
# =============================================================================

Constraint = Union[AtomicConstraint, CompositeConstraint]
"""A constraint is either atomic or composite."""


# =============================================================================
# CONSTRAINT CLASS (Definition 4)
# =============================================================================

class ConstraintClass(Enum):
    """
    Constraint classification per Definition 4:
    
        L = L_xsd ⊎ L_ref ⊎ L_sem ⊎ L_run
        where L_sem = L_kb ⊎ L_deref
    
    This determines what reasoning is possible.
    """
    FULL = auto()      # L_xsd: XSD-typed, fully analyzable
    PARTIAL = auto()   # L_ref: Reference-point dependent
    GROUNDED = auto()  # L_kb: Requires KB/ontology
    DEFERRED = auto()  # L_deref: Requires runtime dereferencing
    RUNTIME = auto()   # L_run: Runtime-only (meteredTime)
    
    def can_analyze_statically(self) -> bool:
        """Can we produce CONFLICT/POSSIBLY-COMPATIBLE?"""
        return self in {ConstraintClass.FULL, ConstraintClass.PARTIAL}


# =============================================================================
# JUDGMENT (Definition 5)
# =============================================================================

class Judgment(Enum):
    """
    ODRL-SA Judgment result per Definition 5:
    
        judge : C × C → {CONFLICT, POSSIBLY-COMPATIBLE, UNKNOWN}
    
    CONFLICT:           No world satisfies both constraints
    POSSIBLY_COMPATIBLE: At least one world may satisfy both  
    UNKNOWN:            Cannot determine (needs grounding/runtime)
    """
    CONFLICT = "CONFLICT"
    POSSIBLY_COMPATIBLE = "POSSIBLY-COMPATIBLE"
    UNKNOWN = "UNKNOWN"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_comparison_operator(op: OperatorType) -> bool:
    """Check if operator is in O_cmp."""
    return op.is_comparison()


def is_set_operator(op: OperatorType) -> bool:
    """Check if operator is in O_set."""
    return op.is_set_based()
