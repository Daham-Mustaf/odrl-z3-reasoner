# src/semantics/validator.py
"""
Constraint Validation for ODRL Policies

Provides validation of constraints before encoding:
- Domain bounds checking
- Operator validity for operand type
- Unit compatibility checking
- Grounding requirement warnings

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union
from enum import Enum

from .operand_registry import get_operand_info, OperandInfo
from .grounding import get_grounding_requirement, GroundingRequirement, get_analysis_capability, AnalysisCapability
from .domains import get_domain_bounds, validate_value_in_domain, DomainBounds
from .operators import parse_operator, get_valid_operators_for_domain, is_operator_valid_for_domain, Operator
from .units import are_units_compatible, check_unit_compatibility, UnitIncompatibleError


class ValidationSeverity(Enum):
    """Severity levels for validation messages"""
    ERROR = "error"         # Cannot proceed
    WARNING = "warning"     # Can proceed but may have issues
    INFO = "info"          # Informational


@dataclass
class ValidationMessage:
    """
    A validation message.
    
    Attributes:
        severity: Error, warning, or info
        code: Machine-readable error code
        message: Human-readable message
        location: Where the issue occurred
        suggestion: How to fix the issue
    """
    severity: ValidationSeverity
    code: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [f"[{self.severity.value.upper()}] {self.code}: {self.message}"]
        if self.location:
            parts.append(f"  Location: {self.location}")
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return '\n'.join(parts)


@dataclass
class ValidationResult:
    """
    Result of validation.
    
    Attributes:
        is_valid: Whether validation passed (no errors)
        messages: List of validation messages
        warnings_count: Number of warnings
        errors_count: Number of errors
    """
    messages: List[ValidationMessage] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)"""
        return not any(m.severity == ValidationSeverity.ERROR for m in self.messages)
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return any(m.severity == ValidationSeverity.WARNING for m in self.messages)
    
    @property
    def errors_count(self) -> int:
        """Count of errors"""
        return sum(1 for m in self.messages if m.severity == ValidationSeverity.ERROR)
    
    @property
    def warnings_count(self) -> int:
        """Count of warnings"""
        return sum(1 for m in self.messages if m.severity == ValidationSeverity.WARNING)
    
    def add_error(self, code: str, message: str, location: str = None, suggestion: str = None):
        """Add an error message"""
        self.messages.append(ValidationMessage(
            severity=ValidationSeverity.ERROR,
            code=code,
            message=message,
            location=location,
            suggestion=suggestion
        ))
    
    def add_warning(self, code: str, message: str, location: str = None, suggestion: str = None):
        """Add a warning message"""
        self.messages.append(ValidationMessage(
            severity=ValidationSeverity.WARNING,
            code=code,
            message=message,
            location=location,
            suggestion=suggestion
        ))
    
    def add_info(self, code: str, message: str, location: str = None, suggestion: str = None):
        """Add an info message"""
        self.messages.append(ValidationMessage(
            severity=ValidationSeverity.INFO,
            code=code,
            message=message,
            location=location,
            suggestion=suggestion
        ))
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one"""
        self.messages.extend(other.messages)
    
    def __str__(self) -> str:
        if not self.messages:
            return "Validation passed with no issues"
        
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}:"]
        lines.append(f"  Errors: {self.errors_count}, Warnings: {self.warnings_count}")
        for msg in self.messages:
            lines.append(str(msg))
        return '\n'.join(lines)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_operand(operand: str) -> ValidationResult:
    """
    Validate an operand name.
    
    Args:
        operand: Operand name
        
    Returns:
        ValidationResult
    """
    result = ValidationResult()
    
    info = get_operand_info(operand)
    
    if info is None:
        result.add_warning(
            code="UNKNOWN_OPERAND",
            message=f"Unknown operand '{operand}'",
            suggestion="Check ODRL vocabulary for valid leftOperand values"
        )
    else:
        # Check grounding requirement
        grounding = get_grounding_requirement(operand)
        
        if grounding == GroundingRequirement.SEMANTIC:
            result.add_warning(
                code="SEMANTIC_GROUNDING_REQUIRED",
                message=f"Operand '{operand}' requires semantic grounding",
                suggestion=f"External KB needed: {info.external_kb or 'unknown'}"
            )
        elif grounding == GroundingRequirement.RUNTIME_ONLY:
            result.add_warning(
                code="RUNTIME_ONLY",
                message=f"Operand '{operand}' cannot be statically analyzed",
                suggestion="This constraint will be skipped in static analysis"
            )
    
    return result


def validate_operator_for_operand(operator: str, operand: str) -> ValidationResult:
    """
    Validate that an operator is valid for an operand.
    
    Args:
        operator: Operator string
        operand: Operand name
        
    Returns:
        ValidationResult
    """
    result = ValidationResult()
    
    # Parse operator
    parsed_op = parse_operator(operator)
    if parsed_op is None:
        result.add_error(
            code="UNKNOWN_OPERATOR",
            message=f"Unknown operator '{operator}'",
            suggestion="Valid operators: eq, neq, lt, lteq, gt, gteq, isAnyOf, isAllOf, isNoneOf, isA, hasPart, isPartOf"
        )
        return result
    
    # Get operand info
    info = get_operand_info(operand)
    if info is None:
        # Already warned about in validate_operand
        return result
    
    # Check operator validity for domain
    domain = info.category.value
    if not is_operator_valid_for_domain(parsed_op, domain):
        valid_ops = get_valid_operators_for_domain(domain)
        result.add_error(
            code="INVALID_OPERATOR_FOR_DOMAIN",
            message=f"Operator '{operator}' is not valid for operand '{operand}' (domain: {domain})",
            suggestion=f"Valid operators for {domain}: {', '.join(op.value for op in valid_ops)}"
        )
    
    return result


def validate_value_for_operand(
    value: Union[int, float, str],
    operand: str
) -> ValidationResult:
    """
    Validate that a value is valid for an operand.
    
    Args:
        value: The value to validate
        operand: Operand name
        
    Returns:
        ValidationResult
    """
    result = ValidationResult()
    
    # Get operand info
    info = get_operand_info(operand)
    if info is None:
        return result  # Already warned
    
    # Check domain bounds for numeric values
    if isinstance(value, (int, float)):
        is_valid, error_msg = validate_value_in_domain(operand, value)
        if not is_valid:
            bounds = get_domain_bounds(operand)
            result.add_error(
                code="VALUE_OUT_OF_DOMAIN",
                message=error_msg,
                suggestion=f"Valid range for {operand}: {bounds}"
            )
    
    return result


def validate_unit_compatibility(
    unit1: Optional[str],
    unit2: Optional[str],
    context: str = ""
) -> ValidationResult:
    """
    Validate that two units are compatible.
    
    Args:
        unit1: First unit
        unit2: Second unit
        context: Context for error message
        
    Returns:
        ValidationResult
    """
    result = ValidationResult()
    
    is_compatible, warning = check_unit_compatibility(unit1, unit2)
    
    if not is_compatible:
        result.add_warning(
            code="UNIT_INCOMPATIBLE",
            message=warning,
            location=context,
            suggestion="Constraints with different units cannot be compared for conflicts"
        )
    
    return result


def validate_constraint(
    operand: str,
    operator: str,
    value: Any,
    unit: Optional[str] = None
) -> ValidationResult:
    """
    Validate a complete constraint.
    
    Args:
        operand: LeftOperand name
        operator: Operator string
        value: RightOperand value
        unit: Optional unit
        
    Returns:
        ValidationResult with all validation messages
    """
    result = ValidationResult()
    
    # Validate operand
    result.merge(validate_operand(operand))
    
    # Validate operator for operand
    result.merge(validate_operator_for_operand(operator, operand))
    
    # Validate value
    result.merge(validate_value_for_operand(value, operand))
    
    # Check if unit is required
    info = get_operand_info(operand)
    if info and info.unit_required and unit is None:
        result.add_warning(
            code="UNIT_REQUIRED",
            message=f"Operand '{operand}' requires a unit but none was provided",
            suggestion="Specify a unit (e.g., currency for payAmount, DPI/PPI for resolution)"
        )
    
    return result


# =============================================================================
# POLICY-LEVEL VALIDATION
# =============================================================================

def validate_constraint_pair_compatibility(
    c1_operand: str,
    c1_operator: str,
    c1_value: Any,
    c1_unit: Optional[str],
    c2_operand: str,
    c2_operator: str,
    c2_value: Any,
    c2_unit: Optional[str]
) -> ValidationResult:
    """
    Validate that two constraints can be compared.
    
    Args:
        c1_*: First constraint components
        c2_*: Second constraint components
        
    Returns:
        ValidationResult indicating if constraints can be compared
    """
    result = ValidationResult()
    
    # Different operands - cannot compare
    if c1_operand != c2_operand:
        result.add_info(
            code="DIFFERENT_OPERANDS",
            message=f"Constraints on different operands ({c1_operand} vs {c2_operand})"
        )
        return result
    
    # Check unit compatibility
    result.merge(validate_unit_compatibility(
        c1_unit, c2_unit,
        context=f"Comparing {c1_operand} constraints"
    ))
    
    # Check grounding
    cap = get_analysis_capability(c1_operand)
    if cap == AnalysisCapability.NOT_POSSIBLE:
        result.add_warning(
            code="CANNOT_ANALYZE",
            message=f"Cannot statically analyze constraints on '{c1_operand}'"
        )
    elif cap == AnalysisCapability.SYNTACTIC_ONLY:
        result.add_warning(
            code="SYNTACTIC_ONLY",
            message=f"Can only perform syntactic comparison for '{c1_operand}' (requires semantic grounding)"
        )
    
    return result


# =============================================================================
# QUICK VALIDATORS
# =============================================================================

def is_valid_constraint(
    operand: str,
    operator: str,
    value: Any,
    unit: Optional[str] = None
) -> bool:
    """
    Quick check if constraint is valid.
    
    Returns True if no errors (warnings are OK).
    """
    result = validate_constraint(operand, operator, value, unit)
    return result.is_valid


def can_compare_constraints(
    c1_operand: str, c1_unit: Optional[str],
    c2_operand: str, c2_unit: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Quick check if two constraints can be compared.
    
    Returns:
        Tuple of (can_compare, reason_if_not)
    """
    # Different operands
    if c1_operand != c2_operand:
        return (False, f"Different operands: {c1_operand} vs {c2_operand}")
    
    # Check unit compatibility
    if not are_units_compatible(c1_unit, c2_unit):
        return (False, f"Incompatible units: {c1_unit} vs {c2_unit}")
    
    # Check if can be analyzed
    cap = get_analysis_capability(c1_operand)
    if cap == AnalysisCapability.NOT_POSSIBLE:
        return (False, f"Operand {c1_operand} cannot be statically analyzed")
    
    return (True, None)