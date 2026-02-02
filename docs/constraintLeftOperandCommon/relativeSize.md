## relativeSize - Deep Semantic Analysis

### 1. ODRL Definition

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

### 2. Key Insight from the Definition

**Critical phrase:** *"expressed as percentages of full values"*

**Example:** *"resized in width to a maximum of **200%**"*

This tells us:
- **100% = original size** (baseline)
- **200% = double the original size** (enlargement)
- **50% = half the original size** (reduction)

---

### 3. Domain Analysis

#### 3.1 What Does the Example Tell Us?

```
"The image can be resized in width to a maximum of 200%"
```

This means:
- **200% is allowed** → Enlargement beyond original is valid
- **Upper bound of 200%** → `relativeSize lteq 200`

#### 3.2 Can relativeSize Exceed 100%?

**YES!** The example explicitly shows 200%.

This is the **key difference** from other percentage-based LeftOperands:

| LeftOperand | Domain | Can exceed 100%? |
|-------------|--------|------------------|
| percentage | [0, 100] | ❌ No |
| relativePosition | [0, 100] | ❌ No |
| relativeTemporalPosition | [0, 100] | ❌ No |
| relativeSpatialPosition | [0, 100] | ❌ No |
| **relativeSize** | **[0, ∞)** | ** Yes** |

#### 3.3 Can relativeSize Be Zero?

**Semantically questionable but technically valid:**

| Value | Meaning | Valid? |
|-------|---------|--------|
| 0% | Asset has zero size (collapsed) | ⚠️ Edge case |
| 0.01% | Extremely small |  Yes |
| 100% | Original size |  Yes |
| 200% | Double size |  Yes |
| ∞ | Unlimited size | ⚠️ No upper bound |

**Decision:** Include zero for completeness, but it represents a degenerate state.

$$\text{dom}(\texttt{relativeSize}) = [0, +\infty)$$

---

### 4. Semantic Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    RELATIVESIZE SEMANTICS                       │
│                                                                 │
│  Scale:   0% ────── 50% ────── 100% ────── 200% ────── ∞       │
│           │         │          │           │                    │
│           │         │          │           │                    │
│       Collapsed  Reduced   Original   Enlarged                  │
│       (invalid)  (shrunk)  (baseline) (expanded)               │
│                                                                 │
│  Constraint: relativeSize lteq 200                             │
│  Meaning: Asset may be resized up to 200% of original          │
│  Allowed: [0, 200]                                              │
│                                                                 │
│  Constraint: relativeSize gteq 50                              │
│  Meaning: Asset must be at least 50% of original               │
│  Allowed: [50, ∞)                                               │
│                                                                 │
│  Constraint: relativeSize eq 100                               │
│  Meaning: Asset must remain original size (no resize)          │
│  Allowed: {100}                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. Comparison: relativeSize vs absoluteSize

| Aspect | relativeSize | absoluteSize |
|--------|--------------|--------------|
| **Semantics** | Percentage of original | Actual measurement |
| **Domain** | [0, ∞) | (0, ∞) |
| **Unit** | Implicit (percentage) | Required (px, mm, MB) |
| **100 means** | Original size | 100 units |
| **200 means** | Double original | 200 units |
| **Zero valid?** | ⚠️ Edge case | ❌ No (degenerate) |
| **Can exceed 100?** |  Yes | N/A (not percentage) |

---

### 6. Why relativeSize ≠ Bounded [0, 100]

#### 6.1 The "Bounded Equivalence Class"

Earlier, we defined the **Bounded Equivalence Class**:

$$\mathcal{L}_{\text{bounded}} = \{\texttt{percentage}, \texttt{relativePosition}, \texttt{relativeTemporalPosition}, \texttt{relativeSpatialPosition}\}$$

All with domain [0, 100].

#### 6.2 relativeSize is NOT in This Class

The ODRL example "maximum of 200%" **explicitly** shows values > 100%.

**Semantic justification:**
- `percentage` = "part of whole" → bounded by whole (100%)
- `relativePosition` = "position within span" → bounded by span (100%)
- `relativeSize` = "scaling factor" → NOT bounded (can enlarge)

```
┌─────────────────────────────────────────────────────────────────┐
│            PERCENTAGE-LIKE LEFTOPERANDS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BOUNDED [0, 100]:                                              │
│  • percentage         - "what fraction of total?"               │
│  • relativePosition   - "where in the span?"                    │
│  • relativeTemporalPosition - "when in the timeline?"          │
│  • relativeSpatialPosition  - "where in the region?"           │
│                                                                 │
│  UNBOUNDED [0, ∞):                                              │
│  • relativeSize       - "how much scaling?"                     │
│                         (can ENLARGE beyond original)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7. Domain Specification

$$\text{dom}(\texttt{relativeSize}) = [0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 | Zero = collapsed (edge case) |
| **Inclusive lower** |  Yes | 0% technically representable |
| **Upper bound** | ∞ | No theoretical maximum |
| **Zero semantics** | Degenerate | Asset has no size |
| **100 semantics** | Original | Baseline (no change) |
| **>100 semantics** | Enlargement | Scaling up |
| **<100 semantics** | Reduction | Scaling down |

---

### 8. Operator Analysis

#### 8.1 Typical Usage Patterns

| Pattern | Example | Meaning |
|---------|---------|---------|
| Upper bound | `lteq 200` | "At most 200% (double)" |
| Lower bound | `gteq 50` | "At least 50% (half)" |
| Exact | `eq 100` | "Original size only" |
| Range | `gteq 50 ∧ lteq 200` | "Between half and double" |
| Prohibition | `gt 100` (prohibited) | "Cannot enlarge" |

#### 8.2 Valid Operators

| Operator | Valid | Typical Use |
|----------|-------|-------------|
| `eq` | Yes | Lock to specific scale |
| `neq` | Yes | Exclude specific scale |
| `lt` | Yes | Strict upper bound |
| `lteq` | Yes | Upper bound (most common) |
| `gt` | Yes | Strict lower bound |
| `gteq` | Yes | Lower bound |
| `isAnyOf` | Yes | Allowed scale factors |
| `isNoneOf` | Yes | Prohibited scale factors |
| `isAllOf` | ⚠️ | Only if all values same |

---

### 9. Conflict Detection

#### 9.1 Abstraction Function

$$\alpha(\texttt{relativeSize } op \; v) = \begin{cases}
[0, v) & \text{if } op = \texttt{lt} \\
[0, v] & \text{if } op = \texttt{lteq} \\
(v, +\infty) & \text{if } op = \texttt{gt} \\
[v, +\infty) & \text{if } op = \texttt{gteq} \\
\{v\} & \text{if } op = \texttt{eq} \\
[0, +\infty) \setminus \{v\} & \text{if } op = \texttt{neq}
\end{cases}$$

#### 9.2 Conflict Examples

```
Scale Axis (%):  0 ────── 50 ────── 100 ────── 200 ────── ∞

CONFLICT: lteq 50 ∧ gteq 100
┌────────────────────────────────────────────────────────────────┐
│  lteq 50:      [0 ═══════ 50]                                  │
│  gteq 100:                      [100 ══════════════════════════►│
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘

COMPATIBLE: gteq 50 ∧ lteq 200
┌────────────────────────────────────────────────────────────────┐
│  gteq 50:            [50 ══════════════════════════════════════►│
│  lteq 200:  [0 ══════════════════════════ 200]                 │
│  Intersection:       [50 ════════════════ 200]                 │
│  Result: COMPATIBLE                                           │
└────────────────────────────────────────────────────────────────┘

CONFLICT: eq 100 ∧ gt 100
┌────────────────────────────────────────────────────────────────┐
│  eq 100:                        {100}                          │
│  gt 100:                             (100 ══════════════════════►│
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘
```

---

### 10. Dimensional Treatment

#### 10.1 ODRL Definition Mentions Multiple Axes

> "Measure(s) of one or two axes for 2D-objects or measure(s) of one to three axes for 3D-objects"

This suggests multi-dimensional interpretation.

#### 10.2 ODRL-SA Treatment: 1D Scalar

**Justification (same as absoluteSize):**

1. **ODRL constraint model**: Single `rightOperand` value
2. **Operators**: `lt`, `gt` induce total order (1D only)
3. **ODRL example**: "resized in **width** to a maximum of 200%" — single axis
4. **Multi-axis**: Requires separate constraints per axis

**Conclusion:** Treat as 1D scalar. Multi-dimensional requires multiple constraints.

---

### 11. SMT Encoding

```python
from z3 import *

class RelativeSizeEncoder:
    """SMT encoder for relativeSize constraints."""
    
    def __init__(self):
        self.var = Real('relativeSize')
    
    def domain_constraint(self) -> BoolRef:
        """Domain: [0, ∞)"""
        return self.var >= 0
    
    def encode(self, operator: str, value: float) -> BoolRef:
        """Encode relativeSize constraint."""
        
        domain = self.domain_constraint()
        
        if operator == "eq":
            return And(domain, self.var == value)
        elif operator == "neq":
            return And(domain, self.var != value)
        elif operator == "lt":
            return And(domain, self.var < value)
        elif operator == "lteq":
            return And(domain, self.var <= value)
        elif operator == "gt":
            return And(domain, self.var > value)
        elif operator == "gteq":
            return And(domain, self.var >= value)
        elif operator == "isAnyOf":
            # value is a list
            return And(domain, Or([self.var == v for v in value]))
        elif operator == "isNoneOf":
            return And(domain, And([self.var != v for v in value]))
        else:
            raise ValueError(f"Invalid operator: {operator}")
```

---

### 12. Quick Reference Card

| Property | Value |
|----------|-------|
| **Semantics** | Scaling factor as percentage of original |
| **Domain** | $[0, +\infty)$ |
| **Lower bound** | 0 (inclusive, edge case) |
| **Upper bound** | ∞ (no limit) |
| **100 means** | Original size (baseline) |
| **>100 means** | Enlargement |
| **<100 means** | Reduction |
| **Unit** | Implicit (percentage) |
| **Operators** | All 9 (eq, neq, lt, lteq, gt, gteq, isAnyOf, isNoneOf, isAllOf) |
| **Category** | $\mathcal{L}_{\text{unbounded-pct}}$ |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **Decidable** |  Yes |
| **External KB** | ❌ No |

---

### 13. Classification Update

#### 13.1 NOT in Bounded Equivalence Class

$$\texttt{relativeSize} \notin \mathcal{L}_{\text{bounded}}$$

#### 13.2 New Category: Unbounded Percentage

$$\mathcal{L}_{\text{unbounded-pct}} = \{\texttt{relativeSize}\}$$

| Category | Domain | Members |
|----------|--------|---------|
| $\mathcal{L}_{\text{bounded}}$ | [0, 100] | percentage, relativePosition, relativeTemporalPosition, relativeSpatialPosition |
| $\mathcal{L}_{\text{unbounded-pct}}$ | [0, ∞) | **relativeSize** |

---

### 14. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .

# ═══════════════════════════════════════════════════════════════
# CONFLICT TESTS
# ═══════════════════════════════════════════════════════════════

# Test 1: Impossible range - CONFLICT
ex:policy_relsize_01
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "100"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ([0,50] ∩ [100,∞) = ∅)

# Test 2: Contradictory equality - CONFLICT
ex:policy_relsize_02
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "100"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "200"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ({100} ∩ {200} = ∅)

# Test 3: Point outside range - CONFLICT
ex:policy_relsize_03
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "100"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:gt ;
                  odrl:rightOperand "100"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ({100} ∩ (100,∞) = ∅)

# ═══════════════════════════════════════════════════════════════
# COMPATIBLE TESTS
# ═══════════════════════════════════════════════════════════════

# Test 4: Valid range - COMPATIBLE (ODRL example)
ex:policy_relsize_04
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "200"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (allows 0-200%)

# Test 5: Original size only - COMPATIBLE
ex:policy_relsize_05
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:eq ;
            odrl:rightOperand "100"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (exactly 100%)

# Test 6: No enlargement - COMPATIBLE
ex:policy_relsize_06
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "100"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (0-100%, no enlargement)

# Test 7: Minimum size - COMPATIBLE
ex:policy_relsize_07
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "50"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (at least 50%)

# Test 8: Range constraint - COMPATIBLE
ex:policy_relsize_08
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeSize ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "200"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: COMPATIBLE (50-200%)

# Test 9: Large enlargement allowed - COMPATIBLE
ex:policy_relsize_09
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "500"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (allows up to 500%)

# ═══════════════════════════════════════════════════════════════
# DEONTIC CONFLICT TESTS
# ═══════════════════════════════════════════════════════════════

# Test 10: Permission-Prohibition overlap - DEONTIC CONFLICT
ex:policy_relsize_10
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "200"^^xsd:decimal
        ]
    ] ;
    odrl:prohibition [
        odrl:action odrl:reproduce ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeSize ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "100"^^xsd:decimal
        ]
    ] .
# Expected: DEONTIC CONFLICT
# Permission: [0, 200]
# Prohibition: [100, ∞)
# Overlap: [100, 200]
```

---

### 15. Configuration Entry

```python
"relativeSize": {
    "class": "FULL",
    "category": "L_unbounded_pct",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,           # Unbounded!
        "inclusive_min": True,  # 0 included (edge case)
        "inclusive_max": None
    },
    "value_type": "xsd:decimal",
    "unit": None,              # Implicit percentage
    "operators": {
        "recommended": ["lteq", "gteq", "eq"],
        "valid": ["eq", "neq", "lt", "lteq", "gt", "gteq", "isAnyOf", "isNoneOf", "isAllOf"]
    },
    "semantics": {
        "100": "original size (baseline)",
        ">100": "enlargement",
        "<100": "reduction",
        "0": "collapsed (edge case)"
    },
    "dimensional": "1D scalar (multi-axis requires multiple constraints)",
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 16. Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   relativeSize LeftOperand                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DEFINITION                                                     │
│  ══════════                                                     │
│  Scaling factor as percentage of original asset size            │
│  Domain: [0, ∞) — CAN EXCEED 100%                              │
│                                                                 │
│  Scale:   0% ────── 50% ────── 100% ────── 200% ────── ∞       │
│           │         │          │           │                    │
│       Collapsed  Reduced   Original   Enlarged                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  KEY DISTINCTION                                                │
│  ═══════════════                                                │
│                                                                 │
│  Bounded [0,100]:          Unbounded [0,∞):                    │
│  • percentage              • relativeSize ← THIS ONE           │
│  • relativePosition                                            │
│  • relativeTemporalPos                                         │
│  • relativeSpatialPos                                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OPERATORS: All 9 valid                                         │
│  UNIT: None (implicit percentage)                               │
│  SMT: QF_LRA, Real sort                                        │
│  DECIDABLE: Yes                                                 │
│  EXTERNAL KB: No                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 17. Publication Statement

> **relativeSize** specifies a scaling factor as a percentage of the original asset size, with domain $[0, +\infty)$. Unlike bounded percentage-based LeftOperands (`percentage`, `relativePosition`, etc.) which are constrained to $[0, 100]$, `relativeSize` permits values exceeding 100% to express enlargement—as explicitly demonstrated by the ODRL example "resized in width to a maximum of 200%". The value 100 represents the original size (baseline); values below 100 indicate reduction, and values above 100 indicate enlargement. Zero represents a degenerate state (collapsed asset). ODRL-SA treats `relativeSize` as a 1D scalar; multi-dimensional constraints require separate constraints per axis. Static conflict detection uses interval intersection over $[0, +\infty)$, detecting impossible combinations such as `lteq 50` ∧ `gteq 100` where $[0, 50] \cap [100, \infty) = \emptyset$.

---

This completes the formal specification for `relativeSize`. The key insight is that **it is NOT bounded by 100%** — it explicitly allows enlargement, making it distinct from other percentage-based LeftOperands.