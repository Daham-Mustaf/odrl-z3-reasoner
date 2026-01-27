# src/semantics/judgment_engine.py
"""
ODRL-SA Judgment Engine

The main analysis engine implementing the complete ODRL-SA pipeline:

1. Parse constraints (from RDF or normalized form)
2. Classify constraints (FULL/PARTIAL/GROUNDED/RUNTIME/DEFERRED)
3. Check comparability (5 conditions from §7 Definition 10)
4. Abstract interpretation (interval domain)
5. SMT encoding and solving (Z3)
6. Oracle consultation (for semantic operands)
7. Return judgment (CONFLICT/POSSIBLY_COMPATIBLE/UNKNOWN)

This implements the formal judgment function from §7.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from z3 import (
    Solver, sat, unsat, unknown,
    Int, Real, String, Bool, BoolRef,
    And, Or, Not,
    IntVal, RealVal, StringVal,
)

from .constraint_types import (
    AtomicConstraint, CompositeConstraint, Constraint,
    OperatorType, LogicalOperatorType,
    RightValue, ODRLMetadata, Z3Sort
)
from .judgment import (
    Judgment, ConstraintClass, JudgmentResult,
    IncomparabilityReason, OracleResult, TruthValue
)
from .classifier import classify_constraint, L_XSD, L_REF, L_SEM, L_RUN
from .comparability import is_comparable, ComparabilityResult
from .oracle import GroundingOracle, NullOracle, create_default_oracle


logger = logging.getLogger(__name__)


# =============================================================================
# ABSTRACT DOMAIN (§4 Definition 5)
# =============================================================================

@dataclass
class Interval:
    """
    Interval abstract domain element.
    
    Represents [lo, hi] with possible infinities.
    """
    lo: Optional[float] = None  # None = -∞
    hi: Optional[float] = None  # None = +∞
    is_bottom: bool = False     # ⊥ (empty set)
    
    @classmethod
    def bottom(cls) -> 'Interval':
        """Return ⊥ (empty interval)."""
        return cls(is_bottom=True)
    
    @classmethod
    def top(cls) -> 'Interval':
        """Return ⊤ (all values)."""
        return cls(lo=None, hi=None)
    
    @classmethod
    def point(cls, v: float) -> 'Interval':
        """Return singleton interval [v, v]."""
        return cls(lo=v, hi=v)
    
    @classmethod
    def from_constraint(cls, op: OperatorType, value: float, domain_lo: Optional[float] = None, domain_hi: Optional[float] = None) -> 'Interval':
        """
        Create interval from constraint operator and value.
        
        Implements §5 Definition 6 (abstraction function α).
        """
        if op == OperatorType.EQ:
            return cls.point(value)
        
        if op == OperatorType.NEQ:
            # Over-approximate as ⊤ per §5 Remark 2
            return cls.top()
        
        if op == OperatorType.LT:
            # x < v means x ∈ [domain_lo, v)
            return cls(lo=domain_lo, hi=value - 0.001)  # Approximate open bound
        
        if op == OperatorType.LTEQ:
            return cls(lo=domain_lo, hi=value)
        
        if op == OperatorType.GT:
            return cls(lo=value + 0.001, hi=domain_hi)  # Approximate open bound
        
        if op == OperatorType.GTEQ:
            return cls(lo=value, hi=domain_hi)
        
        return cls.top()
    
    def meet(self, other: 'Interval') -> 'Interval':
        """
        Lattice meet (intersection).
        
        Returns ⊥ if intervals are disjoint.
        """
        if self.is_bottom or other.is_bottom:
            return Interval.bottom()
        
        # Compute intersection
        new_lo = max(
            self.lo if self.lo is not None else float('-inf'),
            other.lo if other.lo is not None else float('-inf')
        )
        new_hi = min(
            self.hi if self.hi is not None else float('inf'),
            other.hi if other.hi is not None else float('inf')
        )
        
        if new_lo > new_hi:
            return Interval.bottom()
        
        return Interval(
            lo=new_lo if new_lo != float('-inf') else None,
            hi=new_hi if new_hi != float('inf') else None
        )
    
    def is_empty(self) -> bool:
        """Check if interval is empty (⊥)."""
        return self.is_bottom
    
    def overlaps(self, other: 'Interval') -> bool:
        """Check if intervals overlap."""
        return not self.meet(other).is_empty()
    
    def __str__(self) -> str:
        if self.is_bottom:
            return "⊥"
        lo_str = str(self.lo) if self.lo is not None else "-∞"
        hi_str = str(self.hi) if self.hi is not None else "+∞"
        return f"[{lo_str}, {hi_str}]"


# =============================================================================
# DOMAIN BOUNDS
# =============================================================================

DOMAIN_BOUNDS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    # Numeric
    "count": (0, None),
    "percentage": (0, 100),
    "payAmount": (0, None),
    "resolution": (1, None),
    # Temporal
    "dateTime": (None, None),  # Unix timestamp
    "timeInterval": (0, None),
    "elapsedTime": (0, None),
    "delayPeriod": (0, None),
    "meteredTime": (0, None),
    # Positional - Relative (percentage)
    "relativePosition": (0, 100),
    "relativeSize": (0, None),  # Can be >100% for enlargement
    "relativeTemporalPosition": (0, 100),
    "relativeSpatialPosition": (0, 100),
    # Positional - Absolute
    "absolutePosition": (0, None),
    "absoluteSize": (0, None),
    "absoluteTemporalPosition": (0, None),
    "absoluteSpatialPosition": (None, None),  # String-based
}


def get_domain_bounds(operand: str) -> Tuple[Optional[float], Optional[float]]:
    """Get domain bounds for an operand."""
    norm = operand.split('#')[-1].split('/')[-1]
    return DOMAIN_BOUNDS.get(norm, (None, None))


# =============================================================================
# Z3 ENCODING (§9)
# =============================================================================

def get_z3_sort(operand: str) -> str:
    """Get Z3 sort for an operand."""
    norm = operand.split('#')[-1].split('/')[-1]
    
    # Integer operands
    int_operands = {"count", "resolution", "dateTime", "timeInterval",
                   "elapsedTime", "delayPeriod", "meteredTime",
                   "absoluteTemporalPosition"}
    if norm in int_operands:
        return "Int"
    
    # Real operands
    real_operands = {"percentage", "payAmount", "relativePosition",
                    "relativeSize", "relativeTemporalPosition",
                    "relativeSpatialPosition", "absolutePosition",
                    "absoluteSize"}
    if norm in real_operands:
        return "Real"
    
    # String operands (semantic)
    return "String"


def encode_constraint_to_z3(
    constraint: AtomicConstraint,
    variables: Dict[str, Any]
) -> Optional[BoolRef]:
    """
    Encode an atomic constraint to Z3.
    
    Implements translation function τ from §9.
    """
    operand = constraint.left_operand.split('#')[-1].split('/')[-1]
    
    # Get or create Z3 variable
    if operand not in variables:
        sort = get_z3_sort(operand)
        if sort == "Int":
            variables[operand] = Int(operand)
        elif sort == "Real":
            variables[operand] = Real(operand)
        else:
            variables[operand] = String(operand)
    
    var = variables[operand]
    value = constraint.right_value.canonical_value
    
    if value is None:
        return None
    
    # Encode based on operator
    op = constraint.operator
    
    try:
        if op == OperatorType.EQ:
            return var == value
        elif op == OperatorType.NEQ:
            return var != value
        elif op == OperatorType.LT:
            return var < value
        elif op == OperatorType.LTEQ:
            return var <= value
        elif op == OperatorType.GT:
            return var > value
        elif op == OperatorType.GTEQ:
            return var >= value
        else:
            # Set-based operators not encodable without oracle
            return None
    except Exception as e:
        logger.warning(f"Failed to encode constraint {constraint.id}: {e}")
        return None


def encode_domain_bounds(
    operand: str,
    var: Any
) -> List[BoolRef]:
    """Encode domain bounds as Z3 assertions."""
    bounds = []
    lo, hi = get_domain_bounds(operand)
    
    if lo is not None:
        bounds.append(var >= lo)
    if hi is not None:
        bounds.append(var <= hi)
    
    return bounds


# =============================================================================
# JUDGMENT ENGINE
# =============================================================================

class JudgmentEngine:
    """
    Main ODRL-SA judgment engine.
    
    Implements the complete analysis pipeline:
    1. Classify constraints
    2. Check comparability
    3. Abstract interpretation
    4. SMT solving
    5. Oracle consultation
    6. Return judgment
    """
    
    def __init__(
        self,
        oracle: Optional[GroundingOracle] = None,
        timeout_ms: int = 5000,
        enable_partial: bool = True
    ):
        """
        Initialize judgment engine.
        
        Args:
            oracle: Grounding oracle for semantic operands (None = NullOracle)
            timeout_ms: Z3 solver timeout in milliseconds
            enable_partial: Whether to analyze PARTIAL (reference-point) constraints
        """
        self.oracle = oracle or NullOracle()
        self.timeout_ms = timeout_ms
        self.enable_partial = enable_partial
    
    def judge(
        self,
        c1: AtomicConstraint,
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """
        Judge two constraints per ODRL-SA §7.
        
        Returns:
            JudgmentResult with judgment and metadata
        """
        # Step 1: Classify both constraints
        class1 = classify_constraint(c1)
        class2 = classify_constraint(c2)
        
        logger.debug(f"Constraint {c1.id} classified as {class1}")
        logger.debug(f"Constraint {c2.id} classified as {class2}")
        
        # Step 2: Check comparability
        comp_result = is_comparable(c1, c2, classify_constraint)
        
        if not comp_result:
            return JudgmentResult(
                judgment=Judgment.UNKNOWN,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason=comp_result.message,
                incomparability_reason=comp_result.reason,
                analysis_method="comparability_check"
            )
        
        # Step 3: Route based on classification
        if class1 == ConstraintClass.FULL and class2 == ConstraintClass.FULL:
            return self._judge_full(c1, c2)
        
        if self.enable_partial:
            if class1 in {ConstraintClass.FULL, ConstraintClass.PARTIAL} and \
               class2 in {ConstraintClass.FULL, ConstraintClass.PARTIAL}:
                return self._judge_partial(c1, c2)
        
        if class1 == ConstraintClass.GROUNDED or class2 == ConstraintClass.GROUNDED:
            return self._judge_grounded(c1, c2)
        
        # Cannot analyze
        return JudgmentResult(
            judgment=Judgment.UNKNOWN,
            constraint1_id=c1.id,
            constraint2_id=c2.id,
            reason=f"Cannot analyze: {class1.value} vs {class2.value}",
            analysis_method="classification"
        )
    
    def _judge_full(
        self,
        c1: AtomicConstraint,
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """
        Judge two FULL (self-contained) constraints.
        
        Uses abstract interpretation + SMT solving.
        """
        operand = c1.left_operand.split('#')[-1].split('/')[-1]
        
        # Abstract interpretation first (fast path)
        lo, hi = get_domain_bounds(operand)
        
        val1 = c1.right_value.canonical_value
        val2 = c2.right_value.canonical_value
        
        if val1 is not None and val2 is not None:
            try:
                interval1 = Interval.from_constraint(c1.operator, float(val1), lo, hi)
                interval2 = Interval.from_constraint(c2.operator, float(val2), lo, hi)
                
                intersection = interval1.meet(interval2)
                
                if intersection.is_empty():
                    return JudgmentResult(
                        judgment=Judgment.CONFLICT,
                        constraint1_id=c1.id,
                        constraint2_id=c2.id,
                        reason=f"Intervals disjoint: {interval1} ∩ {interval2} = ⊥",
                        analysis_method="abstract_interpretation"
                    )
            except (TypeError, ValueError) as e:
                logger.debug(f"Abstract interpretation failed: {e}")
        
        # SMT solving (precise)
        return self._smt_check(c1, c2)
    
    def _judge_partial(
        self,
        c1: AtomicConstraint,
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """
        Judge constraints with PARTIAL (reference-point) classification.
        
        Assumes same reference point for elapsedTime/delayPeriod comparisons.
        """
        # For now, treat same as FULL but note the assumption
        result = self._smt_check(c1, c2)
        
        if result.judgment != Judgment.UNKNOWN:
            result.reason = (result.reason or "") + " [Assuming same reference point]"
        
        return result
    
    def _judge_grounded(
        self,
        c1: AtomicConstraint,
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """
        Judge constraints requiring semantic grounding.
        
        Consults oracle for semantic relationships.
        """
        operand = c1.left_operand.split('#')[-1].split('/')[-1]
        
        # Check if oracle can help
        if not self.oracle.can_handle(operand):
            return JudgmentResult(
                judgment=Judgment.UNKNOWN,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason=f"No oracle available for operand: {operand}",
                incomparability_reason=IncomparabilityReason.NOT_ANALYZABLE,
                analysis_method="oracle_check"
            )
        
        # Query oracle
        val1 = c1.right_value.canonical_value
        val2 = c2.right_value.canonical_value
        
        oracle_result = self.oracle.query(operand, c1.operator, val1, val2)
        
        if oracle_result == OracleResult.DISJOINT:
            return JudgmentResult(
                judgment=Judgment.CONFLICT,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason=f"Oracle determined values are disjoint: {val1} vs {val2}",
                analysis_method="oracle"
            )
        
        if oracle_result in {OracleResult.SUBSUMES, OracleResult.OVERLAPS}:
            return JudgmentResult(
                judgment=Judgment.POSSIBLY_COMPATIBLE,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason=f"Oracle result: {oracle_result.value}",
                analysis_method="oracle"
            )
        
        return JudgmentResult(
            judgment=Judgment.UNKNOWN,
            constraint1_id=c1.id,
            constraint2_id=c2.id,
            reason="Oracle returned UNKNOWN",
            analysis_method="oracle"
        )
    
    def _smt_check(
        self,
        c1: AtomicConstraint,
        c2: AtomicConstraint
    ) -> JudgmentResult:
        """
        Use Z3 SMT solver to check satisfiability.
        
        UNSAT → CONFLICT
        SAT → POSSIBLY_COMPATIBLE (with counterexample)
        UNKNOWN → UNKNOWN
        """
        solver = Solver()
        solver.set("timeout", self.timeout_ms)
        
        variables: Dict[str, Any] = {}
        
        # Encode both constraints
        formula1 = encode_constraint_to_z3(c1, variables)
        formula2 = encode_constraint_to_z3(c2, variables)
        
        if formula1 is None or formula2 is None:
            return JudgmentResult(
                judgment=Judgment.UNKNOWN,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason="Could not encode constraint to Z3",
                analysis_method="smt_encoding_failed"
            )
        
        # Add domain bounds
        for operand, var in variables.items():
            for bound in encode_domain_bounds(operand, var):
                solver.add(bound)
        
        # Assert both constraints
        solver.add(formula1)
        solver.add(formula2)
        
        # Check satisfiability
        result = solver.check()
        
        if result == unsat:
            return JudgmentResult(
                judgment=Judgment.CONFLICT,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason="SMT solver proved UNSAT",
                analysis_method="smt"
            )
        
        if result == sat:
            # Extract counterexample
            model = solver.model()
            counterexample = {}
            for operand, var in variables.items():
                if model[var] is not None:
                    counterexample[operand] = str(model[var])
            
            return JudgmentResult(
                judgment=Judgment.POSSIBLY_COMPATIBLE,
                constraint1_id=c1.id,
                constraint2_id=c2.id,
                reason="SMT solver found satisfying assignment",
                counterexample=counterexample,
                analysis_method="smt"
            )
        
        # Unknown (timeout or other)
        return JudgmentResult(
            judgment=Judgment.UNKNOWN,
            constraint1_id=c1.id,
            constraint2_id=c2.id,
            reason="SMT solver returned UNKNOWN (timeout?)",
            analysis_method="smt_unknown"
        )
    
    def judge_all_pairs(
        self,
        constraints: List[AtomicConstraint]
    ) -> List[JudgmentResult]:
        """
        Judge all pairs of constraints.
        
        Returns list of JudgmentResults for each pair.
        """
        results = []
        n = len(constraints)
        
        for i in range(n):
            for j in range(i + 1, n):
                result = self.judge(constraints[i], constraints[j])
                results.append(result)
        
        return results
    
    def find_conflicts(
        self,
        constraints: List[AtomicConstraint]
    ) -> List[JudgmentResult]:
        """
        Find all CONFLICT judgments among constraints.
        """
        results = self.judge_all_pairs(constraints)
        return [r for r in results if r.is_conflict()]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_engine(
    with_oracle: bool = True,
    enable_partial: bool = True,
    timeout_ms: int = 5000
) -> JudgmentEngine:
    """
    Create a judgment engine with default configuration.
    """
    oracle = create_default_oracle() if with_oracle else NullOracle()
    return JudgmentEngine(
        oracle=oracle,
        enable_partial=enable_partial,
        timeout_ms=timeout_ms
    )