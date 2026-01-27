# ODRL-SA Implementation Analysis

## 1. ODRL Left Operands - Complete Vocabulary

According to ODRL 2.2 specification, there are **31 left operands**. Here's the status:

### A. NUMERIC OPERANDS (Self-Contained) - FULL Support

| Operand | XSD Type | Domain | Z3 Sort | Status |
|---------|----------|--------|---------|--------|
| `count` | xsd:integer | [0, ∞) | Int |  DONE |
| `percentage` | xsd:decimal | [0, 100] | Real |  DONE |
| `payAmount` | xsd:decimal | [0, ∞) | Real |  DONE |
| `absoluteSize` | xsd:decimal | [0, ∞) | Real |  DONE |
| `relativeSize` | xsd:decimal | [0, 100] | Real |  DONE |
| `resolution` | xsd:decimal | [0, ∞) | Real |  DONE |
| `absolutePosition` | xsd:decimal | (-∞, ∞) | Real |  DONE |
| `relativePosition` | xsd:decimal | [0, 100] | Real |  DONE |
| `absoluteSpatialPosition` | xsd:decimal | (-∞, ∞) | Real |  DONE |
| `relativeSpatialPosition` | xsd:decimal | [0, 100] | Real |  DONE |
| `absoluteTemporalPosition` | xsd:decimal | [0, ∞) | Real |  DONE |
| `relativeTemporalPosition` | xsd:decimal | [0, 100] | Real |  DONE |

**Total: 12 numeric operands - ALL IMPLEMENTED **

### B. TEMPORAL OPERANDS - FULL/PARTIAL Support

| Operand | XSD Type | Normalizer | Status |
|---------|----------|------------|--------|
| `dateTime` | xsd:dateTime | timestamp (seconds) |  DONE |
| `timeInterval` | xsd:duration | seconds |  DONE |
| `elapsedTime` | xsd:duration | seconds |  DONE (PARTIAL class) |
| `delayPeriod` | xsd:duration | seconds |  DONE (PARTIAL class) |
| `meteredTime` | xsd:duration | N/A | ⚠️ RUNTIME - cannot analyze |

**Note on PARTIAL class**: `elapsedTime` and `delayPeriod` can be analyzed for conflict but need runtime values for evaluation.

**Total: 5 temporal operands - 4 analyzable, 1 runtime**

### C. GROUNDED OPERANDS - Need Oracles

| Operand | Expected Values | Oracle Needed | Status |
|---------|-----------------|---------------|--------|
| `language` | BCP47 tags | LanguageOracle | 🚫 NOT DONE |
| `systemDevice` | Device IRIs | SystemOracle | 🚫 NOT DONE |
| `deliveryChannel` | Channel IRIs | DeliveryOracle | 🚫 NOT DONE |
| `industry` | NAICS/ISIC codes | IndustryOracle | 🚫 NOT DONE |
| `spatial` | Geo IRIs | SpatialOracle | 🚫 NOT DONE |
| `media` | MIME types | MediaOracle | 🚫 NOT DONE |
| `purpose` | Purpose IRIs | PurposeOracle | 🚫 NOT DONE |
| `recipient` | Party IRIs | RecipientOracle | 🚫 NOT DONE |
| `event` | Event IRIs | EventOracle | 🚫 NOT DONE |
| `fileFormat` | MIME types | FormatOracle | 🚫 NOT DONE |
| `product` | Product IRIs | ProductOracle | 🚫 NOT DONE |
| `virtualLocation` | URI | LocationOracle | 🚫 NOT DONE |
| `unitOfCount` | Unit IRIs | UnitOracle | 🚫 NOT DONE |

**Total: 13 grounded operands - NONE IMPLEMENTED**

### D. SPECIAL OPERANDS

| Operand | Type | Status |
|---------|------|--------|
| `version` | xsd:string | ⚠️ DEFERRED (string comparison) |

---

## 2. ODRL Operators - Implementation Status

### A. COMPARISON OPERATORS - FULL Support

| Operator | Symbol | Z3 Encoding | Status |
|----------|--------|-------------|--------|
| `eq` | = | `var == value` |  DONE |
| `neq` | ≠ | `var != value` |  DONE |
| `lt` | < | `var < value` |  DONE |
| `lteq` | ≤ | `var <= value` |  DONE |
| `gt` | > | `var > value` |  DONE |
| `gteq` | ≥ | `var >= value` |  DONE |

**Total: 6 comparison operators - ALL IMPLEMENTED **

### B. SET OPERATORS - NOT Implemented

| Operator | Semantics | Z3 Encoding Needed | Status |
|----------|-----------|-------------------|--------|
| `isA` | value isA class | Subsumption check | 🚫 NOT DONE |
| `isAnyOf` | value ∈ {set} | `Or([var == v for v in set])` | 🚫 NOT DONE |
| `isAllOf` | values ⊇ {set} | Complex set logic | 🚫 NOT DONE |
| `isNoneOf` | value ∉ {set} | `And([var != v for v in set])` | 🚫 NOT DONE |
| `hasPart` | value hasPart x | Part-whole reasoning | 🚫 NOT DONE |
| `isPartOf` | value isPartOf x | Part-whole reasoning | 🚫 NOT DONE |

**Total: 6 set operators - NONE IMPLEMENTED**

---

## 3. Logical Constraints (Composite Constraints)

### ODRL Logical Operators

| Operator | Semantics | Parsing | Z3 Encoding | Conflict Detection |
|----------|-----------|---------|-------------|-------------------|
| `and` | All must be true | ⚠️ PARTIAL | ⚠️ PARTIAL | ⚠️ PARTIAL |
| `or` | At least one true | ⚠️ PARTIAL | ⚠️ PARTIAL | 🚫 NOT DONE |
| `xone` | Exactly one true | ⚠️ PARTIAL | ⚠️ PARTIAL | 🚫 NOT DONE |
| `andSequence` | Ordered AND | 🚫 NOT DONE | 🚫 NOT DONE | 🚫 NOT DONE |

### Current Implementation Issues

**Problem 1: Parsing**
```turtle
# This is NOT properly extracted:
odrl:constraint [
    odrl:and (
        [ odrl:leftOperand odrl:count ; odrl:operator odrl:lt ; odrl:rightOperand "5" ]
        [ odrl:leftOperand odrl:count ; odrl:operator odrl:gt ; odrl:rightOperand "10" ]
    )
]
```

**Problem 2: Conflict Detection for Composites**
- AND contradiction: count < 5 AND count > 10 → CONFLICT  (if parsed)
- OR satisfiability: count = 1 OR count = 2 → Need to check if ANY branch works
- XONE overlap: Need to check if MULTIPLE branches can be true simultaneously

---

## 4. Conflict Types - Implementation Status

### A. Constraint-Level Conflicts

| Conflict Type | Example | Detection | Status |
|---------------|---------|-----------|--------|
| Numeric range conflict | count < 5 AND count > 10 | Z3 UNSAT |  DONE |
| DateTime disjoint | date < 2024 AND date > 2025 | Z3 UNSAT |  DONE |
| Duration conflict | elapsed < 1h AND elapsed > 2h | Z3 UNSAT |  DONE |
| Percentage bounds | pct > 100 | Domain violation |  DONE |
| Count non-negative | count < 0 | Domain violation |  DONE |

### B. Rule-Level Conflicts

| Conflict Type | Example | Detection | Status |
|---------------|---------|-----------|--------|
| Permission-Prohibition | perm(use, count<5) vs prohib(use, count<10) | Overlap check | ⚠️ PARTIAL |
| Duty-Prohibition | duty(pay) vs prohib(pay) | Overlap check | ⚠️ PARTIAL |
| Duty incompatibility | duty(A) vs duty(¬A) | Mutual exclusion | 🚫 NOT DONE |

### C. Composite Constraint Conflicts

| Conflict Type | Example | Detection | Status |
|---------------|---------|-----------|--------|
| AND contradiction | and(count<5, count>10) | UNSAT | ⚠️ PARTIAL |
| OR unsatisfiable | or(count<0, count<0) | All branches UNSAT | 🚫 NOT DONE |
| XONE overlap | xone(count<10, count<20) | Multiple SAT | 🚫 NOT DONE |
| XONE empty | xone(count<0, count<0) | No branch SAT | 🚫 NOT DONE |

### D. Cross-Policy Conflicts

| Conflict Type | Example | Detection | Status |
|---------------|---------|-----------|--------|
| Inheritance violation | Child expands parent permission | Subsumption | 🚫 NOT DONE |
| Asset conflict | Different policies on same asset | Cross-check | 🚫 NOT DONE |

---

## 5. Data Types - Implementation Status

### XSD Types Supported

| XSD Type | Normalizer | Z3 Sort | Status |
|----------|------------|---------|--------|
| `xsd:integer` | `to_integer` | `IntSort()` |  DONE |
| `xsd:decimal` | `to_float` | `RealSort()` |  DONE |
| `xsd:double` | `to_float` | `RealSort()` |  DONE |
| `xsd:dateTime` | `datetime_to_timestamp` | `IntSort()` |  DONE |
| `xsd:date` | `datetime_to_timestamp` | `IntSort()` |  DONE |
| `xsd:duration` | `duration_to_seconds` | `IntSort()` |  DONE |
| `xsd:string` | `none` | `StringSort()` | ⚠️ PARTIAL |
| `xsd:anyURI` | `to_uri` | `StringSort()` | ⚠️ PARTIAL |

### Python Types Handled

| Python Type | Normalization | Status |
|-------------|---------------|--------|
| `int` | Pass through |  DONE |
| `float` | Pass through |  DONE |
| `Decimal` | Convert to float |  DONE |
| `datetime` | Convert to timestamp |  DONE |
| `timedelta` | Convert to seconds |  DONE |
| `str` (ISO datetime) | Parse and convert |  DONE |
| `str` (ISO duration) | Parse and convert |  DONE |
| `str` (literal) | Pass through | ⚠️ PARTIAL |

---

## 6. Summary Table

| Category | Total | Implemented | Partial | Not Done |
|----------|-------|-------------|---------|----------|
| Left Operands | 31 | 14 (45%) | 2 (6%) | 15 (49%) |
| Operators | 12 | 6 (50%) | 0 | 6 (50%) |
| Logical Ops | 4 | 0 | 3 (75%) | 1 (25%) |
| Conflict Types | 12 | 5 (42%) | 3 (25%) | 4 (33%) |
| XSD Types | 8 | 6 (75%) | 2 (25%) | 0 |

### Overall: ~50% Complete for Self-Contained Analysis

---

## 7. What's Needed for Full Self-Contained Support

### Phase 1: Complete Set Operators (HIGH PRIORITY)
Files to modify:
- `src/encoder/z3_encoder.py` - Add set operator encoding

### Phase 2: Fix Composite Constraints (HIGH PRIORITY)
Files to modify:
- `src/parser/ttl_parser.py` - Fix AND/OR/XONE parsing
- `src/encoder/z3_encoder.py` - Add composite encoding

### Phase 3: Complete Conflict Detection (MEDIUM PRIORITY)
Files to modify:
- `src/reasoner/conflict_detector.py` - Add all conflict types

### Phase 4: Add Oracles for Grounded (LOWER PRIORITY for self-contained)
Files to create:
- `src/oracles/` - Oracle framework

---

## 8. Files to Update NOW

### Step 1: Replace z3_encoder.py
```bash
cp outputs/encoder/z3_encoder_complete.py src/encoder/z3_encoder.py
```

This adds:
-  Set operators (isAnyOf, isNoneOf, isAllOf, hasPart, isPartOf, isA)
-  String variable support for grounded operands
-  Better XONE encoding
-  Composite constraint registration

### Step 2: Run tests to verify
```bash
uv run pytest tests/ -v
```

### Step 3: Test with TTL files
```bash
uv run python test_ttl_files.py -v
```