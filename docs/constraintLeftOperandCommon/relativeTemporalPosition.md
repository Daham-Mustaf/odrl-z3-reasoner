## relativeTemporalPosition - Formal Specification

### 1. ODRL Definition

```turtle
:relativeTemporalPosition
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    skos:broader :relativePosition ;
    rdfs:label "Relative Temporal Asset Position"@en ;
    skos:definition "A point in space or time defined with coordinates relative 
                     to full measures the positioning of the target Asset."@en ;
    skos:note "See also Absolute Temporal Asset Position. <br />Example: The MP3 
               music file must be positioned between the positions at 33% and 48% 
               of the temporal length of a stream."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 2. Semantic Analysis

#### 2.1 Key Phrases

| Phrase | Interpretation |
|--------|----------------|
| "relative to full measures" | Percentage of total duration |
| "positioning of the target Asset" | Where in the timeline |
| "between 33% and 48%" | Bounded percentage range |
| "temporal length of a stream" | Total duration = 100% |
| `skos:broader :relativePosition` | Inherits from relativePosition |

#### 2.2 What It Measures

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDIA STREAM TIMELINE                        │
│                                                                 │
│  [Start]════════════════════════════════════════════[End]       │
│    0%              33%        48%                   100%        │
│    │                │          │                     │          │
│    │                ├──────────┤                     │          │
│    │                │  ASSET   │                     │          │
│    │                │ POSITION │                     │          │
│    │                │          │                     │          │
│                                                                 │
│  Constraint: relativeTemporalPosition gteq 33                   │
│              relativeTemporalPosition lteq 48                   │
│  Meaning: Asset must be positioned between 33% and 48%          │
│           of the stream's total duration                        │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3 Semantic Interpretation

- **0%** = Beginning of stream/timeline
- **100%** = End of stream/timeline
- **50%** = Exactly halfway through
- **33%** = One-third through the stream

**Example from ODRL:**
> "The MP3 music file must be positioned between the positions at 33% and 48% of the temporal length of a stream."

This means: If the stream is 100 seconds long:
- 33% = 33 seconds from start
- 48% = 48 seconds from start
- Asset must be placed in the window [33s, 48s]

---

### 3. Domain Specification

$$\text{dom}(\texttt{relativeTemporalPosition}) = [0, 100]$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 | Stream beginning |
| **Upper bound** | 100 | Stream end |
| **Inclusive bounds** | Both | 0% and 100% are valid positions |
| **Zero semantics** | Start of stream | Valid position |
| **100 semantics** | End of stream | Valid position |

---

### 4. Bounded Equivalence Class Membership

**relativeTemporalPosition ∈ $\mathcal{L}_{\text{bounded}}$**

```
┌─────────────────────────────────────────────────────────────────┐
│              BOUNDED EQUIVALENCE CLASS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  All members share: Domain [0, 100], SMT QF-LRA, Real sort      │
│                                                                 │
│  ┌─────────────────────┬─────────────────────────────────────┐  │
│  │ LeftOperand         │ What it measures (as %)             │  │
│  ├─────────────────────┼─────────────────────────────────────┤  │
│  │ percentage          │ Generic part-of-whole               │  │
│  │ relativePosition    │ Generic position in span            │  │
│  │ relativeTemporalPos │ Position in TIME (stream duration)  │  │
│  │ relativeSpatialPos  │ Position in SPACE (region)          │  │
│  └─────────────────────┴─────────────────────────────────────┘  │
│                                                                 │
│  NOT in this class:                                             │
│  • relativeSize [0, ∞) — can exceed 100% (enlargement)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. Relationship to Other LeftOperands

#### 5.1 Inheritance Hierarchy

```
relativePosition (generic)
    │
    ├── relativeTemporalPosition (time-specific)
    │       "where in the timeline"
    │
    └── relativeSpatialPosition (space-specific)
            "where in the region"
```

#### 5.2 Comparison with Related LeftOperands

| LeftOperand | Domain | What It Measures | Unit |
|-------------|--------|------------------|------|
| relativeTemporalPosition | [0, 100] | Position as % of duration | Implicit % |
| absoluteTemporalPosition | [0, ∞) | Position in seconds | Implicit seconds |
| relativePosition | [0, 100] | Generic position as % | Implicit % |
| percentage | [0, 100] | Generic part of whole | Implicit % |

#### 5.3 When to Use Which

| Use Case | LeftOperand |
|----------|-------------|
| "Ad at 30% of video" | relativeTemporalPosition |
| "Ad at 180 seconds" | absoluteTemporalPosition |
| "Image in top 25% of page" | relativeSpatialPosition |
| "Use 50% of asset" | percentage |

---

### 6. Operator Specification

#### 6.1 Valid Operators

| Operator | Valid | Typical Use |
|----------|-------|-------------|
| `eq` | ✅ | Exact position (33%) |
| `neq` | ✅ | Exclude position |
| `lt` | ✅ | Before position |
| `lteq` | ✅ | At or before position |
| `gt` | ✅ | After position |
| `gteq` | ✅ | At or after position |
| `isAnyOf` | ✅ | Specific positions |
| `isNoneOf` | ✅ | Exclude positions |
| `isAllOf` | ⚠️ | Only if all same |

#### 6.2 Typical Usage Patterns

```turtle
# Pattern 1: Position window (ODRL example)
# "between 33% and 48%"
[ odrl:and (
    [ odrl:leftOperand odrl:relativeTemporalPosition ;
      odrl:operator odrl:gteq ;
      odrl:rightOperand "33"^^xsd:decimal ]
    [ odrl:leftOperand odrl:relativeTemporalPosition ;
      odrl:operator odrl:lteq ;
      odrl:rightOperand "48"^^xsd:decimal ]
) ]

# Pattern 2: After specific point
# "in the second half of the stream"
[ odrl:leftOperand odrl:relativeTemporalPosition ;
  odrl:operator odrl:gteq ;
  odrl:rightOperand "50"^^xsd:decimal ]

# Pattern 3: Not at beginning or end
# "not in first or last 10%"
[ odrl:and (
    [ odrl:leftOperand odrl:relativeTemporalPosition ;
      odrl:operator odrl:gt ;
      odrl:rightOperand "10"^^xsd:decimal ]
    [ odrl:leftOperand odrl:relativeTemporalPosition ;
      odrl:operator odrl:lt ;
      odrl:rightOperand "90"^^xsd:decimal ]
) ]
```

---

### 7. Abstraction Function

$$\alpha(\texttt{relativeTemporalPosition } op \; v) = \begin{cases}
[0, v) & \text{if } op = \texttt{lt} \\
[0, v] & \text{if } op = \texttt{lteq} \\
(v, 100] & \text{if } op = \texttt{gt} \\
[v, 100] & \text{if } op = \texttt{gteq} \\
\{v\} & \text{if } op = \texttt{eq} \\
[0, 100] \setminus \{v\} & \text{if } op = \texttt{neq}
\end{cases}$$

---

### 8. Conflict Detection

#### 8.1 Conflict Examples

```
Timeline (%):  0 ────── 25 ────── 50 ────── 75 ────── 100

CONFLICT: lteq 25 ∧ gteq 50
┌────────────────────────────────────────────────────────────────┐
│  lteq 25:     [0 ═══════ 25]                                   │
│  gteq 50:                       [50 ═════════════════════ 100] │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘

COMPATIBLE: gteq 33 ∧ lteq 48 (ODRL example)
┌────────────────────────────────────────────────────────────────┐
│  gteq 33:           [33 ════════════════════════════════ 100]  │
│  lteq 48:     [0 ════════════════════ 48]                      │
│  Intersection:      [33 ════════════ 48]                       │
│  Result: COMPATIBLE ✅  Witness: 40                             │
└────────────────────────────────────────────────────────────────┘

CONFLICT: eq 33 ∧ eq 48
┌────────────────────────────────────────────────────────────────┐
│  eq 33:             {33}                                       │
│  eq 48:                          {48}                          │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘
```

#### 8.2 Domain Violation Detection

```
CONFLICT: gt 100 (outside domain)
┌────────────────────────────────────────────────────────────────┐
│  Domain:      [0 ═════════════════════════════════════ 100]    │
│  gt 100:                                                   (100,∞)
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌ (impossible constraint)                    │
└────────────────────────────────────────────────────────────────┘

CONFLICT: lt 0 (outside domain)
┌────────────────────────────────────────────────────────────────┐
│  Domain:      [0 ═════════════════════════════════════ 100]    │
│  lt 0:    (-∞,0)                                               │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌ (impossible constraint)                    │
└────────────────────────────────────────────────────────────────┘
```

---

### 9. SMT Encoding

```python
from z3 import *

class RelativeTemporalPositionEncoder:
    """SMT encoder for relativeTemporalPosition constraints."""
    
    def __init__(self):
        self.var = Real('relativeTemporalPosition')
    
    def domain_constraint(self) -> BoolRef:
        """Domain: [0, 100]"""
        return And(self.var >= 0, self.var <= 100)
    
    def encode(self, operator: str, value: float) -> BoolRef:
        """Encode relativeTemporalPosition constraint."""
        
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

### 10. Quick Reference Card

| Property | Value |
|----------|-------|
| **Semantics** | Position as percentage of temporal duration |
| **Domain** | $[0, 100]$ |
| **Lower bound** | 0 (stream start) |
| **Upper bound** | 100 (stream end) |
| **Value Type** | `xsd:decimal` |
| **Unit** | Implicit (percentage) |
| **Operators** | All 9 valid |
| **Category** | $\mathcal{L}_{\text{bounded}}$ |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **Inheritance** | `skos:broader :relativePosition` |
| **Decidable** | ✅ Yes |
| **External KB** | ❌ No |

---

### 11. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .

# ═══════════════════════════════════════════════════════════════
# CONFLICT TESTS
# ═══════════════════════════════════════════════════════════════

# Test 1: Impossible range - CONFLICT
ex:policy_rtp_01
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "25"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ([0,25] ∩ [50,100] = ∅)

# Test 2: Outside domain (gt 100) - CONFLICT
ex:policy_rtp_02
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:gt ;
            odrl:rightOperand "100"^^xsd:decimal
        ]
    ] .
# Expected: CONFLICT (domain violation)

# Test 3: Outside domain (lt 0) - CONFLICT
ex:policy_rtp_03
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:lt ;
            odrl:rightOperand "0"^^xsd:decimal
        ]
    ] .
# Expected: CONFLICT (domain violation)

# Test 4: Contradictory equality - CONFLICT
ex:policy_rtp_04
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "33"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "48"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: CONFLICT ({33} ∩ {48} = ∅)

# ═══════════════════════════════════════════════════════════════
# COMPATIBLE TESTS
# ═══════════════════════════════════════════════════════════════

# Test 5: ODRL example - COMPATIBLE
ex:policy_rtp_05
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "33"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "48"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: COMPATIBLE (window [33, 48])

# Test 6: Start position - COMPATIBLE
ex:policy_rtp_06
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:eq ;
            odrl:rightOperand "0"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (exactly at start)

# Test 7: End position - COMPATIBLE
ex:policy_rtp_07
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:eq ;
            odrl:rightOperand "100"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (exactly at end)

# Test 8: Second half - COMPATIBLE
ex:policy_rtp_08
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "50"^^xsd:decimal
        ]
    ] .
# Expected: COMPATIBLE (window [50, 100])

# Test 9: Middle section - COMPATIBLE
ex:policy_rtp_09
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:gt ;
                  odrl:rightOperand "10"^^xsd:decimal ]
                [ odrl:leftOperand odrl:relativeTemporalPosition ;
                  odrl:operator odrl:lt ;
                  odrl:rightOperand "90"^^xsd:decimal ]
            )
        ]
    ] .
# Expected: COMPATIBLE (window (10, 90))

# ═══════════════════════════════════════════════════════════════
# DEONTIC CONFLICT TESTS
# ═══════════════════════════════════════════════════════════════

# Test 10: Permission-Prohibition overlap - DEONTIC CONFLICT
ex:policy_rtp_10
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "60"^^xsd:decimal
        ]
    ] ;
    odrl:prohibition [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:relativeTemporalPosition ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "40"^^xsd:decimal
        ]
    ] .
# Expected: DEONTIC CONFLICT
# Permission: [0, 60]
# Prohibition: [40, 100]
# Overlap: [40, 60]
```

---

### 12. Configuration Entry

```python
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
    "value_type": "xsd:decimal",
    "unit": None,  # Implicit percentage
    "operators": {
        "recommended": ["gteq", "lteq", "eq"],
        "valid": ["eq", "neq", "lt", "lteq", "gt", "gteq", "isAnyOf", "isNoneOf", "isAllOf"]
    },
    "inheritance": {
        "broader": "relativePosition"
    },
    "semantics": {
        "0": "stream start",
        "50": "stream midpoint",
        "100": "stream end"
    },
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 13. Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│            relativeTemporalPosition LeftOperand                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DEFINITION                                                     │
│  ══════════                                                     │
│  Position as percentage of temporal (time) duration             │
│  Domain: [0, 100] — BOUNDED                                     │
│                                                                 │
│  Timeline:  0% ────── 33% ────── 48% ────── 100%               │
│             │          │          │          │                  │
│           Start     Position   Position     End                 │
│                      (gteq)     (lteq)                         │
│                         └────────┘                              │
│                         Asset window                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BOUNDED EQUIVALENCE CLASS                                      │
│  ═════════════════════════                                      │
│  ✓ percentage                                                   │
│  ✓ relativePosition                                            │
│  ✓ relativeTemporalPosition  ← THIS                            │
│  ✓ relativeSpatialPosition                                     │
│                                                                 │
│  All share: Domain [0,100], SMT QF-LRA, Real sort              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INHERITANCE                                                    │
│  ═══════════                                                    │
│  skos:broader :relativePosition                                │
│                                                                 │
│  relativePosition (generic)                                     │
│      ├── relativeTemporalPosition (time)                       │
│      └── relativeSpatialPosition (space)                       │
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

### 14. Publication Statement

> **relativeTemporalPosition** specifies a position within a media stream as a percentage of the total temporal duration, with domain $[0, 100]$. The value 0 represents the stream beginning, 100 represents the stream end, and intermediate values represent proportional positions—for example, 33% indicates one-third through the stream. This LeftOperand is a member of the **Bounded Equivalence Class** $\mathcal{L}_{\text{bounded}}$ along with `percentage`, `relativePosition`, and `relativeSpatialPosition`, all sharing the same domain and abstract interpretation. As specified by the ODRL example, constraints like `gteq 33` ∧ `lteq 48` define a valid positioning window within the stream. ODRL-SA detects conflicts via interval intersection: `lteq 25` ∧ `gteq 50` yields CONFLICT since $[0, 25] \cap [50, 100] = \emptyset$. Domain violations (e.g., `gt 100` or `lt 0`) are also detected as conflicts since no value in $[0, 100]$ can satisfy such constraints.

---

This completes the formal specification for `relativeTemporalPosition`. It confirms membership in the **Bounded Equivalence Class** with domain $[0, 100]$, distinguishing it from `relativeSize` which permits unbounded values.