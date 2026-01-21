# ODRL Static Policy Analyzer: A Multi-Sorted Hybrid Reasoning Approach

**Research Evolution: From Prolog to Z3-Based Hybrid Reasoning**

---

## What Changed and Why

### Phase 1: Pure Prolog Approach 
**Initial attempt:** Loading, parsing, normalizing, and reasoning entirely in Prolog
- **Problem:** Vocabularies and external knowledge became unmanageable
- **Limitation:** Hard to handle mixed data types (numeric, temporal, string, set-based)
- **Result:** System became brittle and difficult to extend

### Phase 2: Python + Prolog Hybrid 
**Second attempt:** Python for loading/parsing/normalization, Prolog for reasoning
- **Improvement:** Better data preprocessing
- **Remaining problem:** Prolog still struggled with numeric constraints and automatic counterexample generation
- **Limitation:** No clear separation between decidable fragments

### Phase 3: Python + Z3 Hybrid (Current)
**Final approach:** Python for parsing/hierarchy management, Z3 for constraint solving
- **Key insight:** Different constraint types need different reasoners
- **Architecture:** Multi-sorted type system routes constraints to optimal solver
- **Result:** Sound, decidable, explainable conflict detection with concrete counterexamples

---

## Core Theoretical Contribution

**Claim:** ODRL policy analysis is **not** a single-logic problem—it's a **coordination problem** across decidable fragments.

### Why Z3?
1. **Numeric/Temporal:** SMT solving handles arithmetic constraints naturally
2. **Set Operations:** Z3 Arrays model multi-valued operands (e.g., `language: Array[String, Bool]`)
3. **Counterexamples:** When `SAT(Child ∧ ¬Parent)`, Z3 provides concrete violating context
4. **Decidability:** Stays within decidable fragments (LIA, difference logic, quantifier-free FOL)

### Why Not Pure DL/OWL?
- Description Logic excels at taxonomic reasoning (`isA`, `subClassOf`)
- But fails at numeric comparisons (`count ≤ 10`) and temporal ordering
- **Solution:** Hybrid architecture—DL for taxonomy, Z3 for constraints

---

## Key Technical Decisions

### 1. Multi-Valued Operands as Z3 Arrays
```python
# Before (Prolog): Awkward list handling
language(constraint_1, [en, de, fr]).

# After (Z3): Native set representation
language: Array[String, Bool]
# language["en"] = True  means "en" is in the set
```

**Why:** Z3 Arrays naturally model set membership with first-class quantifier-free reasoning.

### 2. Temporal Operand Normalization
```python
TEMPORAL_OPERAND_ALIASES = {
    'dateTimeBefore': 'currentDateTime',
    'dateTimeAfter': 'currentDateTime',
    'dateTime': 'currentDateTime'
}
```

**Why:** Different ODRL operands refer to the same semantic entity (current time). Unified variable prevents false conflicts.

### 3. Monotonic Policy Refinement
```
Definition: Child refines Parent iff:
  ∀ context: Satisfies(context, Child) ⟹ Satisfies(context, Parent)

Z3 Check: UNSAT(Child ∧ ¬Parent) ?
  → If SAT: expansion violation found (return model as counterexample)
  → If UNSAT: valid refinement ✓
```

**Why:** Enables **provable** inheritance checking—automated verification that child policies don't expand permissions.

### 4. Semantic Contract Layer
```
RDF/OWL Reasoner:
  JPEG ⊑ ImageFormat  (subsumption)

Z3 Encoder:
  fileFormat ∈ {JPEG, PNG, GIF, ...}  (membership)

Bridge Guarantee:
  DL inferences are sound → Z3 assumptions are sound
```

**Why:** Explicit separation of concerns—taxonomic reasoning stays in DL, constraint solving in SMT.

---

## What We Gained

### 1. **Decidable Correctness**
- All checks stay within NP-complete or polynomial fragments
- No undecidable temporal logic or higher-order quantification

### 2. **Concrete Counterexamples**
```python
# Z3 returns actual violating contexts:
Expansion Violation:
  Parent: fileFormat = JPEG
  Child: fileFormat ∈ {JPEG, PNG}
Counterexample:
  context = {fileFormat: "PNG"}
  ✓ Child satisfied
  ✗ Parent violated
```

**Impact:** Not just "conflict detected"—show **exactly** where and how.

### 3. **Sound Under-Approximation**
When domain knowledge is incomplete:
- Engine produces **sound** results (no false positives)
- May miss conflicts (false negatives) but never fabricates them
- This is acceptable for static analyzers (cf. type checkers)

### 4. **Extensibility**
New constraint types → new encoder rules, not full system rewrite:
```python
def _encode_spatial_operator(self, var, op, value):
    # Add RCC-8 reasoning when needed
    if op == OperatorType.SPATIAL_INSIDE:
        return self._check_region_containment(var, value)
```

---

## Lessons Learned

### What Didn't Work
1. **Prolog for everything:** Great for symbolic reasoning, poor for numeric/temporal
2. **Single-solver mentality:** No one logic handles all ODRL constraint types
3. **Runtime evaluation only:** Static analysis catches errors before deployment

### What Worked
1. **Hybrid architecture:** Right tool for each domain (DL for taxonomy, SMT for constraints)
2. **Type-directed encoding:** Operand semantics determine Z3 variable type
3. **Separation of concerns:** Parsing (Python) → Taxonomy (OWL) → Constraints (Z3)
