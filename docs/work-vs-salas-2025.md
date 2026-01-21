

## What Salas et al. (2025) Does

| Aspect | Their Approach |
|--------|----------------|
| **Core Problem** | Policy **evaluation** against a state of the world (events) |
| **Formalism** | First-order logic queries on event relations |
| **State Model** | Events as tuples: `<timestamp, action, actor, asset, ...>` |
| **Semantics** | Query answering (SQL/SPARQL) |
| **Comparison** | Query containment: `p ⊑ p'` iff `∀ω: p(ω) → p'(ω)` |
| **Scope** | Runtime evaluation + policy comparison |

**Key insight**: They model policies as **queries** and states as **database relations**.

---

## What You Did

| Aspect | Our Approach |
|--------|----------------|
| **Core Problem** | **Constraint-level conflict detection** (static analysis) |
| **Formalism** | SMT solving (Z3) on constraint formulas |
| **State Model** | Symbolic variables (count, time, etc.) - no concrete events |
| **Semantics** | Satisfiability checking |
| **Comparison** | Inheritance: `SAT(child ∧ ¬parent)` = violation |
| **Scope** | Static constraint analysis (no runtime) |

**Key insight**: We analyze **policy structure**, not runtime behavior.

---

## 📐 Key Theoretical Difference

### Salas et al.: **Runtime Evaluation Semantics**
```
Given: Policy P, State ω (set of events)
Question: Is ω valid wrt P?
Method: Query answering
```

### Our Work: **Static Constraint Semantics**
```
Given: Policies P_parent, P_child
Question: Does child violate inheritance?
Method: SAT(child ∧ ¬parent)
```

---

## 🔄 How They Relate (Important!)

```
┌─────────────────────────────────────────────────────────────┐
│                    ODRL Policy Analysis                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐    │
│  │  Our WORK          │    │  SALAS ET AL.           │    │
│  │  (Static Analysis)  │    │  (Runtime Evaluation)   │    │
│  ├─────────────────────┤    ├─────────────────────────┤    │
│  │ • Constraint logic  │    │ • Event matching        │    │
│  │ • SMT satisfiability│    │ • Query answering       │    │
│  │ • Inheritance check │    │ • Violation detection   │    │
│  │ • No runtime state  │    │ • Concrete state ω      │    │
│  └──────────┬──────────┘    └───────────┬─────────────┘    │
│             │                           │                   │
│             └───────────┬───────────────┘                   │
│                         │                                   │
│                         ▼                                   │
│            ┌─────────────────────────┐                      │
│            │  COMPLEMENTARY!         │                      │
│            │  Static → Design-time   │                      │
│            │  Runtime → Enforcement  │                      │
│            └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

##  What You Already Have (Strong Position)

| Feature | Status | Notes |
|---------|--------|-------|
| Constraint encoding |  | Z3 formulas |
| Logical operators |  | AND, OR, XONE |
| Inheritance checking |  | `SAT(child ∧ ¬parent)` |
| Conflict detection |  | 12+ types |
| Counterexamples |  | Z3 models |
| Canonical forms |  | Normalization |

---

## 🚀 What You Should Do (Recommendations)

### Option A: **Position as Complementary** (Recommended for Paper)

Frame Our work as **static analysis** that complements runtime evaluation:

```markdown
> "While Salas et al. (2025) address runtime policy evaluation against 
> concrete states, we focus on static constraint-level analysis that 
> detects inheritance violations at design-time, before deployment."
```

**Benefits**:
- Clear scope differentiation
- No need to implement their approach
- Strong standalone contribution

---

### Option B: **Add Policy Comparison Semantics** (Extension)

Adopt their **asymmetric comparison** concept:

```python
def check_policy_containment(policy_a, policy_b) -> bool:
    """
    Check: p_a ⊑ p_b (a contained in b)
    
    Salas et al. Definition:
    p ⊑ p' iff ∀ω: p(ω) → p'(ω)
    
    SMT Translation:
    p ⊑ p' iff UNSAT(p ∧ ¬p')
    """
    formula_a = encode(policy_a)
    formula_b = encode(policy_b)
    
    # Check if a allows anything b forbids
    solver = Solver()
    solver.add(formula_a)
    solver.add(Not(formula_b))
    
    return solver.check() == unsat  # a ⊑ b iff unsat
```

This is **exactly what Our inheritance checker already does!**

---

### Option C: **Map Their Comparison Types to Ours**

| Salas et al. | Our Implementation |
|--------------|---------------------|
| `p ≡ p'` (equivalence) | No violations + no redundancy |
| `p ⊑ p'` (containment) | Valid inheritance (child ⊆ parent) |
| `p ̸⊑ p'` (asymmetric conflict) | **Expansion violation** |
| `p ̸≡ p'` (symmetric conflict) | Any difference |

**You already implement their core comparison!**

---

## 📝 For Our Paper: Related Work Section

```markdown
## Related Work

### Runtime Evaluation Semantics
Salas et al. (2025) propose a formal semantics for ODRL based on query 
answering, modeling policy evaluation as first-order queries over event 
relations. Their approach addresses runtime violation detection given 
concrete states of the world.

### Our Contribution: Static Constraint Analysis
In contrast, our work focuses on **static analysis** of ODRL policies 
at the constraint level. We detect:

1. **Inheritance violations**: When child policies expand parent constraints
2. **Internal inconsistencies**: Unsatisfiable constraint combinations
3. **XONE conflicts**: Overlapping exclusive-or branches

Our approach complements runtime evaluation by identifying structural 
problems at design-time, before policies are deployed.

### Key Difference
| Aspect | Salas et al. | Our Work |
|--------|--------------|----------|
| Input | Policy + State ω | Policy pair |
| Question | Is ω valid? | Is child valid? |
| Method | Query answering | SAT solving |
| Time | Runtime | Design-time |

### Alignment
Our inheritance check `SAT(child ∧ ¬parent)` corresponds to their 
asymmetric conflict detection `p ̸⊑ p'`, validating our theoretical 
foundation while maintaining focus on static analysis.
```

---

## 🎯 Final Recommendation

**Don't change Our implementation.** Our work is:

1.  **Theoretically sound** (matches their containment definition)
2.  **Complementary** (static vs runtime)
3.  **Well-scoped** (constraint-level, not enforcement)
4.  **Publishable** as standalone contribution

**Add to paper**:
- Cite Salas et al. in Related Work
- Explicitly state Our scope is "static constraint analysis"
- Note that Our inheritance check `SAT(child ∧ ¬parent)` aligns with their asymmetric conflict `p ̸⊑ p'`

This positions Our work as a **design-time complement** to their **runtime approach**. 