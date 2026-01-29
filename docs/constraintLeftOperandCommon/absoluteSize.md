## absoluteSize - Final Formal Specification

### ODRL Vocabulary Definition

```turtle
:absoluteSize
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Absolute Asset Size"@en ;
    skos:definition "Measure(s) of one or two axes for 2D-objects or 
                     measure(s) of one to three axes for 3D-objects 
                     of the target Asset."@en ;
    skos:note "Example: The image can be resized in width to a maximum 
               of 1000px."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Intuitive Semantics

**What it measures:** The physical or logical dimensions of an asset using concrete measurement units.

| Context | Example Values | Units |
|---------|----------------|-------|
| Image dimensions | 1000, 1920, 4096 | pixels (PX) |
| Print dimensions | 210, 297 | millimeters (mm) |
| File size | 1024, 1048576 | bytes (BYTE, KiloBYTE, MegaBYTE) |
| Video resolution | 1920, 1080 | pixels |

**Use cases:**
- Image resizing limits ("max width 1000px" — from ODRL example)
- File size restrictions ("max 10MB for email attachment")
- Print constraints ("A4 paper = 210mm × 297mm")
- Thumbnail generation ("reduce to max 256px")

---

### 2. Formal Domain Specification

$$\text{dom}(\texttt{absoluteSize}) = \mathbb{R}_{> 0} = (0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (exclusive) | Zero size is degenerate (no asset) |
| **Upper bound** | ∞ | No theoretical maximum |
| **XSD Type** | `xsd:decimal` | Numeric value |

> Zero is **NOT** valid for `absoluteSize` — an asset with zero size does not exist. This distinguishes it from `absolutePosition` where zero (origin) is meaningful.

---

### 3. Unit Specification

**Unit Required:** Yes

| Property | Value |
|----------|-------|
| **Unit categories** | Length, Data |
| **Spatial units** | pixels (PX), millimeters (MilliM), inches (IN), centimeters (CentiM) |
| **Data units** | bytes (BYTE), kilobytes (KiloBYTE), megabytes (MegaBYTE), gigabytes (GigaBYTE) |

**QUDT URIs:**

| Category | Unit | QUDT URI |
|----------|------|----------|
| Spatial | pixel | `http://qudt.org/vocab/unit/PX` |
| Spatial | millimeter | `http://qudt.org/vocab/unit/MilliM` |
| Spatial | centimeter | `http://qudt.org/vocab/unit/CentiM` |
| Spatial | inch | `http://qudt.org/vocab/unit/IN` |
| Data | byte | `http://qudt.org/vocab/unit/BYTE` |
| Data | kilobyte | `http://qudt.org/vocab/unit/KiloBYTE` |
| Data | megabyte | `http://qudt.org/vocab/unit/MegaBYTE` |
| Data | gigabyte | `http://qudt.org/vocab/unit/GigaBYTE` |

**Unit Comparability Rule:**
- Same unit → Comparable
- Different units → **UNKNOWN** (no automatic conversion)
- Missing unit → **UNKNOWN**

**Rationale for no unit conversion:**
1. Spatial and data units are incomparable categories
2. Even within categories (e.g., PX vs MM), conversion requires context (DPI)
3. Data units (KB, MB) have ambiguous bases (1000 vs 1024)
4. Conservative approach preserves soundness

---

### 4. Dimensional Treatment

The definition mentions "one to three axes" for multi-dimensional objects, but:

**ODRL-SA Treatment:** 1D scalar

**Justification:**
1. ODRL constraint model provides single `rightOperand`
2. Example uses "width" — a single axis measurement
3. Operators `lt`, `gt` induce total order (well-defined for 1D only)
4. Multi-axis constraints require multiple separate constraints

> The ODRL example "resized in width to a maximum of 1000px" confirms single-axis interpretation. For multi-dimensional size constraints, policy authors should use multiple constraints (one per axis) or profile-specific extensions.

---

### 5. Operator Specification

**Valid operators:** 9 of 12

| Operator | Valid | Semantics |
|----------|-------|-----------|
| `eq` | ✅ | Exact size required |
| `neq` | ✅ | Any size except specified |
| `lt` | ✅ | Smaller than this size |
| `lteq` | ✅ | At most this size |
| `gt` | ✅ | Larger than this size |
| `gteq` | ✅ | At least this size |
| `isAnyOf` | ✅ | Size in enumerated set |
| `isNoneOf` | ✅ | Size not in enumerated set |
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

def encode_absoluteSize(operator: str, value, unit: str = None) -> BoolRef:
    """
    Encode absoluteSize constraint.
    Returns BoolVal(True) with UNKNOWN flag if unit missing/incompatible.
    """
    if unit is None:
        # Cannot analyze without unit
        return BoolVal(True)  # Over-approximate, mark UNKNOWN
    
    # Variable name includes unit for isolation
    x = Real(f'absoluteSize_{normalize_unit(unit)}')
    domain = x > 0  # (0, ∞) — strictly positive
    
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
    """Normalize size unit to canonical form."""
    UNIT_MAP = {
        # Spatial units
        "px": "PX", "PX": "PX", "pixel": "PX", "pixels": "PX",
        "http://qudt.org/vocab/unit/PX": "PX",
        "mm": "MilliM", "MilliM": "MilliM", "millimeter": "MilliM",
        "http://qudt.org/vocab/unit/MilliM": "MilliM",
        "cm": "CentiM", "CentiM": "CentiM", "centimeter": "CentiM",
        "http://qudt.org/vocab/unit/CentiM": "CentiM",
        "in": "IN", "IN": "IN", "inch": "IN", "inches": "IN",
        "http://qudt.org/vocab/unit/IN": "IN",
        # Data units
        "byte": "BYTE", "BYTE": "BYTE", "bytes": "BYTE", "B": "BYTE",
        "http://qudt.org/vocab/unit/BYTE": "BYTE",
        "kb": "KiloBYTE", "KB": "KiloBYTE", "KiloBYTE": "KiloBYTE", "kilobyte": "KiloBYTE",
        "http://qudt.org/vocab/unit/KiloBYTE": "KiloBYTE",
        "mb": "MegaBYTE", "MB": "MegaBYTE", "MegaBYTE": "MegaBYTE", "megabyte": "MegaBYTE",
        "http://qudt.org/vocab/unit/MegaBYTE": "MegaBYTE",
        "gb": "GigaBYTE", "GB": "GigaBYTE", "GigaBYTE": "GigaBYTE", "gigabyte": "GigaBYTE",
        "http://qudt.org/vocab/unit/GigaBYTE": "GigaBYTE",
    }
    return UNIT_MAP.get(unit, unit)  # Unknown units stay as-is

def are_units_compatible(unit1: str, unit2: str) -> bool:
    """Check if two size units are comparable."""
    if unit1 is None or unit2 is None:
        return False
    return normalize_unit(unit1) == normalize_unit(unit2)
```

---

### 7. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ (0, ∞) (rational intervals over positive reals)

**Abstraction function:**

$$\alpha(\texttt{absoluteSize op } v) = \begin{cases}
[v, v] & \text{if op} = \texttt{eq} \\
(0, v) & \text{if op} = \texttt{lt} \\
(0, v] & \text{if op} = \texttt{lteq} \\
(v, +\infty) & \text{if op} = \texttt{gt} \\
[v, +\infty) & \text{if op} = \texttt{gteq} \\
(0, +\infty) \setminus \{v\} & \text{if op} = \texttt{neq}
\end{cases}$$

**Concretization:**

$$\gamma([a, b]) = \{ r \in \mathbb{R}_{> 0} \mid a \leq r \leq b \}$$

---

### 8. Conflict Detection

**Judgment rules:**

$$\frac{\text{unit-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\text{unit-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

$$\frac{\neg\text{unit-compatible}(c_1, c_2)}{\texttt{UNKNOWN}(c_1, c_2)}$$

**Examples (same unit - pixels):**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Judgment |
|--------------|--------------|------------|------------|----------|
| `lteq 500` | `gteq 1000` | (0, 500] | [1000, ∞) | **CONFLICT** |
| `lteq 1000` | `gteq 500` | (0, 1000] | [500, ∞) | POSSIBLY-COMPATIBLE |
| `eq 1920` | `eq 1080` | {1920} | {1080} | **CONFLICT** |
| `gt 0` | `lteq 4096` | (0, ∞) | (0, 4096] | POSSIBLY-COMPATIBLE |
| `neq 1000` | `eq 1000` | (0,∞) \ {1000} | {1000} | **CONFLICT** |

**Examples (different units):**

| Constraint 1 | Constraint 2 | Judgment |
|--------------|--------------|----------|
| `lteq 1000 PX` | `gteq 100 MilliM` | **UNKNOWN** |
| `eq 1024 BYTE` | `eq 1 KiloBYTE` | **UNKNOWN** |
| `lteq 10 MegaBYTE` | `gteq 5` (no unit) | **UNKNOWN** |

> Note: Even `1024 BYTE` vs `1 KiloBYTE` yields UNKNOWN — ODRL-SA does not perform unit conversion to avoid ambiguity (binary vs decimal kilobyte).

---

### 9. Comparison with Related LeftOperands

| LeftOperand | Domain | Zero Valid | Unit Required | Semantics |
|-------------|--------|------------|---------------|-----------|
| **absoluteSize** | (0, ∞) | ❌ No | ✅ Yes | Physical/logical dimension |
| **relativeSize** | [0, ∞) | ✅ Yes* | ❌ No (implicit %) | Ratio to original |
| **absolutePosition** | [0, ∞) | ✅ Yes (origin) | ✅ Yes | Location |
| **resolution** | (0, ∞) | ❌ No | ✅ Yes | Density |

*Note: `relativeSize` at 0% is degenerate but technically admitted.

**Key distinctions:**
- `absoluteSize`: Actual measurement, strictly positive, unit-dependent
- `relativeSize`: Percentage of original, allows >100% (enlargement)
- Domain (0, ∞) vs [0, ∞): Zero excluded for size, included for position

---

### 10. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | FULL (when unit present) |
| **Category** | L_unit |
| **Equivalence Class** | None (unique unit-dependent semantics) |
| **External KB Required** | No |
| **Decidable** | Yes |

---

### 11. Configuration Entry

```python
"absoluteSize": {
    "class": "FULL",
    "category": "L_unit",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": False,  # Strictly positive (zero excluded)
        "inclusive_max": None
    },
    "operators": [
        "eq", "neq", "lt", "lteq", "gt", "gteq",
        "isAnyOf", "isNoneOf", "isAllOf"
    ],
    "unit": {
        "required": True,
        "categories": ["length", "data"],
        "common": {
            "length": ["PX", "MilliM", "CentiM", "IN"],
            "data": ["BYTE", "KiloBYTE", "MegaBYTE", "GigaBYTE"]
        },
        "qudt": [
            "http://qudt.org/vocab/unit/PX",
            "http://qudt.org/vocab/unit/MilliM",
            "http://qudt.org/vocab/unit/CentiM",
            "http://qudt.org/vocab/unit/IN",
            "http://qudt.org/vocab/unit/BYTE",
            "http://qudt.org/vocab/unit/KiloBYTE",
            "http://qudt.org/vocab/unit/MegaBYTE",
            "http://qudt.org/vocab/unit/GigaBYTE"
        ]
    },
    "dimensions": 1,
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 12. LaTeX Table Entry

```latex
\multicolumn{6}{l}{\textit{Unit-Dependent (4)}} \\
payAmount & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
resolution & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
absolutePosition & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
absoluteSize & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
```

**Domain summary for unit-dependent LeftOperands:**

| LeftOperand | Domain | Zero |
|-------------|--------|------|
| payAmount | $\mathbb{R}_{\geq 0}$ | ✅ Valid (free) |
| absolutePosition | $\mathbb{R}_{\geq 0}$ | ✅ Valid (origin) |
| resolution | $\mathbb{R}_{> 0}$ | ❌ Invalid |
| absoluteSize | $\mathbb{R}_{> 0}$ | ❌ Invalid |

---

### 13. Publication Statement

> **absoluteSize** measures the physical or logical dimensions of an asset using concrete measurement units, with domain ℝ>0 excluding zero as a degenerate state (an asset cannot have zero size). The ODRL definition mentions "one to three axes" for multi-dimensional objects, but the example "resized in width to a maximum of 1000px" confirms single-axis interpretation; multi-dimensional constraints require separate constraints per axis. Units span spatial (pixels, millimeters) and data (bytes, megabytes) categories, but ODRL-SA requires exact unit match—even semantically equivalent values like 1024 BYTE and 1 KiloBYTE yield UNKNOWN, avoiding ambiguity between binary and decimal interpretations. Each (absoluteSize, unit) pair maps to a separate Z3 Real variable, ensuring unit-mismatched constraints cannot produce false conflicts. Conflict detection reduces to interval intersection over positive reals within QF_LRA.

---

### 14. Summary Table

| Aspect | Specification |
|--------|---------------|
| **Semantics** | Physical/logical dimension of asset |
| **Domain** | (0, ∞) ⊂ ℝ, zero excluded |
| **Operators** | 9/12 (numeric + set, excluding semantic) |
| **isAllOf** | SAT iff all values identical |
| **Unit** | Required (length/data) |
| **Unit mismatch** | → UNKNOWN |
| **Dimensions** | 1D scalar |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **External KB** | Not required |
| **Decidable** | Yes |
| **Category** | L_unit |

---

### 15. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .
@prefix qudt: <http://qudt.org/vocab/unit/> .

# Test 1: Same unit (pixels) - CONFLICT
ex:policy_absSize_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "500"^^xsd:decimal ;
                  odrl:unit qudt:PX ]
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "1000"^^xsd:decimal ;
                  odrl:unit qudt:PX ]
            )
        ]
    ] .
# Expected: CONFLICT ((0,500] ∩ [1000,∞) = ∅)

# Test 2: Same unit (pixels) - COMPATIBLE
ex:policy_absSize_compatible
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "500"^^xsd:decimal ;
                  odrl:unit qudt:PX ]
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "1000"^^xsd:decimal ;
                  odrl:unit qudt:PX ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE ([500,1000] ≠ ∅)

# Test 3: Different unit categories (PX vs BYTE) - UNKNOWN
ex:policy_absSize_different_category
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "1000"^^xsd:decimal ;
                  odrl:unit qudt:PX ]
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "1048576"^^xsd:decimal ;
                  odrl:unit qudt:BYTE ]
            )
        ]
    ] .
# Expected: UNKNOWN (PX ≠ BYTE, incomparable categories)

# Test 4: Same category different units (BYTE vs KiloBYTE) - UNKNOWN
ex:policy_absSize_same_category_different_unit
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "1024"^^xsd:decimal ;
                  odrl:unit qudt:BYTE ]
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "1"^^xsd:decimal ;
                  odrl:unit qudt:KiloBYTE ]
            )
        ]
    ] .
# Expected: UNKNOWN (no unit conversion, even though 1024 BYTE ≈ 1 KB)

# Test 5: ODRL example - max 1000px width
ex:policy_absSize_odrl_example
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:constraint [
            odrl:leftOperand odrl:absoluteSize ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "1000"^^xsd:decimal ;
            odrl:unit qudt:PX
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE (valid constraint)

# Test 6: File size limit
ex:policy_absSize_file_limit
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:distribute ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "1"^^xsd:decimal ;
                  odrl:unit qudt:MegaBYTE ]
                [ odrl:leftOperand odrl:absoluteSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "10"^^xsd:decimal ;
                  odrl:unit qudt:MegaBYTE ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE ([1,10] MB ≠ ∅)
```

---

### 16. Unit-Dependent LeftOperands Summary

| LeftOperand | Domain | Zero | Unit Category | Common Units |
|-------------|--------|------|---------------|--------------|
| **payAmount** | [0, ∞) | ✅ Free | Currency | EUR, USD, GBP |
| **absolutePosition** | [0, ∞) | ✅ Origin | Time/Length/Data | SEC, PX, BYTE |
| **resolution** | (0, ∞) | ❌ | Density | DPI, PPI |
| **absoluteSize** | (0, ∞) | ❌ | Length/Data | PX, MM, BYTE, MB |

All four share:
- Category: L_unit
- SMT Theory: QF_LRA
- Unit required: Yes
- Unit mismatch → UNKNOWN
- External KB: Not required
- Decidable: Yes

