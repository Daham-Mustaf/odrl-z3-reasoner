# Resolution Test Suite - 47 Tests

## Comparison Operators (01-09)
| Test | Expected | Description |
|------|----------|-------------|
| 01 | CONFLICT | eq 300 ∧ eq 600 |
| 02 | CONSISTENT | eq 300 ∧ eq 300 |
| 03 | CONFLICT | ≤300 ∧ ≥600 |
| 04 | CONSISTENT | ≤1200 ∧ ≥300 |
| 05 | CONFLICT | <150 ∧ >300 |
| 06 | CONSISTENT | <300 ∧ >72 |
| 07 | CONFLICT | =300 ∧ ≠300 |
| 08 | CONSISTENT | =300 ∧ ≠600 |
| 09 | CONSISTENT | ≥300 ∧ ≤300 (exactly 300) |

## Set Operators (10-15, 25)
| Test | Expected | Description |
|------|----------|-------------|
| 10 | CONSISTENT | isAnyOf ∧ ≥300 |
| 11 | CONFLICT | isAnyOf ∧ >600 |
| 12 | CONSISTENT | isNoneOf ∧ =300 |
| 13 | CONFLICT | isNoneOf [..300] ∧ =300 |
| 14 | CONSISTENT | isAllOf identical |
| 15 | CONFLICT | isAllOf different |
| 25 | CONFLICT | isAnyOf ∧ isNoneOf |

## Unit Handling (16-17, 24, 39-43)
| Test | Expected | Description |
|------|----------|-------------|
| 16 | CONSISTENT | DPI vs PPI (independent vars) |
| 17 | CONFLICT | PPI ≤300 ∧ ≥600 |
| 24 | CONFLICT | Full IRI unit |
| 39 | CONSISTENT | DPI eq 72 ∧ PPI eq 300 |
| 40 | UNKNOWN | Missing unit |
| 41 | UNKNOWN/CONSISTENT | Mixed units |
| 42 | CONSISTENT | Full IRI same unit |
| 43 | CONSISTENT | Full IRI different units |

## Deontic (19-20, 22)
| Test | Expected | Description |
|------|----------|-------------|
| 18 | CONSISTENT | ODRL example |
| 19 | DEONTIC-CONFLICT | Perm ∩ Prohib |
| 20 | CONSISTENT | Perm ∩ Prohib = ∅ |
| 21 | CONSISTENT | 3 constraints |
| 22 | CONSISTENT | Web license |
| 23 | CONFLICT | Tiered licensing |

## OR Operator (26-28)
| Test | Expected | Description |
|------|----------|-------------|
| 26 | CONSISTENT | OR(≤150, ≥300) |
| 27 | CONSISTENT | (≤150 OR ≥600) AND ≥72 |
| 28 | CONFLICT | (≤72 OR =300) AND >300 |

## XONE Operator (29-32)
| Test | Expected | Description |
|------|----------|-------------|
| 29 | CONSISTENT | XONE(≤150, ≥300) disjoint |
| 30 | CONSISTENT | XONE(≤300, ≥150) overlap |
| 31 | CONSISTENT | XONE 3 branches |
| 32 | CONFLICT | XONE(≤150, ≥600) AND =300 |

## Tautology (33-35)
| Test | Expected | Description |
|------|----------|-------------|
| 33 | TAUTOLOGY | ≥0 (domain is (0,∞)) |
| 34 | TAUTOLOGY | OR(≤300, >300) |
| 35 | TAUTOLOGY | >0 |

## Redundancy (36-38)
| Test | Expected | Description |
|------|----------|-------------|
| 36 | REDUNDANT | Duplicate constraints |
| 37 | REDUNDANT | ≤300 ∧ ≤600 (subsumed) |
| 38 | REDUNDANT | ≤300 ∧ ≥0 (tautology in AND) |

## Unsatisfiable (44-47)
| Test | Expected | Description |
|------|----------|-------------|
| 44 | UNSATISFIABLE | eq -100 |
| 45 | UNSATISFIABLE | lt 0 |
| 46 | UNSATISFIABLE | lteq 0 |
| 47 | UNSATISFIABLE | eq 0 |

## Summary
- **CONFLICT**: 01, 03, 05, 07, 11, 13, 15, 17, 23, 24, 25, 28, 32
- **CONSISTENT**: 02, 04, 06, 08, 09, 10, 12, 14, 16, 18, 20, 21, 22, 26, 27, 29, 30, 31, 39, 42, 43
- **DEONTIC-CONFLICT**: 19
- **TAUTOLOGY**: 33, 34, 35
- **REDUNDANT**: 36, 37, 38
- **UNSATISFIABLE**: 44, 45, 46, 47
- **UNKNOWN**: 40, 41

Run: `uv run python main.py tests/ttl/resolution --all`
