## resolution - Final Formal Specification

### ODRL Vocabulary Definition

```turtle
:resolution
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Rendition Resolution"@en ;
    skos:definition "Resolution of the rendition of the target Asset."@en ;
    skos:note "Example: the image may be printed at 1200dpi."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Intuitive Semantics

**What it measures:** The output resolution (pixel/dot density) when rendering an asset.

| Value | Meaning |
|-------|---------|
| 72 DPI | Screen resolution (low) |
| 150 DPI | Draft print quality |
| 300 DPI | Standard print quality |
| 1200 DPI | High-quality print (from ODRL example) |

**Use cases:**
- Print quality restrictions ("max 300 DPI for web distribution")
- High-resolution access control ("1200 DPI requires premium license")
- Device-specific rendering limits

---

### 2. Formal Domain Specification

$$\text{dom}(\texttt{resolution}) = \mathbb{R}_{> 0} = (0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (exclusive) | Zero resolution is undefined/degenerate |
| **Upper bound** | ∞ | No theoretical maximum |
| **XSD Type** | `xsd:decimal` | Numeric value |

> Although mathematically the domain extends to infinity, practical resolutions rarely exceed 10,000 DPI. ODRL-SA admits the full domain for generality.

---

### 3. Unit Specification

**Unit Required:** ✅ Yes

| Property | Value |
|----------|-------|
| **Unit category** | Density (dots/pixels per unit length) |
| **Common units** | DPI (dots per inch), PPI (pixels per inch) |
| **QUDT URIs** | `http://qudt.org/vocab/unit/DPI`, `http://qudt.org/vocab/unit/PPI` |

**Unit Comparability Rule:**
- Same unit → Comparable
- Different units → **UNKNOWN** (no automatic conversion)
- Missing unit → **UNKNOWN**

**Rationale for no conversion:** DPI and PPI are technically equivalent (1 DPI = 1 PPI), but:
1. Some contexts distinguish them (print vs screen)
2. Other density units exist (DPCM, DPMM)
3. Conservative approach preserves soundness

---

### 4. Operator Specification

**Valid operators:** 9 of 12

| Operator | Valid | Semantics |
|----------|-------|-----------|
| `eq` | ✅ | Exact resolution required |
| `neq` | ✅ | Any resolution except specified |
| `lt` | ✅ | Lower than this resolution |
| `lteq` | ✅ | At most this resolution |
| `gt` | ✅ | Higher than this resolution |
| `gteq` | ✅ | At least this resolution |
| `isAnyOf` | ✅ | Resolution in enumerated set |
| `isNoneOf` | ✅ | Resolution not in enumerated set |
| `isAllOf` | ✅ | Satisfiable iff all values identical |
| `isA` | ❌ | Semantic, not applicable to numeric |
| `hasPart` | ❌ | Semantic, not applicable to numeric |
| `isPartOf` | ❌ | Semantic, not applicable to numeric |

**isAllOf formal semantics:**

$$\texttt{isAllOf}(\{v_1, \ldots, v_n\}) \equiv \begin{cases} x = v_1 & \text{if } v_1 = v_2 = \cdots = v_n \\ \bot & \text{otherwise} \end{cases}$$

---

### 5. SMT Encoding

**Theory:** QF_LRA (Quantifier-Free Linear Real Arithmetic)

**Z3 Sort:** Real

```python
from z3 import *

def encode_resolution(operator: str, value, unit: str = None) -> BoolRef:
    """
    Encode resolution constraint.
    Returns BoolVal(True) with UNKNOWN flag if unit missing/incompatible.
    """
    if unit is None:
        # Cannot analyze without unit
        return BoolVal(True)  # Over-approximate, mark UNKNOWN
    
    # Variable name includes unit for isolation
    x = Real(f'resolution_{normalize_unit(unit)}')
    domain = x > 0  # (0, ∞)
    
    if operator == "eq":
        return And(domain, x == value)
    elif operator == "neq":
        return And(domain, x != value)
    elif operator == "lt":
        return And(domain, x < value)
    elif operator == "lteq":
        return And(domain, x <= value)
    elif operator == "gt":
        return And(domain, x > value)
    elif operator == "gteq":
        return And(domain, x >= value)
    elif operator == "isAnyOf":
        return And(domain, Or([x == v for v in value]))
    elif operator == "isNoneOf":
        return And(domain, And([x != v for v in value]))
    elif operator == "isAllOf":
        if len(set(value)) == 1:
            return And(domain, x == value[0])
        else:
            return BoolVal(False)

def normalize_unit(unit: str) -> str:
    """Normalize resolution unit to canonical form."""
    UNIT_MAP = {
        "dpi": "DPI",
        "DPI": "DPI",
        "http://qudt.org/vocab/unit/DPI": "DPI",
        "ppi": "PPI",
        "PPI": "PPI",
        "http://qudt.org/vocab/unit/PPI": "PPI",
    }
    return UNIT_MAP.get(unit, unit)  # Unknown units stay as-is

def are_units_compatible(unit1: str, unit2: str) -> bool:
    """Check if two resolution units are comparable."""
    if unit1 is None or unit2 is None:
        return False
    return normalize_unit(unit1) == normalize_unit(unit2)
```

---

### 6. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ (0, ∞) (rational intervals over positive reals)

**Abstraction function:**

$$\alpha(\texttt{resolution op } v) = \begin{cases}
[v, v] & \text{if op} = \texttt{eq} \\
(0, v) & \text{if op} = \texttt{lt} \\
(0, v] & \text{if op} = \texttt{lteq} \\
(v, +\infty) & \text{if op} = \texttt{gt} \\
[v, +\infty) & \text{if op} = \texttt{gteq} \\
(0, +\infty) \setminus \{v\} & \text{if op} = \texttt{neq}
\end{cases}$$

**Concretization:**

$$\gamma([a, b]) = \{ r \in \mathbb{R}_{>0} \mid a \leq r \leq b \}$$

---

### 7. Conflict Detection

**Judgment rules:**

$$\frac{\text{unit-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\text{unit-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

$$\frac{\neg\text{unit-compatible}(c_1, c_2)}{\texttt{UNKNOWN}(c_1, c_2)}$$

**Examples (same unit - DPI):**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Judgment |
|--------------|--------------|------------|------------|----------|
| `lteq 300` | `gteq 600` | (0, 300] | [600, ∞) | **CONFLICT** |
| `lteq 1200` | `gteq 300` | (0, 1200] | [300, ∞) | POSSIBLY-COMPATIBLE |
| `eq 300` | `eq 600` | {300} | {600} | **CONFLICT** |
| `gt 72` | `lt 300` | (72, ∞) | (0, 300) | POSSIBLY-COMPATIBLE |
| `neq 300` | `eq 300` | (0,∞) \ {300} | {300} | **CONFLICT** |

**Examples (different units):**

| Constraint 1 | Constraint 2 | Judgment |
|--------------|--------------|----------|
| `lteq 300 DPI` | `gteq 600 PPI` | **UNKNOWN** |
| `eq 1200 DPI` | `eq 1200` (no unit) | **UNKNOWN** |

---

### 8. Comparison with Related LeftOperands

| LeftOperand | Domain | Unit Required | Category |
|-------------|--------|---------------|----------|
| **resolution** | (0, ∞) | ✅ Yes (DPI/PPI) | L_unit |
| **absoluteSize** | (0, ∞) | ✅ Yes (bytes/px) | L_unit |
| **payAmount** | [0, ∞) | ✅ Yes (currency) | L_unit |
| **percentage** | [0, 100] | ❌ No | L_bounded |
| **relativeSize** | [0, ∞) | ❌ No (implicit %) | L_percentage_unbounded |

**Key distinction:** `resolution` is strictly positive (no zero) and unit-dependent. Unlike `relativeSize` which is a dimensionless ratio, `resolution` requires explicit density units for comparison.

---

### 9. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | FULL (when unit present) |
| **Category** | L_unit |
| **Equivalence Class** | None (unique unit-dependent semantics) |
| **External KB Required** | No |
| **Decidable** | Yes |

---

### 10. Configuration Entry

```python
"resolution": {
    "class": "FULL",
    "category": "L_unit",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": False,  # Strictly positive
        "inclusive_max": None
    },
    "operators": [
        "eq", "neq", "lt", "lteq", "gt", "gteq",
        "isAnyOf", "isNoneOf", "isAllOf"
    ],
    "unit": {
        "required": True,
        "category": "density",
        "common": ["DPI", "PPI"],
        "qudt": [
            "http://qudt.org/vocab/unit/DPI",
            "http://qudt.org/vocab/unit/PPI"
        ]
    },
    "dimensions": 1,
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 11. LaTeX Table Entry (for your document)

Update Table 1 in your LaTeX document:

```latex
\multicolumn{6}{l}{\textit{Unit-Dependent (4)}} \\
payAmount & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
resolution & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
absolutePosition & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
absoluteSize & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
```

Note: `resolution` and `absoluteSize` have domain $\mathbb{R}_{> 0}$ (strictly positive), while `payAmount` and `absolutePosition` have domain $\mathbb{R}_{\geq 0}$ (non-negative, includes zero).

---

### 12. Publication Statement

> **resolution** measures the output density (dots/pixels per unit length) when rendering an asset, with domain ℝ>0 excluding zero as a degenerate state. The ODRL example "printed at 1200dpi" confirms numeric density interpretation. ODRL-SA requires explicit units (DPI, PPI) for constraint comparison; constraints with different or missing units yield UNKNOWN, preserving soundness without assuming unit equivalence. Each (resolution, unit) pair maps to a separate Z3 Real variable, ensuring unit-mismatched constraints cannot produce false conflicts. Conflict detection reduces to interval intersection over positive reals within QF_LRA.

