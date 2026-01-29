## payAmount - Formal Specification

### ODRL Vocabulary Definition

```turtle
:payAmount
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Payment Amount"@en ;
    skos:definition "The amount of a financial payment. Right operand 
                     value MUST be an xsd:decimal."@en ;
    skos:note "Can be used for compensation duties with the unit property 
               indicating the currency of the payment."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Intuitive Semantics

**What it measures:** The monetary value of a payment associated with asset usage.

| Value | Meaning |
|-------|---------|
| 0 | Free (no payment required) |
| 9.99 | Typical digital content price |
| 100.00 | Standard licensing fee |
| 10000.00 | Enterprise licensing |

**Use cases:**
- Licensing fees ("pay at least €50 for commercial use")
- Compensation duties ("royalty payment of $0.01 per use")
- Tiered pricing ("free if payment < €10, premium otherwise")

---

### 2. Formal Domain Specification

$$\text{dom}(\texttt{payAmount}) = \mathbb{R}_{\geq 0} = [0, +\infty)$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (inclusive) | Zero payment = free access |
| **Upper bound** | ∞ | No theoretical maximum |
| **XSD Type** | `xsd:decimal` | **Explicitly required** by ODRL definition |

> Zero is semantically valid for `payAmount` (represents free/no-cost access), unlike `resolution` where zero is degenerate.

---

### 3. Unit Specification

**Unit Required:** Yes (currency)

| Property | Value |
|----------|-------|
| **Unit category** | Currency |
| **Common units** | EUR, USD, GBP, JPY, CHF |
| **Standard** | ISO 4217 currency codes |
| **QUDT URIs** | `http://qudt.org/vocab/unit/EUR`, `http://qudt.org/vocab/unit/USD`, etc. |

**Unit Comparability Rule:**
- Same currency → Comparable
- Different currencies → **UNKNOWN** (no automatic conversion)
- Missing unit → **UNKNOWN**

**Rationale for no currency conversion:**
1. Exchange rates are temporal (change continuously)
2. Would require external data source
3. Violates static analysis assumptions
4. Conservative approach preserves soundness

---

### 4. Operator Specification

**Valid operators:** 9 of 12

| Operator | Valid | Semantics |
|----------|-------|-----------|
| `eq` | ✅ | Exact amount required |
| `neq` | ✅ | Any amount except specified |
| `lt` | ✅ | Less than this amount |
| `lteq` | ✅ | At most this amount |
| `gt` | ✅ | More than this amount |
| `gteq` | ✅ | At least this amount |
| `isAnyOf` | ✅ | Amount in enumerated set |
| `isNoneOf` | ✅ | Amount not in enumerated set |
| `isAllOf` | ✅ | Satisfiable iff all values identical |
| `isA` | ❌ | Semantic, not applicable to numeric |
| `hasPart` | ❌ | Semantic, not applicable to numeric |
| `isPartOf` | ❌ | Semantic, not applicable to numeric |

**isAllOf formal semantics:**

$$\texttt{isAllOf}(\{v_1, \ldots, v_n\}) \equiv \begin{cases} x = v_1 & \text{if } v_1 = v_2 = \cdots = v_n \\ \bot & \text{otherwise} \end{cases}$$

---

### 5. SMT Encoding

**Theory:** QF_LRA (Quantifier-Free Linear Real Arithmetic)

**Z3 Sort:** Real

```python
from z3 import *

def encode_payAmount(operator: str, value, unit: str = None) -> BoolRef:
    """
    Encode payAmount constraint.
    Returns BoolVal(True) with UNKNOWN flag if unit missing/incompatible.
    """
    if unit is None:
        # Cannot analyze without currency
        return BoolVal(True)  # Over-approximate, mark UNKNOWN
    
    # Variable name includes currency for isolation
    x = Real(f'payAmount_{normalize_currency(unit)}')
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

def normalize_currency(unit: str) -> str:
    """Normalize currency to canonical ISO 4217 form."""
    CURRENCY_MAP = {
        # ISO 4217 codes
        "EUR": "EUR", "USD": "USD", "GBP": "GBP", 
        "JPY": "JPY", "CHF": "CHF", "CAD": "CAD",
        # Lowercase variants
        "eur": "EUR", "usd": "USD", "gbp": "GBP",
        # QUDT URIs
        "http://qudt.org/vocab/unit/EUR": "EUR",
        "http://qudt.org/vocab/unit/USD": "USD",
        "http://qudt.org/vocab/unit/GBP": "GBP",
        "http://qudt.org/vocab/unit/JPY": "JPY",
        # Common symbols (optional support)
        "€": "EUR", "$": "USD", "£": "GBP", "¥": "JPY",
    }
    return CURRENCY_MAP.get(unit, unit)  # Unknown currencies stay as-is

def are_currencies_compatible(unit1: str, unit2: str) -> bool:
    """Check if two currencies are comparable."""
    if unit1 is None or unit2 is None:
        return False
    return normalize_currency(unit1) == normalize_currency(unit2)
```

---

### 6. Abstract Interpretation

**Abstract Domain:** 𝕀_ℚ ∩ [0, ∞) (rational intervals over non-negative reals)

**Abstraction function:**

$$\alpha(\texttt{payAmount op } v) = \begin{cases}
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

### 7. Conflict Detection

**Judgment rules:**

$$\frac{\text{currency-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket = \emptyset}{\texttt{CONFLICT}(c_1, c_2)}$$

$$\frac{\text{currency-compatible}(c_1, c_2) \land \llbracket c_1 \rrbracket \cap \llbracket c_2 \rrbracket \neq \emptyset}{\texttt{POSSIBLY-COMPATIBLE}(c_1, c_2)}$$

$$\frac{\neg\text{currency-compatible}(c_1, c_2)}{\texttt{UNKNOWN}(c_1, c_2)}$$

**Examples (same currency - EUR):**

| Constraint 1 | Constraint 2 | Interval 1 | Interval 2 | Judgment |
|--------------|--------------|------------|------------|----------|
| `lteq 50` | `gteq 100` | [0, 50] | [100, ∞) | **CONFLICT** |
| `lteq 100` | `gteq 50` | [0, 100] | [50, ∞) | POSSIBLY-COMPATIBLE |
| `eq 0` | `gt 0` | {0} | (0, ∞) | **CONFLICT** |
| `gteq 0` | `lteq 1000` | [0, ∞) | [0, 1000] | POSSIBLY-COMPATIBLE |
| `neq 100` | `eq 100` | [0,∞) \ {100} | {100} | **CONFLICT** |

**Examples (different currencies):**

| Constraint 1 | Constraint 2 | Judgment |
|--------------|--------------|----------|
| `lteq 50 EUR` | `gteq 100 USD` | **UNKNOWN** |
| `eq 100 EUR` | `eq 100 GBP` | **UNKNOWN** |
| `gteq 0 EUR` | `lteq 1000` (no unit) | **UNKNOWN** |

---

### 8. Special Case: Zero Payment (Free Access)

Unlike `resolution` where zero is degenerate, `payAmount eq 0` is semantically meaningful:

```turtle
# Valid: Free access constraint
ex:freeAccess a odrl:Constraint ;
    odrl:leftOperand odrl:payAmount ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "0"^^xsd:decimal ;
    odrl:unit <http://qudt.org/vocab/unit/EUR> .
```

**Interpretation:** No payment required (free/gratis access).

**Conflict example:**
- `payAmount eq 0 EUR` ∧ `payAmount gt 0 EUR` → **CONFLICT**
- (Cannot be both free and require payment)

---

### 9. Comparison with Related LeftOperands

| LeftOperand | Domain | Zero Valid | Unit Required | Category |
|-------------|--------|------------|---------------|----------|
| **payAmount** | [0, ∞) | ✅ Yes (free) | ✅ Currency | L_unit |
| **resolution** | (0, ∞) | ❌ No | ✅ DPI/PPI | L_unit |
| **absoluteSize** | (0, ∞) | ❌ No | ✅ bytes/px | L_unit |
| **absolutePosition** | [0, ∞) | ✅ Yes (origin) | ✅ sec/bytes | L_unit |

**Key distinction:** `payAmount` includes zero (free access is valid), has currency units, and the ODRL definition **explicitly mandates** `xsd:decimal` datatype.

---

### 10. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | FULL (when unit present) |
| **Category** | L_unit |
| **Equivalence Class** | None (unique currency-dependent semantics) |
| **External KB Required** | No |
| **Decidable** | Yes |

---

### 11. Configuration Entry

```python
"payAmount": {
    "class": "FULL",
    "category": "L_unit",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": True,  # Zero is valid (free access)
        "inclusive_max": None
    },
    "operators": [
        "eq", "neq", "lt", "lteq", "gt", "gteq",
        "isAnyOf", "isNoneOf", "isAllOf"
    ],
    "unit": {
        "required": True,
        "category": "currency",
        "standard": "ISO 4217",
        "common": ["EUR", "USD", "GBP", "JPY", "CHF", "CAD"],
        "qudt": [
            "http://qudt.org/vocab/unit/EUR",
            "http://qudt.org/vocab/unit/USD",
            "http://qudt.org/vocab/unit/GBP",
            "http://qudt.org/vocab/unit/JPY"
        ]
    },
    "datatype": "xsd:decimal",  # Explicitly required by ODRL
    "dimensions": 1,
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---

### 12. LaTeX Table Entry

```latex
\multicolumn{6}{l}{\textit{Unit-Dependent (4)}} \\
payAmount & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
resolution & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
absolutePosition & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{\geq 0}$ & LRA & \fullmark & \fullmark \\
absoluteSize & $\mathcal{L}_{\text{unit}}$ & $\mathbb{R}_{> 0}$ & LRA & \fullmark & \fullmark \\
```

---

### 13. Publication Statement

> **payAmount** measures the monetary value of payments associated with asset usage, with domain ℝ≥0 explicitly including zero to represent free/gratis access. The ODRL definition mandates `xsd:decimal` datatype and notes that "the unit property indicat[es] the currency." ODRL-SA requires explicit ISO 4217 currency codes for constraint comparison; constraints with different or missing currencies yield UNKNOWN. Currency conversion is intentionally excluded—exchange rates are temporal and would require external data, violating static analysis assumptions. Each (payAmount, currency) pair maps to a separate Z3 Real variable (e.g., `payAmount_EUR`, `payAmount_USD`), ensuring currency-mismatched constraints cannot produce false conflicts. Conflict detection reduces to interval intersection over non-negative reals within QF_LRA.

---

### 14. Summary Table

| Aspect | Specification |
|--------|---------------|
| **Semantics** | Financial payment amount |
| **Domain** | [0, ∞) ⊂ ℝ, zero included (free access) |
| **Datatype** | `xsd:decimal` (ODRL-mandated) |
| **Operators** | 9/12 (numeric + set, excluding semantic) |
| **isAllOf** | SAT iff all values identical |
| **Unit** | Required (ISO 4217 currency) |
| **Unit mismatch** | → UNKNOWN |
| **Dimensions** | 1D scalar |
| **SMT Theory** | QF_LRA |
| **Z3 Sort** | Real |
| **External KB** | Not required |
| **Decidable** | Yes |
| **Category** | L_unit |

---

### 15. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .
@prefix qudt: <http://qudt.org/vocab/unit/> .

# Test 1: Same currency - CONFLICT
ex:policy_payAmount_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "50"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "100"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
            )
        ]
    ] .
# Expected: CONFLICT ([0,50] ∩ [100,∞) = ∅)

# Test 2: Same currency - COMPATIBLE
ex:policy_payAmount_compatible
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "50"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "100"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
            )
        ]
    ] .
# Expected: POSSIBLY-COMPATIBLE ([50,100] ≠ ∅)

# Test 3: Different currencies - UNKNOWN
ex:policy_payAmount_different_currency
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "50"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "100"^^xsd:decimal ;
                  odrl:unit qudt:USD ]
            )
        ]
    ] .
# Expected: UNKNOWN (EUR ≠ USD)

# Test 4: Free access vs paid - CONFLICT
ex:policy_payAmount_free_vs_paid
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "0"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
                [ odrl:leftOperand odrl:payAmount ;
                  odrl:operator odrl:gt ;
                  odrl:rightOperand "0"^^xsd:decimal ;
                  odrl:unit qudt:EUR ]
            )
        ]
    ] .
# Expected: CONFLICT ({0} ∩ (0,∞) = ∅)
```