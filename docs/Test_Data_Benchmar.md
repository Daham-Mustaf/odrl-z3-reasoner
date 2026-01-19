# Test Data & Benchmark Design

## Philosophy
**Comprehensive, Realistic, Stressful** - Cover all operators, real policies, edge cases, and performance limits.

---

## 1. Test Dataset Structure

```
tests/
├── unit/                          # Single constraint tests
│   ├── operators/
│   │   ├── relational/
│   │   │   ├── eq.json
│   │   │   ├── neq.json
│   │   │   ├── lt.json
│   │   │   ├── lteq.json
│   │   │   ├── gt.json
│   │   │   └── gteq.json
│   │   ├── set/
│   │   │   ├── isA.json
│   │   │   ├── isAllOf.json
│   │   │   ├── isAnyOf.json
│   │   │   ├── isNoneOf.json
│   │   │   ├── hasPart.json
│   │   │   └── isPartOf.json
│   │   └── logical/
│   │       ├── and.json
│   │       ├── or.json
│   │       ├── xone.json
│   │       └── andSequence.json
│   ├── leftOperands/
│   │   ├── numeric/
│   │   │   ├── count.json
│   │   │   ├── percentage.json
│   │   │   └── payAmount.json
│   │   ├── temporal/
│   │   │   ├── dateTime.json
│   │   │   ├── elapsedTime.json
│   │   │   ├── delayPeriod.json
│   │   │   └── timeInterval.json
│   │   ├── set/
│   │   │   ├── language.json
│   │   │   ├── fileFormat.json
│   │   │   └── industry.json
│   │   └── spatial/
│   │       ├── spatial.json
│   │       └── spatialCoordinates.json
│   └── metadata/
│       ├── unit.json
│       ├── unitOfCount.json
│       └── dataType.json
│
├── integration/                   # Multi-constraint policies
│   ├── consistency/
│   │   ├── consistent_simple.json
│   │   ├── inconsistent_numeric.json
│   │   ├── inconsistent_temporal.json
│   │   └── inconsistent_mixed.json
│   ├── conflicts/
│   │   ├── permission_prohibition.json
│   │   ├── xone_violation.json
│   │   └── multiple_conflicts.json
│   ├── inheritance/
│   │   ├── valid_refinement.json
│   │   ├── expansion_numeric.json
│   │   ├── expansion_set.json
│   │   └── expansion_mixed.json
│   └── redundancy/
│       ├── simple_redundancy.json
│       ├── implied_constraints.json
│       └── transitive_redundancy.json
│
├── reference_policies/                    # Real ODRL policies
│   ├── creative_commons/
│   │   ├── cc_by.json
│   │   ├── cc_by_nc.json
│   │   └── cc_by_sa.json
│   ├── publishing/
│   │   ├── academic_license.json
│   │   ├── newspaper_syndication.json
│   │   └── ebook_drm.json
│   ├── data_sharing/
│   │   ├── open_data.json
│   │   ├── personal_data_gdpr.json
│   │   └── research_data.json
│   └── media/
│       ├── video_streaming.json
│       ├── music_licensing.json
│       └── photo_stock.json
│
├── edge_cases/                    # Corner cases
│   ├── empty_policy.json
│   ├── no_constraints.json
│   ├── single_constraint.json
│   ├── deeply_nested_logical.json
│   ├── all_operators.json
│   ├── circular_reference.json
│   ├── malformed_dates.json
│   └── extreme_values.json
│
├── stress/                        # Performance tests
│   ├── large_scale/
│   │   ├── 100_constraints.json
│   │   ├── 1000_constraints.json
│   │   ├── 10000_constraints.json
│   │   └── 100000_constraints.json
│   ├── deep_nesting/
│   │   ├── nested_10_levels.json
│   │   ├── nested_50_levels.json
│   │   └── nested_100_levels.json
│   ├── combinatorial/
│   │   ├── xone_10_options.json
│   │   ├── xone_100_options.json
│   │   └── and_or_mixed.json
│   └── inheritance/
│       ├── chain_10_levels.json
│       ├── chain_100_levels.json
│       └── diamond_inheritance.json
│
└── regression/                    # Previously found bugs
    ├── bug_001_dateTime_overflow.json
    ├── bug_002_xone_false_positive.json
    └── ...
```

---

## 2. Unit Test Examples

### 2.1 Operators

**Relational: `eq`**
```json
{
  "test_id": "unit_op_eq_001",
  "description": "Basic equality on count",
  "policy": {
    "@context": "http://www.w3.org/ns/odrl.jsonld",
    "@type": "Policy",
    "permission": [{
      "action": "use",
      "constraint": [{
        "leftOperand": "count",
        "operator": "eq",
        "rightOperand": 5
      }]
    }]
  },
  "expected": {
    "status": "VALID",
    "errors": 0,
    "warnings": 0
  }
}
```

**Set: `isAnyOf`**
```json
{
  "test_id": "unit_op_isAnyOf_001",
  "description": "File format in set",
  "policy": {
    "permission": [{
      "action": "distribute",
      "constraint": [{
        "leftOperand": "fileFormat",
        "operator": "isAnyOf",
        "rightOperand": ["image/jpeg", "image/png"]
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

**Logical: `xone`**
```json
{
  "test_id": "unit_op_xone_001",
  "description": "Exclusive one - valid",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "xone": [
          {"leftOperand": "spatial", "operator": "eq", "rightOperand": "Germany"},
          {"leftOperand": "spatial", "operator": "eq", "rightOperand": "France"}
        ]
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

### 2.2 Left Operands

**Numeric: `count`**
```json
{
  "test_id": "unit_leftOp_count_001",
  "description": "Count with inequality",
  "policy": {
    "permission": [{
      "action": "reproduce",
      "constraint": [{
        "leftOperand": "count",
        "operator": "lteq",
        "rightOperand": 10
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

**Temporal: `dateTime`**
```json
{
  "test_id": "unit_leftOp_dateTime_001",
  "description": "Valid date range",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "leftOperand": "dateTime",
        "operator": "gteq",
        "rightOperand": "2025-01-01T00:00:00Z",
        "dataType": "xsd:dateTime"
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

**Spatial: `spatial`**
```json
{
  "test_id": "unit_leftOp_spatial_001",
  "description": "Named geographic region",
  "policy": {
    "permission": [{
      "action": "distribute",
      "constraint": [{
        "leftOperand": "spatial",
        "operator": "eq",
        "rightOperand": "http://sws.geonames.org/2921044/"
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

---

## 3. Integration Test Examples

### 3.1 Inconsistency

**Inconsistent Numeric**
```json
{
  "test_id": "int_inconsistent_001",
  "description": "Impossible count constraint",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "and": [
          {"leftOperand": "count", "operator": "gt", "rightOperand": 100},
          {"leftOperand": "count", "operator": "lt", "rightOperand": 50}
        ]
      }]
    }]
  },
  "expected": {
    "status": "INCONSISTENT",
    "errors": 1,
    "issues": [{
      "type": "INCONSISTENCY",
      "rule_type": "permission",
      "message": "count gt 100 AND count lt 50"
    }]
  }
}
```

**Inconsistent Temporal**
```json
{
  "test_id": "int_inconsistent_002",
  "description": "Impossible date range",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "and": [
          {"leftOperand": "dateTime", "operator": "gteq", "rightOperand": "2025-06-01"},
          {"leftOperand": "dateTime", "operator": "lteq", "rightOperand": "2025-01-01"}
        ]
      }]
    }]
  },
  "expected": {
    "status": "INCONSISTENT",
    "errors": 1,
    "issues": [{
      "type": "INCONSISTENCY"
    }]
  }
}
```

### 3.2 Conflicts

**Permission-Prohibition Conflict**
```json
{
  "test_id": "int_conflict_001",
  "description": "Same action, overlapping constraints",
  "policy": {
    "permission": [{
      "uid": "perm:01",
      "action": "distribute",
      "constraint": [{
        "leftOperand": "fileFormat",
        "operator": "eq",
        "rightOperand": "image/jpeg"
      }]
    }],
    "prohibition": [{
      "uid": "prohib:01",
      "action": "distribute",
      "constraint": [{
        "leftOperand": "fileFormat",
        "operator": "isAnyOf",
        "rightOperand": ["image/jpeg", "image/png"]
      }]
    }]
  },
  "expected": {
    "status": "CONFLICT",
    "errors": 1,
    "issues": [{
      "type": "PERMISSION_PROHIBITION_CONFLICT",
      "permission_id": "perm:01",
      "prohibition_id": "prohib:01",
      "counterexample": {
        "fileFormat": "image/jpeg"
      }
    }]
  }
}
```

**XONE Violation**
```json
{
  "test_id": "int_conflict_002",
  "description": "Multiple XONE constraints satisfied",
  "policy": {
    "duty": [{
      "action": "compensate",
      "constraint": [{
        "xone": [
          {"leftOperand": "spatial", "operator": "eq", "rightOperand": "Germany"},
          {"leftOperand": "spatial", "operator": "eq", "rightOperand": "Europe"}
        ]
      }]
    }]
  },
  "expected": {
    "status": "CONFLICT",
    "errors": 1,
    "issues": [{
      "type": "XONE_VIOLATION",
      "satisfied_count": 2
    }]
  },
  "note": "Germany is part of Europe, both satisfied"
}
```

### 3.3 Inheritance

**Valid Refinement**
```json
{
  "test_id": "int_inherit_001",
  "description": "Child more restrictive",
  "parent_policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "leftOperand": "dateTime",
        "operator": "gteq",
        "rightOperand": "2025-01-01"
      }]
    }]
  },
  "child_policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "leftOperand": "dateTime",
        "operator": "gteq",
        "rightOperand": "2025-06-01"
      }]
    }]
  },
  "expected": {
    "inheritance_valid": true,
    "errors": 0
  }
}
```

**Expansion Violation**
```json
{
  "test_id": "int_inherit_002",
  "description": "Child expands permissions",
  "parent_policy": {
    "permission": [{
      "action": "distribute",
      "constraint": [{
        "leftOperand": "fileFormat",
        "operator": "eq",
        "rightOperand": "image/jpeg"
      }]
    }]
  },
  "child_policy": {
    "permission": [{
      "action": "distribute",
      "constraint": [{
        "leftOperand": "fileFormat",
        "operator": "isAnyOf",
        "rightOperand": ["image/jpeg", "image/png"]
      }]
    }]
  },
  "expected": {
    "status": "EXPANSION",
    "inheritance_valid": false,
    "errors": 1,
    "issues": [{
      "type": "EXPANSION",
      "counterexample": {
        "fileFormat": "image/png"
      }
    }]
  }
}
```

### 3.4 Redundancy

**Simple Redundancy**
```json
{
  "test_id": "int_redundancy_001",
  "description": "Weaker constraint redundant",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "and": [
          {"uid": "c1", "leftOperand": "count", "operator": "lteq", "rightOperand": 50},
          {"uid": "c2", "leftOperand": "count", "operator": "lteq", "rightOperand": 100}
        ]
      }]
    }]
  },
  "expected": {
    "status": "VALID",
    "warnings": 1,
    "issues": [{
      "type": "REDUNDANCY",
      "severity": "WARNING",
      "redundant": "c2",
      "implied_by": "c1"
    }]
  }
}
```

---

## 4. Real-World Test Examples

### 4.1 Creative Commons BY

```json
{
  "test_id": "real_cc_by_001",
  "description": "Creative Commons Attribution",
  "policy": {
    "@type": "Set",
    "permission": [{
      "action": ["reproduce", "distribute", "modify"],
      "duty": [{
        "action": "attribute"
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

### 4.2 Academic Publishing

```json
{
  "test_id": "real_academic_001",
  "description": "Academic journal article license",
  "policy": {
    "permission": [{
      "action": "distribute",
      "constraint": [{
        "and": [
          {"leftOperand": "purpose", "operator": "eq", "rightOperand": "education"},
          {"leftOperand": "count", "operator": "lteq", "rightOperand": 1},
          {"leftOperand": "dateTime", "operator": "gteq", "rightOperand": "2025-01-01"}
        ]
      }],
      "duty": [{
        "action": "attribute"
      }]
    }],
    "prohibition": [{
      "action": "commercialize"
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

### 4.3 GDPR Data Sharing

```json
{
  "test_id": "real_gdpr_001",
  "description": "Personal data processing under GDPR",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "and": [
          {"leftOperand": "purpose", "operator": "eq", "rightOperand": "research"},
          {"leftOperand": "spatial", "operator": "eq", "rightOperand": "EU"},
          {"leftOperand": "delayPeriod", "operator": "lteq", "rightOperand": "P30D"}
        ]
      }],
      "duty": [{
        "action": "delete",
        "constraint": [{
          "leftOperand": "dateTime",
          "operator": "lteq",
          "rightOperand": "2026-12-31"
        }]
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

---

## 5. Edge Cases

### 5.1 Empty Policy
```json
{
  "test_id": "edge_empty_001",
  "description": "Policy with no rules",
  "policy": {
    "@type": "Policy"
  },
  "expected": {
    "status": "VALID",
    "warnings": 0
  }
}
```

### 5.2 Deeply Nested Logical
```json
{
  "test_id": "edge_nested_001",
  "description": "10 levels of AND nesting",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "and": [
          {"and": [
            {"and": [
              {"leftOperand": "count", "operator": "gt", "rightOperand": 0}
              // ... 7 more levels
            ]}
          ]}
        ]
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

### 5.3 All Operators
```json
{
  "test_id": "edge_all_ops_001",
  "description": "Policy using all operators",
  "policy": {
    "permission": [{
      "action": "use",
      "constraint": [{
        "and": [
          {"leftOperand": "count", "operator": "eq", "rightOperand": 5},
          {"leftOperand": "count", "operator": "neq", "rightOperand": 10},
          {"leftOperand": "percentage", "operator": "lt", "rightOperand": 50},
          {"leftOperand": "percentage", "operator": "lteq", "rightOperand": 100},
          {"leftOperand": "dateTime", "operator": "gt", "rightOperand": "2025-01-01"},
          {"leftOperand": "dateTime", "operator": "gteq", "rightOperand": "2025-01-01"},
          {"leftOperand": "fileFormat", "operator": "isA", "rightOperand": "ImageFormat"},
          {"leftOperand": "language", "operator": "isAnyOf", "rightOperand": ["en", "de"]},
          {"leftOperand": "language", "operator": "isNoneOf", "rightOperand": ["fr", "es"]}
        ]
      }]
    }]
  },
  "expected": {
    "status": "VALID"
  }
}
```

---

## 6. Stress Tests

### 6.1 Large Scale

**100 Constraints**
```python
# Generator script
def generate_large_policy(n_constraints):
    constraints = [
        {
            "leftOperand": "count",
            "operator": "lteq",
            "rightOperand": i
        }
        for i in range(1, n_constraints + 1)
    ]
    
    return {
        "test_id": f"stress_large_{n_constraints}",
        "description": f"Policy with {n_constraints} constraints",
        "policy": {
            "permission": [{
                "action": "use",
                "constraint": [{"and": constraints}]
            }]
        },
        "expected": {
            "status": "VALID",
            "max_time_ms": 5000  # Performance benchmark
        }
    }

# Generate tests
generate_large_policy(100)
generate_large_policy(1000)
generate_large_policy(10000)
```

### 6.2 Deep Nesting

**100 Levels Deep**
```python
def generate_deep_nesting(depth):
    def nest(level):
        if level == depth:
            return {"leftOperand": "count", "operator": "gt", "rightOperand": 0}
        return {"and": [nest(level + 1)]}
    
    return {
        "test_id": f"stress_depth_{depth}",
        "policy": {
            "permission": [{
                "action": "use",
                "constraint": [nest(0)]
            }]
        },
        "expected": {
            "status": "VALID",
            "max_time_ms": 1000
        }
    }
```

### 6.3 Combinatorial Explosion

**XONE with 100 Options**
```python
def generate_xone_stress(n_options):
    options = [
        {"leftOperand": "spatial", "operator": "eq", "rightOperand": f"Country{i}"}
        for i in range(n_options)
    ]
    
    return {
        "test_id": f"stress_xone_{n_options}",
        "policy": {
            "permission": [{
                "action": "use",
                "constraint": [{"xone": options}]
            }]
        },
        "expected": {
            "status": "VALID",
            "max_time_ms": 10000
        }
    }
```

### 6.4 Inheritance Chain

**100-Level Inheritance**
```python
def generate_inheritance_chain(depth):
    policies = []
    
    for i in range(depth):
        policy = {
            "uid": f"policy:{i}",
            "permission": [{
                "action": "use",
                "constraint": [{
                    "leftOperand": "count",
                    "operator": "lteq",
                    "rightOperand": 100 - i
                }]
            }]
        }
        
        if i > 0:
            policy["inheritsFrom"] = f"policy:{i-1}"
        
        policies.append(policy)
    
    return {
        "test_id": f"stress_inherit_chain_{depth}",
        "policies": policies,
        "expected": {
            "inheritance_valid": True,
            "max_time_ms": 5000
        }
    }
```

---

## 7. Benchmark Specifications

### 7.1 Performance Targets

| Test Category | Constraint Count | Max Time | Max Memory |
|--------------|------------------|----------|------------|
| Unit | 1 | 10ms | 10MB |
| Integration | 5-10 | 100ms | 50MB |
| Real-World | 10-50 | 500ms | 100MB |
| Stress-100 | 100 | 1s | 200MB |
| Stress-1K | 1,000 | 5s | 500MB |
| Stress-10K | 10,000 | 30s | 2GB |

### 7.2 Benchmark Metrics

```python
@dataclass
class BenchmarkResult:
    test_id: str
    constraint_count: int
    
    # Timing
    parse_time_ms: float
    classification_time_ms: float
    encoding_time_ms: float
    solving_time_ms: float
    total_time_ms: float
    
    # Memory
    peak_memory_mb: float
    
    # Correctness
    expected_status: str
    actual_status: str
    match: bool
    
    # SMT Stats
    smt_assertions: int
    smt_variables: int
    smt_solver_calls: int
```

### 7.3 Benchmark Runner

```python
class BenchmarkRunner:
    def run_benchmark_suite(self, test_dir: str) -> BenchmarkReport:
        results = []
        
        for test_file in self.discover_tests(test_dir):
            result = self.run_single_benchmark(test_file)
            results.append(result)
        
        return BenchmarkReport(
            total_tests=len(results),
            passed=sum(1 for r in results if r.match),
            failed=sum(1 for r in results if not r.match),
            avg_time_ms=mean(r.total_time_ms for r in results),
            max_time_ms=max(r.total_time_ms for r in results),
            avg_memory_mb=mean(r.peak_memory_mb for r in results),
            results=results
        )
    
    def run_single_benchmark(self, test_file: str) -> BenchmarkResult:
        test = load_test(test_file)
        
        # Start monitoring
        start_time = time.perf_counter()
        tracemalloc.start()
        
        # Run analysis
        with Timer() as parse_timer:
            policy = parse_policy(test["policy"])
        
        with Timer() as classify_timer:
            graph = classify_constraints(policy)
        
        with Timer() as encode_timer:
            formula = encode_to_smt(graph)
        
        with Timer() as solve_timer:
            result = analyze_policy(formula)
        
        # Stop monitoring
        total_time = (time.perf_counter() - start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return BenchmarkResult(
            test_id=test["test_id"],
            constraint_count=count_constraints(policy),
            parse_time_ms=parse_timer.elapsed_ms,
            classification_time_ms=classify_timer.elapsed_ms,
            encoding_time_ms=encode_timer.elapsed_ms,
            solving_time_ms=solve_timer.elapsed_ms,
            total_time_ms=total_time,
            peak_memory_mb=peak / 1024 / 1024,
            expected_status=test["expected"]["status"],
            actual_status=result.status,
            match=(result.status == test["expected"]["status"])
        )
```

---

## 8. Test Execution Plan

### 8.1 CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/unit/ -v
      - name: Upload coverage
        uses: codecov/codecov-action@v2
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/integration/ -v
  
  stress-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v2
      - name: Run stress tests
        run: pytest tests/stress/ -v --benchmark
  
  regression-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run regression tests
        run: pytest tests/regression/ -v
```

### 8.2 Test Commands

```bash
# Run all tests
pytest tests/

# Run by category
pytest tests/unit/
pytest tests/integration/
pytest tests/reference_policies/
pytest tests/stress/

# Run specific operator tests
pytest tests/unit/operators/relational/
pytest tests/unit/operators/set/

# Run benchmarks
pytest tests/stress/ --benchmark

# Run with coverage
pytest tests/ --cov=odrl_analyzer --cov-report=html

# Run stress tests only
pytest tests/stress/ -k "stress_large"

# Run inheritance tests
pytest tests/integration/inheritance/ -v
```

---

## 9. Test Coverage Goals

### 9.1 Code Coverage
- Overall: **>90%**
- Core encoding: **100%**
- Operator handlers: **100%**
- Error handling: **>80%**

### 9.2 Operator Coverage
- All 6 relational operators: **100%**
- All 6 set operators: **100%**
- All 3 logical operators: **100%**
- `andSequence`: **normalization only**

### 9.3 Left Operand Coverage
- Numeric (3): `count`, `percentage`, `payAmount`
- Temporal (5): `dateTime`, `elapsedTime`, `delayPeriod`, `timeInterval`, `meteredTime`
- Set (5): `language`, `fileFormat`, `industry`, `product`, `purpose`
- Spatial (2): `spatial`, `spatialCoordinates`
- **Total: 15+ left operands tested**

---

## 10. Benchmark Report Format

```
╔════════════════════════════════════════════════════════╗
║           ODRL Analyzer Benchmark Report              ║
╚════════════════════════════════════════════════════════╝

Test Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tests:        1,245
Passed:             1,243 (99.8%)
Failed:             2 (0.2%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Performance:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Average Time:       45ms
Max Time:           2,340ms (stress_10k)
P50:                23ms
P95:                156ms
P99:                890ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Memory:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Average Peak:       78MB
Max Peak:           1,234MB (stress_10k)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

By Category:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unit Tests:         567 passed, 0 failed (avg: 12ms)
Integration:        345 passed, 1 failed (avg: 67ms)
Real-World:         45 passed, 0 failed (avg: 123ms)
Stress:             286 passed, 1 failed (avg: 456ms)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failures:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. int_conflict_042: Expected CONFLICT, got VALID
2. stress_inherit_1000: Timeout (>30s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Final Test Plan Summary

### Test Dataset Size
- **Unit tests**: ~600
- **Integration tests**: ~350
- **Real-world tests**: ~50
- **Stress tests**: ~300
- **Total**: ~1,300 tests

### Coverage
- All operators: 
- All left operands: 
- All metadata: 
- Edge cases: 
- Performance limits: 
