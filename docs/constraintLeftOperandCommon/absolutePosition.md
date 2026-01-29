## absolutePosition - Final Formal Specification

### ODRL Vocabulary Definition

```turtle
:absolutePosition
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Absolute Asset Position"@en ;
    skos:definition "A point in space or time defined with absolute 
                     coordinates for the positioning of the target 
                     Asset."@en ;
    skos:note "Example: The upper left corner of a picture may be 
               constrained to a specific position of the canvas 
               rendering it."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Intuitive Semantics

**What it measures:** The absolute location of an asset in space or time, using concrete measurement units.

| Context | Example Values | Units |
|---------|----------------|-------|
| Temporal | 30, 120, 3600 | seconds |
| Spatial (image) | 100, 500, 1024 | pixels |
| Spatial (print) | 25.4, 50.8 | millimeters |
| Data stream | 1024, 65536 | bytes |

**Use cases:**
- Video insertion points ("advertisement at 30 seconds")
- Image positioning ("watermark at pixel 100")
- Audio segmentation ("clip starts at byte 65536")
- Print layout ("logo at 25mm from edge")

---

### 2. Formal Domain Specification

$$\text{dom}(\texttt{absolutePosition}) = \mathbb{R}_{\geq 0} = [0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (inclusive) | Zero = origin/start position |
| **Upper bound** | ∞ | No theoretical maximum |
| **XSD Type** | `xsd:decimal` | Numeric value |

> Zero is semantically valid for `absolutePosition` (represents origin/start), unlike `resolution` or `absoluteSize` where zero is degenerate.

---

### 3. Unit Specification

**Unit Required:** ✅ Yes

| Property | Value |
|----------|-------|
| **Unit categories** | Time, Length, Data |
| **Temporal units** | seconds (SEC), minutes (MIN), hours (HR) |
| **Spatial units** | pixels (PX), millimeters (MM), inches (IN) |
| **Data units** | bytes (BYTE), kilobytes (KiloBYTE) |

**QUDT URIs:**

| Category | Unit | QUDT URI |
|----------|------|----------|
| Time | second | `http://qudt.org/vocab/unit/SEC` |
| Time | minute | `http://qudt.org/vocab/unit/MIN` |
| Time | hour | `http://qudt.org/vocab/unit/HR` |
| Spatial | pixel | `http://qudt.org/vocab/unit/PX` |
| Spatial | millimeter | `http://qudt.org/vocab/unit/MilliM` |
| Spatial | inch | `http://qudt.org/vocab/unit/IN` |
| Data | byte | `http://qudt.org/vocab/unit/BYTE` |

**Unit Comparability Rule:**
- Same unit → Comparable
- Different units → **UNKNOWN** (no automatic conversion)
- Missing unit → **UNKNOWN**

**Rationale for no unit conversion:**
1. Context determines appropriate unit (temporal vs spatial vs data)
2. Conversion between categories is semantically invalid
3. Even within categories, conversion adds complexity
4. Conservative approach preserves soundness

---

### 4. Dimensional Treatment

The definition mentions "point in space or time" which could imply multi-dimensional, but:

**ODRL-SA Treatment:** 1D scalar

**Justification:**
1. ODRL constraint model provides single `rightOperand`
2. ODRL has separate `absoluteSpatialPosition` for explicit 2D/3D coordinates
3. "Space or time" phrasing suggests unified 1D abstraction
4. Operators `lt`, `gt` induce total order (well-defined for 1D only)

> ODRL LeftOperands describe *what is constrained*, not *how an action interprets it geometrically*. Multi-dimensional positioning requires `absoluteSpatialPosition` or multiple constraints.

---

### 5. Operator Specification

**Valid operators:** 9 of 12

| Operator | Valid | Semantics |
|----------|-------|-----------|
| `eq` | ✅ | Exact position required |
| `neq` | ✅ | Any position except specified |
| `lt` | ✅ | Before this position |
| `lteq` | ✅ | At or before this position |
| `gt` | ✅ | After this position |
| `gteq` | ✅ | At or after this position |
| `isAnyOf` | ✅ | Position in enumerated set |
| `isNoneOf` | ✅ | Position not in enumerated set |
| `isAllOf` | ✅ | Satisfiable iff all values identical |
| `isA` | ❌ | Semantic, not applicable to numeric |
| `hasPart` | ❌ | Semantic, not applicable to numeric |
| `isPartOf` | ❌ | Semantic, not applicable to numeric |

**isAllOf formal semantics:**

$$\texttt{isAllOf}(\{v_1, \ldots, v_n\}) \equiv \begin{cases} x = v_1 & \text{if } v_1 = v_2 = \cdots = v_n \\ \bot & \text{otherwise} \end{cases}$$

---

### 6. SMT Encoding

**Theory:** QF_LRA (Quantifier-Free Linear Real Arithmetic)

**Z3 Sort:** Real

```python
from z3 import *

def encode_absolutePosition(operator: str, value, unit: str = None) -> BoolRef:
    """
    Encode absolutePosition constraint.
    Returns BoolVal(True) with UNKNOWN flag if unit missing/incompatible.
    """
    if unit is None:
        # Cannot analyze without unit
        return BoolVal(True)  # Over-approximate, mark UNKNOWN
    
    # Variable name includes unit for isolation
    x = Real(f'absolutePosition_{normalize_unit(unit)}')
    domain = x >= 0  # [0, ∞)
    
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
    """Normalize position unit to canonical form."""
    UNIT_MAP = {
        # Time units
        "sec": "SEC", "SEC": "SEC", "second": "SEC", "seconds": "SEC",
        "http://qudt.org/vocab/unit/SEC": "SEC",
        "min": "MIN", "MIN": "MIN", "minute": "MIN", "minutes": "MIN",
        "http://qudt.org/vocab/unit/MIN": "MIN",
        "hr": "HR", "HR": "HR", "hour": "HR", "hours": "HR",
        "http://qudt.org/vocab/unit/HR": "HR",
        # Spatial units
        "px": "PX", "PX": "PX", "pixel": "PX", "pixels": "PX",
        "http://qudt.org/vocab/unit/PX": "PX",
        "mm": "MilliM", "MilliM": "MilliM", "millimeter": "MilliM",
        "http://qudt.org/vocab/unit/MilliM": "MilliM",
        "in": "IN", "IN": "IN", "inch": "IN", "inches": "IN",
        "http://qudt.org/vocab/unit/IN": "IN",
        # Data units
        "byte": "BYTE", "BYTE": "BYTE", "bytes": "BYTE",
        "http://qudt.org/vocab/unit/BYTE": "BYTE",
    }
    return UNIT_MAP.get(unit, unit)  # Unknown units stay as-is

def are_units_compatible(unit1: str, unit2: str) -> bool:
    """Check if two position units are comparable."""
    if unit1 is None or unit2 is None:
        return False
    return normalize_unit(unit1) == normalize_unit(unit2)
```

---

### 7. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ [0, ∞) (rational intervals over non-negative reals)

**Abstraction function:**

$$\alpha(\texttt{absolutePosition op } v) = \begin{cases}
[v, v] & \text{if op} = \texttt{eq} \\
[0, v) & \text{if op} = \texttt{lt} \\
[0, v] & \text{if op} = \texttt{lteq} \\
(v, +\infty) & \text{if op} = \texttt{gt} \\
[v, +\infty) & \text{if op} = \texttt{gteq} \\
[0, +\infty) \setminus \{v\} & \text{if op} = \texttt{neq}
\end{cases}$$

**Concretization:**

$$\gamma([a, b]) = \{ r \in \mathbb{R}_{\geq 0} \mid a \leq r \leq b \}$$

---

### 8. Conflict Detection

**Judgment rules:**

$$\frac{\text{unit-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\text{unit-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

$$\frac{\neg\text{unit-compatible}(c_1, c_2)}{\texttt{UNKNOWN}(c_1, c_2)}$$

**Examples (same unit - seconds):**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Judgment |
|--------------|--------------|------------|------------|----------|
| `lteq 30` | `gteq 60` | [0, 30] | [60, ∞) | **CONFLICT** |
| `lteq 120` | `gteq 60` | [0, 120] | [60, ∞) | POSSIBLY-COMPATIBLE |
| `eq 0` | `gt 0` | {0} | (0, ∞) | **CONFLICT** |
| `gteq 0` | `lteq 3600` | [0, ∞) | [0, 3600] | POSSIBLY-COMPATIBLE |
| `neq 30` | `eq 30` | [0,∞) \ {30} | {30} | **CONFLICT** |

**Examples (different units):**

| Constraint 1 | Constraint 2 | Judgment |
|--------------|--------------|----------|
| `lteq 30 SEC` | `gteq 100 PX` | **UNKNOWN** |
| `eq 60 SEC` | `eq 1 MIN` | **UNKNOWN** |
| `gteq 0 BYTE` | `lteq 1024` (no unit) | **UNKNOWN** |

> Note: Even `60 SEC` vs `1 MIN` yields UNKNOWN — ODRL-SA does not perform unit conversion within categories to preserve simplicity and soundness.

---

### 9. Special Case: Origin Position (Zero)

`absolutePosition eq 0` is semantically meaningful:

```turtle
# Valid: Content must start at origin
ex:startAtOrigin a odrl:Constraint ;
    odrl:leftOperand odrl:absolutePosition ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "0"^^xsd:decimal ;
    odrl:unit <http://qudt.org/vocab/unit/SEC> .
```

**Interpretation:** Asset positioned at the start/origin.

---

### 10. Comparison with Related LeftOperands

| LeftOperand | Domain | Zero Valid | Unit Required | Dimensions |
|-------------|--------|------------|---------------|------------|
| **absolutePosition** | [0, ∞) | ✅ Yes (origin) | ✅ Yes | 1D |
| **absoluteSpatialPosition** | ℝ²≥0 | ✅ Yes | ✅ Yes | 2D/3D |
| **absoluteTemporalPosition** | [0, ∞) | ✅ Yes | ❌ No (implicit) | 1D |
| **relativePosition** | [0, 100] | ✅ Yes | ❌ No (implicit %) | 1D |

**Key distinctions:**
- `absolutePosition`: Generic, requires unit, 1D
- `absoluteSpatialPosition`: Explicitly spatial, multi-dimensional
- `absoluteTemporalPosition`: Explicitly temporal, unit-free (assumes seconds)
- `relativePosition`: Percentage-based, bounded, no unit

---

### 11. Relationship to Taxonomy

```
Position LeftOperands:
├── Relative (percentage-based)
│   ├── relativePosition [0,100]
│   ├── relativeTemporalPosition [0,100]
│   └── relativeSpatialPosition [0,100]^n
└── Absolute (unit-based)
    ├── absolutePosition [0,∞) + unit  ← THIS ONE
    ├── absoluteTemporalPosition [0,∞) implicit seconds
    └── absoluteSpatialPosition ℝ^n + unit
```

---

### 12. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | FULL (when unit present) |
| **Category** | L_unit |
| **Equivalence Class** | None (unique unit-dependent semantics) |
| **External KB Required** | No |
| **Decidable** | Yes |

---

### 13. Configuration Entry

```python
"absolutePosition": {
    "class": "FULL",
    "category": "L_unit",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": True,  # Zero is valid (origin)
        "inclusive_max": None
    },
    "operators": [
        "eq", "neq", "lt", "lteq", "gt", "gteq",
        "isAnyOf", "isNoneOf", "isAllOf"
    ],
    "unit": {
        "required": True,
        "categories": ["time", "length", "data"],
        "common": {
            "time": ["SEC", "MIN", "HR"],
            "length": ["PX", "MilliM", "IN"],
            "data": ["BYTE", "KiloBYTE"]
        },
        "qudt": [
            "http://qudt.org/vocab/unit/SEC",
            "http://qudt.org/vocab/unit/MIN",
            "http://qudt.org/vocab/unit/HR",
            "http://qudt.org/vocab/unit/PX",
            "http://qudt.org/vocab/unit/MilliM",
            "http://qudt.org/vocab/unit/BYTE"
        ]
    },
    "dimensions": 1,
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 14. LaTeX Table Entry

```latex
\multicolumn{6}{l}{\textit{Unit-Dependent (4)}} \\
payAmount & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
resolution & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
absolutePosition & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
absoluteSize & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
```

---

### 15. Publication Statement

> **absolutePosition** measures the absolute location of an asset in space or time using concrete measurement units, with domain ℝ≥0 including zero to represent origin positions. The ODRL definition's "point in space or time" is treated as a 1D scalar—explicit multi-dimensional positioning requires `absoluteSpatialPosition`. Units span multiple categories (temporal: seconds, minutes; spatial: pixels, millimeters; data: bytes), but ODRL-SA requires exact unit match for comparison—even semantically equivalent values like 60 SEC and 1 MIN yield UNKNOWN, as unit conversion would add complexity without clear benefit. Each (absolutePosition, unit) pair maps to a separate Z3 Real variable, ensuring unit-mismatched constraints cannot produce false conflicts. Conflict detection reduces to interval intersection over non-negative reals within QF_LRA.

---

### 16. Summary Table

| Aspect | Specification |
|--------|---------------|
| **Semantics** | Absolute location in space or time |
| **Domain** | [0, ∞) ⊂ ℝ, zero included (origin) |
| **Operators** | 9/12 (numeric + set, excluding semantic) |
| **isAllOf** | SAT iff all values identical |
| **Unit** | Required (time/length/data) |
| **Unit mismatch** | → UNKNOWN |
| **Dimensions** | 1D scalar |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **External KB** | Not required |
| **Decidable** | Yes |
| **Category** | L_unit |

---

### 17. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .
@prefix qudt: <http://qudt.org/vocab/unit/> .

# Test 1: Same unit (seconds) - CONFLICT
ex:policy_absPosition_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "30"^^xsd:decimal ;
                  odrl:unit qudt:SEC ]
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "60"^^xsd:decimal ;
                  odrl:unit qudt:SEC ]
            )
        ]
    ] .
# Expected: CONFLICT ([0,30] ∩ [60,∞) = ∅)

# Test 2: Same unit (seconds) - COMPATIBLE
ex:policy_absPosition_compatible
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "30"^^xsd:decimal ;
                  odrl:unit qudt:SEC ]
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "120"^^xsd:decimal ;
                  odrl:unit qudt:SEC ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE ([30,120] ≠ ∅)

# Test 3: Different units (SEC vs PX) - UNKNOWN
ex:policy_absPosition_different_unit_category
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "30"^^xsd:decimal ;
                  odrl:unit qudt:SEC ]
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "100"^^xsd:decimal ;
                  odrl:unit qudt:PX ]
            )
        ]
    ] .
# Expected: UNKNOWN (SEC ≠ PX, different categories)

# Test 4: Same category different units (SEC vs MIN) - UNKNOWN
ex:policy_absPosition_same_category_different_unit
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "60"^^xsd:decimal ;
                  odrl:unit qudt:SEC ]
                [ odrl:leftOperand odrl:absolutePosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "1"^^xsd:decimal ;
                  odrl:unit qudt:MIN ]
            )
        ]
    ] .
# Expected: UNKNOWN (no unit conversion, even though 60 SEC = 1 MIN)

# Test 5: Origin position - valid
ex:policy_absPosition_origin
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:absolutePosition ;
            odrl:operator odrl:eq ;
            odrl:rightOperand "0"^^xsd:decimal ;
            odrl:unit qudt:SEC
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE (valid constraint, zero is origin)
```