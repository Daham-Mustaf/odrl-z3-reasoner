# src/encoder/z3_encoder.py
"""
ODRL-SA Z3 Encoder

Encodes FULL class (L_xsd) constraints to Z3 formulas for SMT solving.

Implements the abstract interpretation from the formal specification:
    
    Abstraction Function (Definition 8):
        α(c) maps constraint c to abstract domain element
        
    For operator ⋈ and value v:
        eq  → [v, v]
        neq → ⊤ (over-approximation, refined by SMT)
        lt  → [inf, v)
        lteq → [inf, v]
        gt  → (v, sup]
        gteq → [v, sup]

    Meet Operation (Definition 9):
        [a,b] ⊓ [c,d] = [max(a,c), min(b,d)] if valid, else ⊥

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
    # Comparisons
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

from core.types import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
    Judgment,
    ConstraintClass,
)
from core.classifier import classify_constraint, L_XSD
from core.judgment import JudgmentResult, is_comparable

logger = logging.getLogger(__name__)


# =============================================================================
# DOMAIN BOUNDS (Table 6 from XSD Reference)
# =============================================================================

@dataclass
class DomainBounds:
    """Domain bounds for a LeftOperand."""
    min_val: Optional[float]  # None = -∞
    max_val: Optional[float]  # None = +∞
    is_integer: bool
    use_real: bool  # Use Real sort instead of Int

# Domain bounds per LeftOperand (from formal spec)
DOMAIN_BOUNDS: Dict[str, DomainBounds] = {
    # Numeric
    "count": DomainBounds(0, None, True, False),
    "percentage": DomainBounds(0, 100, False, True),
    "payAmount": DomainBounds(0, None, False, True),
    "resolution": DomainBounds(0, None, False, True),
    
    # Temporal
    "dateTime": DomainBounds(None, None, True, False),  # Unix timestamp
    "timeInterval": DomainBounds(0, None, True, False),  # Seconds
    
    # Positional - Absolute
    "absolutePosition": DomainBounds(0, None, False, True),
    "absoluteSize": DomainBounds(0, None, False, True),
    "absoluteTemporalPosition": DomainBounds(0, None, False, True),
    "absoluteSpatialPosition": DomainBounds(0, None, False, True),
    
    # Positional - Relative (0-100%)
    "relativePosition": DomainBounds(0, 100, False, True),
    "relativeSize": DomainBounds(0, 100, False, True),
    "relativeTemporalPosition": DomainBounds(0, 100, False, True),
    "relativeSpatialPosition": DomainBounds(0, 100, False, True),
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
    
    def get_variable(
        self, 
        left_operand: str,
        unit: Optional[str] = None,
        unit_of_count: Optional[str] = None
    ) -> Any:
        """Get or create Z3 variable for a constraint."""
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
            # policyUsage - cannot encode statically
            logger.warning(f"Cannot encode policyUsage constraint: {constraint}")
            return BoolVal(True)  # Over-approximate as always satisfiable
        
        if constraint.right_operand.is_iri:
            # IRI reference - treat as string equality
            # This is a simplification for FULL class
            return BoolVal(True)
        
        # Convert value to Z3
        z3_value = self._to_z3_value(value, var)
        
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
        else:
            # Set-based operators - not handled in FULL class
            logger.warning(f"Set operator {op} not handled in FULL encoder")
            return BoolVal(True)
    
    def _to_z3_value(self, value: Any, var: Any) -> Any:
        """Convert Python value to Z3 value matching variable sort."""
        if value is None:
            return IntVal(0)
        
        # Handle datetime (convert to timestamp)
        if hasattr(value, 'timestamp'):
            value = int(value.timestamp())
        
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
                # String value - return 0 as placeholder
                logger.warning(f"Cannot convert string '{value}' to Z3 numeric")
                return IntVal(0)
        
        return IntVal(0)


# =============================================================================
# COMPOSITE CONSTRAINT ENCODER
# =============================================================================

class CompositeEncoder:
    """
    Encodes CompositeConstraints (logical combinations).
    """
    
    def __init__(self, constraint_encoder: ConstraintEncoder):
        self.constraint_encoder = constraint_encoder
        self._constraint_map: Dict[str, AtomicConstraint] = {}
    
    def register_constraint(self, constraint: AtomicConstraint):
        """Register an atomic constraint for reference by composites."""
        self._constraint_map[constraint.uid] = constraint
    
    def encode(self, composite: CompositeConstraint) -> Any:
        """Encode a composite constraint."""
        # Encode all operands
        encoded_operands = []
        for operand in composite.operands:
            if isinstance(operand, str):
                # Reference to registered constraint
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
        
        # Apply logical operator
        op = composite.operator
        
        if op == LogicalOperator.AND:
            return And(*encoded_operands)
        elif op == LogicalOperator.OR:
            return Or(*encoded_operands)
        elif op == LogicalOperator.XONE:
            # Exactly one: sum of (1 if true else 0) = 1
            # Encode as: Or of (this AND NOT all others)
            xone_clauses = []
            for i, enc in enumerate(encoded_operands):
                others = [Not(e) for j, e in enumerate(encoded_operands) if j != i]
                xone_clauses.append(And(enc, *others))
            return Or(*xone_clauses)
        elif op == LogicalOperator.AND_SEQUENCE:
            # For static analysis, treat as AND (sequence requires runtime)
            return And(*encoded_operands)
        
        return BoolVal(True)


# =============================================================================
# JUDGMENT ENGINE (SMT-based)
# =============================================================================

class Z3JudgmentEngine:
    """
    Performs judgment using Z3 SMT solver.
    
    Implements Definition 6 (Judgment Rules):
        judge(c₁, c₂) = 
            CONFLICT           if comparable ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# = ⊥
            POSSIBLY-COMPATIBLE if comparable ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# ≠ ⊥
            UNKNOWN            if ¬comparable
    """
    
    def __init__(self):
        self.var_manager = Z3VariableManager()
        self.constraint_encoder = ConstraintEncoder(self.var_manager)
    
    def judge(
        self, 
        c1: AtomicConstraint, 
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """
        Judge two constraints.
        
        Returns:
            CONFLICT if unsatisfiable
            POSSIBLY-COMPATIBLE if satisfiable
            UNKNOWN if not comparable
        """
        # Check comparability first
        comp_result = is_comparable(c1, c2)
        if not comp_result.comparable:
            return JudgmentResult(
                judgment=Judgment.UNKNOWN,
                comparable=False,
                incomparability_reason=comp_result.reason,
                explanation=comp_result.details
            )
        
        # Reset variable manager
        self.var_manager.clear()
        
        # Encode constraints
        z3_c1 = self.constraint_encoder.encode(c1)
        z3_c2 = self.constraint_encoder.encode(c2)
        
        # Get domain bounds
        domain_constraints = self.var_manager.get_domain_constraints()
        
        # Create solver and check satisfiability
        solver = Solver()
        solver.add(And(z3_c1, z3_c2))
        solver.add(*domain_constraints)
        
        result = solver.check()
        
        if result == unsat:
            return JudgmentResult(
                judgment=Judgment.CONFLICT,
                comparable=True,
                explanation=f"UNSAT: {c1} ∧ {c2} has no solution"
            )
        elif result == sat:
            # Extract counterexample
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
        """
        Check if a set of constraints is satisfiable.
        
        Returns:
            (CONFLICT, None) if unsatisfiable
            (POSSIBLY-COMPATIBLE, model) if satisfiable
            (UNKNOWN, None) if undetermined
        """
        # Reset
        self.var_manager.clear()
        
        # Encode all constraints
        encoded = [self.constraint_encoder.encode(c) for c in constraints]
        domain_constraints = self.var_manager.get_domain_constraints()
        
        # Solve
        solver = Solver()
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
            
            # Convert Z3 value to Python
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

def judge_constraints(
    c1: AtomicConstraint, 
    c2: AtomicConstraint
) -> JudgmentResult:
    """
    Convenience function to judge two constraints.
    
    Example:
        result = judge_constraints(c1, c2)
        if result.judgment == Judgment.CONFLICT:
            print("Constraints conflict!")
    """
    engine = Z3JudgmentEngine()
    return engine.judge(c1, c2)


def check_consistency(constraints: List[AtomicConstraint]) -> Tuple[Judgment, Optional[Dict]]:
    """
    Check if a list of constraints is consistent (satisfiable).
    
    Example:
        judgment, model = check_consistency([c1, c2, c3])
        if judgment == Judgment.CONFLICT:
            print("Constraints are inconsistent!")
    """
    engine = Z3JudgmentEngine()
    return engine.check_satisfiability(constraints)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    from core.types import RightOperand
    
    print("=" * 60)
    print("Z3 Encoder Test")
    print("=" * 60)
    
    # Test 1: Conflict detection
    print("\nTest 1: Conflict (count ≤ 10 ∧ count ≥ 20)")
    c1 = AtomicConstraint(
        uid='c1',
        left_operand='count',
        operator=OperatorType.LTEQ,
        right_operand=RightOperand.literal(10)
    )
    c2 = AtomicConstraint(
        uid='c2',
        left_operand='count',
        operator=OperatorType.GTEQ,
        right_operand=RightOperand.literal(20)
    )
    
    result = judge_constraints(c1, c2)
    print(f"  c1: {c1}")
    print(f"  c2: {c2}")
    print(f"  Judgment: {result.judgment.value}")
    print(f"  Explanation: {result.explanation}")
    
    # Test 2: Compatible
    print("\nTest 2: Compatible (count ≤ 10 ∧ count ≥ 5)")
    c3 = AtomicConstraint(
        uid='c3',
        left_operand='count',
        operator=OperatorType.GTEQ,
        right_operand=RightOperand.literal(5)
    )
    
    result = judge_constraints(c1, c3)
    print(f"  c1: {c1}")
    print(f"  c3: {c3}")
    print(f"  Judgment: {result.judgment.value}")
    if result.counterexample:
        print(f"  Counterexample: {result.counterexample}")
    
    # Test 3: DateTime conflict
    print("\nTest 3: DateTime conflict")
    c4 = AtomicConstraint(
        uid='c4',
        left_operand='dateTime',
        operator=OperatorType.LT,
        right_operand=RightOperand.literal(1704067200)  # 2024-01-01
    )
    c5 = AtomicConstraint(
        uid='c5',
        left_operand='dateTime',
        operator=OperatorType.GT,
        right_operand=RightOperand.literal(1735689600)  # 2025-01-01
    )
    
    result = judge_constraints(c4, c5)
    print(f"  c4: {c4}")
    print(f"  c5: {c5}")
    print(f"  Judgment: {result.judgment.value}")
    
    # Test 4: Consistency check
    print("\nTest 4: Consistency check (3 constraints)")
    constraints = [
        AtomicConstraint('x1', 'percentage', OperatorType.GTEQ, RightOperand.literal(10)),
        AtomicConstraint('x2', 'percentage', OperatorType.LTEQ, RightOperand.literal(50)),
        AtomicConstraint('x3', 'percentage', OperatorType.GT, RightOperand.literal(60)),  # Conflict!
    ]
    
    judgment, model = check_consistency(constraints)
    print(f"  Constraints: {[str(c) for c in constraints]}")
    print(f"  Judgment: {judgment.value}")
    
    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)