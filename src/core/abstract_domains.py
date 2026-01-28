# =============================================================================
# Abstract Interpretation Domains for ODRL-SA
# =============================================================================
#
# Implements interval abstract domains for all 𝓛_xsd equivalence classes:
#   - BoundedDomain: 𝓛_bounded = [0, 100]
#   - IntegerDomain: 𝓛_int = ℤ≥0
#   - DateTimeDomain: 𝓛_datetime = ℤ
#   - UnitDependentDomain: 𝓛_unit = ℝ≥0
#   - RealDomain: 𝓛_real = ℝ≥0
#   - CoordsDomain: 𝓛_coords = ℝ≥0²
#   - VocabDomain: 𝓛_vocab = finite set
#   - RefDomain: 𝓛_ref = ℤ≥0 (partial)
#
# Theory Reference: Final Classification, Theorems 1-4
# =============================================================================

from dataclasses import dataclass
from typing import Optional, List, Tuple, Set, Any
import math


# =============================================================================
# INTERVAL ABSTRACT DOMAIN
# =============================================================================

@dataclass
class Interval:
    """
    Numeric interval [lo, hi] or ⊥ (empty).
    
    Lattice structure:
    - ⊥ (bottom): empty set
    - ⊤ (top): unbounded interval
    - ⊓ (meet): intersection
    - ⊔ (join): convex hull
    """
    lo: Optional[float] = None  # None = -∞
    hi: Optional[float] = None  # None = +∞
    is_bottom: bool = False
    
    @staticmethod
    def bottom() -> 'Interval':
        return Interval(None, None, is_bottom=True)
    
    @staticmethod
    def top() -> 'Interval':
        return Interval(None, None, is_bottom=False)
    
    @staticmethod
    def point(v: float) -> 'Interval':
        return Interval(v, v)
    
    @staticmethod
    def closed(lo: float, hi: float) -> 'Interval':
        if lo > hi:
            return Interval.bottom()
        return Interval(lo, hi)
    
    def meet(self, other: 'Interval') -> 'Interval':
        """Intersection: [a,b] ⊓ [c,d] = [max(a,c), min(b,d)]"""
        if self.is_bottom or other.is_bottom:
            return Interval.bottom()
        
        lo = max(self.lo or -math.inf, other.lo or -math.inf)
        hi = min(self.hi or math.inf, other.hi or math.inf)
        
        if lo > hi:
            return Interval.bottom()
        
        return Interval(
            lo if lo != -math.inf else None,
            hi if hi != math.inf else None
        )
    
    def join(self, other: 'Interval') -> 'Interval':
        """Convex hull: [a,b] ⊔ [c,d] = [min(a,c), max(b,d)]"""
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        
        lo = min(self.lo or -math.inf, other.lo or -math.inf)
        hi = max(self.hi or math.inf, other.hi or math.inf)
        
        return Interval(
            lo if lo != -math.inf else None,
            hi if hi != math.inf else None
        )
    
    def is_empty(self) -> bool:
        return self.is_bottom
    
    def contains(self, value: float) -> bool:
        if self.is_bottom:
            return False
        lo = self.lo if self.lo is not None else -math.inf
        hi = self.hi if self.hi is not None else math.inf
        return lo <= value <= hi
    
    def __repr__(self) -> str:
        if self.is_bottom:
            return "⊥"
        lo_str = str(self.lo) if self.lo is not None else "-∞"
        hi_str = str(self.hi) if self.hi is not None else "+∞"
        return f"[{lo_str}, {hi_str}]"


# =============================================================================
# ABSTRACTION FUNCTION
# =============================================================================

def alpha(operator: str, value: float, 
          domain_min: float = None, domain_max: float = None) -> Interval:
    """
    Abstraction function α: constraints → abstract domain
    
    | Operator | α(constraint)           |
    |----------|-------------------------|
    | eq v     | [v, v]                  |
    | neq v    | ⊤ (over-approximation)  |
    | lt v     | [min, v-ε]              |
    | lteq v   | [min, v]                |
    | gt v     | [v+ε, max]              |
    | gteq v   | [v, max]                |
    """
    d_min = domain_min if domain_min is not None else -math.inf
    d_max = domain_max if domain_max is not None else math.inf
    
    if operator == 'eq':
        return Interval.point(value)
    elif operator == 'neq':
        return Interval(
            d_min if d_min != -math.inf else None,
            d_max if d_max != math.inf else None
        )
    elif operator == 'lt':
        return Interval(
            d_min if d_min != -math.inf else None,
            value
        )
    elif operator == 'lteq':
        return Interval(
            d_min if d_min != -math.inf else None,
            value
        )
    elif operator == 'gt':
        return Interval(
            value,
            d_max if d_max != math.inf else None
        )
    elif operator == 'gteq':
        return Interval(
            value,
            d_max if d_max != math.inf else None
        )
    elif operator == 'isAnyOf':
        if isinstance(value, (list, tuple)):
            result = Interval.bottom()
            for v in value:
                result = result.join(Interval.point(v))
            return result
        return Interval.point(value)
    elif operator == 'isNoneOf':
        return Interval(
            d_min if d_min != -math.inf else None,
            d_max if d_max != math.inf else None
        )
    else:
        return Interval(
            d_min if d_min != -math.inf else None,
            d_max if d_max != math.inf else None
        )


# =============================================================================
# EQUIVALENCE CLASS DOMAINS
# =============================================================================

class BoundedDomain:
    """
    𝓛_bounded = {percentage, relativePosition, relativeSize, 
                 relativeTemporalPosition, relativeSpatialPosition}
    
    Domain: [0, 100]
    SMT Theory: QF-LRA
    
    Theorem 1 (Bounded Equivalence):
    The five LeftOperands in 𝓛_bounded are formally equivalent and can be
    analyzed by a unified procedure parameterized only by operator and value.
    """
    DOMAIN_MIN = 0
    DOMAIN_MAX = 100
    MEMBERS = {"percentage", "relativePosition", "relativeSize",
               "relativeTemporalPosition", "relativeSpatialPosition"}
    
    @classmethod
    def alpha(cls, operator: str, value: float) -> Interval:
        return alpha(operator, value, domain_min=cls.DOMAIN_MIN, domain_max=cls.DOMAIN_MAX)
    
    @classmethod
    def is_valid_value(cls, value: float) -> bool:
        return cls.DOMAIN_MIN <= value <= cls.DOMAIN_MAX
    
    @classmethod
    def top(cls) -> Interval:
        return Interval(cls.DOMAIN_MIN, cls.DOMAIN_MAX)


class IntegerDomain:
    """
    𝓛_int = {count, timeInterval}
    
    Domain: ℤ≥0
    SMT Theory: QF-LIA
    """
    DOMAIN_MIN = 0
    DOMAIN_MAX = None
    MEMBERS = {"count", "timeInterval"}
    
    @classmethod
    def alpha(cls, operator: str, value: int) -> Interval:
        return alpha(operator, value, domain_min=cls.DOMAIN_MIN, domain_max=None)
    
    @classmethod
    def is_valid_value(cls, value: float) -> bool:
        return value >= 0 and value == int(value)
    
    @classmethod
    def top(cls) -> Interval:
        return Interval(cls.DOMAIN_MIN, None)


class DateTimeDomain:
    """
    𝓛_datetime = {dateTime}
    
    Domain: ℤ (Unix timestamp, unbounded)
    SMT Theory: QF-LIA
    """
    DOMAIN_MIN = None
    DOMAIN_MAX = None
    MEMBERS = {"dateTime"}
    
    @classmethod
    def alpha(cls, operator: str, value: int) -> Interval:
        return alpha(operator, value, domain_min=None, domain_max=None)
    
    @classmethod
    def top(cls) -> Interval:
        return Interval.top()


class UnitDependentDomain:
    """
    𝓛_unit = {payAmount, resolution, absolutePosition, absoluteSize}
    
    Domain: ℝ≥0 (or ℝ>0 for resolution, absoluteSize)
    SMT Theory: QF-LRA
    
    Comparability Rule: Same unit required; no automatic conversion.
    """
    DOMAIN_MIN = 0
    DOMAIN_MAX = None
    MEMBERS = {"payAmount", "resolution", "absolutePosition", "absoluteSize"}
    STRICT_POSITIVE = {"resolution", "absoluteSize"}  # ℝ>0
    
    @classmethod
    def alpha(cls, operator: str, value: float) -> Interval:
        return alpha(operator, value, domain_min=cls.DOMAIN_MIN, domain_max=None)
    
    @classmethod
    def is_valid_value(cls, value: float, operand: str = None) -> bool:
        if operand in cls.STRICT_POSITIVE:
            return value > 0
        return value >= 0
    
    @classmethod
    def top(cls) -> Interval:
        return Interval(cls.DOMAIN_MIN, None)


class RealDomain:
    """
    𝓛_real = {absoluteTemporalPosition}
    
    Domain: ℝ≥0
    SMT Theory: QF-LRA
    """
    DOMAIN_MIN = 0
    DOMAIN_MAX = None
    MEMBERS = {"absoluteTemporalPosition"}
    
    @classmethod
    def alpha(cls, operator: str, value: float) -> Interval:
        return alpha(operator, value, domain_min=cls.DOMAIN_MIN, domain_max=None)
    
    @classmethod
    def top(cls) -> Interval:
        return Interval(cls.DOMAIN_MIN, None)


class CoordsDomain:
    """
    𝓛_coords = {absoluteSpatialPosition}
    
    Domain: ℝ≥0² (2D) or ℝ≥0³ (3D)
    SMT Theory: QF-LRA
    Operators: Only eq/neq meaningful statically
    """
    DOMAIN_MIN = 0
    DOMAIN_MAX = None
    MEMBERS = {"absoluteSpatialPosition"}
    VALID_OPERATORS = {"eq", "neq"}
    
    @classmethod
    def alpha(cls, operator: str, value: float) -> Interval:
        if operator not in cls.VALID_OPERATORS:
            return Interval.top()  # Over-approximate for invalid operators
        return alpha(operator, value, domain_min=cls.DOMAIN_MIN, domain_max=None)


class VocabDomain:
    """
    𝓛_vocab = {unitOfCount}
    
    Domain: 𝒰 = {perUser, perDevice, perOrganization, perSession} ∪ extensions
    SMT Theory: QF-UF
    """
    MEMBERS = {"unitOfCount"}
    STANDARD_VALUES = {"perUser", "perDevice", "perOrganization", "perSession"}
    
    @classmethod
    def is_valid_value(cls, value: str) -> bool:
        # Standard values are always valid; extensions are allowed
        return True
    
    @classmethod
    def is_standard_value(cls, value: str) -> bool:
        return value in cls.STANDARD_VALUES


class RefDomain:
    """
    𝓛_ref = {elapsedTime, delayPeriod}
    
    Domain: ℤ≥0 (duration in seconds)
    SMT Theory: QF-LIA
    Static Analysis: ⚠️ Partial (assumes policy activation as reference)
    """
    DOMAIN_MIN = 0
    DOMAIN_MAX = None
    MEMBERS = {"elapsedTime", "delayPeriod"}
    
    @classmethod
    def alpha(cls, operator: str, value: int) -> Interval:
        return alpha(operator, value, domain_min=cls.DOMAIN_MIN, domain_max=None)
    
    @classmethod
    def top(cls) -> Interval:
        return Interval(cls.DOMAIN_MIN, None)


# =============================================================================
# DOMAIN LOOKUP
# =============================================================================

def get_domain_for_operand(operand: str):
    """Get the appropriate domain class for a LeftOperand."""
    if operand in BoundedDomain.MEMBERS:
        return BoundedDomain
    elif operand in IntegerDomain.MEMBERS:
        return IntegerDomain
    elif operand in DateTimeDomain.MEMBERS:
        return DateTimeDomain
    elif operand in UnitDependentDomain.MEMBERS:
        return UnitDependentDomain
    elif operand in RealDomain.MEMBERS:
        return RealDomain
    elif operand in CoordsDomain.MEMBERS:
        return CoordsDomain
    elif operand in VocabDomain.MEMBERS:
        return VocabDomain
    elif operand in RefDomain.MEMBERS:
        return RefDomain
    else:
        return None


def check_conflict_abstract(
    c1_op: str, c1_val: float,
    c2_op: str, c2_val: float,
    operand: str
) -> str:
    """
    Check for conflict using abstract interpretation.
    
    Returns: 'CONFLICT', 'POSSIBLY-COMPATIBLE', or 'UNKNOWN'
    """
    domain = get_domain_for_operand(operand)
    if domain is None:
        return 'UNKNOWN'
    
    abs1 = domain.alpha(c1_op, c1_val)
    abs2 = domain.alpha(c2_op, c2_val)
    
    result = abs1.meet(abs2)
    
    if result.is_empty():
        return 'CONFLICT'
    else:
        return 'POSSIBLY-COMPATIBLE'


# =============================================================================
# STATISTICS
# =============================================================================

def print_statistics():
    """Print classification statistics."""
    print("=" * 60)
    print("ODRL LeftOperand Abstract Domain Statistics")
    print("=" * 60)
    
    domains = [
        ("𝓛_bounded", BoundedDomain),
        ("𝓛_int", IntegerDomain),
        ("𝓛_datetime", DateTimeDomain),
        ("𝓛_unit", UnitDependentDomain),
        ("𝓛_real", RealDomain),
        ("𝓛_coords", CoordsDomain),
        ("𝓛_vocab", VocabDomain),
        ("𝓛_ref", RefDomain),
    ]
    
    total = 0
    for name, domain in domains:
        count = len(domain.MEMBERS)
        total += count
        print(f"{name}: {count} → {domain.MEMBERS}")
    
    print(f"\nTotal in 𝓛_xsd ∪ 𝓛_vocab ∪ 𝓛_ref: {total}")
    print(f"\nTheorem 2 (Coverage):")
    print(f"  ✅ Fully Analyzable: 15 (47%)")
    print(f"  ⚠️  Partially Analyzable: 2 (6%)")
    print(f"  ❌ Requires External/Runtime: 15 (47%)")


if __name__ == "__main__":
    print_statistics()
    
    # Test examples
    print("\n" + "=" * 60)
    print("Test Examples")
    print("=" * 60)
    
    # Test bounded domain
    print("\n--- 𝓛_bounded (percentage) ---")
    print(f"eq 50: {BoundedDomain.alpha('eq', 50)}")
    print(f"lteq 30: {BoundedDomain.alpha('lteq', 30)}")
    print(f"gteq 50: {BoundedDomain.alpha('gteq', 50)}")
    print(f"lteq 30 ⊓ gteq 50: {BoundedDomain.alpha('lteq', 30).meet(BoundedDomain.alpha('gteq', 50))}")
    
    # Test integer domain
    print("\n--- 𝓛_int (count) ---")
    print(f"eq 5: {IntegerDomain.alpha('eq', 5)}")
    print(f"lt 10: {IntegerDomain.alpha('lt', 10)}")