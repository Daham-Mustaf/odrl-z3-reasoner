## `percentage` — Complete Formal Specification

### 1. ODRL Definition (Source)

```turtle
:percentage
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Asset Percentage"@en ;
    skos:definition "A percentage amount of the target Asset relevant for 
                     exercising the action of the Rule. Right operand value 
                     MUST be an xsd:decimal from 0 to 100."@en ;
    skos:note "Example: Extract less than or equal to 50%."@en ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 2. Formal Definition

```
LeftOperand:   odrl:percentage
Category:      𝓛_xsd
XSD Type:      xsd:decimal
Domain:        𝒟_percentage = [0, 100] ⊂ ℚ
Semantics:     Percentage amount of target Asset for action
Unit:          ❌ Not applicable (inherently percentage)
Scope:         ❌ None
Reference:     ❌ None (self-contained)
ODRL Status:   Non-Normative
```

---

### 3. Domain Specification

$$\mathcal{D}_{\text{percentage}} = \{x \in \mathbb{Q} \mid 0 \leq x \leq 100\}$$

| Property | Value |
|----------|-------|
| Lower bound | 0 (inclusive) |
| Upper bound | 100 (inclusive) |
| Type | Rational (xsd:decimal) |
| Closed |  Yes (bounded both sides) |

---

### 4. Valid Operators

| Operator | Valid | Category | SMT Encoding |
|----------|:-----:|----------|--------------|
| `eq` |  | Comparison | `(= percentage v)` |
| `neq` |  | Comparison | `(not (= percentage v))` |
| `lt` |  | Comparison | `(< percentage v)` |
| `lteq` |  | Comparison | `(<= percentage v)` |
| `gt` |  | Comparison | `(> percentage v)` |
| `gteq` |  | Comparison | `(>= percentage v)` |
| `isAnyOf` |  | Set | `(or (= percentage v₁) ...)` |
| `isNoneOf` |  | Set | `(and (not (= percentage v₁)) ...)` |
| `isAllOf` | ⚠️ | Set | Degenerates to `eq` |
| `isA` | ❌ | Semantic | No taxonomy for decimals |
| `hasPart` | ❌ | Semantic | No mereology |
| `isPartOf` | ❌ | Semantic | No mereology |

**Summary:** 9/12 operators valid (75%)

---

### 5. Abstract Domain

$$\mathcal{A}_{\text{percentage}} = \mathbb{I}_{[0,100]} = \{[a,b] \mid 0 \leq a \leq b \leq 100\} \cup \{\bot\}$$

**Lattice structure:**
- ⊥ (bottom): empty set
- ⊤ (top): [0, 100]
- Meet (⊓): interval intersection
- Join (⊔): interval hull

---

### 6. Abstraction Function

$$\alpha : 2^{\mathcal{W}} \to \mathcal{A}_{\text{percentage}}$$

| Operator | Constraint | α(constraint) |
|----------|------------|---------------|
| `eq v` | percentage = v | [v, v] |
| `neq v` | percentage ≠ v | ⊤ (over-approximation) |
| `lt v` | percentage < v | [0, v) |
| `lteq v` | percentage ≤ v | [0, v] |
| `gt v` | percentage > v | (v, 100] |
| `gteq v` | percentage ≥ v | [v, 100] |
| `isAnyOf V` | percentage ∈ V | ⊔{[v,v] \| v ∈ V} |
| `isNoneOf V` | percentage ∉ V | ⊤ (over-approximation) |

---

### 7. Concretization Function

$$\gamma : \mathcal{A}_{\text{percentage}} \to 2^{\mathcal{W}}$$

$$\gamma([a, b]) = \{w \mid w(\text{percentage}) \downarrow \land a \leq w(\text{percentage}) \leq b\}$$

$$\gamma(\bot) = \emptyset$$

$$\gamma(\top) = \mathcal{W}$$

---

### 8. Galois Connection

$$(\alpha, \gamma)$$ forms a Galois connection:

$$\forall S \subseteq \mathcal{W}, \forall a \in \mathcal{A}: \alpha(S) \sqsubseteq a \iff S \subseteq \gamma(a)$$

---

### 9. Judgment Function

$$\text{judge} : \mathcal{C}_{\text{percentage}} \times \mathcal{C}_{\text{percentage}} \to \{\texttt{CONFLICT}, \texttt{POSSIBLY-COMPATIBLE}, \texttt{UNKNOWN}\}$$

$$\text{judge}(c_1, c_2) = \begin{cases} \texttt{CONFLICT} & \text{if } \llbracket c_1 \rrbracket^\# \sqcap \llbracket c_2 \rrbracket^\# = \bot \\ \texttt{POSSIBLY-COMPATIBLE} & \text{if } \llbracket c_1 \rrbracket^\# \sqcap \llbracket c_2 \rrbracket^\# \neq \bot \\ \texttt{UNKNOWN} & \text{if not comparable} \end{cases}$$

**Note:** For `percentage`, all valid constraints are always comparable (same LeftOperand, no unit, no scope).

---

### 10. SMT Theory

**Theory:** QF-LRA (Quantifier-Free Linear Real Arithmetic)

```smt
; Declaration
(declare-const percentage Real)

; Domain constraint
(assert (>= percentage 0))
(assert (<= percentage 100))

; Operator encodings
(define-fun percentage_eq ((v Real)) Bool 
    (= percentage v))

(define-fun percentage_neq ((v Real)) Bool 
    (not (= percentage v)))

(define-fun percentage_lt ((v Real)) Bool 
    (< percentage v))

(define-fun percentage_lteq ((v Real)) Bool 
    (<= percentage v))

(define-fun percentage_gt ((v Real)) Bool 
    (> percentage v))

(define-fun percentage_gteq ((v Real)) Bool 
    (>= percentage v))
```

---

### 11. Conflict Patterns

| Pattern | c₁ | c₂ | Meet | Result |
|---------|----|----|------|--------|
| Contradictory equality | `eq 30` | `eq 50` | [30,30] ⊓ [50,50] = ⊥ | `CONFLICT` |
| Impossible range | `lteq 30` | `gteq 50` | [0,30] ⊓ [50,100] = ⊥ | `CONFLICT` |
| Boundary touch | `lt 50` | `gteq 50` | [0,50) ⊓ [50,100] = ⊥ | `CONFLICT` |
| Domain violation | `lt 0` | any | ⊥ | `CONFLICT` |
| Domain violation | `gt 100` | any | ⊥ | `CONFLICT` |
| Overlapping | `lteq 50` | `gteq 30` | [0,50] ⊓ [30,100] = [30,50] | `POSSIBLY-COMPATIBLE` |
| Subsumption | `lteq 30` | `lteq 50` | [0,30] ⊓ [0,50] = [0,30] | `POSSIBLY-COMPATIBLE` |
| Point in range | `eq 40` | `lteq 50` | [40,40] ⊓ [0,50] = [40,40] | `POSSIBLY-COMPATIBLE` |

---

### 12. Validation Rules

| Rule | Condition | Action |
|------|-----------|--------|
| V1 | rightOperand < 0 | `INVALID` (domain violation) |
| V2 | rightOperand > 100 | `INVALID` (domain violation) |
| V3 | rightOperand not xsd:decimal | `INVALID` (type error) |
| V4 | operator ∈ {isA, hasPart, isPartOf} | `INVALID` (operator error) |

---

### 13. ODRL Turtle Examples

```turtle
# Example 1: Extract at most 50%
ex:c1 a odrl:Constraint ;
    odrl:leftOperand odrl:percentage ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "50"^^xsd:decimal .

# Example 2: Extract at least 10%
ex:c2 a odrl:Constraint ;
    odrl:leftOperand odrl:percentage ;
    odrl:operator odrl:gteq ;
    odrl:rightOperand "10"^^xsd:decimal .

# Example 3: Exactly 25%
ex:c3 a odrl:Constraint ;
    odrl:leftOperand odrl:percentage ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "25"^^xsd:decimal .

# Example 4: One of specific percentages
ex:c4 a odrl:Constraint ;
    odrl:leftOperand odrl:percentage ;
    odrl:operator odrl:isAnyOf ;
    odrl:rightOperand ("10"^^xsd:decimal "25"^^xsd:decimal "50"^^xsd:decimal) .

# Example 5: Logical composition
ex:c5 a odrl:LogicalConstraint ;
    odrl:and (ex:c1 ex:c2) .  # Between 10% and 50%
```

---

### 14. Complete SMT Encoding Example

```smt
; ============================================
; PERCENTAGE CONSTRAINT ANALYSIS
; ============================================

; Variable declaration with domain
(declare-const percentage Real)
(assert (>= percentage 0))
(assert (<= percentage 100))

; ============================================
; EXAMPLE 1: Conflict Detection
; Policy 1: percentage lteq 30
; Policy 2: percentage gteq 50
; ============================================

(push)
(assert (<= percentage 30))  ; P1
(assert (>= percentage 50))  ; P2
(check-sat)  ; Result: UNSAT → CONFLICT
(pop)

; ============================================
; EXAMPLE 2: Compatible
; Policy 1: percentage lteq 50
; Policy 2: percentage gteq 30
; ============================================

(push)
(assert (<= percentage 50))  ; P1
(assert (>= percentage 30))  ; P2
(check-sat)  ; Result: SAT → POSSIBLY-COMPATIBLE
(get-model)  ; Example: percentage = 40
(pop)

; ============================================
; EXAMPLE 3: Logical Composition (AND)
; percentage gteq 10 AND percentage lteq 50
; ============================================

(push)
(assert (and (>= percentage 10) (<= percentage 50)))
(check-sat)  ; Result: SAT
(get-model)  ; Example: percentage = 30
(pop)

; ============================================
; EXAMPLE 4: Logical Composition (XONE)
; xone(percentage lt 25, percentage gt 75)
; ============================================

(push)
(define-fun c1 () Bool (< percentage 25))
(define-fun c2 () Bool (> percentage 75))
(assert (= 1 (+ (ite c1 1 0) (ite c2 1 0))))  ; Exactly one
(check-sat)  ; Result: SAT
(get-model)  ; Example: percentage = 10 or percentage = 80
(pop)
```

---

### 15. Summary Table

| Dimension | Value |
|-----------|-------|
| **LeftOperand** | `odrl:percentage` |
| **Category** | 𝓛_xsd |
| **XSD Type** | xsd:decimal |
| **Domain** | [0, 100] ⊂ ℚ |
| **Valid Operators** | 9/12 (75%) |
| **— Comparison** | 6/6  |
| **— Set** | 3/6 ⚠️ |
| **— Semantic** | 0/3 ❌ |
| **Abstract Domain** | 𝕀_[0,100] (bounded intervals) |
| **SMT Theory** | QF-LRA (decidable) |
| **Static Analyzability** |  Full |
| **Unit** | ❌ Not applicable |
| **Scope** | ❌ None |
| **Reference Point** | ❌ None |
| **Comparability** | Always (same LeftOperand) |
| **ODRL Status** | Non-Normative |

---

### 16. Formal Theorems for `percentage`

**Theorem 1 (Soundness):**
$$\text{judge}(c_1, c_2) = \texttt{CONFLICT} \implies \nexists w \in \mathcal{W}: \llbracket c_1 \rrbracket(w) = \mathbf{T} \land \llbracket c_2 \rrbracket(w) = \mathbf{T}$$

**Theorem 2 (Decidability):**
$$\forall c_1, c_2 \in \mathcal{C}_{\text{percentage}}: \text{judge}(c_1, c_2) \text{ is decidable}$$

**Theorem 3 (Completeness for Comparison Operators):**
For constraints using only comparison operators (eq, neq, lt, lteq, gt, gteq):
$$\text{judge}(c_1, c_2) = \texttt{POSSIBLY-COMPATIBLE} \implies \exists w \in \mathcal{W}: \llbracket c_1 \rrbracket(w) = \mathbf{T} \land \llbracket c_2 \rrbracket(w) = \mathbf{T}$$

**Theorem 4 (Domain Closure):**
$$\forall c \in \mathcal{C}_{\text{percentage}}: \llbracket c \rrbracket^\# \sqsubseteq [0, 100]$$

---

### 17. Paper Statement

> The `odrl:percentage` LeftOperand is classified as 𝓛_xsd with a bounded domain [0, 100]. All comparison and set-membership operators are valid, yielding 9/12 operator coverage. The abstract domain is the interval lattice 𝕀_[0,100], enabling sound and complete conflict detection via QF-LRA satisfiability. No unit, scope, or external knowledge is required, making `percentage` fully self-contained and statically analyzable.

## Key Insight for Paper

> **For `odrl:percentage` ∈ 𝓛_xsd with closed domain [0,100]:**
> - Comparability always holds (no unit, scope, or reference)
> - `UNKNOWN` is **unreachable**
> - Judgment ∈ {`CONFLICT`, `POSSIBLY-COMPATIBLE`}
> - Decidable via QF-LRA

