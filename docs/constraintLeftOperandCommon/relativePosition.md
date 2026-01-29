## relativePosition Family - Final Formal Specification

### ODRL Vocabulary Definitions

```turtle
:relativePosition
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Relative Asset Position"@en ;
    skos:definition "A point in space or time defined with coordinates 
                     relative to full measures the positioning of the 
                     target Asset."@en ;
    skos:note "Example: The upper left corner of a picture may be 
               constrained to a specific position of the canvas 
               rendering it."@en ;
    skos:scopeNote "Non-Normative"@en .

:relativeSpatialPosition
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    skos:broader :relativePosition ;
    rdfs:label "Relative Spatial Asset Position"@en ;
    skos:definition "The relative spatial positions - expressed as 
                     percentages of full values - of four corners of a 
                     rectangle on a 2D-canvas or the eight corners of a 
                     cuboid in a 3D-space of the target Asset."@en ;
    skos:note "See also Absolute Spatial Asset Position."@en ;
    skos:scopeNote "Non-Normative"@en .

:relativeTemporalPosition
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    skos:broader :relativePosition ;
    rdfs:label "Relative Temporal Asset Position"@en ;
    skos:definition "A point in space or time defined with coordinates 
                     relative to full measures the positioning of the 
                     target Asset."@en ;
    skos:note "See also Absolute Temporal Asset Position.
               Example: The MP3 music file must be positioned between 
               the positions at 33% and 48% of the temporal length of 
               a stream."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Taxonomy Structure

```
relativePosition (abstract parent)
    ├── relativeSpatialPosition (spatial specialization)
    └── relativeTemporalPosition (temporal specialization)
```

The `skos:broader` relation establishes conceptual hierarchy without enforcing OWL-style property inheritance.

---

### 2. Semantic Analysis

#### 2.1 relativePosition (Parent)

| Aspect | Analysis |
|--------|----------|
| **Definition** | "A point in space or time defined with coordinates relative to full measures" |
| **Key phrase** | "relative to full measures" → percentage of total extent |
| **Domain** | [0, 100] |
| **Dimensionality** | Abstract in vocabulary; **1D scalar in ODRL-SA interpretation** |
| **Role** | Generic LeftOperand when spatial vs temporal distinction unnecessary |

#### 2.2 relativeTemporalPosition

| Aspect | Analysis |
|--------|----------|
| **Definition** | Position on timeline |
| **Example** | "positioned between 33% and 48% of the temporal length" |
| **Domain** | [0, 100] — confirmed by example |
| **Dimensionality** | 1D — timeline is inherently one-dimensional |

#### 2.3 relativeSpatialPosition

| Aspect | Analysis |
|--------|----------|
| **Definition** | "four corners of a rectangle on a 2D-canvas or eight corners of a cuboid in a 3D-space" |
| **True semantics** | 2D/3D bounding box region |
| **ODRL-SA treatment** | 1D scalar (see §5) |

---

### 3. Domain Specification

$$\text{dom}(\mathcal{L}_{\text{bounded}}) = [0, 100] \subset \mathbb{R}$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 | Start of extent |
| **Upper bound** | 100 | End of extent |
| **XSD Type** | `xsd:decimal` | Numeric percentage |

**Key distinction from relativeSize:** Position cannot exceed the extent—you cannot be at 150% of a timeline—but size can exceed original—you can scale to 200%.

| LeftOperand | Domain | Bounded | Semantics |
|-------------|--------|---------|-----------|
| relativePosition family | [0, 100] | Yes | Position within extent |
| relativeSize | [0, ∞) | No | Ratio to original size |

---

### 4. Operator Specification

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
| `isAllOf` | ✅ | Satisfiable iff all values identical; otherwise trivially unsatisfiable |
| `isA` | ❌ | Semantic, not applicable to numeric |
| `hasPart` | ❌ | Semantic, not applicable to numeric |
| `isPartOf` | ❌ | Semantic, not applicable to numeric |

**isAllOf formal semantics:**

$$\texttt{isAllOf}(\{v_1, \ldots, v_n\}) \equiv \begin{cases} x = v_1 & \text{if } v_1 = v_2 = \cdots = v_n \\ \bot & \text{otherwise} \end{cases}$$

---

### 5. relativeSpatialPosition: Dimensional Treatment

#### 5.1 The Challenge

ODRL definition describes **bounding boxes** (2D rectangles, 3D cuboids), but:
- ODRL constraint model provides single `rightOperand`
- Operators `lt`, `gt`, etc. induce only a **partial order** in ℝ², which is incompatible with ODRL's total-order comparison semantics

#### 5.2 ODRL-SA Choice

**1D scalar treatment** with documented precision loss.

**Justification:**
1. ODRL Core lacks multi-valued constraint syntax
2. True 2D/3D region conflict detection requires richer model
3. 1D treatment preserves soundness (over-approximates)
4. Consistent with sibling LeftOperand treatment

> True 2D/3D region semantics require application-layer interpretation beyond ODRL Core's constraint model.

---

### 6. SMT Encoding

**Theory:** QF_LRA (Quantifier-Free Linear Real Arithmetic)

**Z3 Sort:** Real

```python
from z3 import *

def encode_relativePosition_family(
    leftoperand: str, 
    operator: str, 
    value
) -> BoolRef:
    """
    Unified encoder for relativePosition, relativeTemporalPosition,
    and relativeSpatialPosition.
    """
    x = Real(leftoperand)
    domain = And(x >= 0, x <= 100)  # [0, 100]
    
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

---

### 7. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ [0, 100] (rational intervals bounded to [0, 100])

**Abstraction function:**

$$\alpha(\texttt{op } v) = \begin{cases}
[v, v] & \text{if op} = \texttt{eq} \\
[0, v) \cap [0,100] & \text{if op} = \texttt{lt} \\
[0, v] \cap [0,100] & \text{if op} = \texttt{lteq} \\
(v, 100] & \text{if op} = \texttt{gt} \\
[v, 100] & \text{if op} = \texttt{gteq} \\
[0, 100] \setminus \{v\} & \text{if op} = \texttt{neq}
\end{cases}$$

**Concretization:**

$$\gamma([a, b]) = \{ r \in [0, 100] \mid a \leq r \leq b \}$$

---

### 8. Bounded Equivalence Class

$$\mathcal{L}_{\text{bounded}} = \{\texttt{percentage}, \texttt{relativePosition}, \texttt{relativeTemporalPosition}, \texttt{relativeSpatialPosition}\}$$

**Equivalence properties:**
- Same domain: [0, 100]
- Same operators: 9/12
- Same SMT theory: QF_LRA
- Same abstract domain: 𝕀_ℚ ∩ [0, 100]

**Theorem (Bounded Equivalence):** For any constraints $c_1, c_2$ over LeftOperands in $\mathcal{L}_{\text{bounded}}$, the conflict judgment depends only on operator and value, not on LeftOperand identity.

$$\forall \ell_1, \ell_2 \in \mathcal{L}_{\text{bounded}}: \text{Judge}(\ell_1 \text{ op}_1 \text{ } v_1, \ell_2 \text{ op}_2 \text{ } v_2) = \text{Judge}(\text{op}_1 \text{ } v_1, \text{op}_2 \text{ } v_2)$$

---

### 9. Conflict Detection

**Judgment rules:**

$$\frac{\llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

**Examples:**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Judgment |
|--------------|--------------|------------|------------|----------|
| `gteq 60` | `lteq 40` | [60, 100] | [0, 40] | **CONFLICT** |
| `gteq 33` | `lteq 48` | [33, 100] | [0, 48] | POSSIBLY-COMPATIBLE |
| `eq 25` | `eq 75` | {25} | {75} | **CONFLICT** |
| `gt 50` | `lt 50` | (50, 100] | [0, 50) | **CONFLICT** |
| `neq 50` | `eq 50` | [0,100] \ {50} | {50} | **CONFLICT** |

---

### 10. Configuration

```python
LEFTOPERAND_CONFIG = {
    "relativePosition": {
        "class": "FULL",
        "category": "L_bounded",
        "z3_sort": "Real",
        "domain": {
            "min": 0,
            "max": 100,
            "inclusive_min": True,
            "inclusive_max": True
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
    },
    "relativeTemporalPosition": {
        "class": "FULL",
        "category": "L_bounded",
        "z3_sort": "Real",
        "domain": {
            "min": 0,
            "max": 100,
            "inclusive_min": True,
            "inclusive_max": True
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
    },
    "relativeSpatialPosition": {
        "class": "FULL",
        "category": "L_bounded",
        "z3_sort": "Real",
        "domain": {
            "min": 0,
            "max": 100,
            "inclusive_min": True,
            "inclusive_max": True
        },
        "operators": [
            "eq", "neq", "lt", "lteq", "gt", "gteq",
            "isAnyOf", "isNoneOf", "isAllOf"
        ],
        "unit": None,
        "dimensions": 1,
        "external_kb": False,
        "decidable": True,
        "smt_theory": "QF_LRA",
        "note": "True 2D/3D region semantics simplified to 1D scalar"
    }
}
```

---

### 11. Publication Statement

> The **relativePosition** family comprises three LeftOperands with `skos:broader` hierarchy: `relativePosition` (generic), `relativeTemporalPosition` (timeline-specific), and `relativeSpatialPosition` (canvas-specific). All share domain [0, 100] representing percentage of total extent—unlike `relativeSize` which permits values >100% for enlargement, as one cannot be at 150% of a timeline but can scale to 200% of original size. The temporal example "positioned between 33% and 48%" confirms bounded interpretation. For `relativeSpatialPosition`, ODRL's definition describes 2D/3D bounding boxes, but comparison operators induce only a partial order in ℝⁿ, incompatible with ODRL's total-order semantics. ODRL-SA therefore treats all three as 1D scalars in QF_LRA, preserving soundness through over-approximation while documenting precision loss. These LeftOperands form the bounded equivalence class $\mathcal{L}_{\text{bounded}}$ alongside `percentage`: conflict judgment depends only on operator and value, not LeftOperand identity.

---

### 12. Summary Table

| LeftOperand | Domain | Dim | Semantics | Class |
|-------------|--------|-----|-----------|-------|
| **relativePosition** | [0, 100] | 1D | Generic position as % | 𝓛_bounded |
| **relativeTemporalPosition** | [0, 100] | 1D | Timeline position as % | 𝓛_bounded |
| **relativeSpatialPosition** | [0, 100] | 1D* | Spatial position as % | 𝓛_bounded |
| **relativeSize** | [0, ∞) | 1D | Size as % of original | L_percentage_unbounded |

*