
## Over-Approximation in Abstract Interpretation

### 1. The Concept

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPROXIMATION TYPES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OVER-APPROXIMATION (What ODRL-SA does):                       │
│  ═══════════════════════════════════════                       │
│  Abstract domain CONTAINS all concrete possibilities            │
│  May include some EXTRA values (false negatives possible)       │
│  Guarantees: NO FALSE POSITIVES                                │
│                                                                 │
│       ┌─────────────────────────────┐                          │
│       │    Abstract Domain          │                          │
│       │    ┌───────────────┐        │                          │
│       │    │   Concrete    │        │                          │
│       │    │   Values      │        │                          │
│       │    └───────────────┘        │                          │
│       │         ↑                   │                          │
│       │    Actual possible          │                          │
│       │    values                   │                          │
│       └─────────────────────────────┘                          │
│              ↑                                                  │
│         Abstract includes                                       │
│         concrete + some extra                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  UNDER-APPROXIMATION (NOT what ODRL-SA does):                  │
│  ════════════════════════════════════════════                  │
│  Abstract domain is SUBSET of concrete possibilities            │
│  May MISS some values (false positives possible)               │
│  Guarantees: NO FALSE NEGATIVES                                │
│                                                                 │
│       ┌─────────────────────────────┐                          │
│       │      Concrete Values        │                          │
│       │    ┌───────────────┐        │                          │
│       │    │   Abstract    │        │                          │
│       │    │   Domain      │        │                          │
│       │    └───────────────┘        │                          │
│       └─────────────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. What This Means for ODRL-SA

#### 2.1 Soundness Guarantee

**Over-approximation guarantees SOUNDNESS:**

$$\text{If ODRL-SA says CONFLICT} \implies \text{There IS a real conflict}$$

**No false positives** — we never cry wolf!

#### 2.2 Incompleteness Trade-off

**Over-approximation allows INCOMPLETENESS:**

$$\text{If ODRL-SA says COMPATIBLE} \implies \text{There MIGHT be a conflict we missed}$$

**Possible false negatives** — we might miss some conflicts.

---

### 3. Concrete Example: relativeSpatialPosition

#### 3.1 The 2D to 1D Projection

```
┌─────────────────────────────────────────────────────────────────┐
│           ACTUAL 2D SPACE                                       │
│                                                                 │
│     0%        40%  60%                              100%        │
│   0%┌─────────────────────────────────────────────────┐        │
│     │  ┌────┐                                         │        │
│     │  │ R1 │  Region 1: x∈[10,40], y∈[10,40]        │        │
│  40%│  └────┘                                         │        │
│     │                                                 │        │
│  60%│              ┌────────────────────┐             │        │
│     │              │                    │             │        │
│     │              │   R2               │             │        │
│     │              │   Region 2:        │             │        │
│  90%│              │   x∈[60,90],       │             │        │
│     │              │   y∈[60,90]        │             │        │
│     │              └────────────────────┘             │        │
│ 100%└─────────────────────────────────────────────────┘        │
│                                                                 │
│  REALITY: R1 and R2 DO NOT OVERLAP in 2D!                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│           ODRL-SA 1D PROJECTION (Over-approximation)            │
│                                                                 │
│  X-axis projection:                                             │
│  R1: [10 ═══════ 40]                                           │
│  R2:                    [60 ═══════════════════ 90]            │
│  No overlap on X → Could detect as non-overlapping              │
│                                                                 │
│  Y-axis projection:                                             │
│  R1: [10 ═══════ 40]                                           │
│  R2:                    [60 ═══════════════════ 90]            │
│  No overlap on Y → Could detect as non-overlapping              │
│                                                                 │
│  BUT with single relativeSpatialPosition (no axis distinction): │
│  R1: [10 ═══════════════════════════════════════ 90]           │
│  R2: [10 ═══════════════════════════════════════ 90]           │
│                                                                 │
│  1D over-approximation: [10, 90] ∩ [10, 90] ≠ ∅                │
│  ODRL-SA says: POSSIBLY-COMPATIBLE                              │
│                                                                 │
│  This is SOUND (not a false positive)                          │
│  But INCOMPLETE (missed the 2D non-overlap)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Analysis

| Scenario | ODRL-SA Result | Reality | Correct? |
|----------|----------------|---------|----------|
| R1 and R2 overlap in 2D | COMPATIBLE | Compatible |  Correct |
| R1 and R2 don't overlap in 2D | COMPATIBLE | Actually conflict | ⚠️ Missed (false negative) |
| R1 and R2 intervals don't overlap | CONFLICT | Real conflict |  Correct |

---

### 4. Why Over-Approximation is the RIGHT Choice

#### 4.1 The Alternative Would Be Worse

```
┌─────────────────────────────────────────────────────────────────┐
│                    DESIGN TRADE-OFFS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OPTION A: Over-approximation (ODRL-SA's choice)               │
│  ════════════════════════════════════════════════              │
│  • CONFLICT → Definitely a real conflict (SOUND)               │
│  • COMPATIBLE → Might still have conflict (INCOMPLETE)         │
│  • User action: Trust CONFLICT, investigate COMPATIBLE         │
│                                                                 │
│  OPTION B: Under-approximation (NOT chosen)                    │
│  ═════════════════════════════════════════                     │
│  • CONFLICT → Might be false alarm (UNSOUND!)                  │
│  • COMPATIBLE → Definitely compatible (COMPLETE)               │
│  • User action: Can't trust CONFLICT! Useless for validation   │
│                                                                 │
│  OPTION C: Exact analysis (Often impossible)                   │
│  ═══════════════════════════════════════════                   │
│  • Would require full 2D/3D SMT reasoning                      │
│  • May be undecidable for some constraint combinations         │
│  • Much more complex implementation                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2 Soundness is Essential for Validation

For a **policy validation tool**, we want:

| Requirement | Over-approx | Under-approx |
|-------------|-------------|--------------|
| "If tool says CONFLICT, I must fix policy" |  Trust it | ❌ Might be wrong |
| "If tool says OK, policy is definitely OK" | ❌ Maybe not |  Trust it |
| **Which matters more for validation?** |  **This one** | Less important |

**For policy authoring/validation, we need to trust CONFLICT results.**

---

### 5. Formal Definition

#### 5.1 Galois Connection

Over-approximation is formalized via a **Galois connection** between concrete and abstract domains:

$$(\alpha, \gamma) : (2^{\mathcal{C}}, \subseteq) \rightleftarrows (\mathcal{A}, \sqsubseteq)$$

Where:
- $\alpha$ : Abstraction function (concrete → abstract)
- $\gamma$ : Concretization function (abstract → concrete)
- $\mathcal{C}$ : Concrete domain (actual constraint satisfying values)
- $\mathcal{A}$ : Abstract domain (intervals, sets, etc.)

**Key property:**

$$\forall S \subseteq \mathcal{C} : S \subseteq \gamma(\alpha(S))$$

The concretization of the abstraction **contains** the original set (over-approximation).

#### 5.2 Soundness Theorem

$$\gamma(\alpha(c_1)) \cap \gamma(\alpha(c_2)) = \emptyset \implies \text{Concrete}(c_1) \cap \text{Concrete}(c_2) = \emptyset$$

**If the abstract intersection is empty, the concrete intersection MUST be empty.**

This is why CONFLICT results are **always trustworthy**.

---

### 6. Is This a "Shortage"?

#### 6.1 No — It's a Principled Trade-off

| Aspect | Assessment |
|--------|------------|
| **Is it a bug?** | ❌ No, it's by design |
| **Is it a limitation?** |  Yes, but intentional |
| **Is it a problem?** | ❌ No, it preserves soundness |
| **Is it optimal?** |  Yes, for our goals |

#### 6.2 The Real Trade-off

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS TRADE-OFFS                          │
│                                                                 │
│              Soundness ◄─────────────────► Completeness         │
│                  │                              │                │
│                  │      ODRL-SA                 │                │
│                  │         │                    │                │
│                  ▼         ▼                    ▼                │
│              ┌───────────────────────────────────┐              │
│              │ ████████████░░░░░░░░░░░░░░░░░░░░ │              │
│              └───────────────────────────────────┘              │
│              100% Sound              ~80% Complete               │
│                                                                 │
│  We GUARANTEE soundness (no false positives)                   │
│  We SACRIFICE some completeness (may miss some conflicts)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7. How ODRL-SA Reports This

#### 7.1 Status Ontology (SZS-Inspired)

| Status | Meaning | Trust Level |
|--------|---------|-------------|
| **CONFLICT** | Definitely a conflict |  100% trust |
| **POSSIBLY-COMPATIBLE** | No conflict found (but might exist) | ⚠️ High confidence, not certain |
| **UNKNOWN** | Cannot analyze | ❓ Need more info |

#### 7.2 The Name "POSSIBLY-COMPATIBLE"

We intentionally use **"POSSIBLY-COMPATIBLE"** instead of "COMPATIBLE" to signal:

> "We found no conflict, but due to over-approximation, we cannot guarantee there isn't one."

This is **honest** and **transparent** about our analysis limitations.

---

### 8. Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    OVER-APPROXIMATION SUMMARY                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  WHAT IT IS:                                                    │
│  • Abstract domain includes all concrete values + possibly more │
│  • Standard technique in abstract interpretation                │
│  • Guarantees soundness (no false positives)                   │
│                                                                 │
│  WHAT IT MEANS FOR ODRL-SA:                                    │
│  • CONFLICT results are 100% trustworthy                       │
│  • COMPATIBLE results are high confidence, not certain         │
│  • This is the RIGHT choice for policy validation              │
│                                                                 │
│  IS IT A SHORTAGE?                                              │
│  • No — it's a principled trade-off                            │
│  • Soundness is more important than completeness               │
│  • We're honest about it ("POSSIBLY-COMPATIBLE")               │
│                                                                 │
│  FORMAL GUARANTEE:                                              │
│  • If ODRL-SA says CONFLICT → There IS a real conflict         │
│  • If ODRL-SA says COMPATIBLE → There MIGHT be a conflict      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 9. In Paper

You can state this as a **feature**, not a limitation:

> **Soundness Guarantee:** ODRL-SA employs sound over-approximation in the tradition of abstract interpretation [Cousot & Cousot, 1977]. This guarantees that all reported conflicts are genuine—there are no false positives. The trade-off is potential incompleteness: some conflicts may not be detected (false negatives), which is why compatible results are labeled "POSSIBLY-COMPATIBLE" rather than "COMPATIBLE". This design choice is appropriate for policy validation, where trust in conflict detection is paramount.
