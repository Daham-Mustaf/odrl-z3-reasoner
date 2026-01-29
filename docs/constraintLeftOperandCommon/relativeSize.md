## relativeSize - Final Formal Specification

### ODRL Vocabulary Definition

```turtle
:relativeSize
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Relative Asset Size"@en ;
    skos:definition "Measure(s) of one or two axes for 2D-objects or 
                     measure(s) of one to three axes for 3D-objects - 
                     expressed as percentages of full values - of the 
                     target Asset."@en ;
    skos:note "Example: The image can be resized in width to a maximum 
               of 200%. Note: See the Left Operand absoluteSize."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Intuitive Semantics

**What it measures:** The size of an asset relative to its original/reference size.

| Value | Meaning |
|-------|---------|
| 0% | Zero size (degenerate, asset deleted) |
| 50% | Half the original size (shrunk) |
| 100% | Original size (unchanged) |
| 200% | Double the original size (enlarged) |

**Use cases:**
- Image resizing constraints ("thumbnails must be ≤ 25%")
- Video scaling limits ("no enlargement beyond 150%")
- 3D model scaling ("maintain size between 80-120%")

---

### 2. Formal Domain Specification

$$\text{dom}(\texttt{relativeSize}) = \mathbb{R}_{\geq 0} = [0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 | Zero size is theoretical minimum |
| **Upper bound** | ∞ | "200%" example shows >100 valid |
| **XSD Type** | `xsd:decimal` | Numeric percentage value |

> Although 0% is admitted in the formal domain [0, ∞), it represents a **degenerate asset state** (zero-dimensional object) and may be disallowed by application-specific constraints. ODRL-SA admits it for completeness; practical policies typically use `gt 0` or `gteq ε` for some small ε > 0.

---

### 3. Dimensional Treatment

The definition mentions "one to three axes" but ODRL constraint model uses single `rightOperand`:

```turtle
odrl:leftOperand odrl:relativeSize ;
odrl:operator odrl:lteq ;
odrl:rightOperand "200"^^xsd:decimal .  # Single value
```

**ODRL-SA Treatment:** 1D scalar.

**Justification:** ODRL LeftOperands describe *what is constrained*, not *how an action interprets it geometrically*. Axis semantics belong to the action/application layer. Multiple axes require either uniform interpretation or multiple separate constraints.

---

### 4. Operator Specification

**Valid operators:** 9 of 12

| Operator | Valid | Semantics |
|----------|-------|-----------|
| `eq` | ✅ | Exact size ratio required |
| `neq` | ✅ | Any size except specified |
| `lt` | ✅ | Strictly smaller than ratio |
| `lteq` | ✅ | At most this ratio |
| `gt` | ✅ | Strictly larger than ratio |
| `gteq` | ✅ | At least this ratio |
| `isAnyOf` | ✅ | Size in enumerated set |
| `isNoneOf` | ✅ | Size not in enumerated set |
| `isAllOf` | ✅ | Satisfiable iff all listed values identical; otherwise trivially unsatisfiable |
| `isA` | ❌ | Semantic, not applicable to numeric |
| `hasPart` | ❌ | Semantic, not applicable to numeric |
| `isPartOf` | ❌ | Semantic, not applicable to numeric |

**isAllOf formal semantics:**

$$\texttt{isAllOf}(\{v_1, \ldots, v_n\}) \equiv \begin{cases} x = v_1 & \text{if } v_1 = v_2 = \cdots = v_n \\ \bot & \text{otherwise} \end{cases}$$

---

### 5. Unit Semantics

| Property | Value |
|----------|-------|
| **Unit required?** | No |
| **Implicit unit** | Percentage (%) |
| **Unit conversion** | Not applicable |

Unlike `absoluteSize` (which requires bytes, pixels, mm), `relativeSize` is dimensionless—a pure ratio.

---

### 6. SMT Encoding

**Theory:** QF_LRA (Quantifier-Free Linear Real Arithmetic)

**Z3 Sort:** Real

```python
from z3 import *

def encode_relativeSize(operator: str, value) -> BoolRef:
    x = Real('relativeSize')
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
            return BoolVal(False)  # Trivially unsatisfiable
```

---

### 7. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ [0, ∞) (rational intervals over non-negative reals)

**Abstraction function:**

$$\alpha(\texttt{relativeSize op } v) = \begin{cases}
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

$$\frac{\llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

**Examples:**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Intersection | Judgment |
|--------------|--------------|------------|------------|--------------|----------|
| `lteq 100` | `gteq 150` | [0, 100] | [150, ∞) | ∅ | **CONFLICT** |
| `lteq 200` | `gteq 150` | [0, 200] | [150, ∞) | [150, 200] | POSSIBLY-COMPATIBLE |
| `eq 100` | `eq 200` | {100} | {200} | ∅ | **CONFLICT** |
| `lt 100` | `gt 50` | [0, 100) | (50, ∞) | (50, 100) | POSSIBLY-COMPATIBLE |
| `neq 100` | `eq 100` | ℝ≥0 \ {100} | {100} | ∅ | **CONFLICT** |

---

### 9. Comparison with Related LeftOperands

| LeftOperand | Domain | Unit | Bounded | Reference |
|-------------|--------|------|---------|-----------|
| **relativeSize** | [0, ∞) | implicit % | No | Original asset size |
| **absoluteSize** | ℝ>0 | required | No | None (absolute) |
| **percentage** | [0, 100] | implicit % | Yes | Context-dependent |
| **relativePosition** | [0, 100] | implicit % | Yes | Total extent |

**Key distinction:** `relativeSize` allows >100% (enlargement), unlike bounded percentage LeftOperands.

---

### 10. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | FULL (𝓛_xsd) |
| **Category** | L_percentage_unbounded |
| **Equivalence Class** | None (unique semantics) |
| **External KB Required** | No |
| **Decidable** | Yes |

---

### 11. Configuration Entry

```python
"relativeSize": {
    "class": "FULL",
    "category": "L_percentage_unbounded",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": True
    },
    "operators": [
        "eq", "neq", "lt", "lteq", "gt", "gteq",
        "isAnyOf", "isNoneOf", "isAllOf"
    ],
    "unit": None,
    "dimensions": 1,
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 12. Publication Statement

> **relativeSize** measures asset dimensions as percentages of original size, with domain ℝ≥0 permitting both reduction (0-100%) and enlargement (>100%). Although 0% is formally admitted, it represents a degenerate state and may be application-disallowed. Unlike bounded percentage LeftOperands (`percentage`, `relativePosition`), `relativeSize` has no upper bound—the ODRL example "maximum of 200%" confirms values exceeding 100% are valid. ODRL-SA encodes constraints in QF_LRA using a single Real variable, treating multi-axis references as uniform scaling; per-axis control requires multiple constraints. The set operator `isAllOf` is satisfiable iff all listed values are identical. No external knowledge base required; conflict detection reduces to interval intersection over non-negative reals.

