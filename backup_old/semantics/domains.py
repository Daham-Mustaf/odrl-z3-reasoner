# src/semantics/domains.py
"""
Domain Bounds and Validation for ODRL Operands

Defines domain constraints for each operand:
- Bounded ranges (e.g., percentage ∈ [0, 100])
- Non-negative constraints (e.g., count ≥ 0)
- Generates Z3 assertions for domain enforcement

Based on: ODRL XSD-Grounded Constraint Reference Specification v1.0
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Union, List
from enum import Enum


@dataclass(frozen=True)
class DomainBounds:
    """
    Domain bounds for an operand.
    
    Attributes:
        min_value: Minimum allowed value (None = unbounded below)
        max_value: Maximum allowed value (None = unbounded above)
        min_inclusive: Whether minimum is inclusive (default True)
        max_inclusive: Whether maximum is inclusive (default True)
        integer_only: Whether only integer values are allowed
    """
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_inclusive: bool = True
    max_inclusive: bool = True
    integer_only: bool = False
    
    @property
    def is_bounded_below(self) -> bool:
        """Check if there's a lower bound"""
        return self.min_value is not None
    
    @property
    def is_bounded_above(self) -> bool:
        """Check if there's an upper bound"""
        return self.max_value is not None
    
    @property
    def is_bounded(self) -> bool:
        """Check if there's any bound"""
        return self.is_bounded_below or self.is_bounded_above
    
    @property
    def is_finite(self) -> bool:
        """Check if domain is finite (bounded both ways)"""
        return self.is_bounded_below and self.is_bounded_above
    
    def contains(self, value: Union[int, float]) -> bool:
        """
        Check if a value is within the domain bounds.
        
        Args:
            value: The value to check
            
        Returns:
            True if value is within bounds
        """
        if self.integer_only and not isinstance(value, int) and value != int(value):
            return False
        
        if self.is_bounded_below:
            if self.min_inclusive:
                if value < self.min_value:
                    return False
            else:
                if value <= self.min_value:
                    return False
        
        if self.is_bounded_above:
            if self.max_inclusive:
                if value > self.max_value:
                    return False
            else:
                if value >= self.max_value:
                    return False
        
        return True
    
    def __str__(self) -> str:
        """Human-readable representation"""
        if not self.is_bounded:
            return "(-∞, +∞)"
        
        left = "[" if self.min_inclusive else "("
        right = "]" if self.max_inclusive else ")"
        min_str = str(self.min_value) if self.is_bounded_below else "-∞"
        max_str = str(self.max_value) if self.is_bounded_above else "+∞"
        
        result = f"{left}{min_str}, {max_str}{right}"
        if self.integer_only:
            result += " ∩ ℤ"
        return result


# =============================================================================
# DOMAIN BOUNDS REGISTRY
# =============================================================================

DOMAIN_BOUNDS: Dict[str, DomainBounds] = {
    # =========================================================================
    # NUMERIC
    # =========================================================================
    
    'count': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=True
    ),
    
    'percentage': DomainBounds(
        min_value=0,
        max_value=100,
        integer_only=False
    ),
    
    'payAmount': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=False
    ),
    
    'resolution': DomainBounds(
        min_value=0,
        max_value=None,
        min_inclusive=False,  # Must be positive, not zero
        integer_only=False
    ),
    
    # =========================================================================
    # TEMPORAL
    # =========================================================================
    
    'dateTime': DomainBounds(
        min_value=None,  # Can be any timestamp
        max_value=None,
        integer_only=True  # Unix timestamp
    ),
    
    'timeInterval': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=True  # Seconds
    ),
    
    'elapsedTime': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=True  # Seconds
    ),
    
    'delayPeriod': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=True  # Seconds
    ),
    
    'meteredTime': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=True  # Seconds
    ),
    
    # =========================================================================
    # POSITIONAL - ABSOLUTE
    # =========================================================================
    
    'absolutePosition': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=False
    ),
    
    'absoluteSize': DomainBounds(
        min_value=0,
        max_value=None,
        min_inclusive=False,  # Must be positive
        integer_only=False
    ),
    
    'absoluteTemporalPosition': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=False
    ),
    
    'absoluteSpatialPosition': DomainBounds(
        min_value=0,
        max_value=None,
        integer_only=False
    ),
    
    # =========================================================================
    # POSITIONAL - RELATIVE (all [0, 100])
    # =========================================================================
    
    'relativePosition': DomainBounds(
        min_value=0,
        max_value=100,
        integer_only=False
    ),
    
    'relativeSize': DomainBounds(
        min_value=0,
        max_value=100,
        integer_only=False
    ),
    
    'relativeTemporalPosition': DomainBounds(
        min_value=0,
        max_value=100,
        integer_only=False
    ),
    
    'relativeSpatialPosition': DomainBounds(
        min_value=0,
        max_value=100,
        integer_only=False
    ),
}

# Operands without numeric domain bounds (categorical, etc.)
# These are not in DOMAIN_BOUNDS and will return None


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


def get_domain_bounds(operand: str) -> Optional[DomainBounds]:
    """
    Get domain bounds for an operand.
    
    Args:
        operand: Operand name (with or without namespace)
        
    Returns:
        DomainBounds if operand has numeric bounds, None otherwise
    """
    name = _normalize_operand_name(operand)
    return DOMAIN_BOUNDS.get(name)


def has_domain_bounds(operand: str) -> bool:
    """Check if an operand has domain bounds defined."""
    return get_domain_bounds(operand) is not None


def validate_value_in_domain(
    operand: str,
    value: Union[int, float]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is within the operand's domain.
    
    Args:
        operand: Operand name
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if valid
    """
    bounds = get_domain_bounds(operand)
    
    if bounds is None:
        # No bounds defined, assume valid
        return (True, None)
    
    if not bounds.contains(value):
        return (False, f"Value {value} is outside domain {bounds} for operand '{operand}'")
    
    return (True, None)


# =============================================================================
# Z3 INTEGRATION
# =============================================================================

def get_z3_domain_assertions(operand: str, z3_var: Any) -> List[Any]:
    """
    Generate Z3 assertions for domain bounds.
    
    Args:
        operand: Operand name
        z3_var: Z3 variable to constrain
        
    Returns:
        List of Z3 assertion expressions
        
    Note:
        Import z3 only when needed to avoid dependency issues.
    """
    bounds = get_domain_bounds(operand)
    
    if bounds is None:
        return []
    
    # Import z3 here to avoid circular imports and missing dependency issues
    try:
        import z3
    except ImportError:
        return []
    
    assertions = []
    
    if bounds.is_bounded_below:
        if bounds.min_inclusive:
            assertions.append(z3_var >= bounds.min_value)
        else:
            assertions.append(z3_var > bounds.min_value)
    
    if bounds.is_bounded_above:
        if bounds.max_inclusive:
            assertions.append(z3_var <= bounds.max_value)
        else:
            assertions.append(z3_var < bounds.max_value)
    
    return assertions


def get_z3_domain_assertions_smtlib(operand: str, var_name: str) -> List[str]:
    """
    Generate SMT-LIB format assertions for domain bounds.
    
    Args:
        operand: Operand name
        var_name: Name of the SMT variable
        
    Returns:
        List of SMT-LIB assertion strings
    """
    bounds = get_domain_bounds(operand)
    
    if bounds is None:
        return []
    
    assertions = []
    
    if bounds.is_bounded_below:
        op = ">=" if bounds.min_inclusive else ">"
        assertions.append(f"(assert ({op} {var_name} {bounds.min_value}))")
    
    if bounds.is_bounded_above:
        op = "<=" if bounds.max_inclusive else "<"
        assertions.append(f"(assert ({op} {var_name} {bounds.max_value}))")
    
    return assertions


# =============================================================================
# DOMAIN VALIDATION ERRORS
# =============================================================================

class DomainValidationError(Exception):
    """Raised when a value is outside its domain bounds"""
    
    def __init__(self, operand: str, value: Any, bounds: DomainBounds):
        self.operand = operand
        self.value = value
        self.bounds = bounds
        super().__init__(
            f"Value {value} is outside domain {bounds} for operand '{operand}'"
        )


def validate_or_raise(operand: str, value: Union[int, float]) -> None:
    """
    Validate value and raise DomainValidationError if invalid.
    
    Args:
        operand: Operand name
        value: Value to validate
        
    Raises:
        DomainValidationError: If value is outside domain
    """
    bounds = get_domain_bounds(operand)
    
    if bounds is not None and not bounds.contains(value):
        raise DomainValidationError(operand, value, bounds)


# =============================================================================
# STATISTICS
# =============================================================================

def get_bounded_operands() -> List[str]:
    """Get list of all operands with domain bounds."""
    return list(DOMAIN_BOUNDS.keys())


def get_finite_domain_operands() -> List[str]:
    """Get list of operands with finite (both-sided) bounds."""
    return [
        name for name, bounds in DOMAIN_BOUNDS.items()
        if bounds.is_finite
    ]


def get_domain_statistics() -> Dict[str, Any]:
    """Get statistics about domain bounds."""
    finite = get_finite_domain_operands()
    bounded = get_bounded_operands()
    
    return {
        'total_with_bounds': len(bounded),
        'finite_domains': len(finite),
        'finite_operands': finite,
        'bounded_operands': bounded,
    }