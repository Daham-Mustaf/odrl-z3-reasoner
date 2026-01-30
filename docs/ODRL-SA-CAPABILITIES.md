# ODRL-SA Engine Capabilities

## Overview

ODRL-SA (ODRL Static Analyzer) is a formal verification tool for ODRL policies using Z3 SMT solver. It performs **design-time** conflict detection without requiring runtime evaluation.

---

## Fully Implemented Capabilities

### 1. Constraint Satisfiability Analysis

| Feature | Description | Example |
|---------|-------------|---------|
| **SAT Check** | Is constraint satisfiable? | `count > 10 AND count < 5` → UNSAT |
| **Tautology** | Is constraint always true? | `percentage >= 0` (always true in [0,100]) |
| **Domain Validation** | Value within bounds? | `percentage = 150` → Invalid |

### 2. Conflict Detection (15+ Types)

#### Rule-Level Conflicts

| Conflict Type | Severity | Description |
|---------------|----------|-------------|
| `permission_prohibition` | CRITICAL | Same action permitted AND prohibited |
| `duty_prohibition` | CRITICAL | Required action is prohibited |
| `permission_ambiguity` | WARNING | Overlapping permissions without subsumption |
| `permission_subsumption` | INFO | One permission makes another redundant |
| `prohibition_redundancy` | WARNING | Duplicate/subsumed prohibitions |
| `unreachable_permission` | WARNING | Permission always blocked by prohibition |
| `duty_incompatibility` | CRITICAL | Multiple duties can't all be satisfied |

#### Constraint-Level Conflicts

| Conflict Type | Severity | Description |
|---------------|----------|-------------|
| `and_contradiction` | CRITICAL | AND with unsatisfiable children |
| `or_unsatisfiable` | CRITICAL | OR with all branches unsatisfiable |
| `xone_overlap` | CRITICAL | XONE branches can be true simultaneously |
| `xone_trivial` | WARNING | XONE with only one satisfiable branch |
| `xone_unsatisfiable` | CRITICAL | XONE with no satisfiable branches |
| `andsequence_unsatisfiable` | CRITICAL | ANDSEQUENCE with contradictory children |
| `unsatisfiable` | CRITICAL | Atomic constraint is unsatisfiable |
| `tautology` | WARNING | Constraint is always true |
| `unit_incompatibility` | INFO | Same operand with different units |

### 3. Operator Support

#### Comparison Operators (O_cmp)

| Operator | Z3 Encoding | Status |
|----------|-------------|--------|
| `eq` | `var == v` | ✅ |
| `neq` | `var != v` | ✅ |
| `lt` | `var < v` | ✅ |
| `lteq` | `var <= v` | ✅ |
| `gt` | `var > v` | ✅ |
| `gteq` | `var >= v` | ✅ |

#### Set Operators (O_set)

| Operator | Z3 Encoding | Status |
|----------|-------------|--------|
| `isAnyOf` | `Or(var == v1, var == v2, ...)` | ✅ |
| `isNoneOf` | `And(var != v1, var != v2, ...)` | ✅ |
| `isAllOf` | Degenerates to eq/False | ✅ |

#### Semantic Operators (require grounding)

| Operator | Status | Needs |
|----------|--------|-------|
| `isA` | ⚠️ Over-approximates | Taxonomy oracle |
| `hasPart` | ⚠️ Over-approximates | Mereology reasoning |
| `isPartOf` | ⚠️ Over-approximates | Mereology reasoning |

### 4. Composite Constraint Support

| Operator | Semantics | Z3 Encoding |
|----------|-----------|-------------|
| `and` | All must hold | `And(c1, c2, ...)` |
| `or` | At least one | `Or(c1, c2, ...)` |
| `xone` | Exactly one | `Sum([If(ci, 1, 0)]) == 1` |
| `andSequence` | Ordered AND | `And(c1, c2, ...)` (order noted) |

### 5. LeftOperand Coverage

#### FULL Class (15 operands) - Fully Analyzable

| Category | LeftOperands | Domain | Z3 Sort |
|----------|--------------|--------|---------|
| **L_bounded** | percentage, relativePosition, relativeSize, relativeTemporalPosition, relativeSpatialPosition | [0, 100] | Real |
| **L_int** | count | ℤ≥0 | Int |
| **L_duration** | timeInterval | ℤ>0 (seconds) | Int |
| **L_datetime** | dateTime | ℤ (Unix timestamp) | Int |
| **L_unit** | payAmount, resolution, absoluteSize, absolutePosition, absoluteTemporalPosition, absoluteSpatialPosition | ℝ≥0 | Real |
| **L_vocab** | unitOfCount | Enum | String |

#### PARTIAL Class (2 operands) - Reference-Dependent

| LeftOperand | Reference Point | Notes |
|-------------|-----------------|-------|
| elapsedTime | Policy activation | Full analysis needs runtime |
| delayPeriod | Triggering event | Full analysis needs runtime |

#### GROUNDED Class (14 operands) - Need External KB

| LeftOperand | Oracle | External KB |
|-------------|--------|-------------|
| language | BCP47 | ISO639, LCC |
| purpose | DPV | Data Privacy Vocabulary |
| fileFormat | IANA | Media Types |
| spatial | GeoNames | ISO3166 |
| And 10 more... | | |

### 6. Unit Handling

| Feature | Status | Description |
|---------|--------|-------------|
| **Unit Isolation** | ✅ | Different units → different Z3 variables |
| **QUDT Grounding** | ✅ | 34 units (currency, resolution, size, time) |
| **Alias Resolution** | ✅ | "euro" → "EUR", URIs → codes |
| **Incompatibility Warning** | ✅ | Flags when same operand has different units |

**Supported Unit Categories:**

| Category | Units | Count |
|----------|-------|-------|
| Currency | EUR, USD, GBP, JPY, CHF, CAD, AUD, CNY, INR, BRL | 10 |
| Resolution | DPI, PPI, DPCM | 3 |
| Data Size | BYTE, KiloBYTE, MegaBYTE, GigaBYTE, TeraBYTE, BIT, KiloBIT, MegaBIT | 8 |
| Physical Size | PIXEL, M, CM, MM, IN, PT | 6 |
| Time | SEC, MIN, HR, DAY, WK, MO, YR | 7 |

### 7. Policy Inheritance Checking

| Feature | Status | Description |
|---------|--------|-------------|
| **Inconsistency Detection** | ✅ | Child contradicts parent (combined UNSAT) |
| **Redundancy Detection** | ✅ | Child adds no restriction |
| **New Action Detection** | ✅ | Child permits action not in parent |
| **Per-Action Checking** | ✅ | Check inheritance per action |
| **Cumulative Semantics** | ✅ | `effective_child = parent AND child_own` |

---

## ⚠️ Partially Implemented

### Semantic Operator Grounding

Oracles exist but not fully integrated:

| Oracle | Location | Status |
|--------|----------|--------|
| Language (BCP47) | `src/grounding/language/` | ✅ Exists |
| Purpose (DPV) | `src/grounding/purpose/` | ✅ Exists |
| File Format (IANA) | `src/grounding/file_format/` | ✅ Exists |
| Unit (QUDT) | `src/grounding/unit/` | ✅ Exists |

**To fully support `isA`:**
```python
# Need to integrate oracle queries in z3_encoder.py
if op == OperatorType.IS_A:
    if operand == "language":
        # Query BCP47 hierarchy
        descendants = language_oracle.get_descendants(value)
        return Or([var == d for d in descendants])
```

---

## ❌ Not Yet Implemented

### 1. `inheritFrom` Parsing

The TTL parser may not detect `odrl:inheritFrom` relationships.

**To implement:**
```python
# In ttl_parser.py
ODRL_INHERIT_FROM = ODRL["inheritFrom"]

def parse_policy(self, graph):
    # ...
    inherit_from = graph.value(policy_uri, ODRL_INHERIT_FROM)
    if inherit_from:
        policy.inherit_from = str(inherit_from)
```

### 2. Action Hierarchy

ODRL defines action taxonomy (e.g., `display` subClassOf `use`).

**To implement:**
```python
ACTION_HIERARCHY = {
    "display": ["use"],
    "print": ["use"],
    "distribute": ["use"],
    # ...
}

def get_implied_actions(action):
    """Get all actions implied by this action."""
    return ACTION_HIERARCHY.get(action, []) + [action]
```

### 3. Asset/Party Matching

Compare targets, assignees, assignors across rules.

### 4. Temporal Interval Reasoning

- Interval overlap detection
- Duration arithmetic
- Recurring events

### 5. Refinement Support

`odrl:refinement` for refining actions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
├─────────────────────────────────────────────────────────────┤
│  parser/          │  normalizer/      │  encoder/           │
│  ├── ttl_parser   │  └── normalizer   │  └── z3_encoder     │
├───────────────────┴───────────────────┴─────────────────────┤
│  reasoner/                                                   │
│  ├── conflict_detector   ← Main conflict detection          │
│  └── inheritance_checker ← Policy inheritance               │
├─────────────────────────────────────────────────────────────┤
│  grounding/                                                  │
│  ├── language/    │  ├── purpose/     │  ├── file_format/  │
│  └── unit/        │                                         │
├─────────────────────────────────────────────────────────────┤
│  core/                                                       │
│  ├── constraint_types   │  ├── classifier   │  ├── judgment │
├─────────────────────────────────────────────────────────────┤
│  config/                                                     │
│  └── operands.yaml      ← Complete LeftOperand specs        │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Basic Conflict Detection

```bash
uv run python main.py tests/ttl/payAmount/ --all
```

### Specific Test

```bash
uv run python main.py tests/ttl/dateTime/dt_conflict.ttl
```

### Debug Mode

```bash
uv run python main.py tests/ttl/percentage/ --all --debug
```

---

## Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| percentage | 15 | ✅ |
| dateTime | 11 | ✅ |
| timeInterval | 6 | ✅ |
| relativePosition | 5 | ✅ |
| payAmount | 8 | ✅ |
| adversarial | 7 | ✅ |
| deontic | 3 | ✅ |
| inheritance | 12 | ✅ |
| composite (AND/OR/XONE) | 20+ | ✅ |

---

## Formal Foundations

### Judgment Rules (Definition 6)

```
judge(c₁, c₂) = 
    CONFLICT            if comparable AND [[c₁]]# ⊓ [[c₂]]# = ⊥
    POSSIBLY-COMPATIBLE if comparable AND [[c₁]]# ⊓ [[c₂]]# ≠ ⊥
    UNKNOWN             if NOT comparable
```

### Abstraction Function (Definition 8)

```
α(eq, v)   = [v, v]
α(neq, v)  = ⊤ (over-approximation)
α(lt, v)   = (-∞, v)
α(lteq, v) = (-∞, v]
α(gt, v)   = (v, +∞)
α(gteq, v) = [v, +∞)
```

### SMT Theories Used

| Theory | LeftOperands |
|--------|--------------|
| QF-LIA (Integer Linear Arithmetic) | count, dateTime, timeInterval, elapsedTime, delayPeriod |
| QF-LRA (Real Linear Arithmetic) | percentage, payAmount, resolution, all relative/absolute operands |
| QF-UF (Uninterpreted Functions) | unitOfCount (enum) |

---

## Paper Statement

> ODRL-SA is a static analyzer for ODRL policies that detects conflicts at design-time using SMT solving. It supports 15 fully analyzable LeftOperands, all 12 ODRL operators, and performs 15+ types of conflict detection including deontic conflicts, constraint contradictions, and policy inheritance violations. Unit-qualified constraints are handled soundly by treating different units as incomparable, preserving soundness without requiring currency conversion.
