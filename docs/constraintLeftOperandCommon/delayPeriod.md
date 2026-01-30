## delayPeriod - Deep Semantic Analysis

### 1. ODRL Definition

```turtle
:delayPeriod
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Delay Period"@en ;
    skos:definition "A time delay period prior to exercising the action of the Rule. 
                     The point in time triggering this period MAY be defined by another 
                     temporal Constraint combined by a Logical Constraint (utilising 
                     the odrl:andSequence operand). Right operand value MUST be an 
                     xsd:duration as defined by [[xmlschema11-2]]."@en ;
    skos:note "Only the eq, gt, gteq operators SHOULD be used. 
               <br />Example: delayPeriod eq P60M indicates a delay of 60 Minutes 
               before exercising the action."@en ;
    skos:scopeNote "Non-Normative"@en .
```

> ⚠️ **Note:** Again, `P60M` = 60 **Months**, not 60 Minutes. Should be `PT60M`.

---

### 2. What Does delayPeriod Actually Mean?

#### 2.1 Core Semantics

```
"A time delay period PRIOR TO exercising the action"
```

This means: **You must WAIT this long before you can perform the action.**

| Concept | Meaning |
|---------|---------|
| **Delay** | Waiting period, embargo, cool-down |
| **Prior to** | Before action is allowed |
| **Triggering point** | When does the delay start? |

#### 2.2 Semantic Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        TIME AXIS                                │
│                                                                 │
│  [Trigger Point]════ DELAY PERIOD ════►[Action Allowed]         │
│        t₀              (wait)              t₀ + d               │
│        │                                      │                 │
│        │◄──────── delayPeriod = d ───────────►│                 │
│        │                                      │                 │
│   ❌ Action                              ✅ Action              │
│   NOT allowed                              allowed              │
│                                                                 │
│  Constraint: delayPeriod gteq PT60M                            │
│  Meaning: Must wait AT LEAST 60 minutes before action          │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3 Key Insight: delayPeriod vs elapsedTime

| Aspect | elapsedTime | delayPeriod |
|--------|-------------|-------------|
| **Semantics** | Duration FOR which action is valid | Duration BEFORE action is allowed |
| **Window** | Action valid DURING this time | Action valid AFTER this time |
| **Typical use** | "Valid for 30 days" | "Embargo for 30 days" |
| **Operators** | lteq (upper bound) | gteq (lower bound) |

```
elapsedTime lteq 30D:
[Reference]═══════════════════════►
           ✅ Action allowed        ❌ After 30 days

delayPeriod gteq 30D:
[Trigger]══════════════════════════►
          ❌ Must wait              ✅ After 30 days
```

**They are COMPLEMENTARY temporal constraints!**

---

### 3. The Trigger Point Problem

#### 3.1 What ODRL Says

```
"The point in time triggering this period MAY be defined by another 
temporal Constraint combined by a Logical Constraint (utilising the 
odrl:andSequence operand)."
```

This is **more explicit** than `elapsedTime`! ODRL suggests using `andSequence` to define the trigger.

#### 3.2 Trigger Point Options

| Trigger | Example | Meaning |
|---------|---------|---------|
| **Policy assignment** | Implicit | Wait from when policy is assigned |
| **Asset creation** | `dateTime eq 2025-01-01` | Wait from asset creation date |
| **Event occurrence** | `event eq publication` | Wait from publication event |
| **Another constraint** | Via `andSequence` | Chained temporal logic |

#### 3.3 andSequence Pattern

```turtle
# "Wait 30 days after publication before allowing distribution"
ex:constraint_sequence a odrl:LogicalConstraint ;
    odrl:andSequence (
        [ odrl:leftOperand odrl:event ;
          odrl:operator odrl:eq ;
          odrl:rightOperand ex:publication ]
        [ odrl:leftOperand odrl:delayPeriod ;
          odrl:operator odrl:gteq ;
          odrl:rightOperand "P30D"^^xsd:duration ]
    ) .
```

**Semantics:** 
1. First, the publication event must occur
2. Then, wait 30 days
3. Only then, action is permitted

---

### 4. Operator Analysis

#### 4.1 Recommended Operators

ODRL says: **"Only the eq, gt, gteq operators SHOULD be used"**

| Operator | Meaning | Use Case |
|----------|---------|----------|
| `eq` | Exactly this delay | "Wait exactly 30 days" |
| `gt` | More than this delay | "Wait more than 30 days" |
| `gteq` | At least this delay | "Wait at least 30 days" (most common) |

#### 4.2 Why NOT lt, lteq?

Think about it semantically:

```
delayPeriod lteq PT30M
= "The delay must be at most 30 minutes"
= "You must act WITHIN 30 minutes of trigger"
```

This is **strange** — it's an upper bound on waiting, which means:
- You CAN'T wait too long
- You MUST act soon after trigger

This is semantically closer to a **deadline** than a **delay**!

**But it's not invalid** — just unusual and potentially confusing.

#### 4.3 Full Operator Semantics

| Operator | Constraint | Action Allowed When |
|----------|------------|---------------------|
| `gteq d` | Wait at least d | `t ≥ t₀ + d` |
| `gt d` | Wait more than d | `t > t₀ + d` |
| `eq d` | Wait exactly d | `t = t₀ + d` |
| `lteq d` | Wait at most d | `t₀ ≤ t ≤ t₀ + d` |
| `lt d` | Wait less than d | `t₀ ≤ t < t₀ + d` |
| `neq d` | Wait any time except d | `t ≠ t₀ + d` |

---

### 5. Conflict Analysis

#### 5.1 When Do Conflicts Occur?

**Same principle as elapsedTime:** Conflicts occur when the intersection of allowed time intervals is empty.

But there's a **key difference** in interpretation:

| elapsedTime | delayPeriod |
|-------------|-------------|
| Constrains the **duration** of validity | Constrains the **start** of validity |
| Window: `[t₀, t₀ + d]` | Window: `[t₀ + d, ∞)` |

#### 5.2 Pure Duration Conflicts

**Same as elapsedTime** — if delay constraints are contradictory:

| Constraint 1 | Constraint 2 | Analysis | Result |
|--------------|--------------|----------|--------|
| `gteq 60M` | `lteq 30M` | [60, ∞) ∩ (0, 30] = ∅ | **CONFLICT** |
| `eq 30M` | `eq 60M` | {30} ∩ {60} = ∅ | **CONFLICT** |
| `gt 60M` | `lteq 60M` | (60, ∞) ∩ (0, 60] = ∅ | **CONFLICT** |
| `gteq 30M` | `lteq 60M` | [30, ∞) ∩ (0, 60] = [30, 60] | COMPATIBLE |

```
Duration Axis (minutes):  0 ────────────────────────────────────► ∞

CONFLICT: gteq 60M ∧ lteq 30M
┌────────────────────────────────────────────────────────────────┐
│  gteq 60M:                        [60 ════════════════════════►│
│  lteq 30M:    (0 ═══════ 30]                                   │
│  Intersection: ∅                                               │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘

COMPATIBLE: gteq 30M ∧ lteq 60M
┌────────────────────────────────────────────────────────────────┐
│  gteq 30M:              [30 ══════════════════════════════════►│
│  lteq 60M:    (0 ════════════════ 60]                          │
│  Intersection:          [30 ══════ 60]                         │
│  Result: COMPATIBLE ✅                                          │
└────────────────────────────────────────────────────────────────┘
```

#### 5.3 delayPeriod vs elapsedTime Interaction

**This is interesting!** What if a policy has BOTH?

```turtle
ex:policy a odrl:Set ;
    odrl:permission [
        odrl:action odrl:distribute ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:delayPeriod ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "P30D"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "P60D"^^xsd:duration ]
            )
        ]
    ] .
```

**Interpretation:**
- delayPeriod gteq P30D: "Wait at least 30 days after trigger"
- elapsedTime lteq P60D: "Valid for at most 60 days from reference"

**Question:** Are these conflicting?

**It depends on the reference points!**

```
Case 1: Same reference point (t₀ = trigger)
┌────────────────────────────────────────────────────────────────┐
│  Timeline:   t₀ ──────────────────────────────────────────►    │
│              │                                                 │
│  delayPeriod gteq 30D:        ❌ wait ❌       ✅ allowed ✅    │
│                          [0 ════════ 30) [30 ════════════►     │
│                                                                │
│  elapsedTime lteq 60D:        ✅ valid ✅           ❌ expired  │
│                          [0 ══════════════════ 60]             │
│                                                                │
│  Combined:                              ✅ valid window ✅      │
│                                    [30 ══════════ 60]          │
│                                                                │
│  Result: COMPATIBLE (30-day window exists)                     │
└────────────────────────────────────────────────────────────────┘

Case 2: delayPeriod > elapsedTime (same reference)
┌────────────────────────────────────────────────────────────────┐
│  delayPeriod gteq 60D:                    [60 ════════════►    │
│  elapsedTime lteq 30D:    [0 ══════ 30]                        │
│                                                                │
│  Combined: ∅ (must wait 60 days, but expires in 30)            │
│                                                                │
│  Result: CONFLICT ❌                                            │
└────────────────────────────────────────────────────────────────┘
```

#### 5.4 Deontic Conflicts with delayPeriod

**Scenario: Permission with delay vs Immediate Prohibition**

```turtle
ex:policy a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:delayPeriod ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "P30D"^^xsd:duration
        ]
    ] ;
    odrl:prohibition [
        odrl:action odrl:use ;
        # No temporal constraint = always prohibited
    ] .
```

**Analysis:**
- Permission: Use allowed AFTER 30 days
- Prohibition: Use NEVER allowed (no constraint = always applies)
- **Result: CONFLICT** — prohibition always blocks permission

**Scenario: Permission delay vs Prohibition delay**

```turtle
ex:policy a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:delayPeriod ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "P60D"^^xsd:duration
        ]
    ] ;
    odrl:prohibition [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:delayPeriod ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "P90D"^^xsd:duration
        ]
    ] .
```

**Analysis:**
- Permission: Use allowed AFTER 60 days → window [60, ∞)
- Prohibition: Use prohibited if delay ≤ 90 days → prohibited during [0, 90]
- Overlap: [60, 90] — both permission and prohibition apply!
- **Result: DEONTIC CONFLICT**

```
┌────────────────────────────────────────────────────────────────┐
│  Timeline (days):  0 ────── 60 ────── 90 ────────────────►     │
│                                                                │
│  Permission (gteq 60D):          [60 ════════════════════►     │
│                           (allowed after 60 days)              │
│                                                                │
│  Prohibition (lteq 90D):   [0 ═══════════════ 90]              │
│                           (prohibited until 90 days)           │
│                                                                │
│  Overlap:                        [60 ════ 90]                  │
│                                                                │
│  Result: DEONTIC CONFLICT ❌                                    │
│  Witness: day 75 (permitted AND prohibited)                    │
└────────────────────────────────────────────────────────────────┘
```

---

### 6. Domain Specification

$$\text{dom}(\texttt{delayPeriod}) = \mathbb{R}_{\geq 0} = [0, +\infty)$$

**Wait — should zero be valid?**

| Value | Meaning | Valid? |
|-------|---------|--------|
| `delayPeriod eq 0` | "No delay required" | ✅ Yes (immediate) |
| `delayPeriod gteq 0` | "Wait at least 0" | ✅ Yes (trivially satisfied) |

**Unlike elapsedTime**, zero delay IS meaningful:
- `delayPeriod eq 0` = "Action allowed immediately"
- This is semantically valid (no waiting required)

**But is it useful?** Not really — if no delay is required, why have the constraint?

**ODRL-SA Decision:**

$$\text{dom}(\texttt{delayPeriod}) = \mathbb{R}_{\geq 0} = [0, +\infty)$$

Include zero for completeness, but flag as potentially meaningless.

---

### 7. Formal Semantic Model

#### 7.1 Constraint Semantics

Let:
- $t_0$ = trigger point (event, date, implicit)
- $d$ = delay duration
- $t$ = current time

**Action allowed at time $t$ iff:**

| Constraint | Condition |
|------------|-----------|
| `delayPeriod eq d` | $t = t_0 + d$ |
| `delayPeriod gt d` | $t > t_0 + d$ |
| `delayPeriod gteq d` | $t \geq t_0 + d$ |
| `delayPeriod lt d` | $t_0 \leq t < t_0 + d$ |
| `delayPeriod lteq d` | $t_0 \leq t \leq t_0 + d$ |
| `delayPeriod neq d` | $t \neq t_0 + d$ |

#### 7.2 Abstraction for Static Analysis

For static analysis (without knowing $t_0$), we abstract to **delay duration intervals**:

$$\alpha(\texttt{delayPeriod } op \; d) = \begin{cases}
\{d\} & \text{if } op = \texttt{eq} \\
(d, +\infty) & \text{if } op = \texttt{gt} \\
[d, +\infty) & \text{if } op = \texttt{gteq} \\
[0, d) & \text{if } op = \texttt{lt} \\
[0, d] & \text{if } op = \texttt{lteq} \\
[0, +\infty) \setminus \{d\} & \text{if } op = \texttt{neq}
\end{cases}$$

**Note:** Domain starts at 0, not (0, ∞) like elapsedTime!

---

### 8. Comparison: elapsedTime vs delayPeriod

| Aspect | elapsedTime | delayPeriod |
|--------|-------------|-------------|
| **Semantics** | Duration of validity | Waiting period before action |
| **Domain** | $(0, +\infty)$ | $[0, +\infty)$ |
| **Zero valid?** | ❌ No | ✅ Yes (no delay) |
| **Typical operator** | `lteq` (upper bound) | `gteq` (lower bound) |
| **Recommended ops** | eq, lt, lteq | eq, gt, gteq |
| **Trigger** | Implicit reference | MAY be explicit via andSequence |
| **Window** | $[t_0, t_0 + d]$ | $[t_0 + d, +\infty)$ |

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPLEMENTARY SEMANTICS                                        │
│                                                                 │
│  elapsedTime lteq D:                                           │
│  [t₀]═══════════════════►[t₀+D]                                │
│       ✅ valid window        ❌ expired                         │
│                                                                 │
│  delayPeriod gteq D:                                           │
│  [t₀]═══════════════════►[t₀+D]════════════════════►           │
│       ❌ must wait           ✅ allowed                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 9. Analysis Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                ODRL-SA delayPeriod Analysis                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PHASE 1: Pure Duration Analysis (ALWAYS)                 │  │
│  │  ─────────────────────────────────────────                │  │
│  │  • Detects: Delay interval impossibilities                │  │
│  │  • Domain: x ≥ 0 (zero allowed)                          │  │
│  │  • Method: SMT interval intersection                      │  │
│  │  • Sound: ✅  Complete: ✅                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PHASE 2: Temporal Interaction Analysis (CONDITIONAL)     │  │
│  │  ─────────────────────────────────────────                │  │
│  │  • Detects: delayPeriod vs elapsedTime conflicts          │  │
│  │  • Requires: Same reference point assumption              │  │
│  │  • Method: Window intersection                            │  │
│  │  • Sound: ✅  Complete: Conditional                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PHASE 3: Deontic Conflict Analysis                       │  │
│  │  ─────────────────────────────────────────                │  │
│  │  • Detects: Permission ∩ Prohibition ≠ ∅                  │  │
│  │  • Method: Check overlap of delay windows                 │  │
│  │  • Sound: ✅  Complete: ✅                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 10. Conflict Patterns Summary

#### 10.1 Pure Delay Conflicts

| Pattern | Example | Interval Analysis | Result |
|---------|---------|-------------------|--------|
| Impossible range | `gteq 60M ∧ lteq 30M` | [60,∞) ∩ [0,30] = ∅ | CONFLICT |
| Contradictory eq | `eq 30M ∧ eq 60M` | {30} ∩ {60} = ∅ | CONFLICT |
| Point outside | `eq 60M ∧ lt 60M` | {60} ∩ [0,60) = ∅ | CONFLICT |
| Valid window | `gteq 30M ∧ lteq 60M` | [30,∞) ∩ [0,60] = [30,60] | COMPATIBLE |

#### 10.2 Delay vs Elapsed Conflicts

| delayPeriod | elapsedTime | Same ref? | Analysis | Result |
|-------------|-------------|-----------|----------|--------|
| `gteq 30D` | `lteq 60D` | ✅ | [30,∞) ∩ [0,60] = [30,60] | COMPATIBLE |
| `gteq 60D` | `lteq 30D` | ✅ | [60,∞) ∩ [0,30] = ∅ | CONFLICT |
| `gteq 30D` | `lteq 60D` | ❌ | Unknown reference | UNKNOWN |

#### 10.3 Deontic Conflicts

| Permission | Prohibition | Analysis | Result |
|------------|-------------|----------|--------|
| `delay gteq 60D` | `delay lteq 90D` | [60,∞) ∩ [0,90] = [60,90] | DEONTIC CONFLICT |
| `delay gteq 60D` | `delay lt 60D` | [60,∞) ∩ [0,60) = ∅ | NO CONFLICT |
| `delay gteq 60D` | (no constraint) | [60,∞) ∩ [0,∞) = [60,∞) | DEONTIC CONFLICT |

---

### 11. Quick Reference Card

| Property | Value |
|----------|-------|
| **Semantics** | Waiting period before action is allowed |
| **Domain** | $[0, +\infty)$ seconds |
| **Zero valid?** | ✅ Yes (no delay = immediate) |
| **Value Type** | `xsd:duration` (ISO 8601) |
| **Operators (Recommended)** | `eq`, `gt`, `gteq` |
| **Operators (Valid)** | `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` |
| **Typical pattern** | `gteq` (minimum wait) |
| **Trigger point** | MAY be defined via `andSequence` |
| **Category** | $\mathcal{L}_{\text{duration}}$ |
| **SMT Theory** | QF_LRA |
| **Decidable** | ✅ Yes |

---

### 12. Key Insights

#### Insight 1: Complementary to elapsedTime
- `elapsedTime`: Upper bound on validity duration
- `delayPeriod`: Lower bound on when action starts

#### Insight 2: Zero is Valid
- `delayPeriod eq 0` = "No delay required" (immediate action)
- Unlike `elapsedTime` where zero is meaningless

#### Insight 3: Trigger Point is More Explicit
- ODRL suggests using `andSequence` to define trigger
- More compositional than `elapsedTime`

#### Insight 4: Typical Operators are Inverted
- `elapsedTime` typically uses `lteq` (at most this long)
- `delayPeriod` typically uses `gteq` (wait at least this long)

#### Insight 5: Cross-Constraint Conflicts
- `delayPeriod gteq D₁` + `elapsedTime lteq D₂` where D₁ > D₂ = CONFLICT
- "Must wait longer than validity period" = impossible

---

### 13. Recommended Implementation

```python
"delayPeriod": {
    "class": "FULL",
    "category": "L_duration",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": True,   # x >= 0 (zero allowed!)
        "inclusive_max": None
    },
    "value_type": "xsd:duration",
    "operators": {
        "recommended": ["eq", "gt", "gteq"],
        "valid": ["eq", "neq", "lt", "lteq", "gt", "gteq"]
    },
    "trigger": {
        "mechanism": "andSequence",
        "implicit_allowed": True
    },
    "relation_to": {
        "elapsedTime": "complementary",
        "dateTime": "can_define_trigger"
    },
    "external_kb": False,
    "decidable": True,
    "smt_theory": "QF_LRA"
}
```

---
