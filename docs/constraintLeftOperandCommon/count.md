## `count` — Complete Formal Specification

### 1. Definition

```
LeftOperand:  odrl:count
XSD Type:     xsd:integer
Domain:       ℤ≥0 = {0, 1, 2, 3, ...}
Semantics:    Numeric count of executions of the action of the Rule
Unit:         Not applicable (uses unitOfCount instead)
Scope:        unitOfCount (optional)
ODRL Status:  Non-Normative
```

### 2. Valid Operators (9/12)

| Operator | Valid | SMT Encoding | Example |
|----------|:-----:|--------------|---------|
| `eq` |  | `(= count v)` | `count eq 5` |
| `neq` |  | `(not (= count v))` | `count neq 0` |
| `lt` |  | `(< count v)` | `count lt 10` |
| `lteq` |  | `(<= count v)` | `count lteq 10` |
| `gt` |  | `(> count v)` | `count gt 0` |
| `gteq` |  | `(>= count v)` | `count gteq 5` |
| `isAnyOf` |  | `(or (= count v₁) ...)` | `count isAnyOf [1,3,5]` |
| `isNoneOf` |  | `(and (not (= count v₁)) ...)` | `count isNoneOf [0,13]` |
| `isAllOf` | ⚠️ | `(= count v)` iff singleton | Degenerates to `eq` |
| `isA` | ❌ | — | No taxonomy for integers |
| `hasPart` | ❌ | — | Integers have no mereological parts |
| `isPartOf` | ❌ | — | Integers are not parts of wholes |

### 3. Abstract Domain

```
𝒜_count = 𝕀_ℤ≥0 = {[a,b] | 0 ≤ a ≤ b ≤ +∞} ∪ {⊥}
```

| Operator | α(constraint) | Notes |
|----------|---------------|-------|
| `eq v` | `[v, v]` | Point interval |
| `neq v` | `⊤` | Over-approximation (SMT refines) |
| `lt v` | `[0, v-1]` | Upper-bounded, v > 0 required |
| `lteq v` | `[0, v]` | Upper-bounded |
| `gt v` | `[v+1, +∞)` | Lower-bounded |
| `gteq v` | `[v, +∞)` | Lower-bounded |
| `isAnyOf V` | `⊔{[v,v] | v ∈ V}` | Finite set (non-convex) |
| `isNoneOf V` | `⊤` | Over-approximation (SMT refines) |
| `isAllOf V` | `[v,v]` if `|V|=1` else `⊥` | Only valid for singleton |

### 4. Logical Operators

| Operator | Semantics | SMT Encoding |
|----------|-----------|--------------|
| `and` | ∧ (conjunction) | `(and c₁ c₂ ... cₙ)` |
| `or` | ∨ (disjunction) | `(or c₁ c₂ ... cₙ)` |
| `xone` | ⊕ (exactly one) | `(= 1 (+ (ite c₁ 1 0) ...))` |
| `andSequence` | Ordered ∧ | Collapsed to `and` (static) |

**Interpretation:** Existential satisfiability (∃w : φ(w))

### 5. Scope Handling (`unitOfCount`)

```
unitOfCount ∈ {odrl:perUser, odrl:perDevice, odrl:perOrganization, odrl:perSession, ⊥}
```

| Value | URI | Semantics |
|-------|-----|-----------|
| (default) | `⊥` | Total cumulative count |
| perUser | `odrl:perUser` | Count per unique user |
| perDevice | `odrl:perDevice` | Count per unique device |
| perOrganization | `odrl:perOrganization` | Count per organization |
| perSession | `odrl:perSession` | Count per session |

**Comparability Rule:**
```
comparable(c₁, c₂) ⟺ 
    unitOfCount(c₁) = unitOfCount(c₂) 
  ∨ unitOfCount(c₁) = ⊥ 
  ∨ unitOfCount(c₂) = ⊥
```

| c₁.unitOfCount | c₂.unitOfCount | Comparable? |
|----------------|----------------|-------------|
| ⊥ | ⊥ |  Yes |
| ⊥ | perUser |  Yes (assume same) |
| perUser | perUser |  Yes |
| perUser | perDevice | ❌ No → `UNKNOWN` |

### 6. Conflict Patterns

| Pattern | c₁ | c₂ | Result |
|---------|----|----|--------|
| Contradictory equality | `eq 5` | `eq 10` | `CONFLICT` |
| Impossible range | `lteq 5` | `gteq 10` | `CONFLICT` |
| Empty intersection | `lt 5` | `gt 10` | `CONFLICT` |
| Boundary touch | `lt 5` | `gteq 5` | `CONFLICT` |
| Overlapping | `lteq 10` | `gteq 5` | `POSSIBLY-COMPATIBLE` |
| Subsumption | `lteq 5` | `lteq 10` | `POSSIBLY-COMPATIBLE` |
| Different scope | `eq 5 [perUser]` | `eq 5 [perDevice]` | `UNKNOWN` |

### 7. Complete SMT Theory

```smt
; === Declaration ===
(declare-const count Int)
(assert (>= count 0))  ; Domain: ℤ≥0

; === Comparison Operators ===
(define-fun count_eq ((v Int)) Bool 
  (= count v))

(define-fun count_neq ((v Int)) Bool 
  (not (= count v)))

(define-fun count_lt ((v Int)) Bool 
  (< count v))

(define-fun count_lteq ((v Int)) Bool 
  (<= count v))

(define-fun count_gt ((v Int)) Bool 
  (> count v))

(define-fun count_gteq ((v Int)) Bool 
  (>= count v))

; === Set Operators ===
; isAnyOf: count ∈ {v₁, v₂, ...}
(define-fun count_isAnyOf_3 ((v1 Int) (v2 Int) (v3 Int)) Bool
  (or (= count v1) (= count v2) (= count v3)))

; isNoneOf: count ∉ {v₁, v₂, ...}
(define-fun count_isNoneOf_2 ((v1 Int) (v2 Int)) Bool
  (and (not (= count v1)) (not (= count v2))))

; isAllOf: only valid for singleton, degenerates to eq
(define-fun count_isAllOf_1 ((v Int)) Bool
  (= count v))

; === Logical Composition ===
; xone(c₁, c₂, ..., cₙ): exactly one holds
; Encoding: sum of indicator variables = 1
```

### 8. ODRL Turtle Examples

```turtle
# Example 1: Simple count limit
ex:c1 a odrl:Constraint ;
    odrl:leftOperand odrl:count ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "10"^^xsd:integer .

# Example 2: Count with scope
ex:c2 a odrl:Constraint ;
    odrl:leftOperand odrl:count ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "5"^^xsd:integer ;
    odrl:unitOfCount odrl:perUser .

# Example 3: Count in set
ex:c3 a odrl:Constraint ;
    odrl:leftOperand odrl:count ;
    odrl:operator odrl:isAnyOf ;
    odrl:rightOperand ("1"^^xsd:integer "3"^^xsd:integer "5"^^xsd:integer) .

# Example 4: Logical composition
ex:c4 a odrl:LogicalConstraint ;
    odrl:and (ex:c1 ex:c2) .
```

