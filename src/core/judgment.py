# src/core/judgment.py
"""
ODRL-SA Judgment Functions

Implements Definition 5 (Judgment) and Definition 6 (Judgment Rules):

Definition 5:
    judge : C × C → {CONFLICT, POSSIBLY-COMPATIBLE, UNKNOWN}

Definition 6 (Rules):
    judge(c₁, c₂) = 
        CONFLICT           if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# = ⊥
        POSSIBLY-COMPATIBLE if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# ≠ ⊥
        UNKNOWN            if ¬comparable(c₁,c₂)

Definition 7 (Comparability):
    comparable(c₁, c₂) ⟺ 
        ℓ₁ = ℓ₂ ∧
        class(c₁), class(c₂) ∈ {FULL, PARTIAL} ∧
        unit-compatible(c₁, c₂) ∧
        scope-compatible(c₁, c₂) ∧
        temporal-compatible(c₁, c₂)
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Any
from enum import Enum, auto

from .constraint_types import (
    AtomicConstraint, 
    Judgment, 
    ConstraintClass,
    OperatorType,
)
from .classifier import classify_constraint, ClassificationResult


# =============================================================================
# LEFTOPERAND CATEGORIES (from formal specification)
# =============================================================================

# LeftOperands that REQUIRE unit for comparability
# These yield UNKNOWN if unit is missing or mismatched
L_UNIT_REQUIRED = {
    "payAmount",
    "resolution",
    "absolutePosition",
    "absoluteSize",
}

# LeftOperands that use unitOfCount as optional scope
# Missing scope -> default (comparable)
# Different scopes -> UNKNOWN
L_SCOPE_DEPENDENT = {
    "count",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
    if '/' in unit:
        return unit.split('/')[-1]
    if '#' in unit:
        return unit.split('#')[-1]
    return unit


# =============================================================================
# UNIT ORACLE INTEGRATION
# =============================================================================

# Try to import unit oracle; fallback to simple string matching if unavailable
try:
    from grounding.unit import are_units_compatible
    UNIT_ORACLE_AVAILABLE = True
except ImportError:
    UNIT_ORACLE_AVAILABLE = False
    
    def are_units_compatible(u1: str, u2: str) -> bool:
        """Fallback: normalize and compare."""
        u1_norm = normalize_unit(u1)
        u2_norm = normalize_unit(u2)
        return u1_norm == u2_norm


# =============================================================================
# COMPARABILITY RESULT
# =============================================================================

class IncomparabilityReason(Enum):
    """Why two constraints cannot be compared."""
    DIFFERENT_OPERANDS = auto()
    NON_ANALYZABLE_CLASS = auto()
    INCOMPATIBLE_UNITS = auto()
    MISSING_REQUIRED_UNIT = auto()  # NEW: For L_UNIT_REQUIRED operands
    INCOMPATIBLE_SCOPE = auto()
    INCOMPATIBLE_TEMPORAL_REF = auto()
    MISSING_ORACLE = auto()


@dataclass
class ComparabilityResult:
    """Result of checking if two constraints are comparable."""
    comparable: bool
    reason: Optional[IncomparabilityReason] = None
    details: str = ""


# =============================================================================
# COMPARABILITY CHECKS (Definition 7)
# =============================================================================

def check_same_operand(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """Check: ℓ₁ = ℓ₂ (same LeftOperand)."""
    l1 = normalize_operand(c1.left_operand)
    l2 = normalize_operand(c2.left_operand)
    
    if l1 != l2:
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.DIFFERENT_OPERANDS,
            details=f"Different LeftOperands: {l1} vs {l2}"
        )
    return ComparabilityResult(comparable=True)


def check_analyzable_class(
    class1: ClassificationResult, 
    class2: ClassificationResult
) -> ComparabilityResult:
    """Check: class(c₁), class(c₂) ∈ {FULL, PARTIAL} or both GROUNDED with oracle."""
    
    analyzable = {ConstraintClass.FULL, ConstraintClass.PARTIAL}
    
    # Both FULL or PARTIAL - always comparable
    if class1.constraint_class in analyzable and class2.constraint_class in analyzable:
        return ComparabilityResult(comparable=True)
    
    # Both GROUNDED - comparable if oracle available
    if (class1.constraint_class == ConstraintClass.GROUNDED and 
        class2.constraint_class == ConstraintClass.GROUNDED):
        if class1.oracle_available and class2.oracle_available:
            return ComparabilityResult(comparable=True)
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.MISSING_ORACLE,
            details=f"Oracle not available: {class1.oracle_needed}"
        )
    
    # Mixed or non-analyzable
    return ComparabilityResult(
        comparable=False,
        reason=IncomparabilityReason.NON_ANALYZABLE_CLASS,
        details=f"Classes: {class1.constraint_class.name}, {class2.constraint_class.name}"
    )


def check_unit_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check: unit-compatible(c₁, c₂).
    
    CRITICAL FIX: Different behavior for L_UNIT_REQUIRED vs other operands.
    
    For L_UNIT_REQUIRED (payAmount, resolution, absolutePosition, absoluteSize):
        - Unit is REQUIRED
        - Missing unit -> UNKNOWN (NOT comparable)
        - Different units -> UNKNOWN (NOT comparable)
        - Same unit -> comparable
        
    For other operands:
        - Both None -> comparable
        - One None, one specified -> incompatible (ambiguous)
        - Both specified -> use oracle for alias resolution
    """
    u1 = c1.unit
    u2 = c2.unit
    
    # Get normalized operand name
    operand = normalize_operand(c1.left_operand)
    
    # =========================================================================
    # CRITICAL FIX: Handle L_UNIT_REQUIRED operands differently
    # =========================================================================
    if operand in L_UNIT_REQUIRED:
        # Both must have units
        if u1 is None and u2 is None:
            return ComparabilityResult(
                comparable=False,
                reason=IncomparabilityReason.MISSING_REQUIRED_UNIT,
                details=f"{operand} requires unit for comparison but both constraints lack units"
            )
        
        if u1 is None:
            return ComparabilityResult(
                comparable=False,
                reason=IncomparabilityReason.MISSING_REQUIRED_UNIT,
                details=f"{operand} requires unit but first constraint has no unit"
            )
        
        if u2 is None:
            return ComparabilityResult(
                comparable=False,
                reason=IncomparabilityReason.MISSING_REQUIRED_UNIT,
                details=f"{operand} requires unit but second constraint has no unit"
            )
        
        # Both have units - check if compatible
        if are_units_compatible(u1, u2):
            return ComparabilityResult(comparable=True)
        
        # Different units - not comparable
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.INCOMPATIBLE_UNITS,
            details=f"Cannot compare {operand} with different units: {normalize_unit(u1)} vs {normalize_unit(u2)}"
        )
    
    # =========================================================================
    # Original logic for non-unit-required operands
    # =========================================================================
    
    # Both None - compatible
    if u1 is None and u2 is None:
        return ComparabilityResult(comparable=True)
    
    # One None, one specified - incompatible (ambiguous)
    if (u1 is None) != (u2 is None):
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.INCOMPATIBLE_UNITS,
            details=f"Unit mismatch: {u1} vs {u2}"
        )
    
    # Both specified - use oracle for compatibility check
    # Handles aliases: are_units_compatible("euro", "EUR") → True
    if are_units_compatible(u1, u2):
        return ComparabilityResult(comparable=True)
    
    # Different units (no conversion available)
    return ComparabilityResult(
        comparable=False,
        reason=IncomparabilityReason.INCOMPATIBLE_UNITS,
        details=f"Different units: {u1} vs {u2}"
    )


def check_scope_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Check: scope-compatible(c₁, c₂) for unitOfCount.
    
    For L_SCOPE_DEPENDENT (count):
        - Both None -> comparable (default scope)
        - One None, one specified -> comparable (default matches any)
        - Both specified, same -> comparable
        - Both specified, different -> UNKNOWN
    """
    s1 = c1.unit_of_count
    s2 = c2.unit_of_count
    
    # Get normalized operand name
    operand = normalize_operand(c1.left_operand)
    
    # Only applies to scope-dependent operands
    if operand not in L_SCOPE_DEPENDENT:
        # For non-scope-dependent operands, scope is irrelevant
        return ComparabilityResult(comparable=True)
    
    # Both None - compatible (default scope)
    if s1 is None and s2 is None:
        return ComparabilityResult(comparable=True)
    
    # One None, one specified - compatible (default matches any)
    # This is different from units because scope has a meaningful default
    if s1 is None or s2 is None:
        return ComparabilityResult(comparable=True)
    
    # Both specified - must match
    s1_norm = normalize_unit(s1)
    s2_norm = normalize_unit(s2)
    
    if s1_norm != s2_norm:
        return ComparabilityResult(
            comparable=False,
            reason=IncomparabilityReason.INCOMPATIBLE_SCOPE,
            details=f"Different scopes: {s1_norm} vs {s2_norm}"
        )
    
    return ComparabilityResult(comparable=True)


def check_temporal_compatible(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """Check: temporal-compatible(c₁, c₂) for reference point alignment."""
    l1 = normalize_operand(c1.left_operand)
    l2 = normalize_operand(c2.left_operand)
    
    # Reference-point operands
    ref_point_ops = {"elapsedTime", "delayPeriod"}
    
    # If neither uses reference points - compatible
    if l1 not in ref_point_ops and l2 not in ref_point_ops:
        return ComparabilityResult(comparable=True)
    
    # If both use same reference-point operand - comparable
    # (They share the same reference point)
    if l1 == l2 and l1 in ref_point_ops:
        return ComparabilityResult(comparable=True)
    
    # Mixing reference-point with absolute - incompatible
    # (e.g., elapsedTime vs dateTime)
    return ComparabilityResult(
        comparable=False,
        reason=IncomparabilityReason.INCOMPATIBLE_TEMPORAL_REF,
        details=f"Cannot compare {l1} with {l2}: different temporal references"
    )


def is_comparable(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """
    Full comparability check per Definition 7.
    
    comparable(c₁, c₂) ⟺ 
        ℓ₁ = ℓ₂ ∧
        class(c₁), class(c₂) ∈ {FULL, PARTIAL} ∧
        unit-compatible(c₁, c₂) ∧
        scope-compatible(c₁, c₂) ∧
        temporal-compatible(c₁, c₂)
    """
    # 1. Same operand check
    result = check_same_operand(c1, c2)
    if not result.comparable:
        return result
    
    # 2. Analyzable class
    class1 = classify_constraint(c1)
    class2 = classify_constraint(c2)
    result = check_analyzable_class(class1, class2)
    if not result.comparable:
        return result
    
    # 3. Unit compatible (CRITICAL FIX: handles L_UNIT_REQUIRED correctly)
    result = check_unit_compatible(c1, c2)
    if not result.comparable:
        return result
    
    # 4. Scope compatible
    result = check_scope_compatible(c1, c2)
    if not result.comparable:
        return result
    
    # 5. Temporal compatible
    result = check_temporal_compatible(c1, c2)
    if not result.comparable:
        return result
    
    return ComparabilityResult(comparable=True)


# =============================================================================
# JUDGMENT RESULT
# =============================================================================

@dataclass
class JudgmentResult:
    """
    Complete judgment result with explanation.
    """
    judgment: Judgment
    """The judgment: CONFLICT, POSSIBLY-COMPATIBLE, or UNKNOWN."""
    
    comparable: bool
    """Were the constraints comparable?"""
    
    incomparability_reason: Optional[IncomparabilityReason] = None
    """If not comparable, why?"""
    
    explanation: str = ""
    """Human-readable explanation."""
    
    counterexample: Optional[Any] = None
    """For POSSIBLY-COMPATIBLE: a satisfying assignment."""
    
    def __str__(self) -> str:
        return f"{self.judgment.value}: {self.explanation}"


# =============================================================================
# JUDGMENT FUNCTION (Definition 5-6)
# =============================================================================

def judge(c1: AtomicConstraint, c2: AtomicConstraint) -> JudgmentResult:
    """
    Main judgment function per Definition 5-6.
    
    judge(c₁, c₂) = 
        CONFLICT           if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# = ⊥
        POSSIBLY-COMPATIBLE if comparable(c₁,c₂) ∧ ⟦c₁⟧# ⊓ ⟦c₂⟧# ≠ ⊥
        UNKNOWN            if ¬comparable(c₁,c₂)
    
    Note: The abstract interpretation (⟦c⟧#) and meet operation (⊓)
    are implemented in the encoder module. This function delegates
    the actual SMT solving there.
    """
    # Check comparability
    comp_result = is_comparable(c1, c2)
    
    if not comp_result.comparable:
        return JudgmentResult(
            judgment=Judgment.UNKNOWN,
            comparable=False,
            incomparability_reason=comp_result.reason,
            explanation=comp_result.details
        )
    
    # Constraints are comparable - delegate to SMT solver
    # This is a placeholder - actual implementation uses Z3
    # For now, return a result that indicates we need the encoder
    return JudgmentResult(
        judgment=Judgment.UNKNOWN,
        comparable=True,
        explanation="Comparable - needs SMT encoding (implement in encoder module)"
    )


# =============================================================================
# JUDGMENT LATTICE OPERATIONS
# =============================================================================

def judgment_meet(j1: Judgment, j2: Judgment) -> Judgment:
    """
    Meet operation on judgments (most conservative).
    
    CONFLICT ⊓ x = CONFLICT
    UNKNOWN ⊓ POSSIBLY-COMPATIBLE = UNKNOWN
    POSSIBLY-COMPATIBLE ⊓ POSSIBLY-COMPATIBLE = POSSIBLY-COMPATIBLE
    """
    if j1 == Judgment.CONFLICT or j2 == Judgment.CONFLICT:
        return Judgment.CONFLICT
    if j1 == Judgment.UNKNOWN or j2 == Judgment.UNKNOWN:
        return Judgment.UNKNOWN
    return Judgment.POSSIBLY_COMPATIBLE


def judgment_join(j1: Judgment, j2: Judgment) -> Judgment:
    """
    Join operation on judgments (most optimistic).
    
    POSSIBLY-COMPATIBLE ⊔ x = POSSIBLY-COMPATIBLE
    UNKNOWN ⊔ CONFLICT = UNKNOWN
    CONFLICT ⊔ CONFLICT = CONFLICT
    """
    if j1 == Judgment.POSSIBLY_COMPATIBLE or j2 == Judgment.POSSIBLY_COMPATIBLE:
        return Judgment.POSSIBLY_COMPATIBLE
    if j1 == Judgment.UNKNOWN or j2 == Judgment.UNKNOWN:
        return Judgment.UNKNOWN
    return Judgment.CONFLICT


# =============================================================================
# RULE-LEVEL UNIT VALIDATION (NEW)
# =============================================================================

@dataclass
class RuleUnitValidationResult:
    """Result of unit validation for a set of constraints in a rule."""
    is_valid: bool
    reason: Optional[IncomparabilityReason] = None
    details: str = ""
    incomparable_constraints: Optional[list] = None


def validate_rule_units(constraints: list) -> RuleUnitValidationResult:
    """
    Validate that all constraints in a rule are mutually comparable.
    
    This function checks unit comparability for all constraints on the same
    LeftOperand within a rule. If any pair is incomparable, returns failure.
    
    Args:
        constraints: List of AtomicConstraint objects
        
    Returns:
        RuleUnitValidationResult indicating if all constraints are comparable
    """
    from collections import defaultdict
    
    # Group constraints by normalized operand
    by_operand = defaultdict(list)
    
    for c in constraints:
        if hasattr(c, 'left_operand'):
            op = normalize_operand(c.left_operand)
            by_operand[op].append(c)
    
    # Check each operand group
    for operand, cs in by_operand.items():
        if len(cs) < 2:
            continue  # Single constraint, no comparison needed
        
        # Check unit-required operands
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
                    reason=IncomparabilityReason.MISSING_REQUIRED_UNIT,
                    details=f"{operand} requires unit but constraint(s) have none",
                    incomparable_constraints=missing_unit_constraints
                )
            
            # Check all units are the same
            unique_units = set(units)
            if len(unique_units) > 1:
                return RuleUnitValidationResult(
                    is_valid=False,
                    reason=IncomparabilityReason.INCOMPATIBLE_UNITS,
                    details=f"{operand} has mixed units: {unique_units}",
                    incomparable_constraints=[getattr(c, 'uid', str(c)) for c in cs]
                )
        
        # Check scope-dependent operands
        elif operand in L_SCOPE_DEPENDENT:
            scopes = []
            for c in cs:
                scope = getattr(c, 'unit_of_count', None)
                if scope is not None:
                    scopes.append(normalize_unit(scope))
            
            # If any scopes specified, all specified ones must match
            if scopes:
                unique_scopes = set(scopes)
                if len(unique_scopes) > 1:
                    return RuleUnitValidationResult(
                        is_valid=False,
                        reason=IncomparabilityReason.INCOMPATIBLE_SCOPE,
                        details=f"{operand} has mixed scopes: {unique_scopes}",
                        incomparable_constraints=[getattr(c, 'uid', str(c)) for c in cs]
                    )
    
    # All checks passed
    return RuleUnitValidationResult(is_valid=True)