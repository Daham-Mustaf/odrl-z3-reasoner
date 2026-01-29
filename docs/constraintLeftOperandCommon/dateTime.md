## `dateTime` — Final Formal Specification

### 1. ODRL Definition (Source)

```turtle
:dateTime
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Datetime"@en ;
    skos:definition "The date (and optional time and timezone) of exercising 
                     the action of the Rule. Right operand value MUST be an 
                     xsd:date or xsd:dateTime as defined by [[xmlschema11-2]]."@en ;
    skos:note "The use of Timezone information is strongly recommended. 
               The Rule may be exercised before (with operator lt/lteq) or 
               after (with operator gt/gteq) the date(time) defined by the 
               Right operand.
               Example: dateTime gteq 2017-12-31T06:00Z means the Rule can 
               only be exercised after (and including) 6:00AM on the 31st 
               December 2017 UTC time."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 2. Formal Definition

```
LeftOperand:   odrl:dateTime
Category:      𝓛_datetime (subset of 𝓛_xsd)
XSD Type:      xsd:dateTime | xsd:date
Domain:        ℤ (Unix timestamp in seconds)
Semantics:     Absolute point in time for exercising action
Unit:          ❌ Not applicable
Scope:         ❌ None
Reference:     ❌ None (absolute time)
ODRL Status:   Non-Normative
```

---

### 3. Domain Specification

$$\mathcal{D}_{\text{dateTime}} = \mathbb{Z}$$

| Property | Value | Rationale |
|----------|-------|-----------|
| Lower bound | -∞ | Past dates valid (historical constraints) |
| Upper bound | +∞ | Future dates valid (expiration constraints) |
| Type | Integer | Unix timestamp (seconds since 1970-01-01T00:00:00Z) |

**Why ℤ (unbounded):**
- Past dates: "License valid from 2020-01-01"
- Future dates: "License expires 2030-12-31"
- No semantic reason to bound

---

### 4. Valid Operators (9/12)

| Operator | Valid | SMT Encoding | ODRL Example |
|----------|:-----:|--------------|--------------|
| `eq` | ✅ | `(= dateTime v)` | Exact moment |
| `neq` | ✅ | `(not (= dateTime v))` | Not at moment |
| `lt` | ✅ | `(< dateTime v)` | Before date |
| `lteq` | ✅ | `(<= dateTime v)` | On or before |
| `gt` | ✅ | `(> dateTime v)` | After date |
| `gteq` | ✅ | `(>= dateTime v)` | On or after |
| `isAnyOf` | ✅ | `(or (= dateTime v₁) ...)` | Specific dates |
| `isNoneOf` | ✅ | `(and (not (= dateTime v₁)) ...)` | Exclude dates |
| `isAllOf` | ⚠️ | Degenerates to `eq` | — |
| `isA` | ❌ | — | No taxonomy |
| `hasPart` | ❌ | — | No mereology |
| `isPartOf` | ❌ | — | No mereology |

**ODRL explicitly recommends:** `lt`, `lteq`, `gt`, `gteq` for temporal constraints.

---

### 5. DateTime Normalization

**Input:** `xsd:dateTime` or `xsd:date` string
**Output:** Integer (Unix timestamp in seconds)

| Input Type | Example | Normalized |
|------------|---------|------------|
| `xsd:dateTime` with TZ | `2017-12-31T06:00:00Z` | 1514700000 |
| `xsd:dateTime` with offset | `2017-12-31T07:00:00+01:00` | 1514700000 |
| `xsd:dateTime` no TZ | `2017-12-31T06:00:00` | ⚠️ Assume UTC |
| `xsd:date` | `2017-12-31` | 1514678400 (00:00:00 UTC) |

**Timezone handling:**
- With timezone: Use as specified
- Without timezone: **Assume UTC** (ODRL recommends TZ usage)
- `xsd:date` only: Normalize to `T00:00:00Z`

```python
from datetime import datetime, timezone

def to_timestamp(xsd_datetime: str) -> int:
    """
    Normalize xsd:dateTime or xsd:date to Unix timestamp.
    Assumes UTC if no timezone specified.
    """
    # Try xsd:dateTime formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",           # 2017-12-31T06:00:00Z
        "%Y-%m-%dT%H:%M:%S%z",          # 2017-12-31T06:00:00+01:00
        "%Y-%m-%dT%H:%M:%S",            # 2017-12-31T06:00:00 (no TZ)
        "%Y-%m-%d",                      # 2017-12-31 (date only)
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(xsd_datetime, fmt)
            # If no timezone, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    
    raise ValueError(f"Cannot parse datetime: {xsd_datetime}")
```

---

### 6. Abstract Domain

$$\mathcal{A}_{\text{dateTime}} = \mathbb{I}_{\mathbb{Z}} = \{[a,b] \mid a, b \in \mathbb{Z} \cup \{-\infty, +\infty\}, a \leq b\} \cup \{\bot\}$$

| Operator | α(constraint) |
|----------|---------------|
| `eq v` | `[v, v]` |
| `neq v` | `⊤` (over-approximation) |
| `lt v` | `(-∞, v-1]` |
| `lteq v` | `(-∞, v]` |
| `gt v` | `[v+1, +∞)` |
| `gteq v` | `[v, +∞)` |
| `isAnyOf V` | `⊔{[v,v] | v ∈ V}` |
| `isNoneOf V` | `⊤` (over-approximation) |

---

### 7. SMT Encoding

```smt
; Declaration
(declare-const dateTime Int)

; No domain bounds (can be past or future)

; Example 1: dateTime gteq 2017-12-31T06:00Z
; Normalized: 1514700000
(assert (>= dateTime 1514700000))

; Example 2: dateTime lt 2025-01-01T00:00Z
; Normalized: 1735689600
(assert (< dateTime 1735689600))

; Example 3: Valid date range (2020 to 2025)
(assert (and 
    (>= dateTime 1577836800)   ; 2020-01-01T00:00Z
    (<= dateTime 1735689599))) ; 2024-12-31T23:59:59Z
```

**Z3 Sort:** `Int`
- Timestamps are discrete (seconds)
- Integer arithmetic is decidable
- No precision loss

---

### 8. Conflict Patterns

| Pattern | c₁ | c₂ | Result |
|---------|----|----|--------|
| Before vs after | `lteq 2024-12-31` | `gteq 2025-02-01` | `CONFLICT` |
| Overlapping range | `lteq 2025-06-30` | `gteq 2025-01-01` | `POSSIBLY-COMPATIBLE` |
| Exact vs range | `eq 2025-03-15` | `gteq 2025-01-01` | `POSSIBLY-COMPATIBLE` |
| Exact vs exact | `eq 2025-01-01` | `eq 2025-12-31` | `CONFLICT` |
| Adjacent boundary | `lt 2025-01-01` | `gteq 2025-01-01` | `CONFLICT` |
| Touching boundary | `lteq 2025-01-01` | `gteq 2025-01-01` | `POSSIBLY-COMPATIBLE` |

---

### 9. ODRL Turtle Examples

```turtle
# Example 1: Valid until end of 2025
ex:c1 a odrl:Constraint ;
    odrl:leftOperand odrl:dateTime ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "2025-12-31T23:59:59Z"^^xsd:dateTime .

# Example 2: Valid from 2025 onwards
ex:c2 a odrl:Constraint ;
    odrl:leftOperand odrl:dateTime ;
    odrl:operator odrl:gteq ;
    odrl:rightOperand "2025-01-01T00:00:00Z"^^xsd:dateTime .

# Example 3: Date only (no time component)
ex:c3 a odrl:Constraint ;
    odrl:leftOperand odrl:dateTime ;
    odrl:operator odrl:gteq ;
    odrl:rightOperand "2025-01-01"^^xsd:date .

# Example 4: Valid date range (composition)
ex:c4 a odrl:LogicalConstraint ;
    odrl:and (ex:c1 ex:c2) .  # Between 2025-01-01 and 2025-12-31

# Example 5: Specific blackout dates
ex:c5 a odrl:Constraint ;
    odrl:leftOperand odrl:dateTime ;
    odrl:operator odrl:isNoneOf ;
    odrl:rightOperand (
        "2025-12-25T00:00:00Z"^^xsd:dateTime
        "2025-12-26T00:00:00Z"^^xsd:dateTime
    ) .
```

---

### 10. Configuration 

```yaml
dateTime:
  class: FULL
  category: L_datetime
  z3_sort: Int
  domain:
    min: null    # Unbounded (past dates valid)
    max: null    # Unbounded (future dates valid)
  normalizer: to_timestamp
  operators: [eq, neq, lt, lteq, gt, gteq, isAnyOf, isNoneOf]
  restricted_operators: [isAllOf]  # Degenerates to eq
  invalid_operators: [isA, hasPart, isPartOf]
  accepts: [xsd:dateTime, xsd:date]
  timezone_default: UTC
  note: "DateTime values normalized to Unix timestamp (seconds)"
  description: "Absolute point in time for exercising action"
```

---

### 11. Comparison with Related Temporal LeftOperands

| LeftOperand | Semantics | Domain | Type | Reference Point |
|-------------|-----------|--------|------|:---------------:|
| `dateTime` | Absolute instant | ℤ | Timestamp | ❌ None (absolute) |
| `timeInterval` | Recurrence period | ℤ>0 | Duration | ❌ None |
| `elapsedTime` | Continuous elapsed | ℤ≥0 | Duration | ⚠️ Policy activation |
| `delayPeriod` | Delay before action | ℤ≥0 | Duration | ⚠️ Triggering event |
| `absoluteTemporalPosition` | Position in media | ℝ≥0 | Offset | ❌ Media start |

---

### 12. Paper Statement

> The `odrl:dateTime` LeftOperand represents an absolute point in time for exercising an action. ODRL-SA normalizes `xsd:dateTime` and `xsd:date` values to Unix timestamps (integers), enabling efficient SMT reasoning via QF-LIA. The domain is unbounded (ℤ), permitting both past and future dates. All comparison operators are valid, with ODRL explicitly recommending `lt`/`lteq` for "before" constraints and `gt`/`gteq` for "after" constraints. Timezone information is preserved during normalization; values without timezone default to UTC per ODRL recommendation.

---

### 13. Edge Cases

| Case | Handling |
|------|----------|
| No timezone | Assume UTC (with warning) |
| Date only (`xsd:date`) | Normalize to `T00:00:00Z` |
| Leap seconds | Ignored (Unix timestamp convention) |
| Pre-1970 dates | Negative timestamps (valid) |
| Far future dates | Large positive integers (valid) |

