# =============================================================================
# DOMAIN BOUNDS - Complete Configuration (Final Classification)
# =============================================================================
# 
# Replace the existing DOMAIN_BOUNDS in src/encoder/z3_encoder.py with this
#
# Categories:
#   𝓛_bounded: [0, 100] - 5 LeftOperands
#   𝓛_int: ℤ≥0 - 2 LeftOperands  
#   𝓛_datetime: ℤ - 1 LeftOperand
#   𝓛_unit: ℝ≥0 - 4 LeftOperands
#   𝓛_real: ℝ≥0 - 1 LeftOperand
#   𝓛_coords: ℝ≥0 - 1 LeftOperand
#   𝓛_ref: ℤ≥0 - 2 LeftOperands (partial)
#
# Total: 16 LeftOperands with domain bounds (𝓛_xsd + 𝓛_ref)
# =============================================================================

from dataclasses import dataclass
from typing import Optional

@dataclass
class DomainBounds:
    """Domain bounds for a LeftOperand."""
    min_val: Optional[float] = None  # None = -∞
    max_val: Optional[float] = None  # None = +∞
    is_integer: bool = False
    use_real: bool = True
    exclusive_min: bool = False  # For ℝ>0 domains
    category: str = "unknown"  # Equivalence class


# Complete domain bounds for all statically analyzable LeftOperands
DOMAIN_BOUNDS = {
    # =========================================================================
    # 𝓛_bounded — [0, 100] (5 LeftOperands)
    # SMT Theory: QF-LRA
    # =========================================================================
    "percentage": DomainBounds(
        min_val=0, max_val=100, is_integer=False, use_real=True,
        category="L_bounded"
    ),
    "relativePosition": DomainBounds(
        min_val=0, max_val=100, is_integer=False, use_real=True,
        category="L_bounded"
    ),
    "relativeSize": DomainBounds(
    min_val=0, max_val=None, is_integer=False, use_real=True,
    category="L_unbounded_percentage"
    ),
    "relativeTemporalPosition": DomainBounds(
        min_val=0, max_val=100, is_integer=False, use_real=True,
        category="L_bounded"
    ),
    "relativeSpatialPosition": DomainBounds(
        min_val=0, max_val=100, is_integer=False, use_real=True,
        category="L_bounded"
    ),
    
    # =========================================================================
    # 𝓛_int — ℤ≥0 (2 LeftOperands)
    # SMT Theory: QF-LIA
    # =========================================================================
    "count": DomainBounds(
        min_val=0, max_val=None, is_integer=True, use_real=False,
        category="L_int"
    ),
    "timeInterval": DomainBounds(
        min_val=0, max_val=None, is_integer=True, use_real=False,
        category="L_int"
    ),
    
    # =========================================================================
    # 𝓛_datetime — ℤ (1 LeftOperand)
    # SMT Theory: QF-LIA (normalized to Unix timestamp)
    # =========================================================================
    "dateTime": DomainBounds(
        min_val=None, max_val=None, is_integer=True, use_real=False,
        category="L_datetime"
    ),
    
    # =========================================================================
    # 𝓛_unit — ℝ≥0 or ℝ>0 (4 LeftOperands)
    # SMT Theory: QF-LRA
    # Note: Comparability requires same unit
    # =========================================================================
    "payAmount": DomainBounds(
        min_val=0, max_val=None, is_integer=False, use_real=True,
        category="L_unit"
    ),
    "resolution": DomainBounds(
        min_val=0, max_val=None, is_integer=False, use_real=True,
        exclusive_min=True,  # ℝ>0
        category="L_unit"
    ),
    "absolutePosition": DomainBounds(
        min_val=0, max_val=None, is_integer=False, use_real=True,
        category="L_unit"
    ),
    "absoluteSize": DomainBounds(
        min_val=0, max_val=None, is_integer=False, use_real=True,
        exclusive_min=True,  # ℝ>0
        category="L_unit"
    ),
    
    # =========================================================================
    # 𝓛_real — ℝ≥0 (1 LeftOperand)
    # SMT Theory: QF-LRA
    # =========================================================================
    "absoluteTemporalPosition": DomainBounds(
        min_val=0, max_val=None, is_integer=False, use_real=True,
        category="L_real"
    ),
    
    # =========================================================================
    # 𝓛_coords — ℝ≥0 (1 LeftOperand)
    # SMT Theory: QF-LRA
    # Note: Only eq/neq operators are statically meaningful
    # =========================================================================
    "absoluteSpatialPosition": DomainBounds(
        min_val=0, max_val=None, is_integer=False, use_real=True,
        category="L_coords"
    ),
    
    # =========================================================================
    # 𝓛_ref — ℤ≥0 (2 LeftOperands)
    # SMT Theory: QF-LIA
    # Note: Partial analysis (assumes policy activation as reference)
    # =========================================================================
    "elapsedTime": DomainBounds(
        min_val=0, max_val=None, is_integer=True, use_real=False,
        category="L_ref"
    ),
    "delayPeriod": DomainBounds(
        min_val=0, max_val=None, is_integer=True, use_real=False,
        category="L_ref"
    ),
}


# =========================================================================
# CATEGORY SETS (for quick lookup)
# =========================================================================

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

# All fully analyzable (15)
FULLY_ANALYZABLE = L_BOUNDED | L_UNBOUNDED_PERCENTAGE | L_INT | L_DATETIME | L_UNIT | L_REAL | L_COORDS | {"unitOfCount"}

# Partially analyzable (2)
PARTIALLY_ANALYZABLE = L_REF

# Requires external KB (14) - not in DOMAIN_BOUNDS
REQUIRES_ORACLE = {
    "language", "spatial", "spatialCoordinates", "event", "media",
    "industry", "purpose", "recipient", "product", "deliveryChannel",
    "systemDevice", "fileFormat", "virtualLocation", "version"
}

# Runtime only (1) - not in DOMAIN_BOUNDS
RUNTIME_ONLY = {"meteredTime"}


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def get_category(operand: str) -> str:
    """Get the equivalence class for a LeftOperand."""
    if operand in L_BOUNDED:
        return "L_bounded"
    if operand in L_UNBOUNDED_PERCENTAGE:
        return "L_unbounded_percentage"
    elif operand in L_INT:
        return "L_int"
    elif operand in L_DATETIME:
        return "L_datetime"
    elif operand in L_UNIT:
        return "L_unit"
    elif operand in L_REAL:
        return "L_real"
    elif operand in L_COORDS:
        return "L_coords"
    elif operand in L_REF:
        return "L_ref"
    elif operand == "unitOfCount":
        return "L_vocab"
    elif operand in REQUIRES_ORACLE:
        return "L_sem"
    elif operand in RUNTIME_ONLY:
        return "L_run"
    else:
        return "unknown"


def is_analyzable(operand: str) -> bool:
    """Check if operand can be statically analyzed."""
    return operand in FULLY_ANALYZABLE or operand in PARTIALLY_ANALYZABLE


def get_smt_theory(operand: str) -> str:
    """Get the SMT theory for a LeftOperand."""
    bounds = DOMAIN_BOUNDS.get(operand)
    if bounds:
        if bounds.is_integer:
            return "QF-LIA"
        else:
            return "QF-LRA"
    elif operand == "unitOfCount":
        return "QF-UF"
    else:
        return "unknown"


# =========================================================================
# STATISTICS
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DOMAIN_BOUNDS Statistics")
    print("=" * 60)
    
    # Count by category
    categories = {}
    for op, bounds in DOMAIN_BOUNDS.items():
        cat = bounds.category
        categories.setdefault(cat, []).append(op)
    
    for cat, ops in sorted(categories.items()):
        print(f"\n{cat} ({len(ops)}):")
        for op in ops:
            b = DOMAIN_BOUNDS[op]
            domain = f"[{b.min_val or '-∞'}, {b.max_val or '+∞'}]"
            sort = "Int" if b.is_integer else "Real"
            print(f"  {op}: {domain} ({sort})")
    
    print(f"\n{'='*60}")
    print(f"Total in DOMAIN_BOUNDS: {len(DOMAIN_BOUNDS)}")
    print(f"Fully analyzable: {len(FULLY_ANALYZABLE)}")
    print(f"Partially analyzable: {len(PARTIALLY_ANALYZABLE)}")
    print(f"Requires oracle: {len(REQUIRES_ORACLE)}")
    print(f"Runtime only: {len(RUNTIME_ONLY)}")