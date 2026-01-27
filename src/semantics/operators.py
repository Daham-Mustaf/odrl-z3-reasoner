# src/semantics/operators.py
"""
ODRL Operator Semantics

Defines semantics for all ODRL operators:
- Relational operators (eq, neq, lt, lteq, gt, gteq)
- Set-based operators (isAnyOf, isAllOf, isNoneOf)
- Taxonomic operators (isA, hasPart, isPartOf)
- Logical composition operators (and, or, xone, andSequence)

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0

Operator validity by domain:
┌─────────────────────────────────────────────────────────────────┐
│  Relational (6)     │ Valid for: Numeric, Temporal, Positional │
│  Set-based (3)      │ Valid for: Categorical (require grounding)│
│  Taxonomic (3)      │ Valid for: Hierarchical (require grounding)│
│  Logical (4)        │ Valid for: Constraint composition         │
└─────────────────────────────────────────────────────────────────┘
"""

from enum import Enum
from typing import Dict, Set, List, Optional, Callable, Any


class OperatorCategory(Enum):
    """Categories of ODRL operators"""
    RELATIONAL = "relational"
    SET = "set"
    TAXONOMIC = "taxonomic"
    LOGICAL = "logical"


class Operator(Enum):
    """
    All ODRL operators.
    
    Relational operators apply to scalar values (numbers, timestamps).
    Set operators apply to collections and categorical values.
    Taxonomic operators require external hierarchy knowledge.
    Logical operators compose constraints.
    """
    # Relational (6) - For numeric, temporal, positional
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTEQ = "lteq"
    GT = "gt"
    GTEQ = "gteq"
    
    # Set-based (3) - For categorical with multiple values
    IS_ANY_OF = "isAnyOf"
    IS_ALL_OF = "isAllOf"
    IS_NONE_OF = "isNoneOf"
    
    # Taxonomic (3) - Require semantic grounding
    IS_A = "isA"
    HAS_PART = "hasPart"
    IS_PART_OF = "isPartOf"
    
    # Logical composition (4)
    AND = "and"
    OR = "or"
    XONE = "xone"
    AND_SEQUENCE = "andSequence"


# =============================================================================
# OPERATOR SETS BY CATEGORY
# =============================================================================

RELATIONAL_OPERATORS: Set[Operator] = {
    Operator.EQ,
    Operator.NEQ,
    Operator.LT,
    Operator.LTEQ,
    Operator.GT,
    Operator.GTEQ,
}

SET_OPERATORS: Set[Operator] = {
    Operator.IS_ANY_OF,
    Operator.IS_ALL_OF,
    Operator.IS_NONE_OF,
}

TAXONOMIC_OPERATORS: Set[Operator] = {
    Operator.IS_A,
    Operator.HAS_PART,
    Operator.IS_PART_OF,
}

LOGICAL_OPERATORS: Set[Operator] = {
    Operator.AND,
    Operator.OR,
    Operator.XONE,
    Operator.AND_SEQUENCE,
}

# All constraint operators (excluding logical composition)
CONSTRAINT_OPERATORS: Set[Operator] = RELATIONAL_OPERATORS | SET_OPERATORS | TAXONOMIC_OPERATORS


# =============================================================================
# OPERATOR STRING MAPPING
# =============================================================================

OPERATOR_STRING_MAP: Dict[str, Operator] = {
    # Relational
    'eq': Operator.EQ,
    'neq': Operator.NEQ,
    'lt': Operator.LT,
    'lteq': Operator.LTEQ,
    'gt': Operator.GT,
    'gteq': Operator.GTEQ,
    
    # Set
    'isAnyOf': Operator.IS_ANY_OF,
    'isanyof': Operator.IS_ANY_OF,
    'isAllOf': Operator.IS_ALL_OF,
    'isallof': Operator.IS_ALL_OF,
    'isNoneOf': Operator.IS_NONE_OF,
    'isnoneof': Operator.IS_NONE_OF,
    
    # Taxonomic
    'isA': Operator.IS_A,
    'isa': Operator.IS_A,
    'hasPart': Operator.HAS_PART,
    'haspart': Operator.HAS_PART,
    'isPartOf': Operator.IS_PART_OF,
    'ispartof': Operator.IS_PART_OF,
    
    # Logical
    'and': Operator.AND,
    'or': Operator.OR,
    'xone': Operator.XONE,
    'andSequence': Operator.AND_SEQUENCE,
    'andsequence': Operator.AND_SEQUENCE,
}

# Reverse mapping
OPERATOR_TO_STRING: Dict[Operator, str] = {
    Operator.EQ: 'eq',
    Operator.NEQ: 'neq',
    Operator.LT: 'lt',
    Operator.LTEQ: 'lteq',
    Operator.GT: 'gt',
    Operator.GTEQ: 'gteq',
    Operator.IS_ANY_OF: 'isAnyOf',
    Operator.IS_ALL_OF: 'isAllOf',
    Operator.IS_NONE_OF: 'isNoneOf',
    Operator.IS_A: 'isA',
    Operator.HAS_PART: 'hasPart',
    Operator.IS_PART_OF: 'isPartOf',
    Operator.AND: 'and',
    Operator.OR: 'or',
    Operator.XONE: 'xone',
    Operator.AND_SEQUENCE: 'andSequence',
}


# =============================================================================
# OPERATOR SYMBOLS (for display)
# =============================================================================

OPERATOR_SYMBOLS: Dict[Operator, str] = {
    Operator.EQ: '=',
    Operator.NEQ: '≠',
    Operator.LT: '<',
    Operator.LTEQ: '≤',
    Operator.GT: '>',
    Operator.GTEQ: '≥',
    Operator.IS_ANY_OF: '∈',
    Operator.IS_ALL_OF: '⊇',
    Operator.IS_NONE_OF: '∉',
    Operator.IS_A: '⊑',
    Operator.HAS_PART: '⊃',
    Operator.IS_PART_OF: '⊂',
    Operator.AND: '∧',
    Operator.OR: '∨',
    Operator.XONE: '⊕',
    Operator.AND_SEQUENCE: '→',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_operator(op_string: str) -> Optional[Operator]:
    """
    Parse operator string to Operator enum.
    
    Args:
        op_string: Operator string (e.g., 'eq', 'isAnyOf', 'odrl:lt')
        
    Returns:
        Operator enum value, or None if not recognized
    """
    # Strip namespace prefix
    if ':' in op_string:
        op_string = op_string.split(':')[-1]
    if '/' in op_string:
        op_string = op_string.split('/')[-1]
    if '#' in op_string:
        op_string = op_string.split('#')[-1]
    
    return OPERATOR_STRING_MAP.get(op_string) or OPERATOR_STRING_MAP.get(op_string.lower())


def get_operator_type(op_string: str) -> Optional[Operator]:
    """Alias for parse_operator for backwards compatibility."""
    return parse_operator(op_string)


def get_operator_category(operator: Operator) -> OperatorCategory:
    """
    Get the category of an operator.
    
    Args:
        operator: Operator enum value
        
    Returns:
        OperatorCategory
    """
    if operator in RELATIONAL_OPERATORS:
        return OperatorCategory.RELATIONAL
    elif operator in SET_OPERATORS:
        return OperatorCategory.SET
    elif operator in TAXONOMIC_OPERATORS:
        return OperatorCategory.TAXONOMIC
    else:
        return OperatorCategory.LOGICAL


def is_relational_operator(operator: Operator) -> bool:
    """Check if operator is relational."""
    return operator in RELATIONAL_OPERATORS


def is_set_operator(operator: Operator) -> bool:
    """Check if operator is set-based."""
    return operator in SET_OPERATORS


def is_taxonomic_operator(operator: Operator) -> bool:
    """Check if operator is taxonomic (requires semantic grounding)."""
    return operator in TAXONOMIC_OPERATORS


def is_logical_operator(operator: Operator) -> bool:
    """Check if operator is logical composition."""
    return operator in LOGICAL_OPERATORS


def requires_semantic_grounding(operator: Operator) -> bool:
    """Check if operator requires semantic grounding."""
    return operator in TAXONOMIC_OPERATORS


# =============================================================================
# DOMAIN VALIDITY
# =============================================================================

# Which operators are valid for which operand domains
VALID_OPERATORS_BY_DOMAIN: Dict[str, Set[Operator]] = {
    'numeric': RELATIONAL_OPERATORS,
    'temporal': RELATIONAL_OPERATORS,
    'temporal_duration': RELATIONAL_OPERATORS,
    'positional_absolute': RELATIONAL_OPERATORS,
    'positional_relative': RELATIONAL_OPERATORS,
    'categorical': RELATIONAL_OPERATORS | SET_OPERATORS | TAXONOMIC_OPERATORS,
    'spatial': RELATIONAL_OPERATORS | TAXONOMIC_OPERATORS,
    'reference': RELATIONAL_OPERATORS | SET_OPERATORS,
    'version': RELATIONAL_OPERATORS,  # Partial order comparison
}


def get_valid_operators_for_domain(domain: str) -> Set[Operator]:
    """
    Get valid operators for an operand domain.
    
    Args:
        domain: Domain name (e.g., 'numeric', 'categorical')
        
    Returns:
        Set of valid operators for that domain
    """
    return VALID_OPERATORS_BY_DOMAIN.get(domain.lower(), RELATIONAL_OPERATORS)


def is_operator_valid_for_domain(operator: Operator, domain: str) -> bool:
    """
    Check if an operator is valid for a domain.
    
    Args:
        operator: The operator to check
        domain: The domain name
        
    Returns:
        True if operator is valid for domain
    """
    valid_ops = get_valid_operators_for_domain(domain)
    return operator in valid_ops


# =============================================================================
# Z3 ENCODING
# =============================================================================

def operator_to_z3(operator: Operator) -> str:
    """
    Get Z3 function name for an operator.
    
    Args:
        operator: Operator enum value
        
    Returns:
        Z3 function name as string
        
    Note:
        For set/taxonomic operators, returns placeholder that needs
        special handling in the encoder.
    """
    Z3_MAP = {
        Operator.EQ: '=',
        Operator.NEQ: 'distinct',
        Operator.LT: '<',
        Operator.LTEQ: '<=',
        Operator.GT: '>',
        Operator.GTEQ: '>=',
        Operator.AND: 'and',
        Operator.OR: 'or',
    }
    return Z3_MAP.get(operator, operator.value)


def get_z3_relational_func(operator: Operator) -> Optional[Callable]:
    """
    Get Z3 function for relational operator.
    
    Args:
        operator: Operator enum value
        
    Returns:
        Z3 function or None
        
    Note:
        Import z3 only when needed.
    """
    try:
        import z3
    except ImportError:
        return None
    
    FUNC_MAP = {
        Operator.EQ: lambda a, b: a == b,
        Operator.NEQ: lambda a, b: a != b,
        Operator.LT: lambda a, b: a < b,
        Operator.LTEQ: lambda a, b: a <= b,
        Operator.GT: lambda a, b: a > b,
        Operator.GTEQ: lambda a, b: a >= b,
    }
    return FUNC_MAP.get(operator)


# =============================================================================
# OPERATOR SEMANTICS (Formal definitions)
# =============================================================================

OPERATOR_SEMANTICS: Dict[Operator, str] = {
    # Relational
    Operator.EQ: "x = y",
    Operator.NEQ: "x ≠ y",
    Operator.LT: "x < y",
    Operator.LTEQ: "x ≤ y",
    Operator.GT: "x > y",
    Operator.GTEQ: "x ≥ y",
    
    # Set
    Operator.IS_ANY_OF: "x ∈ S (x is in set S)",
    Operator.IS_ALL_OF: "S ⊆ x (all elements of S are in x)",
    Operator.IS_NONE_OF: "x ∩ S = ∅ (x shares no elements with S)",
    
    # Taxonomic
    Operator.IS_A: "x ⊑ y (x is subsumed by y in hierarchy)",
    Operator.HAS_PART: "y ⊂ x (x contains y as part)",
    Operator.IS_PART_OF: "x ⊂ y (x is part of y)",
    
    # Logical
    Operator.AND: "⋀ᵢ cᵢ (all constraints hold)",
    Operator.OR: "⋁ᵢ cᵢ (at least one holds)",
    Operator.XONE: "Σᵢ ⟦cᵢ⟧ = 1 (exactly one holds)",
    Operator.AND_SEQUENCE: "∃ t₁ < t₂ < ... : c₁(t₁) ∧ c₂(t₂) ∧ ...",
}


def get_operator_semantics(operator: Operator) -> str:
    """Get formal semantics definition for an operator."""
    return OPERATOR_SEMANTICS.get(operator, "undefined")


# =============================================================================
# SMT-LIB ENCODING
# =============================================================================

def get_smtlib_operator(operator: Operator) -> str:
    """
    Get SMT-LIB syntax for operator.
    
    Args:
        operator: Operator enum value
        
    Returns:
        SMT-LIB operator string
    """
    SMTLIB_MAP = {
        Operator.EQ: '=',
        Operator.NEQ: 'distinct',
        Operator.LT: '<',
        Operator.LTEQ: '<=',
        Operator.GT: '>',
        Operator.GTEQ: '>=',
        Operator.AND: 'and',
        Operator.OR: 'or',
    }
    return SMTLIB_MAP.get(operator, operator.value)


def encode_relational_smtlib(var: str, operator: Operator, value: Any) -> str:
    """
    Encode relational constraint in SMT-LIB format.
    
    Args:
        var: Variable name
        operator: Relational operator
        value: Value to compare against
        
    Returns:
        SMT-LIB assertion string
    """
    op = get_smtlib_operator(operator)
    return f"({op} {var} {value})"


def encode_xone_smtlib(constraints: List[str]) -> str:
    """
    Encode XONE (exactly-one) constraint in SMT-LIB format.
    
    Args:
        constraints: List of constraint expression strings
        
    Returns:
        SMT-LIB assertion for exactly-one
    """
    # Convert each constraint to 0/1 indicator
    indicators = [f"(ite {c} 1 0)" for c in constraints]
    sum_expr = "(+ " + " ".join(indicators) + ")"
    return f"(= {sum_expr} 1)"