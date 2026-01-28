# src/core/validator.py
"""
ODRL Constraint Validator

Validates constraints against formal specifications:
- Operator validity per operand (Section 4)
- Domain bounds (Section 3)
- Type checking (Section 12)

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
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """Result of constraint validation."""
    is_valid: bool
    errors: list
    warnings: list
    
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


# =============================================================================
# OPERATOR VALIDITY (Section 4)
# =============================================================================

# Valid operators per operand
VALID_OPERATORS: Dict[str, Set[OperatorType]] = {
    # count: 9/12 valid (Section 4)
    'count': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # percentage: 9/12 valid (Section 4)
    'percentage': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # payAmount: same as count/percentage
    'payAmount': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
        OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF,
    },
    
    # dateTime: comparison operators only
    'dateTime': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
    },
    
    # elapsedTime: comparison operators
    'elapsedTime': {
        OperatorType.EQ, OperatorType.NEQ,
        OperatorType.LT, OperatorType.LTEQ,
        OperatorType.GT, OperatorType.GTEQ,
    },
    
    # delayPeriod: comparison operators
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
    'dateTime': {
        OperatorType.IS_A: "No taxonomy for datetime",
        OperatorType.HAS_PART: "No mereology for datetime",
        OperatorType.IS_PART_OF: "No mereology for datetime",
        OperatorType.IS_ANY_OF: "Set operators not meaningful for datetime",
        OperatorType.IS_NONE_OF: "Set operators not meaningful for datetime",
        OperatorType.IS_ALL_OF: "Set operators not meaningful for datetime",
    },
}


# =============================================================================
# DOMAIN BOUNDS (Section 3)
# =============================================================================

@dataclass
class DomainSpec:
    """Domain specification for an operand."""
    min_val: Optional[float]  # None = -∞
    max_val: Optional[float]  # None = +∞
    is_integer: bool
    closed_min: bool = True  # inclusive lower bound
    closed_max: bool = True  # inclusive upper bound


DOMAIN_SPECS: Dict[str, DomainSpec] = {
    # count: ℤ≥0 = [0, +∞)
    'count': DomainSpec(min_val=0, max_val=None, is_integer=True),
    
    # percentage: [0, 100] ⊂ ℚ
    'percentage': DomainSpec(min_val=0, max_val=100, is_integer=False),
    
    # payAmount: [0, +∞) ⊂ ℚ
    'payAmount': DomainSpec(min_val=0, max_val=None, is_integer=False),
    
    # dateTime: any timestamp
    'dateTime': DomainSpec(min_val=None, max_val=None, is_integer=True),
    
    # elapsedTime: [0, +∞) seconds
    'elapsedTime': DomainSpec(min_val=0, max_val=None, is_integer=True),
    
    # delayPeriod: [0, +∞) seconds
    'delayPeriod': DomainSpec(min_val=0, max_val=None, is_integer=True),
    
    # relativePosition: [0, 100]
    'relativePosition': DomainSpec(min_val=0, max_val=100, is_integer=False),
    
    # relativeSize: [0, 100]
    'relativeSize': DomainSpec(min_val=0, max_val=100, is_integer=False),
    
    # absoluteSize: [0, +∞)
    'absoluteSize': DomainSpec(min_val=0, max_val=None, is_integer=False),
    
    # resolution: [0, +∞)
    'resolution': DomainSpec(min_val=0, max_val=None, is_integer=False),
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
    
    # Check if explicitly invalid
    if operand in INVALID_OPERATORS:
        if operator in INVALID_OPERATORS[operand]:
            reason = INVALID_OPERATORS[operand][operator]
            result.add_error(f"Operator '{operator.value}' invalid for '{operand}': {reason}")
            return result
    
    # Check if in valid set (if defined)
    if operand in VALID_OPERATORS:
        if operator not in VALID_OPERATORS[operand]:
            result.add_warning(f"Operator '{operator.value}' may not be meaningful for '{operand}'")
    
    return result


def validate_domain(operand: str, value: Any) -> ValidationResult:
    """
    Validate that value is within domain bounds.
    
    Section 3: Domain Specification
    Section 12: Validation Rules V1, V2
    """
    result = ValidationResult.valid()
    
    if operand not in DOMAIN_SPECS:
        return result  # Unknown operand - skip validation
    
    spec = DOMAIN_SPECS[operand]
    
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
                        f"Domain violation: {operand} value {v} < {spec.min_val}"
                    )
                elif not spec.closed_min and num_val <= spec.min_val:
                    result.add_error(
                        f"Domain violation: {operand} value {v} <= {spec.min_val}"
                    )
            
            # Check upper bound
            if spec.max_val is not None:
                if spec.closed_max and num_val > spec.max_val:
                    result.add_error(
                        f"Domain violation: {operand} value {v} > {spec.max_val}"
                    )
                elif not spec.closed_max and num_val >= spec.max_val:
                    result.add_error(
                        f"Domain violation: {operand} value {v} >= {spec.max_val}"
                    )
            
            # Check integer constraint
            if spec.is_integer and num_val != int(num_val):
                result.add_warning(
                    f"Type warning: {operand} expects integer, got {v}"
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
# UNIT COMPARABILITY (Section 5)
# =============================================================================

def check_unit_comparability(
    c1_operand: str, c1_unit: Optional[str],
    c2_operand: str, c2_unit: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Check if two constraints are comparable based on units.
    
    Section 5: Unit Handling
    
    Two constraints are comparable iff:
    - unitOfCount(c1) = unitOfCount(c2), OR
    - unitOfCount(c1) = ⊥ (None), OR
    - unitOfCount(c2) = ⊥ (None)
    
    Args:
        c1_operand: First constraint's left operand
        c1_unit: First constraint's unit (or None)
        c2_operand: Second constraint's left operand
        c2_unit: Second constraint's unit (or None)
    """
    # Must be same operand
    if c1_operand != c2_operand:
        return False, f"Different operands: {c1_operand} vs {c2_operand}"
    
    # Only applies to certain operands
    unit_operands = {'count', 'payAmount'}
    
    if c1_operand not in unit_operands:
        return True, None
    
    # Both unspecified - comparable
    if c1_unit is None and c2_unit is None:
        return True, None
    
    # One unspecified - comparable
    if c1_unit is None or c2_unit is None:
        return True, None
    
    # Both specified - must match
    if c1_unit != c2_unit:
        return False, f"Different units: {c1_unit} vs {c2_unit}"
    
    return True, None


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
        ('count', OperatorType.EQ, "✅"),
        ('count', OperatorType.IS_A, "❌"),
        ('count', OperatorType.HAS_PART, "❌"),
        ('percentage', OperatorType.LTEQ, "✅"),
        ('percentage', OperatorType.IS_PART_OF, "❌"),
        ('dateTime', OperatorType.GT, "✅"),
        ('dateTime', OperatorType.IS_ANY_OF, "⚠️"),
    ]
    
    for operand, op, expected in tests:
        result = validate_operator(operand, op)
        status = "✅" if result.is_valid else "❌"
        print(f"{expected} {operand} + {op.value}: {status}")
        if result.errors:
            print(f"   Errors: {result.errors}")
        if result.warnings:
            print(f"   Warnings: {result.warnings}")
    
    # Test domain validation
    print("\n--- Domain Validation ---")
    
    domain_tests = [
        ('count', 5, "✅"),
        ('count', -1, "❌"),
        ('percentage', 50, "✅"),
        ('percentage', -10, "❌"),
        ('percentage', 150, "❌"),
        ('payAmount', 100.50, "✅"),
        ('payAmount', -50, "❌"),
    ]
    
    for operand, value, expected in domain_tests:
        result = validate_domain(operand, value)
        status = "✅" if result.is_valid else "❌"
        print(f"{expected} {operand} = {value}: {status}")
        if result.errors:
            print(f"   Errors: {result.errors}")
    
    print("\n" + "=" * 60)