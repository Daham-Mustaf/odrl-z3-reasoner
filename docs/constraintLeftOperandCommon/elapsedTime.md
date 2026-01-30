## elapsedTime - Complete Formal Specification

### 1. ODRL Definition

```turtle
:elapsedTime
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Elapsed Time"@en ;
    skos:definition "A continuous elapsed time period which may be used for 
                     exercising of the action of the Rule. Right operand value 
                     MUST be an xsd:duration as defined by [[xmlschema11-2]]."@en ;
    skos:note "Only the eq, lt, lteq operators SHOULD be used. See also 
               Metered Time. <br />Example: elapsedTime eq P60M indicates 
               a total elapsed time of 60 Minutes."@en ;
    skos:scopeNote "Non-Normative"@en .
```

> ⚠️ **Note:** The ODRL example `P60M` is likely a typo — it means 60 **Months**, not 60 Minutes. Correct form: `PT60M` for 60 minutes.

---

### 2. Quick Reference Card

| Property | Value |
|----------|-------|
| **Semantics** | Continuous time window duration from implicit reference |
| **Domain** | $(0, +\infty)$ seconds |
| **Value Type** | `xsd:duration` (ISO 8601) |
| **Operators (Recommended)** | `eq`, `lt`, `lteq` |
| **Operators (Valid)** | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` |
| **Unit** | Implicit (seconds after parsing) |
| **Category** | $\mathcal{L}_{\text{duration}}$ |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **Reference-Dependent** | Yes (for runtime evaluation) |
| **Static Analysis** | ✅ Partial (interval-based) |
| **External KB** | No |
| **Decidable** | Yes (within scope) |

---

### 3. Semantic Model

#### 3.1 What elapsedTime Measures

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIME AXIS                                   │
│                                                                 │
│    [Reference Point]═══════ elapsed ═══════>[Current Time]      │
│           t₀                                      t             │
│           │                                       │             │
│           │←────────── elapsedTime ──────────────→│             │
│           │         (t - t₀) seconds              │             │
│                                                                 │
│    Constraint: elapsedTime lteq P30D                           │
│    Meaning: (t - t₀) ≤ 30 days                                 │
│    → Action valid within 30 days of reference                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Key Distinction from Related LeftOperands

| LeftOperand | What It Measures | Cumulative? | Reference |
|-------------|------------------|-------------|-----------|
| **elapsedTime** | Wall-clock duration from start | No | Implicit start point |
| **meteredTime** | Accumulated active usage time | Yes | Total usage |
| **dateTime** | Absolute calendar point | N/A | Calendar |
| **timeInterval** | Recurring period length | N/A | Event-based |

**Mental Model:**

- `elapsedTime`: "You have 30 days from activation to use this"
- `meteredTime`: "You have 30 days of actual playback time"
- `dateTime`: "You can use this until December 31, 2025"

---

### 4. Domain Specification

$$\text{dom}(\texttt{elapsedTime}) = \mathbb{R}_{>0} = (0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (exclusive) | Zero duration is meaningless |
| **Upper bound** | ∞ | No theoretical maximum |
| **Zero valid?** | ❌ No | Cannot have zero elapsed time |
| **Internal unit** | Seconds | Normalized from xsd:duration |

---

### 5. Value Type: xsd:duration

#### 5.1 ISO 8601 Format

```
P[n]Y[n]M[n]DT[n]H[n]M[n]S

P     = duration designator (required)
[n]Y  = years
[n]M  = months (BEFORE T)
[n]D  = days
T     = time designator
[n]H  = hours
[n]M  = minutes (AFTER T)
[n]S  = seconds
```

#### 5.2 Examples

| Duration String | Meaning | Seconds |
|-----------------|---------|---------|
| `PT60M` | 60 minutes | 3,600 |
| `PT1H30M` | 1 hour 30 minutes | 5,400 |
| `P1D` | 1 day | 86,400 |
| `P30D` | 30 days | 2,592,000 |
| `P1M` | 1 month | ~2,629,746 (avg) |
| `P1Y` | 1 year | ~31,556,952 (avg) |
| `P60M` | ⚠️ 60 **MONTHS** | ~157,787,280 |

#### 5.3 Normalization to Seconds

| Unit | Seconds | Note |
|------|---------|------|
| Second | 1 | Exact |
| Minute | 60 | Exact |
| Hour | 3,600 | Exact |
| Day | 86,400 | Fixed (ignores DST) |
| Month | 2,629,746 | Average (30.44 days) |
| Year | 31,556,952 | Average (365.25 days) |

> ⚠️ **Warning:** Months and years have variable lengths. ODRL-SA uses average conversions, which may introduce imprecision.

---

### 6. Operator Specification

#### 6.1 Recommended vs Valid

| Operator | Recommended | Valid | Semantics |
|----------|-------------|-------|-----------|
| `eq` | ✅ | ✅ | Exactly this duration |
| `lt` | ✅ | ✅ | Less than (strict upper bound) |
| `lteq` | ✅ | ✅ | At most (upper bound) |
| `gt` | ❌ | ✅ | More than (minimum wait) |
| `gteq` | ❌ | ✅ | At least (minimum duration) |
| `neq` | ❌ | ✅ | Any duration except this |
| `isAnyOf` | ❌ | ❌ | Not meaningful for durations |
| `isNoneOf` | ❌ | ❌ | Not meaningful for durations |
| `isAllOf` | ❌ | ❌ | Not meaningful for durations |

#### 6.2 Operator Semantics

| Operator | Meaning | Typical Use |
|----------|---------|-------------|
| `lteq d` | "Valid for at most d time" | Expiration window |
| `lt d` | "Valid for less than d time" | Strict expiration |
| `eq d` | "Valid at exactly d elapsed" | Specific moment (unusual) |
| `gteq d` | "Valid only after d time" | Cool-down period |
| `gt d` | "Valid only after more than d" | Strict cool-down |
| `neq d` | "Valid except at exactly d" | Exclusion (unusual) |

#### 6.3 Typical Usage Patterns

```turtle
# Pattern 1: Upper Bound (MOST COMMON)
# "License valid for 30 days"
[ odrl:leftOperand odrl:elapsedTime ;
  odrl:operator odrl:lteq ;
  odrl:rightOperand "P30D"^^xsd:duration ]

# Pattern 2: Time Window
# "Available between 1 hour and 24 hours after grant"
[ odrl:and (
    [ odrl:leftOperand odrl:elapsedTime ;
      odrl:operator odrl:gteq ;
      odrl:rightOperand "PT1H"^^xsd:duration ]
    [ odrl:leftOperand odrl:elapsedTime ;
      odrl:operator odrl:lteq ;
      odrl:rightOperand "P1D"^^xsd:duration ]
) ]

# Pattern 3: Minimum Wait (Cool-down)
# "Can only be used after 24 hours"
[ odrl:leftOperand odrl:elapsedTime ;
  odrl:operator odrl:gteq ;
  odrl:rightOperand "P1D"^^xsd:duration ]
```

---

### 7. The Reference Point Problem

#### 7.1 What ODRL Doesn't Specify

ODRL defines elapsed time as "continuous elapsed time period" but **does not specify** the reference point (start time).

| Possible Reference | Meaning |
|-------------------|---------|
| Policy creation time | Clock starts when policy is authored |
| Policy assignment time | Clock starts when policy is assigned to user |
| First access/activation | Clock starts on first use |
| Session start | Clock starts each session |
| Grant time | Clock starts when permission is granted |

#### 7.2 Implications for Analysis

```
┌─────────────────────────────────────────────────────────────┐
│                 ANALYSIS IMPLICATIONS                       │
├─────────────────────────────────────────────────────────────┤
│  Without reference point:                                   │
│  • Can detect duration interval conflicts                   │
│  • Cannot compare with absolute dateTime                    │
│  • Cannot determine runtime validity                        │
├─────────────────────────────────────────────────────────────┤
│  With fixed reference point:                                │
│  • Can transform to absolute time window                    │
│  • Can compare with dateTime constraints                    │
│  • Can detect more conflict types                           │
└─────────────────────────────────────────────────────────────┘
```

---

### 8. Conflict Detection Framework

#### 8.1 Analysis Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 ODRL-SA elapsedTime Analysis                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PHASE 1: Pure Duration Analysis (ALWAYS)                 │  │
│  │  ─────────────────────────────────────────                │  │
│  │  • Input: elapsedTime constraints only                    │  │
│  │  • Method: Interval intersection                          │  │
│  │  • Detects: Duration impossibilities                      │  │
│  │  • Requires: Nothing                                      │  │
│  │  • Sound: ✅  Complete: ✅ (for duration conflicts)        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PHASE 2: Temporal Window Analysis (OPTIONAL)             │  │
│  │  ─────────────────────────────────────────                │  │
│  │  • Input: elapsedTime + dateTime constraints              │  │
│  │  • Method: Transform to absolute time windows             │  │
│  │  • Detects: Cross-constraint temporal conflicts           │  │
│  │  • Requires: Reference time (concrete or symbolic)        │  │
│  │  • Sound: ✅  Complete: Conditional on reference           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PHASE 3: Deontic Conflict Analysis (OPTIONAL)            │  │
│  │  ─────────────────────────────────────────                │  │
│  │  • Input: Permission + Prohibition rules                  │  │
│  │  • Method: Window overlap detection                       │  │
│  │  • Detects: Permission-Prohibition conflicts              │  │
│  │  • Requires: Same-policy rules                            │  │
│  │  • Sound: ✅  Complete: ✅ (within policy)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 8.2 What Each Phase Detects

| Phase | Conflict Type | Example | Detectable? |
|-------|---------------|---------|-------------|
| **1** | Impossible duration range | `lteq 30M` ∧ `gteq 60M` | ✅ CONFLICT |
| **1** | Contradictory equality | `eq 30M` ∧ `eq 60M` | ✅ CONFLICT |
| **1** | Point outside range | `eq 60M` ∧ `lt 60M` | ✅ CONFLICT |
| **1** | Valid window | `gteq 30M` ∧ `lteq 60M` | ✅ COMPATIBLE |
| **2** | elapsedTime vs dateTime | `elapsed lteq 30D` ∧ `dateTime gteq 2025-03-01` | ✅ (with t₀) |
| **3** | Perm-Proh overlap | perm `lteq 60M` ∧ proh `lteq 30M` | ✅ CONFLICT |

---

### 9. Phase 1: Pure Duration Analysis

#### 9.1 Abstract Domain

$$\hat{\mathcal{D}} = \{ I \subseteq (0, +\infty) \mid I \text{ is an interval} \}$$

#### 9.2 Abstraction Function

$$\alpha(\texttt{elapsedTime } op \; d) = \begin{cases}
(0, d) & \text{if } op = \texttt{lt} \\
(0, d] & \text{if } op = \texttt{lteq} \\
(d, +\infty) & \text{if } op = \texttt{gt} \\
[d, +\infty) & \text{if } op = \texttt{gteq} \\
\{d\} & \text{if } op = \texttt{eq} \\
(0, +\infty) \setminus \{d\} & \text{if } op = \texttt{neq}
\end{cases}$$

#### 9.3 Conflict Detection Rule

$$\texttt{CONFLICT}(c_1, c_2, \ldots, c_n) \iff \bigcap_{i=1}^{n} \alpha(c_i) = \emptyset$$

#### 9.4 Visual Examples

```
Duration Axis (seconds):  0 ──────────────────────────────────→ ∞

Example 1: CONFLICT
┌────────────────────────────────────────────────────────────────┐
│  lteq 30M:    (0 ═══════════ 1800]                             │
│  gteq 60M:                              [3600 ═══════════════→ │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘

Example 2: COMPATIBLE
┌────────────────────────────────────────────────────────────────┐
│  gteq 30M:              [1800 ═══════════════════════════════→ │
│  lteq 60M:    (0 ═══════════════════════ 3600]                 │
│  Intersection:          [1800 ═══════════ 3600]                │
│  Result: COMPATIBLE ✅                                          │
└────────────────────────────────────────────────────────────────┘

Example 3: CONFLICT (equality)
┌────────────────────────────────────────────────────────────────┐
│  eq 30M:                {1800}                                 │
│  eq 60M:                              {3600}                   │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘

Example 4: CONFLICT (point outside range)
┌────────────────────────────────────────────────────────────────┐
│  eq 60M:                              {3600}                   │
│  lt 60M:      (0 ══════════════════ 3600)                      │
│  Intersection: ∅ (3600 not in open interval)                   │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘
```

---

### 10. Phase 2: Temporal Window Analysis

#### 10.1 Transformation to Absolute Time

Given reference time $t_0$:

$$\tau(\texttt{elapsedTime } op \; d, t_0) = \{ t \in \mathbb{R} \mid t \geq t_0 \land (t - t_0) \; op \; d \}$$

| Constraint | Absolute Time Window |
|------------|---------------------|
| `elapsedTime lteq d` | $[t_0, t_0 + d]$ |
| `elapsedTime lt d` | $[t_0, t_0 + d)$ |
| `elapsedTime gteq d` | $[t_0 + d, +\infty)$ |
| `elapsedTime gt d` | $(t_0 + d, +\infty)$ |
| `elapsedTime eq d` | $\{t_0 + d\}$ |

#### 10.2 Cross-Constraint Analysis

```
Example: elapsedTime vs dateTime with t₀ = 2025-01-01
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Timeline:  Jan 1 ────────── Jan 31 ────────── Mar 1 ────→     │
│                │                │                │             │
│  Constraint 1: elapsedTime lteq P30D                           │
│  Window:      [Jan 1 ═══════ Jan 31]                           │
│                                                                │
│  Constraint 2: dateTime gteq 2025-03-01                        │
│  Window:                                      [Mar 1 ═══════→  │
│                                                                │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

### 11. Phase 3: Deontic Conflict Analysis

#### 11.1 Permission-Prohibition Overlap

```
Example: Same action, overlapping windows
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Permission: play if elapsedTime lteq PT60M                    │
│  Window:     (0 ═══════════════════════════════ 60]            │
│                                                                │
│  Prohibition: cannot play if elapsedTime lteq PT30M            │
│  Window:     (0 ═══════════════ 30]                            │
│                                                                │
│  Overlap:    (0 ═══════════════ 30]                            │
│                                                                │
│  Result: CONFLICT ❌                                            │
│  Reason: Action is BOTH permitted AND prohibited               │
│          during first 30 minutes                               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### 11.2 Conflict Rule

For same action $a$:

$$\texttt{DEONTIC-CONFLICT}(P, R) \iff \alpha(P) \cap \alpha(R) \neq \emptyset$$

Where:
- $P$ = Permission constraints on $a$
- $R$ = Prohibition constraints on $a$

---

### 12. SMT Encoding

#### 12.1 Duration Parser

```python
import re
from typing import Optional
from dataclasses import dataclass

@dataclass
class ParsedDuration:
    years: float = 0
    months: float = 0
    days: float = 0
    hours: float = 0
    minutes: float = 0
    seconds: float = 0
    
    # Conversion constants
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400
    SECONDS_PER_MONTH = 2629746    # Average: 30.44 days
    SECONDS_PER_YEAR = 31556952    # Average: 365.25 days
    
    def to_seconds(self) -> float:
        return (
            self.years * self.SECONDS_PER_YEAR +
            self.months * self.SECONDS_PER_MONTH +
            self.days * self.SECONDS_PER_DAY +
            self.hours * self.SECONDS_PER_HOUR +
            self.minutes * self.SECONDS_PER_MINUTE +
            self.seconds
        )
    
    def has_variable_components(self) -> bool:
        """Check if duration has month/year (variable length)."""
        return self.years > 0 or self.months > 0


def parse_xsd_duration(duration_str: str) -> Optional[ParsedDuration]:
    """Parse ISO 8601 duration string."""
    pattern = r'^P(?:(\d+(?:\.\d+)?)Y)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
    
    match = re.match(pattern, duration_str)
    if not match:
        return None
    
    g = match.groups()
    return ParsedDuration(
        years=float(g[0] or 0),
        months=float(g[1] or 0),
        days=float(g[2] or 0),
        hours=float(g[3] or 0),
        minutes=float(g[4] or 0),
        seconds=float(g[5] or 0)
    )
```

#### 12.2 SMT Encoder

```python
from z3 import *
from typing import List, Tuple, Optional
from enum import Enum

class ConflictResult(Enum):
    CONFLICT = "CONFLICT"
    COMPATIBLE = "COMPATIBLE"
    UNKNOWN = "UNKNOWN"

class ElapsedTimeEncoder:
    """SMT encoder for elapsedTime constraints."""
    
    RECOMMENDED_OPS = {"eq", "lt", "lteq"}
    VALID_OPS = {"eq", "neq", "lt", "lteq", "gt", "gteq"}
    
    def encode(
        self, 
        operator: str, 
        duration_seconds: float,
        var: ArithRef
    ) -> BoolRef:
        """Encode single constraint as SMT formula."""
        
        # Domain: strictly positive
        domain = var > 0
        
        if operator == "eq":
            return And(domain, var == duration_seconds)
        elif operator == "neq":
            return And(domain, var != duration_seconds)
        elif operator == "lt":
            return And(domain, var < duration_seconds)
        elif operator == "lteq":
            return And(domain, var <= duration_seconds)
        elif operator == "gt":
            return And(domain, var > duration_seconds)
        elif operator == "gteq":
            return And(domain, var >= duration_seconds)
        else:
            raise ValueError(f"Invalid operator: {operator}")
    
    def detect_conflict(
        self,
        constraints: List[Tuple[str, float]]  # [(operator, seconds), ...]
    ) -> Tuple[ConflictResult, Optional[float]]:
        """
        Detect conflicts among elapsedTime constraints.
        Returns (result, witness_seconds_if_compatible).
        """
        solver = Solver()
        var = Real('elapsedTime')
        
        for op, seconds in constraints:
            solver.add(self.encode(op, seconds, var))
        
        if solver.check() == sat:
            model = solver.model()
            witness = float(model[var].as_fraction())
            return (ConflictResult.COMPATIBLE, witness)
        else:
            return (ConflictResult.CONFLICT, None)
```

---

### 13. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | PARTIAL |
| **Category** | $\mathcal{L}_{\text{duration}}$ |
| **Z3 Sort** | Real |
| **Domain** | $(0, +\infty)$ seconds |
| **SMT Theory** | QF_LRA |
| **External KB** | No |
| **Reference-dependent** | Yes (for evaluation) |
| **Static Analysis** | ✅ Phase 1 always; Phase 2-3 conditional |
| **Decidable** | Yes (interval arithmetic) |
| **Complete** | Phase 1: ✅; Phase 2-3: Conditional |

---

### 14. Configuration Entry

```python
"elapsedTime": {
    "class": "PARTIAL",
    "category": "L_duration",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": False,  # Strictly positive
        "inclusive_max": None
    },
    "value_type": "xsd:duration",
    "operators": {
        "recommended": ["eq", "lt", "lteq"],
        "valid": ["eq", "neq", "lt", "lteq", "gt", "gteq"]
    },
    "reference_dependent": True,
    "analysis_phases": {
        "pure_duration": {
            "always": True,
            "requires": []
        },
        "temporal_window": {
            "always": False,
            "requires": ["reference_time"]
        },
        "deontic": {
            "always": False,
            "requires": ["multi_rule_policy"]
        }
    },
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 15. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .

# ═══════════════════════════════════════════════════════════════
# PHASE 1: Pure Duration Tests
# ═══════════════════════════════════════════════════════════════

# Test 1.1: Impossible range - CONFLICT
ex:policy_elapsed_impossible
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "PT30M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: CONFLICT ((0,1800] ∩ [3600,∞) = ∅)

# Test 1.2: Valid window - COMPATIBLE
ex:policy_elapsed_window
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "PT30M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: COMPATIBLE (window: [1800, 3600] seconds)

# Test 1.3: Contradictory equality - CONFLICT
ex:policy_elapsed_eq_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "PT30M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: CONFLICT ({1800} ∩ {3600} = ∅)

# Test 1.4: Point outside range - CONFLICT
ex:policy_elapsed_point_outside
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:lt ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: CONFLICT ({3600} ∩ (0,3600) = ∅)

# Test 1.5: Upper bound only - COMPATIBLE
ex:policy_elapsed_upper_only
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "P30D"^^xsd:duration
        ]
    ] .
# Expected: COMPATIBLE (window: (0, 2592000] seconds)

# ═══════════════════════════════════════════════════════════════
# PHASE 3: Deontic Conflict Tests
# ═══════════════════════════════════════════════════════════════

# Test 3.1: Permission-Prohibition overlap - CONFLICT
ex:policy_deontic_overlap
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "PT60M"^^xsd:duration
        ]
    ] ;
    odrl:prohibition [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "PT30M"^^xsd:duration
        ]
    ] .
# Expected: DEONTIC CONFLICT
# Permission window: (0, 3600] 
# Prohibition window: (0, 1800]
# Overlap: (0, 1800] - both permitted AND prohibited!

# Test 3.2: Non-overlapping deontic - COMPATIBLE
ex:policy_deontic_nonoverlap
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "PT60M"^^xsd:duration
        ]
    ] ;
    odrl:prohibition [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lt ;
            odrl:rightOperand "PT60M"^^xsd:duration
        ]
    ] .
# Expected: COMPATIBLE
# Permission window: [3600, ∞)
# Prohibition window: (0, 3600)
# No overlap - consistent!
```

---

### 16. Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    elapsedTime LeftOperand                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DEFINITION                                                     │
│  ══════════                                                     │
│  Continuous elapsed time period for exercising action           │
│  Value: xsd:duration (ISO 8601)                                 │
│  Domain: (0, ∞) seconds                                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OPERATORS                                                      │
│  ══════════                                                     │
│  Recommended: eq, lt, lteq                                      │
│  Valid: eq, neq, lt, lteq, gt, gteq                            │
│  Invalid: isAnyOf, isNoneOf, isAllOf                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ANALYSIS PHASES                                                │
│  ═══════════════                                                │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │  PHASE 1    │   │  PHASE 2    │   │  PHASE 3    │           │
│  │  Pure       │   │  Temporal   │   │  Deontic    │           │
│  │  Duration   │──▶│  Window     │──▶│  Conflict   │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│        │                 │                 │                    │
│    Always            Optional          Optional                 │
│        │                 │                 │                    │
│  Requires:         Requires:         Requires:                  │
│  Nothing           Reference t₀      Multi-rule                 │
│        │                 │                 │                    │
│  Detects:          Detects:          Detects:                   │
│  • Interval        • elapsed ↔       • Perm-Proh                │
│    conflicts         dateTime          overlap                  │
│                      conflicts                                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SMT ENCODING                                                   │
│  ════════════                                                   │
│  Theory: QF_LRA                                                 │
│  Sort: Real                                                     │
│  Variable: elapsedTime ∈ (0, ∞)                                │
│  Constraint: domain ∧ operator_encoding                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CATEGORY: L_duration                                           │
│  DECIDABLE: Yes                                                 │
│  EXTERNAL KB: No                                                │
│  REFERENCE-DEPENDENT: Yes (for runtime)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 17. Publication Statement

> **elapsedTime** specifies a continuous time window duration during which an action may be exercised, with values expressed as `xsd:duration` (ISO 8601). The semantics represent wall-clock time elapsed from an implicit reference point—unlike `meteredTime` which accumulates only active usage. ODRL-SA implements three-phase analysis: (1) **Pure Duration Analysis** detects interval impossibilities without assumptions, such as `lteq PT30M` ∧ `gteq PT60M` yielding CONFLICT since $(0, 1800] \cap [3600, \infty) = \emptyset$; (2) **Temporal Window Analysis** transforms elapsed constraints to absolute time windows given a reference point, enabling cross-constraint detection with `dateTime`; (3) **Deontic Conflict Analysis** identifies permission-prohibition overlaps where the same action is both permitted and prohibited during the same time window. The ODRL specification recommends only `eq`, `lt`, and `lteq` operators, reflecting typical upper-bound semantics ("valid for at most 30 days"). Durations are normalized to seconds using fixed conversions (day = 86400s) with warnings for variable-length components (months, years use averages). Static conflict detection is sound within each analysis phase; completeness depends on reference time availability.

---

### 18. Related LeftOperands

| LeftOperand | Relationship | Key Difference |
|-------------|--------------|----------------|
| **meteredTime** | Similar domain | Cumulative vs continuous |
| **dateTime** | Complementary | Absolute vs relative |
| **timeInterval** | Different scope | Recurring vs one-time |
| **delayPeriod** | Similar concept | Waiting period before action |

