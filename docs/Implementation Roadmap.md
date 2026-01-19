# Final Agreed Implementation Plan: Static ODRL Constraint Evaluation Engine

**Version 1.0 - Approved Implementation Roadmap**

---

## Executive Summary

This document establishes the definitive implementation plan for a static ODRL policy analysis engine. The plan is structured in phases to avoid refactoring, maintains theoretical rigor, and provides clear milestones for incremental delivery.

**Core Principle**: Build incrementally without breaking existing code. Each phase extends capabilities while preserving previous work.

---

## 1. System Philosophy (Immutable)

### 1.1 Foundational Principles

```
┌─────────────────────────────────────────────────┐
│  POLICIES ARE LOGICAL OBJECTS, NOT PROGRAMS     │
│                                                 │
│  • Static Analysis BEFORE Deployment            │
│  • Separation: Analysis ≠ Enforcement           │
│  • Closed-World Assumption                      │
│  • Monotonic Inheritance                        │
│  • Decidable Reasoning                          │
└─────────────────────────────────────────────────┘
```

### 1.2 What This Engine Does

**DOES**:
- Logical consistency checking
- Monotonic inheritance validation  
- Conflict detection (permission-prohibition, XONE)
- Redundancy analysis
- Counterexample generation

**DOES NOT**:
- Runtime policy enforcement
- Authorization decisions
- Conflict resolution strategies
- Operational semantics

---

## 2. Constraint Taxonomy (Complete Classification)

### 2.1 Category Definitions

| Category | LeftOperand Examples | Metadata Used | Primary Reasoner | Phase |
|----------|---------------------|---------------|------------------|-------|
| **Numeric** | `count`, `percentage`, `payAmount` | `unitOfCount`, `dataType` | SMT (Z3) | Phase 2 |
| **Temporal** | `dateTime`, `elapsedTime`, `delayPeriod`, `timeInterval`, `meteredTime` | `dataType` | SMT (Z3) | Phase 2 |
| **Set/Taxonomic** | `language`, `fileFormat`, `industry`, `product`, `purpose`, `media`, `deliveryChannel` | `dataType` | Symbolic/DL | Phase 3 |
| **Spatial** | `spatial`, `spatialCoordinates`, `absoluteSpatialPosition`, `relativeSpatialPosition` | `dataType` | Optional GIS | Phase 4 |
| **Positional** | `absolutePosition`, `absoluteSize`, `relativePosition`, `relativeSize`, `resolution` | `unit`, `dataType` | SMT (Z3) | Phase 3 |
| **Reference** | `recipient`, `systemDevice`, `event`, `virtualLocation` | None | Symbolic | Phase 3 |
| **Logical** | `and`, `or`, `xone` | None | Boolean SMT | Phase 1 |
| **Sequential** | `andSequence` | None | **Normalization only** | Phase 1 |

### 2.2 Operator Classification

```
Relational Operators (Scalar):
  eq, neq, lt, lteq, gt, gteq
  → Apply to: Numeric, Temporal, Positional
  → Encoding: Direct SMT arithmetic

Set-Based Operators:
  isA, isAllOf, isAnyOf, isNoneOf, hasPart, isPartOf
  → Apply to: Set/Taxonomic, Reference
  → Encoding: Set theory + optional DL

Logical Operators:
  and, or, xone
  → Apply to: Composite constraints
  → Encoding: Boolean SMT

Sequential Operator:
  andSequence
  → Apply to: Temporal ordering
  → Encoding: Normalization ONLY (preserve structure)
```

### 2.3 Metadata Handling

| Metadata | Type | Purpose | Usage |
|----------|------|---------|-------|
| `unit` | URI/String | Measurement unit | Attach to numeric variables in SMT |
| `unitOfCount` | LeftOperand | Multiplier entity | Count-based constraint evaluation |
| `status` | Value | Reference value | Comparison baseline in constraints |
| `dataType` | rdfs:Datatype | Type annotation | Determines SMT sort (Int, Real, String, DateTime) |

**Implementation Rule**: Metadata is **attached to constraint objects** but does not alter core logical structure.

---

## 3. Implementation Phases (No-Refactor Guarantee)

### Phase 0: Foundation (Current State)

**Status**: **COMPLETED**

**Deliverables**:
- Basic constraint parsing
- Atomic constraint to SMT encoding
- Simple consistency checking
- Permission-prohibition conflict detection

**Preserved**: All existing code remains functional.

---

### Phase 1: Canonical Normalization & Logical Operators

**Duration**: 2-3 weeks

**Objectives**:
1. Implement complete ODRL constraint parser (JSON-LD/RDF)
2. Flatten nested logical constraints
3. Build canonical constraint graph representation
4. Encode `and`, `or`, `xone` in SMT
5. **Preserve `andSequence` structure** (no reasoning yet)

**Deliverables**:

```python
# Core data structures
@dataclass
class Constraint:
    left_operand: str          # URI or LeftOperand
    operator: str              # Operator URI
    right_operand: Any         # Value or list
    right_operand_ref: str     # Optional URI
    unit: Optional[str]        # Optional unit
    datatype: Optional[str]    # Optional datatype
    status: Optional[Any]      # Optional status value
    
@dataclass
class LogicalConstraint:
    operator: str              # and, or, xone, andSequence
    operands: List[Constraint | LogicalConstraint]
    
@dataclass
class ConstraintGraph:
    atomic_constraints: List[Constraint]
    logical_constraints: List[LogicalConstraint]
    metadata: Dict[str, Any]
```

**Testing**:
- Parse all ODRL operator/operand combinations
- Verify flattening preserves semantics
- Test `andSequence` structure preservation

**Success Criteria**:
- Parse 100% of ODRL constraint vocabulary
- Canonical graph generated for test policies
- Existing Phase 0 tests still pass

---

### Phase 2: Numeric & Temporal Reasoning (Core SMT)

**Objectives**:
1. Classify constraints by category (Numeric, Temporal, etc.)
2. Implement SMT encoding for all numeric/temporal operators
3. Encode metadata (`unit`, `dataType`) in SMT sorts
4. Implement inheritance checking (`C ⟹ P`)
5. Generate counterexamples for expansion violations

**SMT Encoding Strategy**:

```python
# Numeric constraints
def encode_numeric(constraint: Constraint) -> z3.BoolRef:
    left = z3.Int(constraint.left_operand)  # or Real based on dataType
    right = int(constraint.right_operand)
    
    if constraint.operator == "eq":
        return left == right
    elif constraint.operator == "lt":
        return left < right
    # ... etc
    
# Temporal constraints (normalize to Unix timestamps)
def encode_temporal(constraint: Constraint) -> z3.BoolRef:
    left = z3.Int(constraint.left_operand + "_timestamp")
    right = parse_datetime(constraint.right_operand)  # to timestamp
    
    if constraint.operator == "gteq":
        return left >= right
    # ... etc

# Duration constraints
def encode_duration(constraint: Constraint) -> z3.BoolRef:
    left = z3.Int(constraint.left_operand + "_seconds")
    right = parse_duration(constraint.right_operand)  # to seconds
    
    if constraint.operator == "eq":
        return left == right
    # ... etc
```

**Inheritance Checking**:

```python
def check_inheritance(child: Policy, parent: Policy) -> InheritanceResult:
    """Check if child ⟹ parent"""
    solver = z3.Solver()
    
    # Encode child constraints
    child_formula = encode_policy(child)
    solver.add(child_formula)
    
    # Encode negation of parent
    parent_formula = encode_policy(parent)
    solver.add(z3.Not(parent_formula))
    
    # Check satisfiability
    result = solver.check()
    
    if result == z3.sat:
        # Expansion found
        model = solver.model()
        return InheritanceResult(
            valid=False,
            violation_type="EXPANSION",
            counterexample=extract_counterexample(model)
        )
    else:
        # Valid refinement
        return InheritanceResult(valid=True)
```

**Deliverables**:
- Complete numeric/temporal SMT encoding
- Inheritance checker with counterexamples
- Metadata-aware constraint evaluation
- Test suite for 50+ constraint combinations

**Testing**:
- Numeric: `count`, `percentage`, `payAmount`
- Temporal: `dateTime`, `elapsedTime`, `delayPeriod`, `timeInterval`
- Metadata: constraints with `unit`, `unitOfCount`, `dataType`
- Inheritance: 20+ parent-child policy pairs

**Success Criteria**:
- ✅ All numeric/temporal constraints encoded correctly
- ✅ Inheritance checking produces counterexamples
- ✅ Metadata preserved in explanations
- ✅ Phase 0-1 tests still pass

---

### Phase 3: Set-Based & Symbolic Reasoning

**Duration**: 3-4 weeks

**Objectives**:
1. Implement set-based operator encoding
2. Add symbolic reasoning for taxonomic constraints
3. **Optional**: Integrate lightweight DL reasoner (HermiT/Owlready2)
4. Handle reference-based constraints (`recipient`, `systemDevice`)

**Set Operator Encoding**:

```python
# Set membership (using Z3 arrays)
def encode_set_constraint(constraint: Constraint) -> z3.BoolRef:
    left = z3.String(constraint.left_operand)
    right_set = constraint.right_operand  # list of values
    
    if constraint.operator == "isAnyOf":
        # left ∈ right_set
        return z3.Or([left == z3.StringVal(v) for v in right_set])
    
    elif constraint.operator == "isNoneOf":
        # left ∉ right_set
        return z3.And([left != z3.StringVal(v) for v in right_set])
    
    elif constraint.operator == "isAllOf":
        # For set-valued left operand
        # Encode as: right_set ⊆ left
        # (requires multi-valued operand handling)
        pass
    
    elif constraint.operator == "isA":
        # Requires taxonomy knowledge
        # Fallback: uninterpreted function
        return z3.Bool(f"{left}_isA_{constraint.right_operand}")
```

**Taxonomy Integration** (Optional DL):

```python
# Optional: OWL ontology reasoning
from owlready2 import get_ontology

class TaxonomyReasoner:
    def __init__(self, ontology_path: str):
        self.onto = get_ontology(ontology_path).load()
    
    def is_a(self, instance: str, type_: str) -> bool:
        """Check if instance is of type"""
        # Query ontology
        return self.onto.search(iri=instance).is_a(type_)
    
    def subsumes(self, type1: str, type2: str) -> bool:
        """Check if type1 ⊑ type2"""
        return self.onto.search(iri=type1).is_a(type2)
```

**Deliverables**:
- Set-based operator encoding (all 6 operators)
- Symbolic constraint handling
- Optional taxonomy reasoner integration
- Test suite for set/taxonomic constraints

**Testing**:
- `isAnyOf`, `isNoneOf`, `isAllOf`
- `isA`, `hasPart`, `isPartOf`
- Constraints with external knowledge (if DL integrated)

**Success Criteria**:
- ✅ All set operators correctly encoded
- ✅ Symbolic reasoning works for unknown domains
- ✅ Optional DL integration (if time permits)
- ✅ Phase 0-2 tests still pass

---

### Phase 4: Spatial & Positional Reasoning (Optional)

**Duration**: 2-3 weeks (optional module)

**Objectives**:
1. Implement spatial constraint encoding
2. Integrate GIS library (Shapely or PostGIS)
3. Handle positional constraints (absolute/relative)

**Spatial Encoding**:

```python
from shapely.geometry import Point, Polygon

class SpatialReasoner:
    def point_in_region(self, lat: float, lon: float, 
                        region: str) -> bool:
        """Check if point is in named region"""
        # Load region geometry from knowledge base
        polygon = self.load_region_geometry(region)
        point = Point(lon, lat)
        return polygon.contains(point)
    
    def bbox_contains(self, point: Tuple[float, float],
                     bbox: Tuple[float, float, float, float]) -> bool:
        """Simple bounding box containment"""
        lat, lon = point
        min_lat, min_lon, max_lat, max_lon = bbox
        return (min_lat <= lat <= max_lat and 
                min_lon <= lon <= max_lon)
```

**Integration with SMT**:

```python
# Approximate spatial constraints with linear inequalities
def encode_spatial_bbox(constraint: Constraint) -> z3.BoolRef:
    lat = z3.Real("latitude")
    lon = z3.Real("longitude")
    
    # Extract bounding box from rightOperand
    min_lat, min_lon, max_lat, max_lon = parse_bbox(constraint.right_operand)
    
    return z3.And(
        lat >= min_lat, lat <= max_lat,
        lon >= min_lon, lon <= max_lon
    )
```

**Deliverables**:
- Spatial constraint module (optional)
- GIS integration for complex regions
- Positional constraint encoding

**Testing**:
- Bounding box containment
- Named region queries (if KB available)
- Absolute/relative position constraints

**Success Criteria**:
- ✅ Basic spatial reasoning works
- ✅ Optional GIS integration functional
- ✅ Module is decoupled (can be disabled)

---

### Phase 5: Redundancy Detection & Optimization

**Duration**: 2 weeks

**Objectives**:
1. Implement constraint implication checking (`C1 ⟹ C2`)
2. Detect redundant constraints
3. Suggest constraint simplifications

**Redundancy Detection**:

```python
def detect_redundancy(policy: Policy) -> List[RedundancyWarning]:
    """Find redundant constraints in policy"""
    redundancies = []
    constraints = policy.get_all_constraints()
    
    for i, c1 in enumerate(constraints):
        for j, c2 in enumerate(constraints[i+1:], start=i+1):
            if implies(c1, c2):
                redundancies.append(
                    RedundancyWarning(
                        redundant=c2,
                        implied_by=c1,
                        explanation=f"{c2} is implied by {c1}"
                    )
                )
    
    return redundancies

def implies(c1: Constraint, c2: Constraint) -> bool:
    """Check if c1 ⟹ c2"""
    solver = z3.Solver()
    solver.add(encode_constraint(c1))
    solver.add(z3.Not(encode_constraint(c2)))
    return solver.check() == z3.unsat
```

**Deliverables**:
- Redundancy detection algorithm
- Constraint simplification suggestions
- Performance optimization

**Testing**:
- Redundant numeric constraints
- Implied temporal constraints
- Overlapping set constraints

**Success Criteria**:
- ✅ Redundancy correctly identified
- ✅ No false positives
- ✅ Suggestions are actionable

---

### Phase 6: Reporting & Counterexample Generation

**Duration**: 2 weeks

**Objectives**:
1. Human-readable analysis reports
2. Counterexample interpretation
3. Metadata-aware explanations

**Report Structure**:

```python
@dataclass
class AnalysisReport:
    policy_id: str
    status: PolicyStatus  # VALID, INCONSISTENT, EXPANSION, REDUNDANT
    
    # Consistency check
    is_consistent: bool
    inconsistency_explanation: Optional[str]
    
    # Inheritance check
    inheritance_valid: bool
    expansion_violations: List[ExpansionViolation]
    
    # Conflict detection
    conflicts: List[Conflict]
    
    # Redundancy
    redundancies: List[RedundancyWarning]
    
    # Counterexamples
    counterexamples: List[Counterexample]
    
    # Metadata
    analyzed_constraints: int
    reasoning_time: float

@dataclass
class Counterexample:
    constraint: Constraint
    assignment: Dict[str, Any]  # Variable → Value
    explanation: str
    metadata: Dict[str, Any]    # Include unit, dataType, etc.
```

**Counterexample Extraction**:

```python
def extract_counterexample(model: z3.ModelRef, 
                          constraints: List[Constraint]) -> Counterexample:
    """Convert Z3 model to human-readable counterexample"""
    assignment = {}
    
    for decl in model.decls():
        var_name = decl.name()
        value = model[decl]
        
        # Interpret based on dataType
        if "_timestamp" in var_name:
            assignment[var_name] = timestamp_to_datetime(value.as_long())
        elif "_seconds" in var_name:
            assignment[var_name] = seconds_to_duration(value.as_long())
        else:
            assignment[var_name] = value
    
    # Generate natural language explanation
    explanation = generate_explanation(assignment, constraints)
    
    return Counterexample(
        constraint=constraints[0],
        assignment=assignment,
        explanation=explanation,
        metadata=extract_metadata(constraints)
    )
```

**Deliverables**:
- Complete analysis report generator
- Counterexample interpreter
- Natural language explanations

**Testing**:
- Report generation for all policy statuses
- Counterexample readability
- Metadata preservation in reports

**Success Criteria**:
- ✅ Reports are human-readable
- ✅ Counterexamples are actionable
- ✅ Metadata correctly displayed

---

## 4. Testing Strategy (Continuous)

### 4.1 Test Categories

```
Unit Tests (per phase):
  - Individual operator encoding
  - Metadata handling
  - Constraint classification

Integration Tests (cross-phase):
  - End-to-end policy analysis
  - Inheritance checking with all constraint types
  - Multi-category policies

Regression Tests (all phases):
  - Ensure previous phases still work
  - Performance benchmarks
  - Memory usage

Acceptance Tests (research validation):
  - Real ODRL policies from literature
  - Known conflict cases
  - Edge cases (empty policies, circular refs)
```

### 4.2 Test Data

```
Test Policy Repository:
  /tests/
    ├── unit/
    │   ├── numeric_constraints.json
    │   ├── temporal_constraints.json
    │   ├── set_constraints.json
    │   └── logical_constraints.json
    ├── integration/
    │   ├── inheritance_valid.json
    │   ├── inheritance_expansion.json
    │   └── conflicts.json
    └── real_world/
        ├── creative_commons.json
        ├── academic_publishing.json
        └── data_sharing.json
```

---

## 5. Code Structure (No Refactoring)

### 5.1 Module Organization

```
odrl_analyzer/
├── core/
│   ├── __init__.py
│   ├── constraint.py         # Constraint data structures
│   ├── policy.py             # Policy data structures
│   └── graph.py              # Constraint graph
├── parsing/
│   ├── __init__.py
│   ├── jsonld_parser.py      # JSON-LD parser
│   └── normalizer.py         # Canonical normalization
├── classification/
│   ├── __init__.py
│   ├── categorizer.py        # Constraint categorization
│   └── metadata_extractor.py
├── encoding/
│   ├── __init__.py
│   ├── smt_encoder.py        # SMT encoding (Phase 2)
│   ├── set_encoder.py        # Set encoding (Phase 3)
│   └── spatial_encoder.py    # Spatial encoding (Phase 4)
├── reasoning/
│   ├── __init__.py
│   ├── consistency.py        # Consistency checking
│   ├── inheritance.py        # Inheritance validation
│   ├── conflicts.py          # Conflict detection
│   └── redundancy.py         # Redundancy analysis (Phase 5)
├── knowledge/
│   ├── __init__.py
│   ├── taxonomy.py           # Optional DL reasoner
│   └── spatial.py            # Optional GIS reasoner
├── reporting/
│   ├── __init__.py
│   ├── report.py             # Report generation (Phase 6)
│   └── counterexample.py     # Counterexample extraction
└── tests/
    ├── unit/
    ├── integration/
    └── real_world/
```

### 5.2 Extension Points

```python
# Easy to extend without refactoring
class ConstraintEncoder(ABC):
    @abstractmethod
    def encode(self, constraint: Constraint) -> z3.BoolRef:
        pass

# Register new encoders
ENCODER_REGISTRY = {
    "numeric": NumericEncoder(),
    "temporal": TemporalEncoder(),
    "set": SetEncoder(),
    "spatial": SpatialEncoder(),  # Optional
}

# Add new categories without changing core
def classify_constraint(c: Constraint) -> str:
    if c.left_operand in ["count", "percentage", "payAmount"]:
        return "numeric"
    elif c.left_operand in ["dateTime", "elapsedTime"]:
        return "temporal"
    # ... etc
```

---

## 6. Deliverables & Milestones

### Phase 1: Weeks 1-3
- ✅ Complete ODRL parser
- ✅ Canonical constraint graph
- ✅ Logical operator encoding
- **Milestone**: Parse any ODRL policy into canonical form

### Phase 2: Weeks 4-7
- ✅ Numeric/temporal SMT encoding
- ✅ Inheritance checker
- ✅ Counterexample generation
- **Milestone**: Validate numeric/temporal policy inheritance

### Phase 3: Weeks 8-11
- ✅ Set-based operator encoding
- ✅ Symbolic reasoning
- ✅ Optional DL integration
- **Milestone**: Handle taxonomic constraints

### Phase 4: Weeks 12-14 (Optional)
- ✅ Spatial reasoning module
- ✅ GIS integration
- **Milestone**: Analyze spatial policies

### Phase 5: Weeks 15-16
- ✅ Redundancy detection
- ✅ Optimization suggestions
- **Milestone**: Detect redundant constraints

### Phase 6: Weeks 17-18
- ✅ Reporting system
- ✅ Human-readable explanations
- **Milestone**: Production-ready analyzer

---

## 7. Success Criteria (Final Acceptance)

### Functional Requirements
- ✅ Parse 100% of ODRL constraint vocabulary
- ✅ Correctly classify all constraint categories
- ✅ Encode numeric, temporal, set, and logical constraints in SMT
- ✅ Detect internal inconsistencies
- ✅ Validate monotonic inheritance
- ✅ Generate actionable counterexamples
- ✅ Identify redundant constraints

### Non-Functional Requirements
- ✅ Analysis completes in <5 seconds for typical policies (<100 constraints)
- ✅ Memory usage <500MB for large policies
- ✅ No false positives (only sound results)
- ✅ False negatives documented (missing domain knowledge)

### Research Requirements
- ✅ Theoretical foundations documented
- ✅ Formal semantics specified
- ✅ Comparison with related work
- ✅ Publishable results

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SMT solver performance | Use incremental solving, caching |
| Missing domain knowledge | Graceful degradation to symbolic |
| Complex spatial reasoning | Make GIS module optional |
| `andSequence` complexity | Defer to future LTL extension |
| Taxonomy availability | Provide fallback to uninterpreted |

---

## 9. Future Extensions (Post-Phase 6)

### Short-term (3-6 months)
- Canonical normal forms for equivalence checking
- Policy composition operators (π₁ ⊗ π₂)
- Web-based visualization tool

### Long-term (6-12 months)
- Bounded LTL for `andSequence` reasoning
- Probabilistic constraints
- Interactive policy authoring with LLM assistance
- Integration with policy enforcement engines

---

## 10. Sign-Off

**Agreed Implementation Plan**: This document represents the final, agreed-upon implementation roadmap for the ODRL Static Policy Analysis Engine.

**Principles**:
- ✅ No refactoring between phases
- ✅ Incremental delivery
- ✅ Continuous testing
- ✅ Theoretical rigor maintained
- ✅ Extensible architecture

**Commitment**: Each phase extends capabilities without breaking previous work.

---

**Document Status**: ✅ **APPROVED FOR IMPLEMENTATION**  
**Version**: 1.0 Final  
**Date**: January 2026  
**Estimated Completion**: 18 weeks (4.5 months)

---

## Quick Reference: Operator Handling Summary

| Operator | Category | Phase | Reasoning Method |
|----------|----------|-------|------------------|
| `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq` | Relational | 2 | SMT arithmetic |
| `isA`, `hasPart`, `isPartOf` | Taxonomic | 3 | Symbolic/DL |
| `isAllOf`, `isAnyOf`, `isNoneOf` | Set-based | 3 | SMT arrays/sets |
| `and`, `or`, `xone` | Logical | 1 | Boolean SMT |
| `andSequence` | Sequential | 1 | **Normalization only** |

**Metadata**: `unit`, `unitOfCount`, `status`, `dataType` → Attached to constraints, used in SMT encoding and explanations.
