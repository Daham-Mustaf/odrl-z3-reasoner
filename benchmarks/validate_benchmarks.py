"""
Validate ODRL-SA benchmark problems by running each through Z3.
Splits the combined file into individual problems and checks results.
"""
import subprocess, os, re, tempfile

BENCHMARKS = {
    "ODRL-BND-001": {
        "expected": "sat",
        "desc": "Percentage overlap [30,80]",
        "logic": "QF_LRA",
        "smt": """
(set-logic QF_LRA)
(declare-const percentage Real)
(assert (>= percentage 0))
(assert (<= percentage 100))
(assert (<= percentage 80))
(assert (>= percentage 30))
(check-sat)
(get-model)
(exit)
"""
    },
    "ODRL-BND-002": {
        "expected": "unsat",
        "desc": "Percentage empty intersection",
        "logic": "QF_LRA",
        "smt": """
(set-logic QF_LRA)
(declare-const percentage Real)
(assert (>= percentage 0))
(assert (<= percentage 100))
(assert (<= percentage 20))
(assert (>= percentage 60))
(check-sat)
(exit)
"""
    },
    "ODRL-DNT-001": {
        "expected": "sat",
        "desc": "Deontic conflict: resolution [150,300]",
        "logic": "QF_LRA",
        "smt": """
(set-logic QF_LRA)
(declare-const resolution Real)
(assert (> resolution 0))
(assert (<= resolution 300))
(assert (>= resolution 150))
(check-sat)
(get-model)
(exit)
"""
    },
    "ODRL-DNT-002": {
        "expected": "unsat",
        "desc": "No deontic conflict: disjoint ranges",
        "logic": "QF_LRA",
        "smt": """
(set-logic QF_LRA)
(declare-const resolution Real)
(assert (> resolution 0))
(assert (<= resolution 100))
(assert (>= resolution 300))
(check-sat)
(exit)
"""
    },
    "ODRL-UNT-001": {
        "expected": "sat",
        "desc": "Deontic conflict: payAmount EUR [0,200]",
        "logic": "QF_LRA",
        "smt": """
(set-logic QF_LRA)
(declare-const payAmount_EUR Real)
(assert (>= payAmount_EUR 0))
(assert (<= payAmount_EUR 500))
(assert (<= payAmount_EUR 200))
(check-sat)
(get-model)
(exit)
"""
    },
    "ODRL-UNT-002": {
        "expected": "sat",
        "desc": "Unit mismatch: EUR vs USD (independent)",
        "logic": "QF_LRA",
        "smt": """
(set-logic QF_LRA)
(declare-const payAmount_EUR Real)
(declare-const payAmount_USD Real)
(assert (>= payAmount_EUR 0))
(assert (>= payAmount_USD 0))
(assert (>= payAmount_EUR 100))
(assert (<= payAmount_USD 50))
(check-sat)
(get-model)
(exit)
"""
    },
    "ODRL-MIX-001": {
        "expected": "sat",
        "desc": "Multi-constraint: count+dateTime overlap",
        "logic": "QF_LIA",
        "smt": """
(set-logic QF_LIA)
(declare-const count Int)
(declare-const dateTime Int)
(assert (>= count 0))
(assert (<= count 100))
(assert (<= dateTime 1735689599))
(assert (>= count 20))
(assert (>= dateTime 1704067200))
(check-sat)
(get-model)
(exit)
"""
    },
    "ODRL-INH-001": {
        "expected": "unsat",
        "desc": "Valid inheritance: child ⊆ parent",
        "logic": "QF_LIA",
        "smt": """
(set-logic QF_LIA)
(declare-const count Int)
(assert (>= count 0))
(assert (<= count 50))
(assert (> count 100))
(check-sat)
(exit)
"""
    },
    "ODRL-INH-002": {
        "expected": "sat",
        "desc": "Invalid inheritance: child exceeds parent",
        "logic": "QF_LIA",
        "smt": """
(set-logic QF_LIA)
(declare-const count Int)
(assert (>= count 0))
(assert (<= count 200))
(assert (> count 50))
(check-sat)
(get-model)
(exit)
"""
    },
}

print("=" * 70)
print("ODRL-SA Benchmark Validation")
print("=" * 70)
print()

passed = 0
failed = 0

for name, bench in BENCHMARKS.items():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.smt2', delete=False) as f:
        f.write(bench["smt"])
        f.flush()
        result = subprocess.run(
            ['python3', '-c', f'''
from z3 import *
s = Solver()
s.from_string(open("{f.name}").read())
r = s.check()
print("sat" if r == sat else "unsat" if r == unsat else "unknown")
if r == sat:
    m = s.model()
    for d in m.decls():
        print(f"  {{d.name()}} = {{m[d]}}")
'''],
            capture_output=True, text=True
        )
        os.unlink(f.name)

    actual = result.stdout.strip().split('\n')[0] if result.stdout.strip() else "error"
    ok = actual == bench["expected"]
    status = "✓" if ok else "✗"

    if ok:
        passed += 1
    else:
        failed += 1

    print(f"  {status}  {name:20s}  expected={bench['expected']:6s}  got={actual:6s}  | {bench['desc']}")

    # Print model for sat instances
    if actual == "sat" and result.stdout.strip():
        for line in result.stdout.strip().split('\n')[1:]:
            print(f"     {line}")

print()
print("=" * 70)
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 70)
