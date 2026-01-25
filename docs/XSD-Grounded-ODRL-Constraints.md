# ODRL Constraint Semantics Reference

## XSD-Grounded Constraints for Static Policy Analysis

---

### Self-Contained

| Subcategory | Count | LeftOperands |
|-------------|-------|--------------|
| Numeric | 4 | `count`, `percentage`, `payAmount`, `resolution` |
| Temporal (Absolute) | 2 | `dateTime`, `timeInterval` |
| Positional (Absolute) | 4 | `absolutePosition`, `absoluteSize`, `absoluteTemporalPosition`, `absoluteSpatialPosition` |
| Positional (Relative) | 4 | `relativePosition`, `relativeSize`, `relativeTemporalPosition`, `relativeSpatialPosition` |
| **Total Self-Contained** | **14** | — |

### Reference Point Required

| Count | LeftOperands | Notes |
|-------|--------------|-------|
| 3 | `elapsedTime`, `delayPeriod`, `meteredTime` | `meteredTime` is runtime-only |

### Semantic Grounding Required

| Count | LeftOperands |
|-------|--------------|
| 14 | `language`, `spatial`, `spatialCoordinates`, `event`, `media`, `industry`, `purpose`, `recipient`, `product`, `deliveryChannel`, `systemDevice`, `fileFormat`, `virtualLocation`, `version` |

---

## Reference Tables for XSD-Grounded ODRL Constraints

---

### Table 1: Numeric Constraints

| LeftOperand | XSD Type | Domain | Valid Operators | Unit Required | Unit Handling |
|-------------|----------|--------|-----------------|---------------|---------------|
| `count` | `xsd:integer` | ℕ (≥ 0) | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | No | Uses `unitOfCount` for semantics |
| `percentage` | `xsd:decimal` | [0, 100] | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | No | Percentage of reference quantity |
| `payAmount` | `xsd:decimal` | ℝ (≥ 0) | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | **Yes** | Same unit required, no conversion |
| `resolution` | `xsd:decimal` | ℝ (> 0) | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | **Yes** | Same unit required (DPI, PPI) |

**Unit Policy Decision**: 
> **No unit conversion**. Constraints with different units are treated as **INCOMPARABLE**. Engine reports warning and cannot determine conflict/refinement relationship.

---

### Table 2: Temporal Constraints

| LeftOperand | XSD Type | Domain | Valid Operators | Reference Point | Interpretation |
|-------------|----------|--------|-----------------|-----------------|----------------|
| `dateTime` | `xsd:dateTime` | Instant | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Absolute | Point in time (UTC normalized) |
| `timeInterval` | `xsd:duration` | Duration | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | N/A | Length of time window |
| `elapsedTime` | `xsd:duration` | Duration | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | **Policy activation** | Time since policy became active |
| `meteredTime` | `xsd:duration` | Duration | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | **Cumulative use** | Total active usage time |
| `delayPeriod` | `xsd:duration` | Duration | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | **Triggering event** | Wait time before action allowed |

**Reference Point Decision**:
> For **static analysis**, we use **policy activation time** (deployment/issuance) as default reference point `t₀`. This is the most practical choice because:
> - Known at analysis time
> - Consistent across evaluations  
> - Matches real-world policy lifecycle

---

### Table 3: Positional Constraints (Media Fragments)

| LeftOperand | XSD Type | Domain | Valid Operators | Unit | Interpretation |
|-------------|----------|--------|-----------------|------|----------------|
| `absolutePosition` | `xsd:decimal` | ℝ (≥ 0) | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Seconds/bytes | Absolute offset in media |
| `absoluteSpatialPosition` | Complex | Coordinates | `eq`, `neq` | Pixels | x,y position in visual media |
| `absoluteTemporalPosition` | `xsd:decimal` | ℝ (≥ 0) | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Seconds | Time offset in media |
| `absoluteSize` | `xsd:decimal` | ℝ (> 0) | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Bytes/pixels | Absolute dimension |
| `relativePosition` | `xsd:decimal` | [0, 100] | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Percentage | Relative offset (0-100%) |
| `relativeSpatialPosition` | `xsd:decimal` | [0, 100] | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Percentage | Relative x,y (0-100%) |
| `relativeTemporalPosition` | `xsd:decimal` | [0, 100] | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Percentage | Relative time (0-100%) |
| `relativeSize` | `xsd:decimal` | [0, 100] | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Percentage | Relative dimension (0-100%) |

---

### Table 4: Operator Semantics

| Operator | Symbol | Semantics | Valid For | SMT Encoding |
|----------|--------|-----------|-----------|--------------|
| `eq` | = | Equality | All types | `(= x y)` |
| `neq` | ≠ | Inequality | All types | `(not (= x y))` |
| `lt` | < | Less than | Ordered types | `(< x y)` |
| `lteq` | ≤ | Less or equal | Ordered types | `(<= x y)` |
| `gt` | > | Greater than | Ordered types | `(> x y)` |
| `gteq` | ≥ | Greater or equal | Ordered types | `(>= x y)` |

**Not valid for XSD-grounded constraints** (require semantic grounding):
- `isA`, `isAllOf`, `isAnyOf`, `isNoneOf`, `isPartOf`, `hasPart`

---

### Table 5: Logical Operators for Constraint Composition

| Operator | Semantics | SMT Encoding | Notes |
|----------|-----------|--------------|-------|
| `and` | ⋀ᵢ cᵢ | `(and c1 c2 ... cn)` | All must hold |
| `or` | ⋁ᵢ cᵢ | `(or c1 c2 ... cn)` | At least one holds |
| `xone` | Σᵢ⟦cᵢ⟧ = 1 | `(= 1 (+ (ite c1 1 0) ...))` | Exactly one holds |
| `andSequence` | Ordered ⋀ | See below | Sequential satisfaction |

**andSequence Encoding**:
```smt
; andSequence(c1, c2, c3)
(declare-const t1 Int)
(declare-const t2 Int)
(declare-const t3 Int)
(assert (< t1 t2))
(assert (< t2 t3))
(assert (holds_at c1 t1))
(assert (holds_at c2 t2))
(assert (holds_at c3 t3))
```

---

### Table 6: Domain Bounds and Validation Rules

| LeftOperand | Lower Bound | Upper Bound | Validation Rule |
|-------------|-------------|-------------|-----------------|
| `count` | 0 | ∞ | Must be non-negative integer |
| `percentage` | 0 | 100 | Must be in [0, 100] |
| `payAmount` | 0 | ∞ | Must be non-negative |
| `resolution` | 0 | ∞ | Must be positive |
| `relativePosition` | 0 | 100 | Must be in [0, 100] |
| `relativeSpatialPosition` | 0 | 100 | Must be in [0, 100] |
| `relativeTemporalPosition` | 0 | 100 | Must be in [0, 100] |
| `relativeSize` | 0 | 100 | Must be in [0, 100] |
| `absolutePosition` | 0 | ∞ | Must be non-negative |
| `absoluteSize` | 0 | ∞ | Must be positive |
| `dateTime` | -∞ | ∞ | Valid ISO 8601 datetime |
| `elapsedTime` | 0 | ∞ | Non-negative duration |
| `delayPeriod` | 0 | ∞ | Non-negative duration |
| `meteredTime` | 0 | ∞ | Non-negative duration |
| `timeInterval` | 0 | ∞ | Non-negative duration |

---

### Table 7: unitOfCount Values (ODRL Vocabulary)

| Value | URI | Interpretation |
|-------|-----|----------------|
| Per user | `odrl:perUser` | Count per unique user |
| Per device | `odrl:perDevice` | Count per unique device |
| Per organization | `odrl:perOrganization` | Count per organization |
| Per session | `odrl:perSession` | Count per session |
| Total | (default) | Total cumulative count |

---

### Table 8: Common Unit URIs

| Domain | Unit | Common URIs |
|--------|------|-------------|
| Currency | Euro | `http://dbpedia.org/resource/Euro` |
| Currency | US Dollar | `http://dbpedia.org/resource/US_Dollar` |
| Currency | British Pound | `http://dbpedia.org/resource/Pound_sterling` |
| Resolution | DPI | `http://dbpedia.org/resource/Dots_per_inch` |
| Resolution | PPI | `http://dbpedia.org/resource/Pixels_per_inch` |
| Size | Byte | `http://dbpedia.org/resource/Byte` |
| Size | Kilobyte | `http://dbpedia.org/resource/Kilobyte` |
| Size | Megabyte | `http://dbpedia.org/resource/Megabyte` |
| Time | Second | `http://dbpedia.org/resource/Second` |
| Time | Minute | `http://dbpedia.org/resource/Minute` |
| Time | Hour | `http://dbpedia.org/resource/Hour` |

---

### Table 9: Duration Conversion (for internal normalization)

| XSD Duration | Seconds |
|--------------|---------|
| `PT1S` | 1 |
| `PT1M` | 60 |
| `PT1H` | 3600 |
| `P1D` | 86400 |
| `P1W` | 604800 |
| `P1M` | 2592000 (30 days approx) |
| `P1Y` | 31536000 (365 days approx) |

**Note**: Month and year are approximations. For precise calculation, use calendar-aware arithmetic.

---

### Table 10: Conflict Detection Patterns for Numeric/Temporal

| Pattern | Policy 1 | Policy 2 | Conflict Condition |
|---------|----------|----------|-------------------|
| Range overlap | `x gteq a, x lteq b` | `x gteq c, x lteq d` | `[a,b] ∩ [c,d] ≠ ∅` |
| Point in range | `x eq v` | `x gteq a, x lteq b` | `v ∈ [a,b]` |
| Impossible range | `x gteq a, x lteq b` | — | `a > b` (internal conflict) |
| Contradictory | `x eq v₁` | `x eq v₂` | `v₁ ≠ v₂` |
| Subsumption | `x lteq a` | `x lteq b` | `a ≤ b` (P1 ⊆ P2) |

---

### Table 11: Reference Point Summary

| LeftOperand | Reference Point | Rationale |
|-------------|-----------------|-----------|
| `dateTime` | **Absolute** (no reference needed) | ISO 8601 timestamp is self-contained |
| `elapsedTime` | **Policy activation time** | When policy becomes effective |
| `delayPeriod` | **Triggering event** | Event that starts the delay |
| `meteredTime` | **Cumulative from first use** | Running total of active usage |
| `timeInterval` | **N/A** | Describes duration length, not position |

**For static analysis**:
- `dateTime`: Compare directly
- `elapsedTime`: Assume `t₀ = policy.issued` (or `policy.activated`)
- `delayPeriod`: Cannot evaluate statically without knowing trigger event
- `meteredTime`: Cannot evaluate statically without usage data

---

### Table 12: Static Analyzability

| LeftOperand | Statically Analyzable | Reason |
|-------------|----------------------|--------|
| `dateTime` |  Yes | Absolute values |
| `count` |  Yes (bounds) | Can check bound conflicts |
| `percentage` |  Yes | Fixed domain [0,100] |
| `payAmount` |  Yes (same unit) | If units match |
| `resolution` |  Yes (same unit) | If units match |
| `elapsedTime` | ⚠️ Partial | Need to assume reference point |
| `delayPeriod` | ⚠️ Partial | Trigger event unknown |
| `meteredTime` |  No | Requires runtime usage data |
| `timeInterval` |  Yes | Duration comparison |
| Positional (absolute) |  Yes | If media dimensions known |
| Positional (relative) |  Yes | Fixed domain [0,100] |

---

### Table 13: Complete LeftOperand Classification

| # | LeftOperand | Category | Grounding | Static Analysis |
|---|-------------|----------|-----------|-----------------|
| 1 | `count` | Numeric | Self-contained |  Full |
| 2 | `percentage` | Numeric | Self-contained |  Full |
| 3 | `payAmount` | Numeric | Self-contained |  Full (same unit) |
| 4 | `resolution` | Numeric | Self-contained |  Full (same unit) |
| 5 | `dateTime` | Temporal | Self-contained |  Full |
| 6 | `timeInterval` | Temporal | Self-contained |  Full |
| 7 | `absolutePosition` | Positional | Self-contained |  Full |
| 8 | `absoluteSize` | Positional | Self-contained |  Full |
| 9 | `absoluteTemporalPosition` | Positional | Self-contained |  Full |
| 10 | `absoluteSpatialPosition` | Positional | Self-contained |  Full |
| 11 | `relativePosition` | Positional | Self-contained |  Full |
| 12 | `relativeSize` | Positional | Self-contained |  Full |
| 13 | `relativeTemporalPosition` | Positional | Self-contained |  Full |
| 14 | `relativeSpatialPosition` | Positional | Self-contained |  Full |
| 15 | `elapsedTime` | Temporal | Reference point | ⚠️ Partial |
| 16 | `delayPeriod` | Temporal | Reference point | ⚠️ Partial |
| 17 | `meteredTime` | Temporal | Reference point |  Runtime only |
| 18 | `language` | Categorical | External KB (LCC/Lexvo) |  Requires grounding |
| 19 | `spatial` | Categorical | External KB (GeoNames) |  Requires grounding |
| 20 | `spatialCoordinates` | Categorical | External KB (GeoSPARQL) |  Requires grounding |
| 21 | `event` | Categorical | External KB (Schema.org) |  Requires grounding |
| 22 | `media` | Categorical | External KB (Custom) |  Requires grounding |
| 23 | `industry` | Categorical | External KB (NAICS/ISIC) |  Requires grounding |
| 24 | `purpose` | Categorical | External KB (DPV) |  Requires grounding |
| 25 | `recipient` | Identity | External KB (FOAF/vCard) |  Requires grounding |
| 26 | `product` | Categorical | External KB (UNSPSC) |  Requires grounding |
| 27 | `deliveryChannel` | Categorical | External KB (Custom) |  Requires grounding |
| 28 | `systemDevice` | Identity | External KB (Custom) |  Requires grounding |
| 29 | `fileFormat` | Categorical | External KB (PRONOM/IANA) |  Requires grounding |
| 30 | `virtualLocation` | Identity | External KB (DNS/IP) |  Requires grounding |
| 31 | `version` | Categorical | External KB (SemVer) |  Requires grounding |

---

### Table 14: Summary Statistics

| Metric | Value |
|--------|-------|
| **Total ODRL LeftOperands** | 31 |
| **Self-Contained (XSD-Grounded)** | 14 (45%) |
| **Reference Point Required** | 3 (10%) |
| **Semantic Grounding Required** | 14 (45%) |
| **Fully Statically Analyzable** | 14 (45%) |
| **Partially Statically Analyzable** | 2 (6%) |
| **Runtime Only** | 1 (3%) |
| **Requires External KB** | 14 (45%) |

---

## Key Findings

1. **45% of ODRL constraints are fully self-contained** and can be analyzed using SMT solvers with XSD type semantics alone.

2. **45% require external semantic grounding** through knowledge bases like LCC, GeoNames, DPV, etc.

3. **Only 1 constraint (`meteredTime`) cannot be statically analyzed** — it requires runtime usage data.

4. **Unit handling simplification**: By treating different units as incomparable (no conversion), we maintain soundness while avoiding complexity.

5. **Reference point decision**: Using policy activation time as the default `t₀` enables static analysis of duration-based constraints.

---

## References

1. **ODRL Information Model 2.2** — W3C Recommendation (2018)
2. **ODRL Vocabulary & Expression 2.2** — W3C Recommendation (2018)
3. **XSD Datatypes** — W3C Recommendation
4. **ISO 8601** — Date and time format
5. **Z3: An Efficient SMT Solver** — de Moura & Bjørner (2008)
