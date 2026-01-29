## `payAmount` — Complete Formal Specification

### 1. ODRL Definition (Source)

```turtle
:payAmount
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Payment Amount"@en ;
    skos:definition "The amount of a financial payment. Right operand value 
                     MUST be an xsd:decimal."@en ;
    skos:note "Can be used for compensation duties with the unit property 
               indicating the currency of the payment."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 2. Formal Definition

```
LeftOperand:   odrl:payAmount
Category:      𝓛_unit (unit-dependent)
XSD Type:      xsd:decimal
Domain:        ℝ≥0 = {x ∈ ℚ | x ≥ 0}
Semantics:     Amount of financial payment
Unit:          ✅ REQUIRED (currency)
Scope:         ❌ None
Reference:     ❌ None
ODRL Status:   Non-Normative
```

---

### 3. Domain Specification

$$\mathcal{D}_{\text{payAmount}} = \{x \in \mathbb{Q} \mid x \geq 0\}$$

| Property | Value | Rationale |
|----------|-------|-----------|
| Lower bound | 0 (inclusive) | Payment cannot be negative |
| Upper bound | +∞ | No maximum payment |
| Type | Rational (xsd:decimal) | Currency amounts have decimals |

---

### 4. Unit Handling (Critical)

#### 4.1 Unit is Required

ODRL states: "the unit property indicating the currency of the payment"

```
unit ∈ {EUR, USD, GBP, JPY, CHF, ...} (currency IRIs)
```

Common currency IRIs:
| Currency | IRI Example |
|----------|-------------|
| Euro | `http://dbpedia.org/resource/Euro` |
| US Dollar | `http://dbpedia.org/resource/United_States_dollar` |
| British Pound | `http://dbpedia.org/resource/Pound_sterling` |
| Japanese Yen | `http://dbpedia.org/resource/Japanese_yen` |
| ISO 4217 codes | `http://iso.org/4217/EUR` |

#### 4.2 Comparability Rule

**Critical:** Constraints with different currencies are **NOT comparable**.

$$\text{comparable}(c_1, c_2) \iff \text{unit}(c_1) = \text{unit}(c_2)$$

| c₁.unit | c₂.unit | Comparable? | Result if not |
|---------|---------|:-----------:|---------------|
| EUR | EUR | ✅ Yes | — |
| EUR | USD | ❌ No | `UNKNOWN` |
| EUR | ⊥ (missing) | ❌ No | `UNKNOWN` |
| ⊥ | ⊥ | ⚠️ Risky | `UNKNOWN` (conservative) |

**Design Decision:** No automatic currency conversion.
- Conversion requires external exchange rates
- Rates change over time
- Would introduce unsoundness

#### 4.3 Variable Identity

Each (payAmount, unit) pair gets a **separate Z3 variable**:

```
payAmount[EUR] → payAmount_EUR
payAmount[USD] → payAmount_USD
payAmount[GBP] → payAmount_GBP
```

---

### 5. Valid Operators (9/12)

| Operator | Valid | SMT Encoding | Example |
|----------|:-----:|--------------|---------|
| `eq` | ✅ | `(= payAmount v)` | `payAmount eq 100` |
| `neq` | ✅ | `(not (= payAmount v))` | `payAmount neq 0` |
| `lt` | ✅ | `(< payAmount v)` | `payAmount lt 50` |
| `lteq` | ✅ | `(<= payAmount v)` | `payAmount lteq 100` |
| `gt` | ✅ | `(> payAmount v)` | `payAmount gt 0` |
| `gteq` | ✅ | `(>= payAmount v)` | `payAmount gteq 10` |
| `isAnyOf` | ✅ | `(or (= payAmount v₁) ...)` | `payAmount isAnyOf [10,20,50]` |
| `isNoneOf` | ✅ | `(and (not (= payAmount v₁)) ...)` | `payAmount isNoneOf [0]` |
| `isAllOf` | ⚠️ | Degenerates to `eq` | — |
| `isA` | ❌ | — | No taxonomy for decimals |
| `hasPart` | ❌ | — | No mereology |
| `isPartOf` | ❌ | — | No mereology |

---

### 6. Abstract Domain

$$\mathcal{A}_{\text{payAmount}} = \mathbb{I}_{\mathbb{R}\geq 0} = \{[a,b] \mid 0 \leq a \leq b \leq +\infty\} \cup \{\bot\}$$

| Operator | α(constraint) |
|----------|---------------|
| `eq v` | `[v, v]` |
| `neq v` | `⊤` (over-approximation) |
| `lt v` | `[0, v)` |
| `lteq v` | `[0, v]` |
| `gt v` | `(v, +∞)` |
| `gteq v` | `[v, +∞)` |

---

### 7. SMT Encoding

```smt
; Separate variable per currency
(declare-const payAmount_EUR Real)
(declare-const payAmount_USD Real)
(declare-const payAmount_GBP Real)

; Domain constraints: non-negative
(assert (>= payAmount_EUR 0))
(assert (>= payAmount_USD 0))
(assert (>= payAmount_GBP 0))

; Example 1: payAmount lteq 100 [EUR]
(assert (<= payAmount_EUR 100))

; Example 2: payAmount gteq 50 [EUR]
(assert (>= payAmount_EUR 50))

; Conflict check (same currency)
(push)
(assert (<= payAmount_EUR 30))   ; P1: lteq 30 EUR
(assert (>= payAmount_EUR 50))   ; P2: gteq 50 EUR
(check-sat)  ; UNSAT → CONFLICT
(pop)

; Incomparable (different currencies)
; payAmount_EUR and payAmount_USD are DIFFERENT variables
; No conflict can be detected → UNKNOWN
```

---

### 8. Conflict Patterns

| Pattern | c₁ | c₂ | Result |
|---------|----|----|--------|
| Same currency, conflict | `lteq 50 [EUR]` | `gteq 100 [EUR]` | `CONFLICT` |
| Same currency, compatible | `lteq 100 [EUR]` | `gteq 50 [EUR]` | `POSSIBLY-COMPATIBLE` |
| Different currency | `lteq 50 [EUR]` | `gteq 100 [USD]` | `UNKNOWN` |
| Missing unit | `lteq 50` | `gteq 100` | `UNKNOWN` |
| One missing unit | `lteq 50 [EUR]` | `gteq 100` | `UNKNOWN` |

---

### 9. ODRL Turtle Examples

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .
@prefix dbr: <http://dbpedia.org/resource/> .

# Example 1: Payment at most 100 EUR
ex:c1 a odrl:Constraint ;
    odrl:leftOperand odrl:payAmount ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "100.00"^^xsd:decimal ;
    odrl:unit dbr:Euro .

# Example 2: Payment at least 50 EUR
ex:c2 a odrl:Constraint ;
    odrl:leftOperand odrl:payAmount ;
    odrl:operator odrl:gteq ;
    odrl:rightOperand "50.00"^^xsd:decimal ;
    odrl:unit dbr:Euro .

# Example 3: Exact payment
ex:c3 a odrl:Constraint ;
    odrl:leftOperand odrl:payAmount ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "75.00"^^xsd:decimal ;
    odrl:unit dbr:Euro .

# Example 4: Payment in USD (different currency)
ex:c4 a odrl:Constraint ;
    odrl:leftOperand odrl:payAmount ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "100.00"^^xsd:decimal ;
    odrl:unit dbr:United_States_dollar .

# Example 5: Duty with payment
ex:duty1 a odrl:Duty ;
    odrl:action odrl:compensate ;
    odrl:constraint ex:c1 .

# Example 6: Logical composition (payment range)
ex:c5 a odrl:LogicalConstraint ;
    odrl:and (ex:c1 ex:c2) .  # Between 50 and 100 EUR
```

---

### 10. Implementation

#### 10.1 Configuration

```yaml
payAmount:
  class: FULL
  category: L_unit
  z3_sort: Real
  domain:
    min: 0
    max: null
  requires_unit: true
  unit_type: currency
  valid_units:
    - http://dbpedia.org/resource/Euro
    - http://dbpedia.org/resource/United_States_dollar
    - http://dbpedia.org/resource/Pound_sterling
    - http://dbpedia.org/resource/Japanese_yen
    # ... extensible
  operators: [eq, neq, lt, lteq, gt, gteq, isAnyOf, isNoneOf]
  restricted_operators: [isAllOf]
  invalid_operators: [isA, hasPart, isPartOf]
  note: "Currency unit REQUIRED for comparability"
  description: "Financial payment amount"
```

#### 10.2 Comparability Check

```python
def is_comparable_payAmount(c1: AtomicConstraint, c2: AtomicConstraint) -> ComparabilityResult:
    """Check if two payAmount constraints are comparable."""
    
    # Must be same LeftOperand
    if normalize_operand(c1.left_operand) != "payAmount":
        return ComparabilityResult(False, "Not payAmount")
    if normalize_operand(c2.left_operand) != "payAmount":
        return ComparabilityResult(False, "Not payAmount")
    
    # Must have units
    if c1.unit is None or c2.unit is None:
        return ComparabilityResult(
            comparable=False,
            reason="MISSING_UNIT",
            details="payAmount requires currency unit for comparison"
        )
    
    # Must have SAME unit
    unit1 = normalize_unit(c1.unit)
    unit2 = normalize_unit(c2.unit)
    
    if unit1 != unit2:
        return ComparabilityResult(
            comparable=False,
            reason="UNIT_MISMATCH",
            details=f"Cannot compare {unit1} with {unit2} (no currency conversion)"
        )
    
    return ComparabilityResult(comparable=True)
```

#### 10.3 Variable Manager Update

```python
def get_variable(self, left_operand: str, unit: Optional[str] = None, ...):
    """Get or create Z3 variable."""
    op = normalize_operand(left_operand)
    
    # For unit-dependent operands, unit is part of variable identity
    if op in L_UNIT:
        if unit is None:
            # No unit → use placeholder, will be marked incomparable
            unit = "UNKNOWN"
        key = f"{op}_{normalize_unit(unit)}"
    else:
        key = f"{op}_default"
    
    if key not in self._variables:
        bounds = DOMAIN_BOUNDS.get(op)
        var = Real(key) if bounds and bounds.use_real else Int(key)
        self._variables[key] = var
        self._var_info[key] = {'operand': op, 'unit': unit, 'bounds': bounds}
    
    return self._variables[key]
```

---

### 11. Summary Table

| Dimension | Value |
|-----------|-------|
| **LeftOperand** | `odrl:payAmount` |
| **Category** | 𝓛_unit |
| **XSD Type** | xsd:decimal |
| **Domain** | ℝ≥0 |
| **Valid Operators** | 9/12 (75%) |
| **Abstract Domain** | 𝕀_ℝ≥0 |
| **SMT Theory** | QF-LRA |
| **Z3 Sort** | Real |
| **Decidable** | ✅ Yes (same unit) |
| **Unit** | ✅ **REQUIRED** (currency) |
| **Scope** | ❌ None |
| **Currency Conversion** | ❌ Not supported |
| **Cross-Currency Comparison** | `UNKNOWN` |

---

### 12. Comparison with Other Unit-Dependent LeftOperands

| LeftOperand | Domain | Unit Type | Examples |
|-------------|--------|-----------|----------|
| `payAmount` | ℝ≥0 | Currency | EUR, USD, GBP |
| `resolution` | ℝ>0 | Density | DPI, PPI |
| `absolutePosition` | ℝ≥0 | Length/Time | seconds, bytes, pixels |
| `absoluteSize` | ℝ>0 | Size | bytes, pixels, mm |

**Shared properties:**
- All require unit for comparability
- All use QF-LRA
- All yield `UNKNOWN` on unit mismatch
- No automatic unit conversion

---

### 13. Paper Statement

> The `odrl:payAmount` LeftOperand represents a financial payment amount with mandatory currency unit. ODRL-SA treats each (payAmount, currency) pair as a distinct variable, ensuring constraints with different currencies are classified as `UNKNOWN` rather than falsely compared. Currency conversion is intentionally excluded—it would require external exchange rate data and introduce temporal dependence, violating static analysis assumptions. This design preserves soundness: detected conflicts involve the same currency and are genuine.

---

### 14. Test Cases

| # | c₁ | c₂ | Expected | Reason |
|---|----|----|----------|--------|
| 1 | `lteq 50 [EUR]` | `gteq 100 [EUR]` | `CONFLICT` | [0,50] ∩ [100,∞) = ∅ |
| 2 | `lteq 100 [EUR]` | `gteq 50 [EUR]` | `POSSIBLY-COMPATIBLE` | [0,100] ∩ [50,∞) = [50,100] |
| 3 | `eq 75 [EUR]` | `gteq 50 [EUR]` | `POSSIBLY-COMPATIBLE` | 75 ∈ [50,∞) |
| 4 | `eq 75 [EUR]` | `eq 100 [EUR]` | `CONFLICT` | 75 ≠ 100 |
| 5 | `lteq 50 [EUR]` | `gteq 100 [USD]` | `UNKNOWN` | Different currency |
| 6 | `lteq 50 [EUR]` | `gteq 100` | `UNKNOWN` | Missing unit |
| 7 | `lteq 50` | `gteq 100` | `UNKNOWN` | Both missing unit |

---

**This is the complete formal specification for `payAmount`.**

**Next:** `resolution`, `absolutePosition`, `absoluteSize` follow the same pattern with different unit types.