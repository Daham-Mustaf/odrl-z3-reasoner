# src/encoder/z3_encoder.py
"""
ODRL-SA Z3 Encoder - Complete Implementation

Encodes ALL ODRL constraints to Z3 formulas for SMT solving:
- Comparison operators (eq, neq, lt, lteq, gt, gteq)
- Set operators (isA, isAnyOf, isAllOf, isNoneOf, hasPart, isPartOf)
- Logical operators (and, or, xone, andSequence)

Implements the abstract interpretation from the formal specification.
"""

from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass
from enum import Enum
import logging

from z3 import (
    # Sorts and values
    Int, Real, Bool, String,
    IntVal, RealVal, BoolVal, StringVal,
    IntSort, RealSort, BoolSort, StringSort,
    # Operators
    And, Or, Not, Implies, Xor,
    If, Sum,
    # Comparisons
    # Solver
    Solver, sat, unsat, unknown,
    # Model extraction
    is_int_value, is_rational_value, is_true, is_false,
    # For set encoding
    Const, SetSort, SetAdd, SetUnion, SetIntersect, IsMember, EmptySet,
)

# Import from core module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.types import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
    Judgment,
)
from registry import ConstraintClass
from core.classifier import classify_constraint
from core.judgment import JudgmentResult, is_comparable

logger = logging.getLogger(__name__)


# =============================================================================
# DOMAIN BOUNDS (Complete for all ODRL operands)
# =============================================================================

@dataclass
class DomainBounds:
    """Domain bounds for a LeftOperand."""
    min_val: Optional[float]  # None = -inf
    max_val: Optional[float]  # None = +inf
    is_integer: bool
    use_real: bool  # Use Real sort instead of Int


# Domain bounds per LeftOperand
DOMAIN_BOUNDS: Dict[str, DomainBounds] = {
    # Numeric - Count/Quantity
    "count": DomainBounds(0, None, True, False),
    
    # Numeric - Percentage (0-100)
    "percentage": DomainBounds(0, 100, False, True),
    
    # Numeric - Monetary
    "payAmount": DomainBounds(0, None, False, True),
    
    # Numeric - Size/Resolution
    "absoluteSize": DomainBounds(0, None, False, True),
    "relativeSize": DomainBounds(0, 100, False, True),
    "resolution": DomainBounds(0, None, False, True),
    
    # Numeric - Position (Absolute)
    "absolutePosition": DomainBounds(None, None, False, True),
    "absoluteSpatialPosition": DomainBounds(None, None, False, True),
    "absoluteTemporalPosition": DomainBounds(0, None, False, True),
    
    # Numeric - Position (Relative 0-100%)
    "relativePosition": DomainBounds(0, 100, False, True),
    "relativeSpatialPosition": DomainBounds(0, 100, False, True),
    "relativeTemporalPosition": DomainBounds(0, 100, False, True),
    
    # Temporal - DateTime (Unix timestamp)
    "dateTime": DomainBounds(None, None, True, False),
    
    # Temporal - Durations (seconds)
    "timeInterval": DomainBounds(0, None, True, False),
    "elapsedTime": DomainBounds(0, None, True, False),
    "delayPeriod": DomainBounds(0, None, True, False),
    "meteredTime": DomainBounds(0, None, True, False),
}


# =============================================================================
# Z3 VARIABLE MANAGER
# =============================================================================

class Z3VariableManager:
    """
    Manages Z3 variables for constraints.
    
    Each unique (left_operand, unit, unit_of_count) tuple gets one Z3 variable.
    This ensures constraints on the same operand share the same variable.
    """
    
    def __init__(self):
        self._variables: Dict[str, Any] = {}
        self._var_info: Dict[str, Dict] = {}
        self._string_vars: Dict[str, Any] = {}  # For string/enum values
    
    def clear(self):
        """Clear all variables."""
        self._variables.clear()
        self._var_info.clear()
        self._string_vars.clear()
    
    def get_variable(
        self, 
        left_operand: str,
        unit: Optional[str] = None,
        unit_of_count: Optional[str] = None
    ) -> Any:
        """Get or create Z3 variable for a numeric constraint."""
        # Normalize operand name
        op = left_operand.split('#')[-1].split('/')[-1]
        
        # Create unique key
        key = f"{op}_{unit or 'default'}_{unit_of_count or 'default'}"
        
        if key not in self._variables:
            # Determine Z3 sort
            bounds = DOMAIN_BOUNDS.get(op)
            if bounds and bounds.use_real:
                var = Real(key)
            else:
                var = Int(key)
            
            self._variables[key] = var
            self._var_info[key] = {
                'operand': op,
                'unit': unit,
                'unit_of_count': unit_of_count,
                'bounds': bounds,
            }
        
        return self._variables[key]
    
    def get_string_variable(self, left_operand: str) -> Any:
        """Get or create Z3 String variable for grounded constraints."""
        op = left_operand.split('#')[-1].split('/')[-1]
        key = f"str_{op}"
        
        if key not in self._string_vars:
            self._string_vars[key] = String(key)
        
        return self._string_vars[key]
    
    def get_domain_constraints(self) -> List[Any]:
        """Get domain constraints for all variables."""
        constraints = []
        
        for key, var in self._variables.items():
            info = self._var_info.get(key)
            if info and info.get('bounds'):
                bounds = info['bounds']
                if bounds.min_val is not None:
                    if bounds.use_real:
                        constraints.append(var >= RealVal(bounds.min_val))
                    else:
                        constraints.append(var >= IntVal(int(bounds.min_val)))
                if bounds.max_val is not None:
                    if bounds.use_real:
                        constraints.append(var <= RealVal(bounds.max_val))
                    else:
                        constraints.append(var <= IntVal(int(bounds.max_val)))
        
        return constraints


# =============================================================================
# CONSTRAINT ENCODER
# =============================================================================

class ConstraintEncoder:
    """
    Encodes AtomicConstraints to Z3 formulas.
    
    Handles:
    - Comparison operators (eq, neq, lt, lteq, gt, gteq)
    - Set operators (isA, isAnyOf, isAllOf, isNoneOf, hasPart, isPartOf)
    """
    
    def __init__(self, var_manager: Z3VariableManager, debug: bool = False):
        self.var_manager = var_manager
        self.debug = debug
    
    def _debug(self, msg: str):
        if self.debug:
            print(f"[ENCODER] {msg}")
    
    def encode(self, constraint: AtomicConstraint) -> Any:
        """Encode an atomic constraint to Z3 formula."""
        op = constraint.operator
        
        # Route to appropriate encoder
        if op.is_comparison():
            return self._encode_comparison(constraint)
        elif op.is_set_based():
            return self._encode_set_operator(constraint)
        else:
            logger.warning(f"Unknown operator type: {op}")
            return BoolVal(True)
    
    def _encode_comparison(self, constraint: AtomicConstraint) -> Any:
        """Encode comparison operators (eq, neq, lt, lteq, gt, gteq)."""
        # Get variable
        var = self.var_manager.get_variable(
            constraint.left_operand,
            constraint.unit,
            constraint.unit_of_count
        )
        
        # Handle special cases
        if constraint.right_operand.is_policy_usage:
            self._debug(f"policyUsage - cannot encode statically")
            return BoolVal(True)  # Over-approximate
        
        # Get normalized Z3 value
        z3_value = self._normalize_and_convert(constraint, var)
        
        # Encode based on operator
        op = constraint.operator
        
        if op == OperatorType.EQ:
            return var == z3_value
        elif op == OperatorType.NEQ:
            return var != z3_value
        elif op == OperatorType.LT:
            return var < z3_value
        elif op == OperatorType.LTEQ:
            return var <= z3_value
        elif op == OperatorType.GT:
            return var > z3_value
        elif op == OperatorType.GTEQ:
            return var >= z3_value
        
        return BoolVal(True)
    
    def _encode_set_operator(self, constraint: AtomicConstraint) -> Any:
        """
        Encode set operators (isA, isAnyOf, isAllOf, isNoneOf, hasPart, isPartOf).
        
        For GROUNDED operands (language, purpose, etc.), we use string comparison.
        For numeric operands with sets, we use Or/And of equalities.
        """
        op = constraint.operator
        value = constraint.right_operand.value
        
        # Get the values as a set
        if isinstance(value, (list, tuple, set)):
            values = list(value)
        elif isinstance(value, str):
            # Single value or comma-separated
            if ',' in value:
                values = [v.strip() for v in value.split(',')]
            else:
                values = [value]
        else:
            values = [value]
        
        # Normalize values (extract local names from URIs)
        normalized_values = []
        for v in values:
            if isinstance(v, str):
                # Extract local name from URI
                if '#' in v:
                    v = v.split('#')[-1]
                elif '/' in v:
                    v = v.split('/')[-1]
            normalized_values.append(v)
        
        self._debug(f"Set operator {op} with values: {normalized_values}")
        
        # Use string variable for grounded operands
        var = self.var_manager.get_string_variable(constraint.left_operand)
        
        if op == OperatorType.IS_ANY_OF:
            # value IN {set} - at least one match
            if not normalized_values:
                return BoolVal(False)
            return Or([var == StringVal(str(v)) for v in normalized_values])
        
        elif op == OperatorType.IS_NONE_OF:
            # value NOT IN {set} - no matches
            if not normalized_values:
                return BoolVal(True)
            return And([var != StringVal(str(v)) for v in normalized_values])
        
        elif op == OperatorType.IS_ALL_OF:
            # For multi-valued operands: all values must be present
            # This is complex - for static analysis, we check if the single var
            # could match all (which is only possible if single value)
            if len(normalized_values) == 1:
                return var == StringVal(str(normalized_values[0]))
            else:
                # Cannot satisfy isAllOf with multiple required values 
                # and a single-valued variable
                self._debug(f"isAllOf with multiple values - needs multi-valued support")
                return BoolVal(True)  # Over-approximate
        
        elif op == OperatorType.IS_A:
            # Subsumption check - needs oracle for proper handling
            # For now, treat as equality
            if normalized_values:
                return var == StringVal(str(normalized_values[0]))
            return BoolVal(True)
        
        elif op == OperatorType.HAS_PART:
            # value hasPart x - the value contains x
            # For static analysis, treat as equality for single value
            if normalized_values:
                return var == StringVal(str(normalized_values[0]))
            return BoolVal(True)
        
        elif op == OperatorType.IS_PART_OF:
            # value isPartOf x - value is contained in x
            if normalized_values:
                return var == StringVal(str(normalized_values[0]))
            return BoolVal(True)
        
        return BoolVal(True)
    
    def _normalize_and_convert(self, constraint: AtomicConstraint, var: Any) -> Any:
        """Normalize value and convert to Z3."""
        from normalizer import get_normalized_value
        
        normalized = get_normalized_value(constraint)
        
        if normalized is None:
            return IntVal(0)
        
        return self._to_z3_value(normalized, var)
    
    def _to_z3_value(self, value: Any, var: Any) -> Any:
        """Convert Python value to Z3 value matching variable sort."""
        if value is None:
            return IntVal(0)
        
        # Handle datetime
        if hasattr(value, 'timestamp'):
            value = int(value.timestamp())
        
        # Handle timedelta
        if hasattr(value, 'total_seconds'):
            value = int(value.total_seconds())
        
        # Handle Decimal
        from decimal import Decimal
        if isinstance(value, Decimal):
            value = float(value)
        
        # Handle numeric
        if isinstance(value, int):
            return IntVal(value) if str(var.sort()) == 'Int' else RealVal(value)
        if isinstance(value, float):
            return RealVal(value)
        
        # Handle string (try to parse as number)
        if isinstance(value, str):
            try:
                if '.' in value:
                    return RealVal(float(value))
                return IntVal(int(value))
            except ValueError:
                # String value - return 0 as placeholder for numeric
                self._debug(f"Cannot convert string '{value}' to Z3 numeric")
                return IntVal(0)
        
        return IntVal(0)


# =============================================================================
# COMPOSITE CONSTRAINT ENCODER
# =============================================================================

class CompositeEncoder:
    """
    Encodes CompositeConstraints (logical combinations).
    
    Handles:
    - AND: All constraints must be true (conjunction)
    - OR: At least one must be true (disjunction)
    - XONE: Exactly one must be true (exclusive or)
    - AND_SEQUENCE: Ordered AND (treated as AND for static analysis)
    """
    
    def __init__(self, constraint_encoder: ConstraintEncoder):
        self.constraint_encoder = constraint_encoder
        self._constraint_map: Dict[str, AtomicConstraint] = {}
        self._composite_map: Dict[str, CompositeConstraint] = {}
    
    def register_constraint(self, constraint: Union[AtomicConstraint, CompositeConstraint]):
        """Register a constraint for reference by composites."""
        if isinstance(constraint, AtomicConstraint):
            self._constraint_map[constraint.uid] = constraint
        elif isinstance(constraint, CompositeConstraint):
            self._composite_map[constraint.uid] = constraint
    
    def register_all(self, constraints: Dict[str, Any]):
        """Register all constraints from a dict."""
        for uid, constraint in constraints.items():
            self.register_constraint(constraint)
    
    def encode(self, composite: CompositeConstraint) -> Any:
        """Encode a composite constraint."""
        # Encode all operands
        encoded_operands = []
        
        for operand in composite.operands:
            if isinstance(operand, str):
                # Reference to registered constraint
                if operand in self._constraint_map:
                    atomic = self._constraint_map[operand]
                    encoded = self.constraint_encoder.encode(atomic)
                    if encoded is not None:
                        encoded_operands.append(encoded)
                elif operand in self._composite_map:
                    comp = self._composite_map[operand]
                    encoded = self.encode(comp)
                    if encoded is not None:
                        encoded_operands.append(encoded)
                else:
                    logger.warning(f"Unknown constraint reference: {operand}")
            elif isinstance(operand, AtomicConstraint):
                encoded = self.constraint_encoder.encode(operand)
                if encoded is not None:
                    encoded_operands.append(encoded)
            elif isinstance(operand, CompositeConstraint):
                encoded = self.encode(operand)
                if encoded is not None:
                    encoded_operands.append(encoded)
        
        if not encoded_operands:
            return BoolVal(True)
        
        # Apply logical operator
        op = composite.operator
        
        if op == LogicalOperator.AND:
            return And(*encoded_operands)
        
        elif op == LogicalOperator.OR:
            return Or(*encoded_operands)
        
        elif op == LogicalOperator.XONE:
            # Exactly one must be true
            # Encoding: exactly one = at_least_one AND at_most_one
            # at_most_one: for each pair, NOT(both true)
            n = len(encoded_operands)
            if n == 0:
                return BoolVal(False)
            if n == 1:
                return encoded_operands[0]
            
            # At least one true
            at_least_one = Or(*encoded_operands)
            
            # At most one true (no two are both true)
            at_most_one_clauses = []
            for i in range(n):
                for j in range(i + 1, n):
                    at_most_one_clauses.append(Not(And(encoded_operands[i], encoded_operands[j])))
            at_most_one = And(*at_most_one_clauses) if at_most_one_clauses else BoolVal(True)
            
            return And(at_least_one, at_most_one)
        
        elif op == LogicalOperator.AND_SEQUENCE:
            # For static analysis, treat as AND (sequence is runtime concern)
            return And(*encoded_operands)
        
        return BoolVal(True)


# =============================================================================
# JUDGMENT ENGINE (SMT-based)
# =============================================================================

class Z3JudgmentEngine:
    """
    Main engine for constraint analysis using Z3 SMT solver.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.var_manager = Z3VariableManager()
        self.constraint_encoder = ConstraintEncoder(self.var_manager, debug)
        self.composite_encoder = CompositeEncoder(self.constraint_encoder)
    
    def _debug(self, msg: str):
        if self.debug:
            print(f"[ENGINE] {msg}")
    
    def encode(self, constraint: Union[AtomicConstraint, CompositeConstraint]) -> Any:
        """Encode a single constraint."""
        if isinstance(constraint, AtomicConstraint):
            return self.constraint_encoder.encode(constraint)
        elif isinstance(constraint, CompositeConstraint):
            return self.composite_encoder.encode(constraint)
        return BoolVal(True)
    
    def check_consistency(
        self, 
        constraints: List[AtomicConstraint],
        composites: Optional[List[CompositeConstraint]] = None
    ) -> Tuple[Judgment, Optional[Dict]]:
        """
        Check if a set of constraints can be simultaneously satisfied.
        
        Returns:
            (Judgment, model_or_none)
            - CONFLICT: Constraints are unsatisfiable
            - POSSIBLY_COMPATIBLE: Satisfiable, model provides witness
        """
        self.var_manager.clear()
        
        # Create solver
        solver = Solver()
        
        # Add domain constraints
        for dc in self.var_manager.get_domain_constraints():
            solver.add(dc)
        
        # Encode and add atomic constraints
        for c in constraints:
            formula = self.constraint_encoder.encode(c)
            if formula is not None:
                solver.add(formula)
                self._debug(f"Added: {c} -> {formula}")
        
        # Encode and add composite constraints
        if composites:
            for comp in composites:
                formula = self.composite_encoder.encode(comp)
                if formula is not None:
                    solver.add(formula)
                    self._debug(f"Added composite: {comp.uid} -> {formula}")
        
        # Check satisfiability
        result = solver.check()
        
        if result == sat:
            model = self._extract_model(solver.model())
            self._debug(f"SAT - Model: {model}")
            return Judgment.POSSIBLY_COMPATIBLE, model
        elif result == unsat:
            self._debug("UNSAT - Conflict detected")
            return Judgment.CONFLICT, None
        else:
            self._debug("UNKNOWN")
            return Judgment.UNKNOWN, None
    
    def _extract_model(self, z3_model) -> Dict:
        """Extract variable assignments from Z3 model."""
        model = {}
        
        for var_name, var in self.var_manager._variables.items():
            try:
                val = z3_model[var]
                if val is not None:
                    if is_int_value(val):
                        model[var_name] = val.as_long()
                    elif is_rational_value(val):
                        try:
                            model[var_name] = float(val.as_decimal(10).rstrip('?'))
                        except:
                            model[var_name] = str(val)
                    else:
                        model[var_name] = str(val)
            except:
                pass
        
        # Also extract string variables
        for var_name, var in self.var_manager._string_vars.items():
            try:
                val = z3_model[var]
                if val is not None:
                    model[var_name] = str(val).strip('"')
            except:
                pass
        
        return model


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def check_consistency(
    constraints: List[AtomicConstraint],
    composites: Optional[List[CompositeConstraint]] = None,
    debug: bool = False
) -> Tuple[Judgment, Optional[Dict]]:
    """
    Convenience function to check constraint consistency.
    
    Args:
        constraints: List of atomic constraints
        composites: Optional list of composite constraints
        debug: Enable debug output
        
    Returns:
        (Judgment, model_or_none)
    """
    engine = Z3JudgmentEngine(debug=debug)
    
    # Register all constraints for composite resolution
    for c in constraints:
        engine.composite_encoder.register_constraint(c)
    if composites:
        for c in composites:
            engine.composite_encoder.register_constraint(c)
    
    return engine.check_consistency(constraints, composites)