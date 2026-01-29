# src/encoder/z3_encoder.py
"""
ODRL-SA Z3 Encoder
Encodes FULL class (L_xsd) constraints to Z3 formulas for SMT solving.
Implements the abstract interpretation from the formal specification:
    
    Abstraction Function (Definition 8):
        alpha(c) maps constraint c to abstract domain element
        
    For operator op and value v:
        eq  -> [v, v]
        neq -> T (over-approximation, refined by SMT)
        lt  -> [inf, v)
        lteq -> [inf, v]
        gt  -> (v, sup]
        gteq -> [v, sup]
        
    Set Operators:
        isAnyOf  -> Or(var == v1, var == v2, ...)
        isNoneOf -> And(var != v1, var != v2, ...)
        isAllOf  -> Degenerates to eq for single-valued operands
        
    Meet Operation (Definition 9):
        [a,b] meet [c,d] = [max(a,c), min(b,d)] if valid, else bottom
The encoder translates constraints to Z3 and checks satisfiability.
"""
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
from z3 import (
    # Sorts and values
    Int, Real, Bool, String,
    IntVal, RealVal, BoolVal, StringVal,
    # Operators
    And, Or, Not, Implies,
    # Solver
    Solver, sat, unsat, unknown,
    # Model extraction
    is_int_value, is_rational_value, is_true, is_false,
)
# Import from core module
import sys
from pathlib import Path
# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.constraint_types import (
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
# ORACLE INTEGRATION (SAFE - with fallback)
# =============================================================================
# This section provides oracle integration with ZERO RISK because:
# 1. Uses try/except - if oracle fails, fallback is used
# 2. Fallback behavior is IDENTICAL to current behavior
# 3. Only affects variable naming, not Z3 logic
# =============================================================================

def _get_oracle_registry():
    """
    Lazy load oracle registry.
    
    Returns None if registry is not available (safe fallback).
    """
    try:
        from grounding.oracle_registry import get_registry
        return get_registry()
    except ImportError:
        return None


def _normalize_with_oracle(operand: str, value: str) -> str:
    """
    Normalize value using oracle if available.
    
    SAFE: Falls back to simple IRI extraction if oracle unavailable.
    This ensures behavior is IDENTICAL to before if oracle is not installed.
    
    Args:
        operand: The left operand name (e.g., "payAmount", "language")
        value: The value to normalize (e.g., IRI, code, label)
        
    Returns:
        Normalized string identifier for the value
    """
    if value is None:
        return "default"
    
    # Try oracle normalization
    registry = _get_oracle_registry()
    if registry:
        try:
            from grounding.oracle_registry import get_oracle_type_for_operand
            oracle_type = get_oracle_type_for_operand(operand)
            if oracle_type:
                return registry.normalize(oracle_type, value)
        except Exception:
            pass  # Fall through to fallback
    
    # FALLBACK: Extract local name from IRI (current behavior)
    value = str(value)
    if '/' in value:
        return value.split('/')[-1]
    if '#' in value:
        return value.split('#')[-1]
    return value


# =============================================================================
# DOMAIN BOUNDS (Table 6 from XSD Reference)
# =============================================================================
@dataclass
class DomainBounds:
    """Domain bounds for a LeftOperand."""
    min_val: Optional[float]  # None = -inf
    max_val: Optional[float]  # None = +inf
    is_integer: bool
    use_real: bool  # Use Real sort instead of Int


# Domain bounds per LeftOperand (from formal spec)
DOMAIN_BOUNDS: Dict[str, DomainBounds] = {
    # Numeric
    "count": DomainBounds(0, None, True, False),
    "percentage": DomainBounds(min_val=0, max_val=100, is_integer=False, use_real=True),
    "payAmount": DomainBounds(0, None, False, True),
    "resolution": DomainBounds(0, None, False, True),
    
    # Temporal
    "dateTime": DomainBounds(None, None, True, False),  # Unix timestamp
    "timeInterval": DomainBounds(1, None, True, False),  # Seconds (min=1)
    "elapsedTime": DomainBounds(0, None, True, False),  # Seconds
    "delayPeriod": DomainBounds(0, None, True, False),  # Seconds
    
    # Positional - Absolute
    "absolutePosition": DomainBounds(0, None, False, True),
    "absoluteSize": DomainBounds(0, None, False, True),
    "absoluteTemporalPosition": DomainBounds(0, None, False, True),
    "absoluteSpatialPosition": DomainBounds(0, None, False, True),
    
    # Positional - Relative (0-100%)
    "relativePosition": DomainBounds(0, 100, False, True),
    "relativeSize": DomainBounds(0, None, False, True),
    "relativeTemporalPosition": DomainBounds(0, 100, False, True),
    "relativeSpatialPosition": DomainBounds(0, 100, False, True),
}

# Category sets for convenience
L_BOUNDED = {"percentage", "relativePosition",
            #  "relativeSize", 
             "relativeTemporalPosition", "relativeSpatialPosition"}
L_INT = {"count", "timeInterval"}
L_DATETIME = {"dateTime"}
L_UNIT = {"payAmount", "resolution", "absolutePosition", "absoluteSize"}
L_REAL = {"absoluteTemporalPosition"}
L_COORDS = {"absoluteSpatialPosition"}
L_REF = {"elapsedTime", "delayPeriod"}
L_UNBOUNDED_PERCENTAGE = {
    "relativeSize",  # [0, ∞)
}

FULLY_ANALYZABLE = L_BOUNDED | L_INT | L_DATETIME | L_UNIT | L_REAL | L_UNBOUNDED_PERCENTAGE | L_COORDS | {"unitOfCount"}


# =============================================================================
# OPERATOR RESTRICTIONS
# =============================================================================

# timeInterval only supports 'eq' operator (recurring intervals)
TIMEINTERVAL_VALID_OPS = {OperatorType.EQ}

# absoluteSpatialPosition only supports eq/neq (geometric semantics needed for ordering)
SPATIAL_VALID_OPS = {OperatorType.EQ, OperatorType.NEQ, OperatorType.IS_ANY_OF, OperatorType.IS_NONE_OF}


# =============================================================================
# Z3 VARIABLE MANAGER
# =============================================================================
class Z3VariableManager:
    """
    Manages Z3 variables for constraints.
    
    Each unique (left_operand, unit, unit_of_count) tuple gets one Z3 variable.
    This ensures constraints on the same operand share the same variable.
    
    UPDATED: Now normalizes units via Oracle (if available) so that:
    - "EUR", "euro", "http://qudt.org/vocab/unit/EUR" → same variable
    - Falls back to simple IRI extraction if Oracle unavailable
    """
    
    def __init__(self):
        self._variables: Dict[str, Any] = {}
        self._var_info: Dict[str, Dict] = {}
    
    def get_variable(
        self, 
        left_operand: str,
        unit: Optional[str] = None,
        unit_of_count: Optional[str] = None
    ) -> Any:
        """Get or create Z3 variable for a constraint."""
        # Normalize operand name
        op = left_operand.split('#')[-1].split('/')[-1]
        
        # =====================================================================
        # ORACLE INTEGRATION (safe - has fallback)
        # =====================================================================
        # Normalize unit using oracle (or fallback to IRI extraction)
        normalized_unit = _normalize_with_oracle(op, unit) if unit else "default"
        normalized_scope = _normalize_with_oracle(op, unit_of_count) if unit_of_count else "default"
        
        # Create unique key with normalized names
        key = f"{op}_{normalized_unit}_{normalized_scope}"
        
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
                'unit': unit,  # Store original
                'normalized_unit': normalized_unit,  # Store normalized
                'unit_of_count': unit_of_count,
                'normalized_scope': normalized_scope,  # Store normalized
                'bounds': bounds,
            }
        
        return self._variables[key]
    
    def get_domain_constraints(self) -> List:
        """Get domain bound constraints for all variables."""
        constraints = []
        
        for key, var in self._variables.items():
            info = self._var_info[key]
            bounds = info.get('bounds')
            
            if bounds:
                if bounds.min_val is not None:
                    constraints.append(var >= bounds.min_val)
                if bounds.max_val is not None:
                    constraints.append(var <= bounds.max_val)
        
        return constraints
    
    def clear(self):
        """Clear all variables."""
        self._variables.clear()
        self._var_info.clear()


# =============================================================================
# CONSTRAINT ENCODER
# =============================================================================
class ConstraintEncoder:
    """
    Encodes AtomicConstraints to Z3 formulas.
    
    Supports all ODRL operators:
    - Comparison (O_cmp): eq, neq, lt, lteq, gt, gteq
    - Set (O_set): isAnyOf, isNoneOf, isAllOf, isA, hasPart, isPartOf
    """
    
    def __init__(self, var_manager: Z3VariableManager):
        self.var_manager = var_manager
    
    def encode(self, constraint: AtomicConstraint) -> Any:
        """
        Encode a single atomic constraint to Z3.
        
        Returns a Z3 boolean expression.
        """
        # Get Z3 variable
        var = self.var_manager.get_variable(
            constraint.left_operand,
            constraint.unit,
            constraint.unit_of_count
        )
        
        # Get value
        value = constraint.right_operand.value
        
        # Handle special cases
        if constraint.right_operand.is_policy_usage:
            logger.warning(f"Cannot encode policyUsage constraint: {constraint}")
            return BoolVal(True)  # Over-approximate
        
        if constraint.right_operand.is_iri:
            return BoolVal(True)  # Over-approximate
        
        # Validate operator restrictions
        op_name = constraint.left_operand.split('#')[-1].split('/')[-1]
        op = constraint.operator
        
        if op_name == "timeInterval" and op not in TIMEINTERVAL_VALID_OPS:
            logger.warning(
                f"timeInterval only supports 'eq' operator, got '{op.value}'. "
                f"Result may have unclear semantics."
            )
        
        if op_name == "absoluteSpatialPosition" and op not in SPATIAL_VALID_OPS:
            logger.warning(
                f"absoluteSpatialPosition only supports eq/neq operators, got '{op.value}'. "
                f"Ordering requires geometric semantics."
            )
        
        # =====================================================================
        # COMPARISON OPERATORS (O_cmp)
        # =====================================================================
        
        if op == OperatorType.EQ:
            z3_value = self._normalize_and_convert(constraint, var)
            return var == z3_value
        
        elif op == OperatorType.NEQ:
            z3_value = self._normalize_and_convert(constraint, var)
            return var != z3_value
        
        elif op == OperatorType.LT:
            z3_value = self._normalize_and_convert(constraint, var)
            return var < z3_value
        
        elif op == OperatorType.LTEQ:
            z3_value = self._normalize_and_convert(constraint, var)
            return var <= z3_value
        
        elif op == OperatorType.GT:
            z3_value = self._normalize_and_convert(constraint, var)
            return var > z3_value
        
        elif op == OperatorType.GTEQ:
            z3_value = self._normalize_and_convert(constraint, var)
            return var >= z3_value
        
        # =====================================================================
        # SET OPERATORS (O_set)
        # =====================================================================
        
        elif op == OperatorType.IS_ANY_OF:
            # isAnyOf: value must be one of the set
            # Encode as: Or(var == v1, var == v2, ...)
            return self._encode_is_any_of(constraint, var, value)
        
        elif op == OperatorType.IS_NONE_OF:
            # isNoneOf: value must NOT be any of the set
            # Encode as: And(var != v1, var != v2, ...)
            return self._encode_is_none_of(constraint, var, value)
        
        elif op == OperatorType.IS_ALL_OF:
            # isAllOf: For single-valued operands, degenerates to eq
            # Only satisfiable if set has one element (or all same)
            return self._encode_is_all_of(constraint, var, value)
        
        # =====================================================================
        # SEMANTIC OPERATORS (require grounding)
        # =====================================================================
        
        elif op == OperatorType.IS_A:
            # isA requires taxonomy/ontology reasoning
            logger.warning(f"isA operator requires semantic grounding, over-approximating as True")
            return BoolVal(True)
        
        elif op == OperatorType.HAS_PART:
            # hasPart requires mereological reasoning
            logger.warning(f"hasPart operator requires semantic grounding, over-approximating as True")
            return BoolVal(True)
        
        elif op == OperatorType.IS_PART_OF:
            # isPartOf requires mereological reasoning
            logger.warning(f"isPartOf operator requires semantic grounding, over-approximating as True")
            return BoolVal(True)
        
        # =====================================================================
        # UNKNOWN OPERATOR
        # =====================================================================
        
        else:
            logger.warning(f"Unknown operator {op}, over-approximating as True")
            return BoolVal(True)
    
    def _encode_is_any_of(self, constraint: AtomicConstraint, var: Any, value: Any) -> Any:
        """
        Encode isAnyOf operator.
        
        Semantics: var ∈ {v1, v2, ...}
        Z3: Or(var == v1, var == v2, ...)
        """
        if isinstance(value, (list, tuple, set)):
            if len(value) == 0:
                # Empty set - nothing can match
                return BoolVal(False)
            
            clauses = []
            for v in value:
                z3_v = self._normalize_single_value(v, constraint, var)
                clauses.append(var == z3_v)
            
            return Or(*clauses) if len(clauses) > 1 else clauses[0]
        else:
            # Single value - same as eq
            z3_value = self._normalize_and_convert(constraint, var)
            return var == z3_value
    
    def _encode_is_none_of(self, constraint: AtomicConstraint, var: Any, value: Any) -> Any:
        """
        Encode isNoneOf operator.
        
        Semantics: var ∉ {v1, v2, ...}
        Z3: And(var != v1, var != v2, ...)
        """
        if isinstance(value, (list, tuple, set)):
            if len(value) == 0:
                # Empty set - everything is "none of" empty
                return BoolVal(True)
            
            clauses = []
            for v in value:
                z3_v = self._normalize_single_value(v, constraint, var)
                clauses.append(var != z3_v)
            
            return And(*clauses) if len(clauses) > 1 else clauses[0]
        else:
            # Single value - same as neq
            z3_value = self._normalize_and_convert(constraint, var)
            return var != z3_value
    
    def _encode_is_all_of(self, constraint: AtomicConstraint, var: Any, value: Any) -> Any:
        """
        Encode isAllOf operator.
        
        For single-valued operands (most ODRL numeric operands), this degenerates:
        - If set has 1 element: same as eq
        - If set has multiple DIFFERENT elements: unsatisfiable (False)
        - If set has multiple SAME elements: same as eq to that value
        
        Z3: var == v (if all same) OR False (if different)
        """
        if isinstance(value, (list, tuple, set)):
            values = list(value)
            
            if len(values) == 0:
                # Empty set - vacuously true
                return BoolVal(True)
            
            if len(values) == 1:
                # Single element - same as eq
                z3_v = self._normalize_single_value(values[0], constraint, var)
                return var == z3_v
            
            # Multiple elements - check if all same
            normalized = [self._normalize_single_value(v, constraint, var) for v in values]
            
            # For numeric values, check if all equal
            # This is a simplification - for complex types, might need more logic
            first = values[0]
            if all(v == first for v in values):
                # All same - satisfiable
                z3_v = self._normalize_single_value(first, constraint, var)
                return var == z3_v
            else:
                # Different values - impossible for single-valued var
                logger.debug(f"isAllOf with different values is unsatisfiable")
                return BoolVal(False)
        else:
            # Single value - same as eq
            z3_value = self._normalize_and_convert(constraint, var)
            return var == z3_value
    
    def _normalize_and_convert(self, constraint: AtomicConstraint, var: Any) -> Any:
        """Normalize value and convert to Z3."""
        from normalizer import get_normalized_value
        
        normalized = get_normalized_value(constraint)
        
        if normalized is None:
            return IntVal(0)
        
        return self._to_z3_value(normalized, var)
    
    def _normalize_single_value(self, value: Any, constraint: AtomicConstraint, var: Any) -> Any:
        """Normalize a single value from a list (for set operators)."""
        from normalizer import normalize_value
        
        result = normalize_value(value, constraint.left_operand)
        normalized = result.value if result.success else value
        return self._to_z3_value(normalized, var)
    
    def _to_z3_value(self, value: Any, var: Any) -> Any:
        """Convert Python value to Z3 value matching variable sort."""
        if value is None:
            return IntVal(0)
        
        var_sort = str(var.sort())
        
        # Handle datetime (convert to timestamp)
        if hasattr(value, 'timestamp'):
            timestamp = int(value.timestamp())
            return IntVal(timestamp) if var_sort == 'Int' else RealVal(timestamp)
        
        # Handle date objects (from xsd:date) - convert to start of day UTC
        from datetime import date, datetime, timezone
        if isinstance(value, date) and not isinstance(value, datetime):
            dt = datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=timezone.utc)
            timestamp = int(dt.timestamp())
            return IntVal(timestamp) if var_sort == 'Int' else RealVal(timestamp)
        
        # Handle timedelta (convert to seconds)
        if hasattr(value, 'total_seconds'):
            seconds = int(value.total_seconds())
            return IntVal(seconds) if var_sort == 'Int' else RealVal(seconds)
        
        # Handle Decimal
        from decimal import Decimal
        if isinstance(value, Decimal):
            value = float(value)
        
        # Handle numeric
        if isinstance(value, int):
            return IntVal(value) if var_sort == 'Int' else RealVal(value)
        if isinstance(value, float):
            return RealVal(value) if var_sort == 'Real' else IntVal(int(value))
        
        # Handle string (try to parse)
        if isinstance(value, str):
            return self._parse_string_value(value, var, var_sort)
        
        return IntVal(0)
    
    def _parse_string_value(self, value: str, var: Any, var_sort: str) -> Any:
        """Parse string value to Z3."""
        from datetime import date, datetime, timezone
        
        # Try ISO date/datetime
        try:
            if 'T' in value or ' ' in value:
                if value.endswith('Z'):
                    value_str = value[:-1] + '+00:00'
                else:
                    value_str = value
                dt = datetime.fromisoformat(value_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                timestamp = int(dt.timestamp())
                return IntVal(timestamp) if var_sort == 'Int' else RealVal(timestamp)
            elif '-' in value and len(value) == 10:
                d = date.fromisoformat(value)
                dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
                timestamp = int(dt.timestamp())
                return IntVal(timestamp) if var_sort == 'Int' else RealVal(timestamp)
        except (ValueError, TypeError):
            pass
        
        # Try numeric
        try:
            if '.' in value:
                return RealVal(float(value))
            return IntVal(int(value))
        except ValueError:
            logger.warning(f"Cannot convert string '{value}' to Z3 numeric")
            return IntVal(0)


# =============================================================================
# COMPOSITE CONSTRAINT ENCODER
# =============================================================================
class CompositeEncoder:
    """
    Encodes CompositeConstraints (logical combinations).
    
    Supports: and, or, xone, andSequence
    """
    
    def __init__(self, constraint_encoder: ConstraintEncoder):
        self.constraint_encoder = constraint_encoder
        self._constraint_map: Dict[str, AtomicConstraint] = {}
    
    def register_constraint(self, constraint: AtomicConstraint):
        """Register an atomic constraint for reference by composites."""
        self._constraint_map[constraint.uid] = constraint
    
    def encode(self, composite: CompositeConstraint) -> Any:
        """Encode a composite constraint."""
        encoded_operands = []
        
        for operand in composite.operands:
            if isinstance(operand, str):
                if operand in self._constraint_map:
                    atomic = self._constraint_map[operand]
                    encoded_operands.append(self.constraint_encoder.encode(atomic))
                else:
                    logger.warning(f"Unknown constraint reference: {operand}")
            elif isinstance(operand, AtomicConstraint):
                encoded_operands.append(self.constraint_encoder.encode(operand))
            elif isinstance(operand, CompositeConstraint):
                encoded_operands.append(self.encode(operand))
        
        if not encoded_operands:
            return BoolVal(True)
        
        op = composite.operator
        
        if op == LogicalOperator.AND:
            return And(*encoded_operands)
        
        elif op == LogicalOperator.OR:
            return Or(*encoded_operands)
        
        elif op == LogicalOperator.XONE:
            # Exactly one must be true
            # Encode as: Or(c_i AND NOT(c_j) for all j != i)
            xone_clauses = []
            for i, enc in enumerate(encoded_operands):
                others = [Not(e) for j, e in enumerate(encoded_operands) if j != i]
                if others:
                    xone_clauses.append(And(enc, *others))
                else:
                    xone_clauses.append(enc)
            return Or(*xone_clauses)
        
        elif op == LogicalOperator.AND_SEQUENCE:
            # For static analysis, treat as AND (sequence requires runtime)
            logger.debug("andSequence treated as AND for static analysis")
            return And(*encoded_operands)
        
        return BoolVal(True)


# =============================================================================
# JUDGMENT ENGINE (SMT-based)
# =============================================================================
class Z3JudgmentEngine:
    """
    Performs judgment using Z3 SMT solver.
    
    Implements Definition 6 (Judgment Rules):
        judge(c1, c2) = 
            CONFLICT           if comparable AND [[c1]]# meet [[c2]]# = bottom
            POSSIBLY-COMPATIBLE if comparable AND [[c1]]# meet [[c2]]# != bottom
            UNKNOWN            if NOT comparable
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.var_manager = Z3VariableManager()
        self.constraint_encoder = ConstraintEncoder(self.var_manager)
    
    def encode(self, constraint: AtomicConstraint) -> Any:
        """Encode a single constraint (convenience method)."""
        return self.constraint_encoder.encode(constraint)
    
    def judge(
        self, 
        c1: AtomicConstraint, 
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """Judge two constraints."""
        comp_result = is_comparable(c1, c2)
        if not comp_result.comparable:
            return JudgmentResult(
                judgment=Judgment.UNKNOWN,
                comparable=False,
                incomparability_reason=comp_result.reason,
                explanation=comp_result.details
            )
        
        self.var_manager.clear()
        
        z3_c1 = self.constraint_encoder.encode(c1)
        z3_c2 = self.constraint_encoder.encode(c2)
        
        domain_constraints = self.var_manager.get_domain_constraints()
        
        solver = Solver()
        solver.add(And(z3_c1, z3_c2))
        solver.add(*domain_constraints)
        
        result = solver.check()
        
        if result == unsat:
            return JudgmentResult(
                judgment=Judgment.CONFLICT,
                comparable=True,
                explanation=f"UNSAT: {c1} AND {c2} has no solution"
            )
        elif result == sat:
            model = solver.model()
            counterexample = self._extract_model(model)
            return JudgmentResult(
                judgment=Judgment.POSSIBLY_COMPATIBLE,
                comparable=True,
                explanation=f"SAT: Found satisfying assignment",
                counterexample=counterexample
            )
        else:
            return JudgmentResult(
                judgment=Judgment.UNKNOWN,
                comparable=True,
                explanation="Z3 returned unknown"
            )
    
    def check_satisfiability(
        self, 
        constraints: List[AtomicConstraint]
    ) -> Tuple[Judgment, Optional[Dict]]:
        """Check if a set of constraints is satisfiable."""
        if not constraints:
            return Judgment.POSSIBLY_COMPATIBLE, {}
        
        self.var_manager.clear()
        
        encoded = [self.constraint_encoder.encode(c) for c in constraints]
        domain_constraints = self.var_manager.get_domain_constraints()
        
        solver = Solver()
        if len(encoded) == 1:
            solver.add(encoded[0])
        else:
            solver.add(And(*encoded))
        solver.add(*domain_constraints)
        
        result = solver.check()
        
        if result == unsat:
            return Judgment.CONFLICT, None
        elif result == sat:
            model = solver.model()
            return Judgment.POSSIBLY_COMPATIBLE, self._extract_model(model)
        else:
            return Judgment.UNKNOWN, None
    
    def _extract_model(self, model) -> Dict[str, Any]:
        """Extract variable assignments from Z3 model."""
        result = {}
        for decl in model.decls():
            name = decl.name()
            val = model[decl]
            
            if is_int_value(val):
                result[name] = val.as_long()
            elif is_rational_value(val):
                result[name] = float(val.as_decimal(10).rstrip('?'))
            elif is_true(val):
                result[name] = True
            elif is_false(val):
                result[name] = False
            else:
                result[name] = str(val)
        
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================
def judge_constraints(c1: AtomicConstraint, c2: AtomicConstraint) -> JudgmentResult:
    """Convenience function to judge two constraints."""
    engine = Z3JudgmentEngine()
    return engine.judge(c1, c2)


def check_consistency(constraints: List[AtomicConstraint]) -> Tuple[Judgment, Optional[Dict]]:
    """Check if a list of constraints is consistent (satisfiable)."""
    engine = Z3JudgmentEngine()
    return engine.check_satisfiability(constraints)


# =============================================================================
# MAIN - TESTING
# =============================================================================
if __name__ == "__main__":
    from core.constraint_types import RightOperand
    
    print("=" * 60)
    print("Z3 Encoder Test - All Operators")
    print("=" * 60)
    
    # Test 1: Comparison operators
    print("\n" + "-" * 40)
    print("Test 1: Comparison Operators")
    print("-" * 40)
    
    c1 = AtomicConstraint('c1', 'count', OperatorType.LTEQ, RightOperand.literal(10))
    c2 = AtomicConstraint('c2', 'count', OperatorType.GTEQ, RightOperand.literal(20))
    
    result = judge_constraints(c1, c2)
    print(f"  count <= 10 AND count >= 20")
    print(f"  Judgment: {result.judgment.value}")
    
    c3 = AtomicConstraint('c3', 'count', OperatorType.GTEQ, RightOperand.literal(5))
    result = judge_constraints(c1, c3)
    print(f"  count <= 10 AND count >= 5")
    print(f"  Judgment: {result.judgment.value}")
    if result.counterexample:
        print(f"  Model: {result.counterexample}")
    
    # Test 2: isAnyOf operator
    print("\n" + "-" * 40)
    print("Test 2: isAnyOf Operator")
    print("-" * 40)
    
    c4 = AtomicConstraint('c4', 'count', OperatorType.IS_ANY_OF, RightOperand.literal([5, 10, 15, 20]))
    c5 = AtomicConstraint('c5', 'count', OperatorType.GT, RightOperand.literal(12))
    
    result = judge_constraints(c4, c5)
    print(f"  count isAnyOf [5, 10, 15, 20] AND count > 12")
    print(f"  Judgment: {result.judgment.value}")
    if result.counterexample:
        print(f"  Model: {result.counterexample}")
    
    # Test 3: isNoneOf operator
    print("\n" + "-" * 40)
    print("Test 3: isNoneOf Operator")
    print("-" * 40)
    
    c6 = AtomicConstraint('c6', 'count', OperatorType.IS_NONE_OF, RightOperand.literal([5, 10, 15]))
    c7 = AtomicConstraint('c7', 'count', OperatorType.EQ, RightOperand.literal(10))
    
    result = judge_constraints(c6, c7)
    print(f"  count isNoneOf [5, 10, 15] AND count == 10")
    print(f"  Judgment: {result.judgment.value}")
    
    # Test 4: isAllOf operator (degenerate)
    print("\n" + "-" * 40)
    print("Test 4: isAllOf Operator")
    print("-" * 40)
    
    c8 = AtomicConstraint('c8', 'count', OperatorType.IS_ALL_OF, RightOperand.literal([10, 10, 10]))
    c9 = AtomicConstraint('c9', 'count', OperatorType.GTEQ, RightOperand.literal(5))
    
    result = judge_constraints(c8, c9)
    print(f"  count isAllOf [10, 10, 10] AND count >= 5")
    print(f"  Judgment: {result.judgment.value}")
    if result.counterexample:
        print(f"  Model: {result.counterexample}")
    
    c10 = AtomicConstraint('c10', 'count', OperatorType.IS_ALL_OF, RightOperand.literal([10, 20]))
    result = judge_constraints(c10, c9)
    print(f"  count isAllOf [10, 20] AND count >= 5")
    print(f"  Judgment: {result.judgment.value} (impossible - different values)")
    
    # Test 5: DateTime with isAnyOf
    print("\n" + "-" * 40)
    print("Test 5: DateTime with Set Operators")
    print("-" * 40)
    
    from datetime import datetime, timezone
    dt1 = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
    dt2 = int(datetime(2024, 6, 1, tzinfo=timezone.utc).timestamp())
    dt3 = int(datetime(2024, 12, 1, tzinfo=timezone.utc).timestamp())
    
    c11 = AtomicConstraint('c11', 'dateTime', OperatorType.IS_ANY_OF, RightOperand.literal([dt1, dt2, dt3]))
    c12 = AtomicConstraint('c12', 'dateTime', OperatorType.GT, RightOperand.literal(dt2))
    
    result = judge_constraints(c11, c12)
    print(f"  dateTime isAnyOf [2024-01-01, 2024-06-01, 2024-12-01]")
    print(f"  AND dateTime > 2024-06-01")
    print(f"  Judgment: {result.judgment.value}")
    if result.counterexample:
        print(f"  Model: {result.counterexample}")
    
    # Test 6: payAmount with units
    print("\n" + "-" * 40)
    print("Test 6: payAmount with Units")
    print("-" * 40)
    
    from core.constraint_types import ConstraintMetadata
    
    c13 = AtomicConstraint(
        uid='c13',
        left_operand='payAmount',
        operator=OperatorType.IS_ANY_OF,
        right_operand=RightOperand.literal([10.0, 25.0, 50.0, 100.0]),
        metadata=ConstraintMetadata(unit="http://qudt.org/vocab/unit/EUR")
    )
    c14 = AtomicConstraint(
        uid='c14',
        left_operand='payAmount',
        operator=OperatorType.GTEQ,
        right_operand=RightOperand.literal(75.0),
        metadata=ConstraintMetadata(unit="http://qudt.org/vocab/unit/EUR")
    )
    
    result = judge_constraints(c13, c14)
    print(f"  payAmount isAnyOf [10, 25, 50, 100] EUR")
    print(f"  AND payAmount >= 75 EUR")
    print(f"  Judgment: {result.judgment.value}")
    if result.counterexample:
        print(f"  Model: {result.counterexample}")
    
    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)