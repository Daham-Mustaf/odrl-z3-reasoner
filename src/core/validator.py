# src/core/validator.py
"""
ODRL Constraint Validator
Validates constraints against formal specifications:
- Operator validity per operand (Section 4)
- Domain bounds (Section 3)
- Type checking (Section 12)
- Unit comparability (Section 5) - CRITICAL FIX

Based on formal specifications for each LeftOperand.
NOTE: This module uses minimal imports to avoid circular dependencies.
"""
from typing import Tuple, Optional, Set, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# LOCAL OPERATOR TYPE ENUM (to avoid importing from constraint_types)
# =============================================================================

class OperatorType(Enum):
    """ODRL Operators - local copy to avoid circular imports."""
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTEQ = "lteq"
    GT = "gt"
    GTEQ = "gteq"
    IS_A = "isA"
    HAS_PART = "hasPart"
    IS_PART_OF = "isPartOf"
    IS_ALL_OF = "isAllOf"
    IS_ANY_OF = "isAnyOf"
    IS_NONE_OF = "isNoneOf"


# =============================================================================
# LEFTOPERAND CATEGORIES (from formal specification)
# =============================================================================

# LeftOperands that REQUIRE unit for comparability
# These yield UNKNOWN if unit is missing or mismatched
L_UNIT_REQUIRED: Set[str] = {
    "payAmount",
    "resolution",
    "absolutePosition",
    "absoluteSize",
}

# LeftOperands that use unitOfCount as optional scope
# Missing scope -> default (comparable)
# Different scopes -> UNKNOWN
L_SCOPE_DEPENDENT: Set[str] = {
    "count",
}

# Bounded equivalence class [0, 100]
L_BOUNDED: Set[str] = {
    "percentage",
    "relativePosition",
    "relativeSize",
    "relativeTemporalPosition",
    "relativeSpatialPosition",
}

# Integer LeftOperands
L_INT: Set[str] = {
    "count",
    "timeInterval",
}

# DateTime
L_DATETIME: Set[str] = {
    "dateTime",
}

# Real unbounded
L_REAL: Set[str] = {
    "absoluteTemporalPosition",
}

# Spatial coordinates (2D)
L_COORDS: Set[str] = {
    "absoluteSpatialPosition",
}

# Reference-dependent (partial support)
L_REF: Set[str] = {
    "elapsedTime",
    "delayPeriod",
}

# All fully analyzable LeftOperands
L_FULLY_ANALYZABLE: Set[str] = (
    L_BOUNDED | L_INT | L_DATETIME | L_UNIT_REQUIRED | L_REAL | L_COORDS
)


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """Result of constraint validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    @staticmethod
    def valid() -> 'ValidationResult':
        return ValidationResult(True, [], [])
    
    @staticmethod
    def invalid(error: str) -> 'ValidationResult':
        return ValidationResult(False, [error], [])
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)


@dataclass
class UnitComparabilityResult:
    """Result of unit comparability check."""
    comparable: bool
    reason: Optional[str] = None
    details: Optional[str] = None


# =============================================================================
# UNIT NORMALIZATION
# =============================================================================

def normalize_unit(unit: Optional[str]) -> Optional[str]:
    """
    Normalize unit IRI to canonical form.
    
    Examples:
        "http://qudt.org/vocab/unit/EUR" -> "EUR"
        "http://dbpedia.org/resource/Euro" -> "Euro"
        "EUR" -> "EUR"
    """
    if unit is None:
        return None
    
    # Extract last part of URI
    if '/' in unit:
        return unit.split('/')[-1]
    if '#' in unit:
        return unit.split('#')[-1]
    
    return unit


def normalize_operand(operand: str) -> str:
    """
    Normalize operand IRI to local name.
    
    Examples:
        "http://www.w3.org/ns/odrl/2/payAmount" -> "payAmount"
        "odrl:payAmount" -> "payAmount"
        "payAmount" -> "payAmount"
    """
    if '/' in operand:
        return operand.split('/')[-1]
    if '#' in operand:
        return operand.split('#')[-1]
    if ':' in operand:
        return operand.split(':')[-1]
    return operand


# =============================================================================
# OPERATOR VALIDITY (Section 4)
# =============================================================================

# Valid operators per operand
VALID_OPERATORS: Dict[str, Set[OperatorType]] = {
    # Bounded class: 9/12 valid
    'percentage': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'relativePosition': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'relativeSize': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'relativeTemporalPosition': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'relativeSpatialPosition': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # count: 9/12 valid
    'count': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # timeInterval: 1/12 valid (eq only)
    'timeInterval': {
        OperatorType.EQ,
    },
    
    # dateTime: 9/12 valid
    'dateTime': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # Unit-dependent: 9/12 valid
    'payAmount': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'resolution': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'absolutePosition': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    'absoluteSize': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # absoluteTemporalPosition: 9/12
    'absoluteTemporalPosition': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # absoluteSpatialPosition: 2/12 (eq, neq only - no ordering on 2D)
    'absoluteSpatialPosition': {
        OperatorType.EQ, OperatorType.NEQ,
    },
    
    # Reference-dependent
    'elapsedTime': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
    },
    'delayPeriod': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
    },
}

# Explicitly invalid operators per operand (with reason)
INVALID_OPERATORS: Dict[str, Dict[OperatorType, str]] = {
    'count': {
        OperatorType.IS_A: "No taxonomy for integers",
        OperatorType.HAS_PART: "Integers have no parts (no mereology)",
        OperatorType.IS_PART_OF: "Integers aren't parts (no mereology)",
    },
    'percentage': {
        OperatorType.IS_A: "No taxonomy for decimals",
        OperatorType.HAS_PART: "Decimals have no parts (no mereology)",
        OperatorType.IS_PART_OF: "Decimals aren't parts (no mereology)",
    },
    'payAmount': {
        OperatorType.IS_A: "No taxonomy for decimals",
        OperatorType.HAS_PART: "No mereology for monetary values",
        OperatorType.IS_PART_OF: "No mereology for monetary values",
    },
    'timeInterval': {
        OperatorType.NEQ: "Only eq operator is meaningful for recurring intervals",
        OperatorType.LT: "Only eq operator is meaningful for recurring intervals",
        OperatorType.LTEQ: "Only eq operator is meaningful for recurring intervals",
        OperatorType.GT: "Only eq operator is meaningful for recurring intervals",
        OperatorType.GTEQ: "Only eq operator is meaningful for recurring intervals",
        OperatorType.IS_A: "No taxonomy for durations",
        OperatorType.HAS_PART: "No mereology for durations",
        OperatorType.IS_PART_OF: "No mereology for durations",
    },
    'absoluteSpatialPosition': {
        OperatorType.LT: "No ordering on 2D coordinates",
        OperatorType.LTEQ: "No ordering on 2D coordinates",
        OperatorType.GT: "No ordering on 2D coordinates",
        OperatorType.GTEQ: "No ordering on 2D coordinates",
        OperatorType.IS_A: "No taxonomy for coordinates",
        OperatorType.HAS_PART: "No mereology for coordinates",
        OperatorType.IS_PART_OF: "No mereology for coordinates",
    },
}


# =============================================================================
# DOMAIN BOUNDS (Section 3)
# =============================================================================

@dataclass
class DomainSpec:
    """Domain specification for an operand."""
    min_val: Optional[float]  # None = negative infinity
    max_val: Optional[float]  # None = positive infinity
    is_integer: bool
    closed_min: bool = True   # inclusive lower bound
    closed_max: bool = True   # inclusive upper bound


DOMAIN_SPECS: Dict[str, DomainSpec] = {
    # Bounded [0, 100]
    'percentage': DomainSpec(min_val=0, max_val=100, is_integer=False),
    'relativePosition': DomainSpec(min_val=0, max_val=100, is_integer=False),
    'relativeSize': DomainSpec(min_val=0, max_val=None, is_integer=False),
    'relativeTemporalPosition': DomainSpec(min_val=0, max_val=100, is_integer=False),
    'relativeSpatialPosition': DomainSpec(min_val=0, max_val=100, is_integer=False),
    
    # Integer unbounded
    'count': DomainSpec(min_val=0, max_val=None, is_integer=True),
    'timeInterval': DomainSpec(min_val=1, max_val=None, is_integer=True),  # min=1, not 0
    
    # DateTime (any timestamp)
    'dateTime': DomainSpec(min_val=None, max_val=None, is_integer=True),
    
    # Unit-dependent
    'payAmount': DomainSpec(min_val=0, max_val=None, is_integer=False),
    'resolution': DomainSpec(min_val=0, max_val=None, is_integer=False, closed_min=False),  # > 0
    'absolutePosition': DomainSpec(min_val=0, max_val=None, is_integer=False),
    'absoluteSize': DomainSpec(min_val=0, max_val=None, is_integer=False, closed_min=False),  # > 0
    
    # Real unbounded
    'absoluteTemporalPosition': DomainSpec(min_val=0, max_val=None, is_integer=False),
    'absoluteSpatialPosition': DomainSpec(min_val=0, max_val=None, is_integer=False),
    
    # Reference-dependent
    'elapsedTime': DomainSpec(min_val=0, max_val=None, is_integer=True),
    'delayPeriod': DomainSpec(min_val=0, max_val=None, is_integer=True),
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_operator(operand: str, operator: OperatorType) -> ValidationResult:
    """
    Validate that operator is valid for operand.
    
    Section 4: Valid Operators
    """
    result = ValidationResult.valid()
    op_name = normalize_operand(operand)
    
    # Check if explicitly invalid
    if op_name in INVALID_OPERATORS:
        if operator in INVALID_OPERATORS[op_name]:
            reason = INVALID_OPERATORS[op_name][operator]
            result.add_error(f"Operator '{operator.value}' invalid for '{op_name}': {reason}")
            return result
    
    # Check if in valid set (if defined)
    if op_name in VALID_OPERATORS:
        if operator not in VALID_OPERATORS[op_name]:
            result.add_warning(f"Operator '{operator.value}' may not be meaningful for '{op_name}'")
    
    return result


def validate_domain(operand: str, value: Any) -> ValidationResult:
    """
    Validate that value is within domain bounds.
    
    Section 3: Domain Specification
    Section 12: Validation Rules V1, V2
    """
    result = ValidationResult.valid()
    op_name = normalize_operand(operand)
    
    if op_name not in DOMAIN_SPECS:
        return result  # Unknown operand - skip validation
    
    spec = DOMAIN_SPECS[op_name]
    
    # Try to convert to numeric
    try:
        if isinstance(value, (list, tuple)):
            values = value
        else:
            values = [value]
        
        for v in values:
            num_val = float(v)
            
            # Check lower bound
            if spec.min_val is not None:
                if spec.closed_min and num_val < spec.min_val:
                    result.add_error(
                        f"Domain violation: {op_name} value {v} < {spec.min_val}"
                    )
                elif not spec.closed_min and num_val <= spec.min_val:
                    result.add_error(
                        f"Domain violation: {op_name} value {v} <= {spec.min_val}"
                    )
            
            # Check upper bound
            if spec.max_val is not None:
                if spec.closed_max and num_val > spec.max_val:
                    result.add_error(
                        f"Domain violation: {op_name} value {v} > {spec.max_val}"
                    )
                elif not spec.closed_max and num_val >= spec.max_val:
                    result.add_error(
                        f"Domain violation: {op_name} value {v} >= {spec.max_val}"
                    )
            
            # Check integer constraint
            if spec.is_integer and num_val != int(num_val):
                result.add_warning(
                    f"Type warning: {op_name} expects integer, got {v}"
                )
    
    except (ValueError, TypeError):
        # Cannot validate non-numeric value
        pass
    
    return result


def validate_constraint(operand: str, operator: str, value: Any) -> ValidationResult:
    """
    Validate a constraint against formal specification.
    
    Args:
        operand: Left operand name (e.g., 'count', 'percentage')
        operator: Operator string (e.g., 'eq', 'lteq')
        value: Right operand value
    
    Checks:
    1. Operator validity (Section 4)
    2. Domain bounds (Section 3, 12)
    """
    result = ValidationResult.valid()
    
    # Convert operator string to enum
    try:
        op_enum = OperatorType(operator)
    except ValueError:
        result.add_error(f"Unknown operator: {operator}")
        return result
    
    # Validate operator
    op_result = validate_operator(operand, op_enum)
    result.errors.extend(op_result.errors)
    result.warnings.extend(op_result.warnings)
    if not op_result.is_valid:
        result.is_valid = False
    
    # Validate domain
    domain_result = validate_domain(operand, value)
    result.errors.extend(domain_result.errors)
    result.warnings.extend(domain_result.warnings)
    if not domain_result.is_valid:
        result.is_valid = False
    
    return result


def validate_constraint_object(constraint) -> ValidationResult:
    """
    Validate an AtomicConstraint object.
    
    This version accepts an AtomicConstraint-like object with:
    - left_operand: str
    - operator: OperatorType (or has .value attribute)
    - right_operand: has .value attribute
    """
    operand = constraint.left_operand
    
    # Handle operator (might be enum or have .value)
    if hasattr(constraint.operator, 'value'):
        operator = constraint.operator.value
    else:
        operator = str(constraint.operator)
    
    # Handle value
    if hasattr(constraint.right_operand, 'value'):
        value = constraint.right_operand.value
    else:
        value = constraint.right_operand
    
    return validate_constraint(operand, operator, value)


# =============================================================================
# UNIT COMPARABILITY (Section 5) - CRITICAL FIX
# =============================================================================

def check_unit_comparability(
    c1_operand: str, c1_unit: Optional[str],
    c2_operand: str, c2_unit: Optional[str]
) -> UnitComparabilityResult:
    """
    Check if two constraints are comparable based on units.
    
    Section 5: Unit Handling
    
    Rules:
    1. For L_UNIT_REQUIRED (payAmount, resolution, absolutePosition, absoluteSize):
       - Unit is REQUIRED
       - Missing unit -> UNKNOWN (NOT comparable)
       - Different units -> UNKNOWN (NOT comparable)
       
    2. For L_SCOPE_DEPENDENT (count):
       - unitOfCount is optional scope
       - Missing scope -> comparable (default scope)
       - Different scopes -> UNKNOWN
       - Same scope -> comparable
       
    3. For other operands:
       - Units are not relevant
    
    Args:
        c1_operand: First constraint's left operand
        c1_unit: First constraint's unit (or None)
        c2_operand: Second constraint's left operand
        c2_unit: Second constraint's unit (or None)
        
    Returns:
        UnitComparabilityResult with comparable flag and reason if not
    """
    # Normalize operand names
    op1 = normalize_operand(c1_operand)
    op2 = normalize_operand(c2_operand)
    
    # Must be same operand
    if op1 != op2:
        return UnitComparabilityResult(
            comparable=False,
            reason="DIFFERENT_OPERAND",
            details=f"Cannot compare {op1} with {op2}"
        )
    
    operand = op1
    
    # =========================================================================
    # Case 1: Unit-required operands (payAmount, resolution, etc.)
    # CRITICAL: Missing or different units -> UNKNOWN
    # =========================================================================
    if operand in L_UNIT_REQUIRED:
        # Both must have units
        if c1_unit is None and c2_unit is None:
            return UnitComparabilityResult(
                comparable=False,
                reason="MISSING_REQUIRED_UNIT",
                details=f"{operand} requires unit for comparison but both constraints lack units"
            )
        
        if c1_unit is None:
            return UnitComparabilityResult(
                comparable=False,
                reason="MISSING_REQUIRED_UNIT",
                details=f"{operand} requires unit but first constraint has no unit"
            )
        
        if c2_unit is None:
            return UnitComparabilityResult(
                comparable=False,
                reason="MISSING_REQUIRED_UNIT",
                details=f"{operand} requires unit but second constraint has no unit"
            )
        
        # Normalize units for comparison
        unit1 = normalize_unit(c1_unit)
        unit2 = normalize_unit(c2_unit)
        
        if unit1 != unit2:
            return UnitComparabilityResult(
                comparable=False,
                reason="UNIT_MISMATCH",
                details=f"Cannot compare {operand} with different units: {unit1} vs {unit2}"
            )
        
        # Same unit - comparable
        return UnitComparabilityResult(comparable=True)
    
    # =========================================================================
    # Case 2: Scope-dependent operands (count)
    # Missing scope -> default (comparable)
    # Different scopes -> UNKNOWN
    # =========================================================================
    if operand in L_SCOPE_DEPENDENT:
        # Both unspecified - comparable (default scope)
        if c1_unit is None and c2_unit is None:
            return UnitComparabilityResult(comparable=True)
        
        # One unspecified - comparable (default matches any)
        if c1_unit is None or c2_unit is None:
            return UnitComparabilityResult(comparable=True)
        
        # Both specified - must match
        scope1 = normalize_unit(c1_unit)
        scope2 = normalize_unit(c2_unit)
        
        if scope1 != scope2:
            return UnitComparabilityResult(
                comparable=False,
                reason="SCOPE_MISMATCH",
                details=f"Cannot compare {operand} with different scopes: {scope1} vs {scope2}"
            )
        
        return UnitComparabilityResult(comparable=True)
    
    # =========================================================================
    # Case 3: Other operands - units not relevant
    # =========================================================================
    return UnitComparabilityResult(comparable=True)


# =============================================================================
# RULE-LEVEL UNIT VALIDATION
# =============================================================================

@dataclass
class RuleUnitValidationResult:
    """Result of unit validation for a set of constraints in a rule."""
    is_valid: bool
    reason: Optional[str] = None
    details: Optional[str] = None
    incomparable_constraints: Optional[List[str]] = None


def validate_rule_units(constraints: List[Any]) -> RuleUnitValidationResult:
    """
    Validate that all constraints in a rule are mutually comparable.
    
    This function checks unit comparability for all constraints on the same
    LeftOperand within a rule. If any pair is incomparable, returns UNKNOWN.
    
    Args:
        constraints: List of constraint objects with left_operand and unit attributes
        
    Returns:
        RuleUnitValidationResult indicating if all constraints are comparable
    """
    # Group constraints by normalized operand
    by_operand: Dict[str, List[Any]] = {}
    
    for c in constraints:
        # Get operand name
        if hasattr(c, 'left_operand'):
            op = normalize_operand(c.left_operand)
        else:
            continue
            
        if op not in by_operand:
            by_operand[op] = []
        by_operand[op].append(c)
    
    # Check each operand group
    for operand, cs in by_operand.items():
        if len(cs) < 2:
            continue  # Single constraint, no comparison needed within rule
        
        # =====================================================================
        # Check unit-required operands
        # =====================================================================
        if operand in L_UNIT_REQUIRED:
            units = []
            missing_unit_constraints = []
            
            for c in cs:
                unit = getattr(c, 'unit', None)
                if unit is None:
                    uid = getattr(c, 'uid', str(c))
                    missing_unit_constraints.append(uid)
                else:
                    units.append(normalize_unit(unit))
            
            # Check for missing units
            if missing_unit_constraints:
                return RuleUnitValidationResult(
                    is_valid=False,
                    reason="MISSING_REQUIRED_UNIT",
                    details=f"{operand} requires unit but constraint(s) have none",
                    incomparable_constraints=missing_unit_constraints
                )
            
            # Check all units are the same
            unique_units = set(units)
            if len(unique_units) > 1:
                return RuleUnitValidationResult(
                    is_valid=False,
                    reason="UNIT_MISMATCH",
                    details=f"{operand} has mixed units: {unique_units}",
                    incomparable_constraints=[getattr(c, 'uid', str(c)) for c in cs]
                )
        
        # =====================================================================
        # Check scope-dependent operands
        # =====================================================================
        elif operand in L_SCOPE_DEPENDENT:
            scopes = []
            for c in cs:
                # Check both unit_of_count and unit attributes
                scope = getattr(c, 'unit_of_count', None) or getattr(c, 'unit', None)
                if scope is not None:
                    scopes.append(normalize_unit(scope))
            
            # If any scopes specified, all specified ones must match
            if scopes:
                unique_scopes = set(scopes)
                if len(unique_scopes) > 1:
                    return RuleUnitValidationResult(
                        is_valid=False,
                        reason="SCOPE_MISMATCH",
                        details=f"{operand} has mixed scopes: {unique_scopes}",
                        incomparable_constraints=[getattr(c, 'uid', str(c)) for c in cs]
                    )
    
    # All checks passed
    return RuleUnitValidationResult(is_valid=True)


# =============================================================================
# CONVENIENCE FUNCTION FOR PAIRWISE CHECK
# =============================================================================

def are_constraints_comparable(c1: Any, c2: Any) -> UnitComparabilityResult:
    """
    Check if two constraint objects are comparable.
    
    Convenience wrapper around check_unit_comparability that extracts
    operand and unit from constraint objects.
    
    Args:
        c1: First constraint object
        c2: Second constraint object
        
    Returns:
        UnitComparabilityResult
    """
    op1 = getattr(c1, 'left_operand', '')
    op2 = getattr(c2, 'left_operand', '')
    unit1 = getattr(c1, 'unit', None)
    unit2 = getattr(c2, 'unit', None)
    
    return check_unit_comparability(op1, unit1, op2, unit2)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Constraint Validator Tests")
    print("=" * 60)
    
    # Test operator validation
    print("\n--- Operator Validation ---")
    
    tests = [
        ('count', OperatorType.EQ, True),
        ('count', OperatorType.IS_A, False),
        ('count', OperatorType.HAS_PART, False),
        ('percentage', OperatorType.LTEQ, True),
        ('percentage', OperatorType.IS_PART_OF, False),
        ('dateTime', OperatorType.GT, True),
        ('timeInterval', OperatorType.EQ, True),
        ('timeInterval', OperatorType.LT, False),
        ('absoluteSpatialPosition', OperatorType.EQ, True),
        ('absoluteSpatialPosition', OperatorType.LT, False),
    ]
    
    for operand, op, expected_valid in tests:
        result = validate_operator(operand, op)
        status = "PASS" if result.is_valid == expected_valid else "FAIL"
        valid_str = "valid" if result.is_valid else "invalid"
        print(f"[{status}] {operand} + {op.value}: {valid_str}")
        if result.errors:
            print(f"       Errors: {result.errors}")
        if result.warnings:
            print(f"       Warnings: {result.warnings}")
    
    # Test domain validation
    print("\n--- Domain Validation ---")
    
    domain_tests = [
        ('count', 5, True),
        ('count', -1, False),
        ('percentage', 50, True),
        ('percentage', -10, False),
        ('percentage', 150, False),
        ('payAmount', 100.50, True),
        ('payAmount', -50, False),
        ('timeInterval', 86400, True),
        ('timeInterval', 0, False),  # min is 1
    ]
    
    for operand, value, expected_valid in domain_tests:
        result = validate_domain(operand, value)
        status = "PASS" if result.is_valid == expected_valid else "FAIL"
        valid_str = "valid" if result.is_valid else "invalid"
        print(f"[{status}] {operand} = {value}: {valid_str}")
        if result.errors:
            print(f"       Errors: {result.errors}")
    
    # Test unit comparability
    print("\n--- Unit Comparability (CRITICAL) ---")
    
    unit_tests = [
        # (op1, unit1, op2, unit2, expected_comparable, description)
        ('payAmount', 'EUR', 'payAmount', 'EUR', True, "Same currency"),
        ('payAmount', 'EUR', 'payAmount', 'USD', False, "Different currency"),
        ('payAmount', 'EUR', 'payAmount', None, False, "Missing unit (one)"),
        ('payAmount', None, 'payAmount', None, False, "Missing unit (both)"),
        ('count', 'perUser', 'count', 'perUser', True, "Same scope"),
        ('count', 'perUser', 'count', 'perDevice', False, "Different scope"),
        ('count', 'perUser', 'count', None, True, "Missing scope (one) - OK"),
        ('count', None, 'count', None, True, "Missing scope (both) - OK"),
        ('percentage', None, 'percentage', None, True, "No unit needed"),
        ('resolution', 'DPI', 'resolution', 'PPI', False, "Different unit"),
    ]
    
    for op1, u1, op2, u2, expected, desc in unit_tests:
        result = check_unit_comparability(op1, u1, op2, u2)
        status = "PASS" if result.comparable == expected else "FAIL"
        comp_str = "comparable" if result.comparable else "NOT comparable"
        print(f"[{status}] {desc}: {comp_str}")
        if result.reason:
            print(f"       Reason: {result.reason}")
        if result.details:
            print(f"       Details: {result.details}")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)