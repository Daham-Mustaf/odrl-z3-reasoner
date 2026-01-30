# ODRL delayPeriod Complete Test Suite

## Overview

This test suite contains **20 valid ODRL/Turtle files** for testing the `odrl:delayPeriod` LeftOperand in the ODRL Static Analyzer (ODRL-SA). The tests are organized into two categories:

- **Tests 01-10**: Expected result is **CONFLICT** (INTERNAL-CONFLICT or DEONTIC-CONFLICT)
- **Tests 11-20**: Expected result is **CONSISTENT** (POSSIBLY-COMPATIBLE)

**IMPORTANT**: Test 02 is labeled as CONFLICT in the test numbering but is actually **CONSISTENT** - this is a key difference from `elapsedTime` where zero is invalid!

## Domain Specification

| Property | Value |
|----------|-------|
| Domain | **[0, +∞)** seconds (zero IS valid - means immediate action) |
| Value Type | `xsd:duration` (ISO 8601) |
| Recommended Operators | eq, gt, gteq (lower bounds typical) |
| Valid Operators | eq, neq, lt, lteq, gt, gteq, isAnyOf, isNoneOf |
| Logical | and, or, xone |

## KEY DIFFERENCE FROM elapsedTime

| Property | elapsedTime | delayPeriod |
|----------|-------------|-------------|
| Domain | **(0, +∞)** - zero INVALID | **[0, +∞)** - zero VALID |
| Zero meaning | N/A (domain violation) | "No delay, immediate action" |
| Typical operator | lteq (upper bound) | gteq (lower bound) |
| Semantic | "Valid FOR this duration" | "Must WAIT this duration" |

## Duration Conversion Reference

| Duration | Seconds | Notes |
|----------|---------|-------|
| PT0S | 0 | No delay - immediate (VALID!) |
| PT1M | 60 | 1 minute |
| PT30M | 1800 | 30 minutes |
| PT1H | 3600 | 1 hour |
| P1D | 86400 | 1 day |
| P7D | 604800 | 7 days (1 week) |
| P14D | 1209600 | 14 days (2 weeks) |
| P30D | 2592000 | 30 days (~1 month) |
| P60D | 5184000 | 60 days (~2 months) |
| P90D | 7776000 | 90 days (~3 months) |
| P365D | 31536000 | 365 days (~1 year) |

## Test Summary

### CONFLICT Tests (01, 03-10)

| Test | Description | Conflict Type |
|------|-------------|---------------|
| 01 | Impossible delay range: ≥60min AND ≤30min | INTERNAL |
| 03 | Contradictory equality: eq 30D AND eq 60D | INTERNAL |
| 04 | Point outside range: eq 60D AND lt 60D | INTERNAL |
| 05 | isAnyOf {7D,14D,30D} AND gt 60D | INTERNAL |
| 06 | isNoneOf {30D,60D} AND isAnyOf {30D,60D} | INTERNAL |
| 07 | XONE with forced both branches | INTERNAL |
| 08 | Negative delay (lt 0) - domain violation | INTERNAL |
| 09 | Permission ≥30D AND Prohibition ≤90D (overlap 30-90D) | DEONTIC |
| 10 | Multiple NEQ eliminates all isAnyOf options | INTERNAL |

### CONSISTENT Tests (02, 11-20)

| Test | Description | Example Model |
|------|-------------|---------------|
| **02** | **Zero delay valid (immediate action)** | **0 (immediate)** |
| 11 | Valid delay window: ≥7D AND ≤30D | 14 days |
| 12 | Simple minimum wait: ≥30D (typical pattern) | 30 days |
| 13 | Immediate action: eq 0 (no embargo) | 0 |
| 14 | Embargo tiers: isAnyOf {7D,14D,30D} AND ≤60D | 14 days |
| 15 | isNoneOf {30D,60D} in range [7D,90D] | 14 or 45 days |
| 16 | XONE disjoint: ≤7D XOR ≥30D | 3 days |
| 17 | OR valid branch: ≤1D OR ≥365D | 0 (immediate) |
| 18 | Overlapping ranges: [7D,60D] ∩ [30D,90D] | 45 days |
| 19 | Deontic disjoint: perm ≥60D, prohib <30D | No overlap |
| 20 | Complex nested: ((≥7D AND ≤30D) OR ≥90D) AND ≤365D | 14 days |

## Semantic Comparison with elapsedTime

```
elapsedTime lteq P30D:
┌─────────────────────────────────────────────────────────────────────┐
│  [Reference]═══════════════════════►[+30D]                          │
│              ✅ ACTION VALID          ❌ EXPIRED                     │
│              "Valid FOR 30 days"                                    │
└─────────────────────────────────────────────────────────────────────┘

delayPeriod gteq P30D:
┌─────────────────────────────────────────────────────────────────────┐
│  [Trigger]═══════════════════════►[+30D]════════════════════►       │
│            ❌ MUST WAIT              ✅ ACTION ALLOWED               │
│            "Wait UNTIL 30 days"                                     │
└─────────────────────────────────────────────────────────────────────┘

THEY ARE COMPLEMENTARY!

Combined: delayPeriod gteq P30D AND elapsedTime lteq P60D
┌─────────────────────────────────────────────────────────────────────┐
│  [t₀]═══════════════►[+30D]════════════════►[+60D]                  │
│       ❌ wait          ✅ VALID WINDOW        ❌ expired              │
│                       [30D to 60D]                                  │
└─────────────────────────────────────────────────────────────────────┘
```

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
g.parse('test_01_impossible_delay_range_conflict.ttl', format='turtle')
print(f'Loaded {len(g)} triples')
"
```

## Running Tests with ODRL-SA

```bash
# Example: Test single file
odrl-sa analyze test_01_impossible_delay_range_conflict.ttl

# Expected outputs:
# test_01: CONFLICT
# test_02: CONSISTENT (zero delay is VALID!)
# test_03-10: CONFLICT
# test_11-20: CONSISTENT
```

## Test Differences from elapsedTime Suite

| Test # | elapsedTime | delayPeriod |
|--------|-------------|-------------|
| 02 | eq 0 → CONFLICT | eq 0 → **CONSISTENT** |
| 08 | (lt 0 OR eq 0) → CONFLICT | lt 0 → CONFLICT |
| 13 | gteq 1s (minimal positive) | eq 0 (immediate) |

## License

These test files are provided for testing the ODRL Static Analyzer and may be used freely for research and development purposes.
