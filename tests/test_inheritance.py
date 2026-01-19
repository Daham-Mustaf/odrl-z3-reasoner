# tests/test_inheritance.py
"""
Test monotonic constraint inheritance.

Formal Model:
- Valid inheritance: child ⇒ parent
- Violation: SAT(child ∧ ¬parent)
"""

import pytest
from pathlib import Path

from src.parser.ttl_parser import TTLParser
from src.parser.rdf_extractor import RDFExtractor
from src.normalizer.constraint_normalizer import ConstraintNormalizer
from src.normalizer.canonical_normalizer import ConstraintCanonicalizer
from src.encoder.z3_encoder import Z3Encoder, ClassHierarchy
from src.reasoner.inheritance_checker import InheritanceChecker

TEST_DATA_DIR = Path(__file__).parent / "test_data" / "inheritance"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_policy(ttl_file: str, debug: bool = False):
    """Load and process a policy from TTL file"""
    
    file_path = TEST_DATA_DIR / ttl_file
    if not file_path.exists():
        pytest.skip(f"Test file not found: {file_path}")
    
    parser = TTLParser(debug=debug)
    graph = parser.parse_file(str(file_path))
    
    policies = parser.get_policies()
    if not policies:
        return None, None, None
    
    extractor = RDFExtractor(graph, debug=debug)
    
    # Find parent and child policies
    parent_policy = None
    child_policy = None
    
    for policy_uri in policies:
        policy = extractor.extract_policy(policy_uri)
        
        # Normalize
        normalizer = ConstraintNormalizer(debug=debug)
        policy.constraints = normalizer.normalize_all(policy.constraints)
        
        # Canonicalize
        canonicalizer = ConstraintCanonicalizer(debug=debug)
        policy.constraints = canonicalizer.canonicalize(policy.constraints)
        
        # Determine if parent or child
        policy_id = str(policy_uri)
        if 'parent' in policy_id.lower():
            parent_policy = policy
        elif 'child' in policy_id.lower():
            child_policy = policy
    
    hierarchy = ClassHierarchy(graph)
    encoder = Z3Encoder(hierarchy=hierarchy, debug=debug)
    
    return parent_policy, child_policy, encoder

# =============================================================================
# TEST CASES
# =============================================================================

class InheritanceTestCase:
    """Test case for inheritance"""
    def __init__(self, file: str, expected_violations: int,
                 expected_types: list = None, description: str = ""):
        self.file = file
        self.expected_violations = expected_violations
        self.expected_types = expected_types or []
        self.description = description

INHERITANCE_TESTS = [
    InheritanceTestCase(
        file="valid_restriction.ttl",
        expected_violations=0,
        description="Valid: Child restricts parent (count<=50 ⊂ count<=100)"
    ),
    InheritanceTestCase(
        file="expansion_violation.ttl",
        expected_violations=1,
        expected_types=["expansion"],
        description="Violation: Child expands parent (count<=100 ⊃ count<=50)"
    ),
    InheritanceTestCase(
        file="inconsistent_child.ttl",
        expected_violations=1,
        expected_types=["inconsistent"],
        description="Violation: Child has unsatisfiable constraints"
    ),
    InheritanceTestCase(
        file="redundant_child.ttl",
        expected_violations=1,
        expected_types=["redundant"],
        description="Warning: Child adds no restriction"
    ),
    InheritanceTestCase(
        file="multi_constraint_valid.ttl",
        expected_violations=0,
        description="Valid: Child restricts multiple dimensions"
    ),
    InheritanceTestCase(
        file="partial_expansion.ttl",
        expected_violations=1,
        expected_types=["expansion"],
        description="Violation: Child restricts one, expands another"
    ),
]

XONE_INHERITANCE_TESTS = [
    InheritanceTestCase(
        file="xone_choice_collapse.ttl",
        expected_violations=0,
        description="Valid: XONE choice collapsed to single branch"
    ),
    InheritanceTestCase(
        file="xone_branch_addition.ttl",
        expected_violations=1,
        expected_types=["expansion"],
        description="Violation: XONE adds new branch"
    ),
    InheritanceTestCase(
        file="xone_branch_restriction.ttl",
        expected_violations=0,
        description="Valid: XONE branches restricted"
    ),
    InheritanceTestCase(
        file="xone_to_and_violation.ttl",
        expected_violations=1,
        expected_types=["expansion"],
        description="Violation: XONE changed to AND"
    ),
]

OR_XONE_TESTS = [
    InheritanceTestCase(
        file="or_valid_restriction.ttl",
        expected_violations=0,
        description="Child restricts OR branch - valid"
    ),
    InheritanceTestCase(
        file="or_expansion.ttl",
        expected_violations=1,
        expected_types=["expansion"],
        description="Child expands OR branch - violation"
    ),
    InheritanceTestCase(
        file="xone_to_single.ttl",
        expected_violations=0,
        description="Child collapses XONE to single branch - valid"
    ),
]

# =============================================================================
# PARAMETERIZED TESTS
# =============================================================================

@pytest.mark.parametrize("test_case", INHERITANCE_TESTS, ids=lambda t: t.file)
def test_basic_inheritance(test_case: InheritanceTestCase):
    """Test basic inheritance patterns"""
    
    parent, child, encoder = load_policy(test_case.file, debug=True)
    
    if parent is None or child is None:
        pytest.skip(f"Could not load parent/child from {test_case.file}")
    
    checker = InheritanceChecker(encoder, debug=True)
    violations = checker.check_inheritance(parent, child)
    
    print(f"\n📋 {test_case.description}")
    print(f"   Expected violations: {test_case.expected_violations}")
    print(f"   Actual violations: {len(violations)}")
    
    for v in violations:
        print(f"   • {v.violation_type}: {v.description[:60]}...")
    
    assert len(violations) == test_case.expected_violations, \
        f"Expected {test_case.expected_violations} violations, got {len(violations)}"
    
    if test_case.expected_types:
        actual_types = [v.violation_type for v in violations]
        for expected_type in test_case.expected_types:
            assert expected_type in actual_types, \
                f"Expected violation type '{expected_type}' not found"

@pytest.mark.parametrize("test_case", XONE_INHERITANCE_TESTS, ids=lambda t: t.file)
def test_xone_inheritance(test_case: InheritanceTestCase):
    """Test XONE-specific inheritance patterns"""
    
    parent, child, encoder = load_policy(test_case.file, debug=True)
    
    if parent is None or child is None:
        pytest.skip(f"Could not load parent/child from {test_case.file}")
    
    checker = InheritanceChecker(encoder, debug=True)
    violations = checker.check_inheritance(parent, child)
    
    print(f"\n📋 {test_case.description}")
    print(f"   Expected violations: {test_case.expected_violations}")
    print(f"   Actual violations: {len(violations)}")
    
    for v in violations:
        print(f"   • {v.violation_type}: {v.description[:60]}...")
    
    assert len(violations) == test_case.expected_violations

# =============================================================================
# INDIVIDUAL TESTS
# =============================================================================

def test_valid_restriction():
    """Test: child(count<=50) ⊂ parent(count<=100)"""
    
    parent, child, encoder = load_policy("valid_restriction.ttl", debug=True)
    
    if parent is None or child is None:
        pytest.skip("Test file not found")
    
    checker = InheritanceChecker(encoder, debug=True)
    violations = checker.check_inheritance(parent, child)
    
    assert len(violations) == 0, "Should have no violations"
    print("\n✓ Valid restriction: count<=50 ⊂ count<=100")

def test_expansion_violation():
    """Test: child(count<=100) ⊃ parent(count<=50) is violation"""
    
    parent, child, encoder = load_policy("expansion_violation.ttl", debug=True)
    
    if parent is None or child is None:
        pytest.skip("Test file not found")
    
    checker = InheritanceChecker(encoder, debug=True)
    violations = checker.check_inheritance(parent, child)
    
    assert len(violations) >= 1, "Should detect expansion violation"
    assert any(v.violation_type == "expansion" for v in violations)
    
    # Check counterexample
    expansion = next(v for v in violations if v.violation_type == "expansion")
    assert expansion.counterexample is not None
    print(f"\n✓ Expansion detected with counterexample: {expansion.counterexample}")

# =============================================================================
# SUMMARY TEST
# =============================================================================

def test_inheritance_summary():
    """Print inheritance test summary"""
    
    print("\n" + "="*70)
    print("📋 INHERITANCE CHECKING CAPABILITIES")
    print("="*70)
    
    print("""
    Supported Checks:
    ─────────────────
    Expansion violation    SAT(child ∧ ¬parent)
    Internal inconsistency UNSAT(child)
    Redundancy warning     UNSAT(parent ∧ ¬child)
    Multi-constraint       Conjunction handling
    XONE inheritance       Branch subset checking
    
    Formal Model:
    ─────────────
    Valid inheritance: ⟦child⟧ ⇒ ⟦parent⟧
    Violation:         SAT(⟦child⟧ ∧ ¬⟦parent⟧)
    
    XONE Rules:
    ───────────
    • Collapse:    XONE(A,B) → A         ✓ Valid
    • Add branch:  XONE(A,B) → XONE(A,B,C) ✗ Violation
    • Restrict:    XONE(A,B) → XONE(A',B') ✓ if A'⊂A, B'⊂B
    • XONE→AND:    XONE(A,B) → AND(A,B)    ✗ Violation
    """)
    
    print("="*70)

# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])