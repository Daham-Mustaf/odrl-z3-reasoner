## absoluteTemporalPosition - Final Formal Specification

### ODRL Vocabulary Definition

```turtle
:absoluteTemporalPosition
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    skos:broader :absolutePosition ;
    rdfs:label "Absolute Temporal Asset Position"@en ;
    skos:definition "The absolute temporal positions in a media stream 
                     the target Asset has to fit."@en ;
    skos:note "Use with Actions including the target Asset in a larger 
               media stream. The fragment part of a Media Fragment URI 
               (https://www.w3.org/TR/media-frags/) may be used for the 
               right operand. See the Left Operand relativeTemporalPosition.
               <br />Example: The MP3 music file must be positioned between 
               second 192 and 250 of the temporal length of a stream."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Intuitive Semantics

**What it measures:** The absolute time position within a media stream where an asset must be placed, expressed in seconds.

| Context | Example Values | Interpretation |
|---------|----------------|----------------|
| Video insertion | 192, 250 | Between 3:12 and 4:10 |
| Audio placement | 0, 30 | First 30 seconds |
| Ad break position | 600 | At 10 minutes |
| Clip extraction | 3600 | At 1 hour mark |

**Use cases (from ODRL):**
- "MP3 music file must be positioned between second 192 and 250"
- Ad placement timing in video streams
- Soundtrack synchronization points
- Chapter markers in audiobooks

**Key reference:** W3C Media Fragments URI (https://www.w3.org/TR/media-frags/)

---

### 2. Formal Domain Specification

$$\text{dom}(\texttt{absoluteTemporalPosition}) = \mathbb{R}_{\geq 0} = [0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (inclusive) | Media streams start at t=0 |
| **Upper bound** | ∞ | No theoretical maximum duration |
| **XSD Type** | `xsd:decimal` | Allows fractional seconds |

> Zero **IS** valid — it represents the beginning of the media stream (origin position). This aligns with `absolutePosition` semantics where zero represents origin.

---

### 3. Unit Specification

**Unit Required:** ❌ No (implicit seconds)

| Property | Value |
|----------|-------|
| **Implicit unit** | Seconds |
| **Justification** | ODRL example explicitly uses "second 192 and 250" |
| **Media Fragments** | NPT (Normal Play Time) uses seconds as base |

**Media Fragments URI reference:**
```
t=192,250  →  from 192 seconds to 250 seconds
t=npt:192,250  →  explicit NPT format (Normal Play Time)
```

**Why no explicit unit:**
1. ODRL example: "between second 192 and 250" — seconds are default
2. Media Fragments URI standard uses seconds as base unit
3. `skos:broader :absolutePosition` but specialized for temporal domain
4. Contrast with `absolutePosition` which needs unit (could be temporal, spatial, or data)

**Distinction from absolutePosition:**

| Aspect | absolutePosition | absoluteTemporalPosition |
|--------|------------------|--------------------------|
| Domain | Generic (space or time) | Temporal only |
| Unit | Required (SEC, PX, BYTE, etc.) | Implicit (seconds) |
| Use case | Any positional constraint | Media stream positioning |

---

### 4. Dimensional Treatment

**ODRL-SA Treatment:** 1D scalar (time axis)

**Justification:**
1. Temporal position is inherently 1-dimensional
2. Media streams have linear time progression
3. ODRL example uses scalar values (192, 250)
4. Media Fragments URI uses 1D time intervals

---

### 5. Operator Specification

**Valid operators:** 9 of 12

| Operator | Valid | Semantics |
|----------|-------|-----------|
| `eq` | ✅ | Exact time position |
| `neq` | ✅ | Any time except specified |
| `lt` | ✅ | Before this time |
| `lteq` | ✅ | At or before this time |
| `gt` | ✅ | After this time |
| `gteq` | ✅ | At or after this time |
| `isAnyOf` | ✅ | Position in enumerated set |
| `isNoneOf` | ✅ | Position not in enumerated set |
| `isAllOf` | ✅ | Satisfiable iff all values identical |
| `isA` | ❌ | Semantic, not applicable |
| `hasPart` | ❌ | Semantic, not applicable |
| `isPartOf` | ❌ | Semantic, not applicable |

**Common pattern (from ODRL example):**
```turtle
# "positioned between second 192 and 250"
[ odrl:leftOperand odrl:absoluteTemporalPosition ;
  odrl:operator odrl:gteq ;
  odrl:rightOperand "192"^^xsd:decimal ]
[ odrl:leftOperand odrl:absoluteTemporalPosition ;
  odrl:operator odrl:lteq ;
  odrl:rightOperand "250"^^xsd:decimal ]
```

---

### 6. SMT Encoding

**Theory:** QF_LRA (Quantifier-Free Linear Real Arithmetic)

**Z3 Sort:** Real

```python
from z3 import *

def encode_absoluteTemporalPosition(operator: str, value) -> BoolRef:
    """
    Encode absoluteTemporalPosition constraint.
    Unit is always seconds (implicit).
    """
    x = Real('absoluteTemporalPosition')
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
```

**Key difference from absolutePosition:**
- `absolutePosition`: Variable name includes unit (`absolutePosition_SEC`, `absolutePosition_PX`)
- `absoluteTemporalPosition`: Single variable (implicit seconds)

---

### 7. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ [0, ∞) (rational intervals over non-negative reals)

**Abstraction function:**

$$\alpha(\texttt{absoluteTemporalPosition op } v) = \begin{cases}
[v, v] & \text{if op} = \texttt{eq} \\
[0, v) & \text{if op} = \texttt{lt} \\
[0, v] & \text{if op} = \texttt{lteq} \\
(v, +\infty) & \text{if op} = \texttt{gt} \\
[v, +\infty) & \text{if op} = \texttt{gteq} \\
[0, +\infty) \setminus \{v\} & \text{if op} = \texttt{neq}
\end{cases}$$

---

### 8. Conflict Detection

**Judgment rules:**

$$\frac{\llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

> No UNKNOWN case for same-LeftOperand comparisons — unit is always seconds.

**Examples:**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Judgment |
|--------------|--------------|------------|------------|----------|
| `gteq 192` | `lteq 250` | [192, ∞) | [0, 250] | POSSIBLY-COMPATIBLE |
| `lteq 100` | `gteq 200` | [0, 100] | [200, ∞) | **CONFLICT** |
| `eq 0` | `gt 0` | {0} | (0, ∞) | **CONFLICT** |
| `gteq 0` | `lteq 3600` | [0, ∞) | [0, 3600] | POSSIBLY-COMPATIBLE |
| `eq 192` | `eq 250` | {192} | {250} | **CONFLICT** |
| `neq 192` | `eq 192` | [0,∞)\{192} | {192} | **CONFLICT** |

**ODRL example analysis:**
- "between second 192 and 250" → `gteq 192 ∧ lteq 250`
- Interval: [192, 250]
- Self-consistent: [192, ∞) ∩ [0, 250] = [192, 250] ≠ ∅ ✓

---

### 9. Comparison with Related LeftOperands

**Position LeftOperands Taxonomy:**

```
Position LeftOperands
├── Relative (percentage-based, no unit)
│   ├── relativePosition [0,100]
│   ├── relativeTemporalPosition [0,100]      ← percentage of duration
│   └── relativeSpatialPosition [0,100]^n
└── Absolute (concrete values)
    ├── absolutePosition [0,∞) + unit         ← generic, unit required
    ├── absoluteTemporalPosition [0,∞)        ← temporal only, implicit seconds
    └── absoluteSpatialPosition ℝ^n + unit    ← spatial only, 2D/3D
```

**Detailed comparison:**

| LeftOperand | Domain | Unit | Dimensions | Use Case |
|-------------|--------|------|------------|----------|
| absolutePosition | [0, ∞) | Required | 1D | Generic positioning |
| **absoluteTemporalPosition** | [0, ∞) | Implicit (sec) | 1D | Media stream timing |
| absoluteSpatialPosition | ℝ^n | Required | 2D/3D | Spatial coordinates |
| relativeTemporalPosition | [0, 100] | Implicit (%) | 1D | Percentage of duration |

**Key distinctions:**
- `absoluteTemporalPosition` vs `absolutePosition`: Specialized temporal domain, no explicit unit needed
- `absoluteTemporalPosition` vs `relativeTemporalPosition`: Absolute seconds vs percentage of total duration
- `skos:broader :absolutePosition`: Inheritance relationship confirmed

---

### 10. Cross-LeftOperand Comparison

When comparing `absoluteTemporalPosition` with `absolutePosition` using temporal units:

| Constraint 1 | Constraint 2 | Judgment |
|--------------|--------------|----------|
| `absoluteTemporalPosition gteq 192` | `absolutePosition gteq 192 SEC` | **UNKNOWN** |

**Rationale:**
- Different LeftOperands → different Z3 variables
- Cannot assume semantic equivalence
- Conservative: UNKNOWN preserves soundness

---

### 11. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | FULL |
| **Category** | L_temporal |
| **Equivalence Class** | None |
| **External KB Required** | No |
| **Decidable** | Yes |

---

### 12. Configuration Entry

```python
"absoluteTemporalPosition": {
    "class": "FULL",
    "category": "L_temporal",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": True,   # Zero valid (stream start)
        "inclusive_max": None
    },
    "operators": [
        "eq", "neq", "lt", "lteq", "gt", "gteq",
        "isAnyOf", "isNoneOf", "isAllOf"
    ],
    "unit": {
        "required": False,
        "implicit": "seconds",
        "reference": "https://www.w3.org/TR/media-frags/"
    },
    "dimensions": 1,
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 13. LaTeX Table Entry

```latex
\multicolumn{6}{l}{\textit{Temporal (2)}} \\
dateTime & $\mathcal{L}_{\text{xsd}}$ & $\mathbb{Z}$ & LIA & \fullmark & \fullmark \\
absoluteTemporalPosition & $\mathcal{L}_{\text{temporal}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
```

---

### 14. Publication Statement

> **absoluteTemporalPosition** measures the absolute time position within a media stream where an asset must be placed, with domain ℝ≥0 including zero to represent the stream's beginning. Unlike the generic `absolutePosition` which requires an explicit unit, `absoluteTemporalPosition` uses implicit seconds—consistent with the ODRL example "between second 192 and 250" and the W3C Media Fragments URI standard. The `skos:broader :absolutePosition` relationship indicates specialization for the temporal domain. Conflict detection reduces to interval intersection over non-negative reals within QF_LRA; constraints like `gteq 192` ∧ `lteq 250` produce the satisfying interval [192, 250]. Cross-LeftOperand comparisons with `absolutePosition` (even with SEC unit) yield UNKNOWN as semantic equivalence cannot be assumed.

---

### 15. Summary Table

| Aspect | Specification |
|--------|---------------|
| **Semantics** | Absolute time position in media stream |
| **Domain** | [0, ∞) ⊂ ℝ, zero valid (stream start) |
| **Operators** | 9/12 (numeric + set, excluding semantic) |
| **Unit** | Implicit (seconds) |
| **Reference** | W3C Media Fragments URI |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **Z3 Variable** | Single (`absoluteTemporalPosition`) |
| **External KB** | Not required |
| **Decidable** | Yes |
| **Category** | L_temporal |
| **Broader** | absolutePosition |

---

### 16. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .

# Test 1: ODRL Example - "between second 192 and 250"
ex:policy_absTemp_odrl_example
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "192"^^xsd:decimal ]
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "250"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE ([192,250] ≠ ∅)

# Test 2: Non-overlapping intervals - CONFLICT
ex:policy_absTemp_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "100"^^xsd:decimal ]
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "200"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ([0,100] ∩ [200,∞) = ∅)

# Test 3: Zero position valid (stream start)
ex:policy_absTemp_zero
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "0"^^xsd:decimal ]
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "30"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE ([0,30] = first 30 seconds)

# Test 4: Exact position
ex:policy_absTemp_exact
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:absoluteTemporalPosition ;
            odrl:operator odrl:eq ;
            odrl:rightOperand "600"^^xsd:decimal
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE (exactly at 10 minutes)

# Test 5: Conflicting exact positions
ex:policy_absTemp_exact_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "192"^^xsd:decimal ]
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "250"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ({192} ∩ {250} = ∅)

# Test 6: Zero excluded - CONFLICT
ex:policy_absTemp_zero_excluded
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "0"^^xsd:decimal ]
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:gt ;
                  odrl:rightOperand "0"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ({0} ∩ (0,∞) = ∅)

# Test 7: Ad break at 10 minutes
ex:policy_absTemp_ad_break
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:target ex:advertisement ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "600"^^xsd:decimal ]
                [ odrl:leftOperand odrl:absoluteTemporalPosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "630"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE (30-second ad window at 10 min)
```

---

