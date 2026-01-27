# src/semantics/judgment.py
"""
ODRL-SA Judgment System

Implements the formal judgment function from ODRL-SA specification §7.

Judgments:
- CONFLICT: No world satisfies both constraints (proven unsatisfiable)
- POSSIBLY_COMPATIBLE: At least one world may satisfy both (not proven safe)
- UNKNOWN: Cannot determine; grounding or runtime evaluation required

This module also defines constraint classes per §6:
- FULL: Fully analyzable via abstract interpretation + SMT
- PARTIAL: Analyzable with stated reference point assumptions
- GROUNDED: Requires external semantic grounding (KB, ontology)
- RUNTIME: Requires runtime state; cannot be statically analyzed
- DEFERRED: Requires dereferencing; value unknown at analysis time
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple


# =============================================================================
# JUDGMENT VALUES (§7 Definition 8)
# =============================================================================

class Judgment(Enum):
    """
    ODRL-SA Judgment values.
    
    These are the three possible outcomes of comparing two constraints.
    """
    CONFLICT = "CONFLICT"
    """No world satisfies both constraints - proven logical inconsistency."""
    
    POSSIBLY_COMPATIBLE = "POSSIBLY_COMPATIBLE"
    """At least one world may satisfy both - NOT guaranteed safe."""
    
    UNKNOWN = "UNKNOWN"
    """Cannot determine - requires grounding or runtime evaluation."""
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# CONSTRAINT ANALYZABILITY CLASS (§6 Definition 7)
# =============================================================================

class ConstraintClass(Enum):
    """
    Constraint analyzability classification.
    
    Determines what kind of analysis is possible for a constraint.
    """
    FULL = "FULL"
    """Fully analyzable via abstract interpretation + SMT."""
    
    PARTIAL = "PARTIAL"
    """Analyzable with stated reference point assumptions."""
    
    GROUNDED = "GROUNDED"
    """Requires external semantic grounding (KB, ontology)."""
    
    RUNTIME = "RUNTIME"
    """Requires runtime state; cannot be statically analyzed."""
    
    DEFERRED = "DEFERRED"
    """Requires dereferencing; value unknown at analysis time."""
    
    def is_analyzable(self) -> bool:
        """Check if this class allows static analysis."""
        return self in {ConstraintClass.FULL, ConstraintClass.PARTIAL}
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# INCOMPARABILITY REASONS
# =============================================================================

class IncomparabilityReason(Enum):
    """Reasons why two constraints cannot be compared."""
    
    DIFFERENT_OPERANDS = "different_operands"
    """Constraints have different LeftOperands."""
    
    NOT_ANALYZABLE = "not_analyzable"
    """One or both constraints are not statically analyzable."""
    
    UNIT_MISMATCH = "unit_mismatch"
    """Constraints have incompatible units."""
    
    SCOPE_MISMATCH = "scope_mismatch"
    """Constraints have different unitOfCount scopes."""
    
    TEMPORAL_INCOMPATIBLE = "temporal_incompatible"
    """Cross-temporal comparison not allowed (e.g., delayPeriod vs dateTime)."""
    
    OPERATOR_INVALID = "operator_invalid"
    """Operator not valid for operand (e.g., gt on timeInterval)."""
    
    DEFERRED_VALUE = "deferred_value"
    """One constraint has rightOperandReference requiring dereferencing."""
    
    RUNTIME_REQUIRED = "runtime_required"
    """One constraint requires runtime state (policyUsage, meteredTime)."""
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# JUDGMENT RESULT
# =============================================================================

@dataclass
class JudgmentResult:
    """
    Complete result of judging two constraints.
    
    Contains the judgment value plus metadata about how it was determined.
    """
    judgment: Judgment
    """The judgment value: CONFLICT, POSSIBLY_COMPATIBLE, or UNKNOWN."""
    
    constraint1_id: str
    """ID of the first constraint."""
    
    constraint2_id: str
    """ID of the second constraint."""
    
    reason: Optional[str] = None
    """Human-readable explanation of the judgment."""
    
    incomparability_reason: Optional[IncomparabilityReason] = None
    """If UNKNOWN, why the constraints are incomparable."""
    
    counterexample: Optional[Dict[str, Any]] = None
    """If POSSIBLY_COMPATIBLE, a witness satisfying both constraints."""
    
    analysis_method: Optional[str] = None
    """How the judgment was determined (abstract, smt, oracle)."""
    
    confidence: float = 1.0
    """Confidence in the judgment (1.0 for proven, <1.0 for heuristic)."""
    
    def is_conflict(self) -> bool:
        return self.judgment == Judgment.CONFLICT
    
    def is_compatible(self) -> bool:
        return self.judgment == Judgment.POSSIBLY_COMPATIBLE
    
    def is_unknown(self) -> bool:
        return self.judgment == Judgment.UNKNOWN
    
    def __str__(self) -> str:
        result = f"{self.judgment.value}"
        if self.reason:
            result += f": {self.reason}"
        if self.incomparability_reason:
            result += f" ({self.incomparability_reason})"
        return result


# =============================================================================
# GROUNDING ORACLE RESULT (§9 Definition 15)
# =============================================================================

class OracleResult(Enum):
    """
    Result from a semantic grounding oracle.
    
    Used when comparing constraints on semantically-grounded operands
    (language, spatial, purpose, etc.) that require external knowledge.
    """
    SUBSUMES = "SUBSUMES"
    """First value subsumes/contains second (e.g., 'en' subsumes 'en-US')."""
    
    DISJOINT = "DISJOINT"
    """Values are mutually exclusive (e.g., 'de' disjoint from 'fr')."""
    
    OVERLAPS = "OVERLAPS"
    """Values have non-empty intersection but neither subsumes."""
    
    UNKNOWN = "UNKNOWN"
    """Oracle cannot determine relationship."""
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# THREE-VALUED LOGIC (§3 Definition 4)
# =============================================================================

class TruthValue(Enum):
    """
    Three-valued truth for constraint satisfaction.
    
    ODRL constraints can be:
    - TRUE: Constraint is satisfied
    - FALSE: Constraint is violated
    - UNDEFINED: Constraint is not applicable (operand undefined in world)
    """
    TRUE = "T"
    FALSE = "F"
    UNDEFINED = "⊥"
    
    def __bool__(self) -> bool:
        """Convert to boolean (UNDEFINED -> False for safety)."""
        return self == TruthValue.TRUE
    
    def __and__(self, other: 'TruthValue') -> 'TruthValue':
        """Kleene three-valued AND."""
        if self == TruthValue.FALSE or other == TruthValue.FALSE:
            return TruthValue.FALSE
        if self == TruthValue.UNDEFINED or other == TruthValue.UNDEFINED:
            return TruthValue.UNDEFINED
        return TruthValue.TRUE
    
    def __or__(self, other: 'TruthValue') -> 'TruthValue':
        """Kleene three-valued OR."""
        if self == TruthValue.TRUE or other == TruthValue.TRUE:
            return TruthValue.TRUE
        if self == TruthValue.UNDEFINED or other == TruthValue.UNDEFINED:
            return TruthValue.UNDEFINED
        return TruthValue.FALSE
    
    def __invert__(self) -> 'TruthValue':
        """Kleene three-valued NOT."""
        if self == TruthValue.TRUE:
            return TruthValue.FALSE
        if self == TruthValue.FALSE:
            return TruthValue.TRUE
        return TruthValue.UNDEFINED
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# JUDGMENT LATTICE
# =============================================================================

# Judgment ordering: CONFLICT ⊑ UNKNOWN ⊑ POSSIBLY_COMPATIBLE
# (more certain to less certain about safety)

JUDGMENT_ORDER = {
    Judgment.CONFLICT: 0,
    Judgment.UNKNOWN: 1,
    Judgment.POSSIBLY_COMPATIBLE: 2,
}


def judgment_meet(j1: Judgment, j2: Judgment) -> Judgment:
    """
    Lattice meet (most pessimistic).
    
    Returns the more restrictive judgment.
    CONFLICT ⊓ anything = CONFLICT
    UNKNOWN ⊓ POSSIBLY_COMPATIBLE = UNKNOWN
    """
    if j1 == Judgment.CONFLICT or j2 == Judgment.CONFLICT:
        return Judgment.CONFLICT
    if j1 == Judgment.UNKNOWN or j2 == Judgment.UNKNOWN:
        return Judgment.UNKNOWN
    return Judgment.POSSIBLY_COMPATIBLE


def judgment_join(j1: Judgment, j2: Judgment) -> Judgment:
    """
    Lattice join (most optimistic).
    
    Returns the less restrictive judgment.
    POSSIBLY_COMPATIBLE ⊔ anything = POSSIBLY_COMPATIBLE
    UNKNOWN ⊔ CONFLICT = UNKNOWN
    """
    if j1 == Judgment.POSSIBLY_COMPATIBLE or j2 == Judgment.POSSIBLY_COMPATIBLE:
        return Judgment.POSSIBLY_COMPATIBLE
    if j1 == Judgment.UNKNOWN or j2 == Judgment.UNKNOWN:
        return Judgment.UNKNOWN
    return Judgment.CONFLICT