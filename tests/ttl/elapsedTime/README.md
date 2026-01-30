# ODRL elapsedTime Complete Test Suite

## Overview

This test suite contains **20 valid ODRL/Turtle files** for testing the `odrl:elapsedTime` LeftOperand in the ODRL Static Analyzer (ODRL-SA). The tests are organized into two categories:

- **Tests 01-10**: Expected result is **CONFLICT** (INTERNAL-CONFLICT or DEONTIC-CONFLICT)
- **Tests 11-20**: Expected result is **CONSISTENT** (POSSIBLY-COMPATIBLE)

## Domain Specification

| Property | Value |
|----------|-------|
| Domain | (0, +∞) seconds (strictly positive, zero invalid) |
| Value Type | `xsd:duration` (ISO 8601) |
| Operators | eq, neq, lt, lteq, gt, gteq, isAnyOf, isNoneOf |
| Logical | and, or, xone |

## Duration Conversion Reference

| Duration | Seconds | Notes |
|----------|---------|-------|
| PT1S | 1 | 1 second |
| PT1M | 60 | 1 minute |
| PT30M | 1800 | 30 minutes |
| PT60M | 3600 | 60 minutes = 1 hour |
| PT1H | 3600 | 1 hour |
| PT2H | 7200 | 2 hours |
| PT4H | 14400 | 4 hours |
| PT6H | 21600 | 6 hours |
| PT10H | 36000 | 10 hours |
| P1D | 86400 | 1 day |

**Warning**: `P60M` means 60 MONTHS, not 60 minutes! Use `PT60M` for 60 minutes.

## Test Summary

### CONFLICT Tests (01-10)

| Test | Description | Conflict Type |
|------|-------------|---------------|
| 01 | Temporal range: ≤30min AND ≥60min | INTERNAL |
| 02 | Zero duration (domain violation) | INTERNAL |
| 03 | Contradictory equality: eq 30min AND eq 60min | INTERNAL |
| 04 | Point outside range: eq 60min AND lt 60min | INTERNAL |
| 05 | isAnyOf {1h,2h,3h} AND lt 30min | INTERNAL |
| 06 | isNoneOf {1h,2h} AND isAnyOf {1h,2h} | INTERNAL |
| 07 | XONE with AND forcing both branches | INTERNAL |
| 08 | OR with both branches impossible (lt 0 OR eq 0) | INTERNAL |
| 09 | Permission ≤4h AND Prohibition >2h (overlap 2h-4h) | DEONTIC |
| 10 | Multiple NEQ eliminates all isAnyOf options | INTERNAL |

### CONSISTENT Tests (11-20)

| Test | Description | Example Model |
|------|-------------|---------------|
| 11 | Valid window: ≥30min AND ≤2h | 1 hour |
| 12 | Simple upper bound: ≤60min (ODRL example) | 30 minutes |
| 13 | Stream start: ≥1 second | 1 second |
| 14 | Cue points: isAnyOf {15m,30m,45m} AND ≤1h | 30 minutes |
| 15 | isNoneOf {1h,2h} in range [30m,3h] | 90 minutes |
| 16 | XONE disjoint: ≤30min XOR ≥2h | 15 minutes |
| 17 | OR valid branch: lt 1h OR gt 10h | 30 minutes |
| 18 | Overlapping ranges: [30m,2h] ∩ [1h,3h] | 90 minutes |
| 19 | Deontic disjoint: perm ≥2h, prohib <1h | No overlap |
| 20 | Complex nested: ((≥30m AND ≤2h) OR ≥4h) AND ≤6h | 1 hour |

## File Naming Convention

```
test_XX_descriptive_name.ttl
```

Where XX is the test number (01-20).

## ODRL Best Practices Applied

1. **Explicit UIDs**: Every policy has `odrl:uid` for identification
2. **Descriptions**: Dublin Core `dct:description` on each policy
3. **Typed Constraints**: All constraints have `a odrl:Constraint`
4. **Named Constraints**: Reusable constraint IRIs (e.g., `ex:constraint_01a`)
5. **Standard Prefixes**: Uses standard ODRL, XSD, DCT prefixes
6. **Composite Structure**: Proper nesting with `odrl:and`, `odrl:or`, `odrl:xone`
7. **Duration Format**: ISO 8601 with `xsd:duration` datatype
8. **Inline Comments**: Each file contains analysis documentation

## Usage

```bash
# Validate all files
for f in *.ttl; do rapper -i turtle -c "$f"; done

# Parse with Python rdflib
python3 -c "
from rdflib import Graph
g = Graph()
g.parse('test_01_temporal_range_conflict.ttl', format='turtle')
print(f'Loaded {len(g)} triples')
"
```

## Running Tests with ODRL-SA

```bash
# Example: Test single file
odrl-sa analyze test_01_temporal_range_conflict.ttl

# Expected output for test 01: CONFLICT
# Expected output for test 11: CONSISTENT
```

## License

These test files are provided for testing the ODRL Static Analyzer and may be used freely for research and development purposes.
