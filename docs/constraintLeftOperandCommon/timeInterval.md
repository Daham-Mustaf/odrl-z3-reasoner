## `timeInterval` — Final Formal Specification

### 1. ODRL Definition (Source)

```turtle
:timeInterval
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Recurring Time Interval"@en ;
    skos:definition "A recurring period of time before the next execution 
                     of the action of the Rule. Right operand value MUST be 
                     an xsd:duration as defined by [[xmlschema11-2]]."@en ;
    skos:note "Only the eq operator SHOULD be used. 
               Example: timeInterval eq P7D indicates a recurring 7 day period." ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 2. Formal Definition

```
LeftOperand:   odrl:timeInterval
Category:      𝓛_duration (subset of 𝓛_xsd)
XSD Type:      xsd:duration
Domain:        ℤ>0 = {1, 2, 3, ...} (seconds)
Semantics:     Recurring period between action executions
Unit:          ❌ Implicit (seconds after normalization)
Scope:         ❌ None
ODRL Status:   Non-Normative
```

---

### 3. Domain Specification

$$\mathcal{D}_{\text{timeInterval}} = \{n \in \mathbb{Z} \mid n \geq 1\}$$

| Property | Value | Rationale |
|----------|-------|-----------|
| Lower bound | 1 (exclusive of 0) | 0 = infinite frequency (invalid) |
| Upper bound | +∞ | No maximum recurrence period |
| Type | Integer | Durations are discrete (seconds) |

**Why min = 1, not 0:**
- `timeInterval eq P0S` (0 seconds) means "infinite frequency"
- This violates ODRL's intent of "time between executions"
- Excluding 0 ensures no degenerate models

---

### 4. Valid Operators (1/12) ⚠️ RESTRICTED

| Operator | Valid | Reason |
|----------|:-----:|--------|
| `eq` |  | ODRL: "Only the eq operator SHOULD be used" |
| `neq` | ❌ | Not meaningful for recurrence specification |
| `lt` | ❌ | Recurrence periods are not orderable constraints |
| `lteq` | ❌ | Same |
| `gt` | ❌ | Same |
| `gteq` | ❌ | Same |
| `isAnyOf` | ❌ | Not meaningful |
| `isNoneOf` | ❌ | Not meaningful |
| `isAllOf` | ❌ | Not meaningful |
| `isA` | ❌ | No taxonomy |
| `hasPart` | ❌ | No mereology |
| `isPartOf` | ❌ | No mereology |

**Design rationale:** This restriction is a *feature*, not a limitation. Expressiveness is achieved through:
- Logical operators (AND, OR, XONE)
- Rule composition
- Multiple constraints

---

### 5. Duration Normalization

**Input:** `xsd:duration` string
**Output:** Integer (seconds)

| XSD Duration | Normalized (seconds) |
|--------------|---------------------:|
| `PT1S` | 1 |
| `PT1M` | 60 |
| `PT1H` | 3,600 |
| `P1D` | 86,400 |
| `P7D` | 604,800 |
| `P1W` | 604,800 |

**Rejected durations (non-fixed length):**
- `P1M` (month) — 28-31 days, ambiguous
- `P1Y` (year) — 365-366 days, ambiguous

```python
def to_duration(xsd_duration: str) -> int:
    """
    Normalize xsd:duration to seconds.
    Rejects variable-length durations (months, years).
    """
    # Parse ISO 8601 duration
    parsed = parse_duration(xsd_duration)
    
    # Reject variable-length components
    if parsed.months != 0 or parsed.years != 0:
        raise ValueError(f"Variable-length duration not supported: {xsd_duration}")
    
    # Convert to seconds
    seconds = (
        parsed.days * 86400 +
        parsed.hours * 3600 +
        parsed.minutes * 60 +
        parsed.seconds
    )
    
    # Validate positive
    if seconds < 1:
        raise ValueError(f"Duration must be positive: {xsd_duration}")
    
    return seconds
```

---

### 6. Abstract Domain

```
𝒜_timeInterval = {[n, n] | n ∈ ℤ>0} ∪ {⊥}
```

Since only `eq` is valid, the abstract domain collapses to **point intervals**.

| Operator | α(constraint) |
|----------|---------------|
| `eq v` | `[v, v]` |

---

### 7. SMT Encoding

```smt
; Declaration
(declare-const timeInterval Int)

; Domain constraint: positive integer
(assert (>= timeInterval 1))

; Example: timeInterval eq P7D (604800 seconds)
(assert (= timeInterval 604800))
```

**Z3 Sort:** `Int` (not `Real`)
- Durations are discrete
- Equality on integers is decidable, fast, precise
- No rounding issues

---

### 8. Conflict Patterns

| Pattern | c₁ | c₂ | Result |
|---------|----|----|--------|
| Same interval | `eq P1D` | `eq P1D` | `POSSIBLY-COMPATIBLE` |
| Different intervals | `eq P1D` | `eq P7D` | `CONFLICT` |
| Multiple via OR | `eq P1D OR eq P7D` | `eq P7D` | `POSSIBLY-COMPATIBLE` |

---

### 9. ODRL Turtle Examples

```turtle
# Example 1: Weekly recurring interval
ex:c1 a odrl:Constraint ;
    odrl:leftOperand odrl:timeInterval ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "P7D"^^xsd:duration .

# Example 2: Daily recurring interval
ex:c2 a odrl:Constraint ;
    odrl:leftOperand odrl:timeInterval ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "P1D"^^xsd:duration .

# Example 3: Hourly interval
ex:c3 a odrl:Constraint ;
    odrl:leftOperand odrl:timeInterval ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "PT1H"^^xsd:duration .

# Example 4: Choice of intervals (via LogicalConstraint)
ex:c4 a odrl:LogicalConstraint ;
    odrl:or (ex:c1 ex:c2) .  # Weekly OR daily
```

---

### 10. Configuration

```yaml
timeInterval:
  class: FULL
  category: L_duration
  z3_sort: Int
  domain:
    min: 1        # Not 0 — excludes degenerate "infinite frequency"
    max: null
  normalizer: to_duration
  operators: [eq]
  invalid_operators: [neq, lt, lteq, gt, gteq, isA, hasPart, isPartOf, isAnyOf, isNoneOf, isAllOf]
  rejects: [P1M, P1Y]  # Variable-length durations
  note: "Only equality operator is meaningful for recurring intervals"
  description: "Recurring time interval between executions (seconds)"
```

---

### 11. Summary Table

| Dimension | Value |
|-----------|-------|
| **LeftOperand** | `odrl:timeInterval` |
| **Category** | 𝓛_duration ⊂ 𝓛_xsd |
| **XSD Type** | xsd:duration |
| **Domain** | ℤ>0 (positive integers) |
| **Valid Operators** | 1/12 (eq only) |
| **Abstract Domain** | Point intervals |
| **SMT Theory** | QF-LIA |
| **Z3 Sort** | Int |
| **Decidable** |  Yes |
| **Unit** | Implicit (seconds) |
| **Normalization** | ISO 8601 → seconds |
| **Rejected** | P1M, P1Y (variable-length) |

---

### 12. Paper Statement

> The `odrl:timeInterval` LeftOperand represents a recurring period between action executions. Following ODRL Core's recommendation ("Only the eq operator SHOULD be used"), ODRL-SA restricts `timeInterval` to equality comparisons only. The domain is ℤ>0 (positive integers in seconds), excluding zero to prevent degenerate "infinite frequency" interpretations. Variable-length durations (months, years) are rejected during normalization. This restriction is a design feature: expressiveness is achieved through logical composition (AND, OR, XONE) rather than comparison operators.

---

### 13. Comparison with Related Duration LeftOperands

| LeftOperand | Semantics | Domain | Operators | Reference Point |
|-------------|-----------|--------|:---------:|:---------------:|
| `timeInterval` | Recurrence period | ℤ>0 | eq only | ❌ None |
| `elapsedTime` | Continuous elapsed | ℤ≥0 | eq, lt, lteq | ⚠️ Policy activation |
| `delayPeriod` | Delay before action | ℤ≥0 | eq, gt, gteq | ⚠️ Triggering event |
| `meteredTime` | Accumulated usage | ℤ≥0 | eq, lt, lteq | ❌ Runtime only |

