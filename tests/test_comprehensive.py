# tests/test_comprehensive.py
"""
Comprehensive test suite with expected outcomes.
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

from src.parser.ttl_parser import TTLParser
from src.parser.rdf_extractor import RDFExtractor
from src.normalizer.constraint_normalizer import ConstraintNormalizer
from src.normalizer.canonical_normalizer import ConstraintCanonicalizer
from src.encoder.z3_encoder import Z3Encoder, ClassHierarchy
from src.reasoner.conflict_detector import ConflictDetector

TEST_DATA_DIR = Path(__file__).parent / "test_data"

@dataclass
class TestCase:
    """Test case specification"""
    file: str
    expected_conflicts: int
    expected_conflict_types: Optional[List[str]] = None
    description: str = ""

# =============================================================================
# TEST SPECIFICATIONS
# =============================================================================

ATOMIC_TESTS = [
    TestCase(
        file="atomic/numeric_simple_valid.ttl",
        expected_conflicts=0,
        description="Simple valid constraint - no conflict"
    ),
    TestCase(
        file="atomic/numeric_range_conflict.ttl",
        expected_conflicts=1,
        expected_conflict_types=["permission_prohibition"],
        description="Overlapping numeric ranges - conflict"
    ),
    TestCase(
        file="atomic/numeric_range_disjoint.ttl",
        expected_conflicts=0,
        description="Disjoint numeric ranges - no conflict"
    ),
]

LOGICAL_TESTS = [
    TestCase(
        file="logical/and_simple.ttl",
        expected_conflicts=0,
        description="Simple AND constraint"
    ),
    TestCase(
        file="logical/and_contradiction.ttl",
        expected_conflicts=1,
        expected_conflict_types=["and_contradiction"],
        description="AND with contradictory children"
    ),
    TestCase(
        file="logical/or_simple.ttl",
        expected_conflicts=0,
        description="Simple OR constraint"
    ),
    TestCase(
        file="logical/xone_valid.ttl",
        expected_conflicts=0,
        description="Valid XONE with disjoint branches"
    ),
    TestCase(
        file="logical/xone_overlap.ttl",
        expected_conflicts=1,
        expected_conflict_types=["xone_overlap"],
        description="XONE with overlapping branches"
    ),
]

TEMPORAL_TESTS = [
    TestCase(
        file="temporal/time_window_disjoint.ttl",
        expected_conflicts=0,
        description="Disjoint time windows - no conflict"
    ),
    TestCase(
        file="temporal/time_window_overlap.ttl",
        expected_conflicts=1,
        expected_conflict_types=["permission_prohibition"],
        description="Overlapping time windows - conflict"
    ),
]

STRESS_TESTS = [
    TestCase(
        file="stress/deep_and_nesting.ttl",
        expected_conflicts=0,
        description="Deep AND nesting - should flatten and work"
    ),
]

# =============================================================================
# TEST RUNNER
# =============================================================================

def run_policy_test(ttl_file: str, debug: bool = False):
    """Run complete pipeline on a policy file"""
    
    file_path = TEST_DATA_DIR / ttl_file
    if not file_path.exists():
        pytest.skip(f"Test file not found: {file_path}")
    
    # Parse
    parser = TTLParser(debug=debug)
    graph = parser.parse_file(str(file_path))
    
    policies = parser.get_policies()
    if not policies:
        return [], None
    
    # Extract
    extractor = RDFExtractor(graph, debug=debug)
    policy = extractor.extract_policy(policies[0])
    
    # Normalize
    normalizer = ConstraintNormalizer(debug=debug)
    policy.constraints = normalizer.normalize_all(policy.constraints)
    
    # Canonicalize
    canonicalizer = ConstraintCanonicalizer(debug=debug)
    policy.constraints = canonicalizer.canonicalize(policy.constraints)
    
    # Detect conflicts
    hierarchy = ClassHierarchy(graph)
    encoder = Z3Encoder(hierarchy=hierarchy, debug=debug)
    
    detector = ConflictDetector(debug=debug)
    detector.encoder = encoder
    conflicts = detector.detect_all_conflicts(policy)
    
    return conflicts, canonicalizer

# =============================================================================
# PARAMETERIZED TESTS
# =============================================================================

@pytest.mark.parametrize("test_case", ATOMIC_TESTS, ids=lambda t: t.file)
def test_atomic_constraints(test_case: TestCase):
    """Test atomic constraint handling"""
    conflicts, _ = run_policy_test(test_case.file, debug=True)
    
    print(f"\n📋 {test_case.description}")
    print(f"   Expected conflicts: {test_case.expected_conflicts}")
    print(f"   Actual conflicts: {len(conflicts)}")
    
    assert len(conflicts) == test_case.expected_conflicts, \
        f"Expected {test_case.expected_conflicts} conflicts, got {len(conflicts)}"
    
    if test_case.expected_conflict_types:
        actual_types = [c.conflict_type for c in conflicts]
        for expected_type in test_case.expected_conflict_types:
            assert expected_type in actual_types, \
                f"Expected conflict type '{expected_type}' not found in {actual_types}"

@pytest.mark.parametrize("test_case", LOGICAL_TESTS, ids=lambda t: t.file)
def test_logical_operators(test_case: TestCase):
    """Test logical operator handling"""
    conflicts, _ = run_policy_test(test_case.file, debug=True)
    
    print(f"\n📋 {test_case.description}")
    print(f"   Expected conflicts: {test_case.expected_conflicts}")
    print(f"   Actual conflicts: {len(conflicts)}")
    
    assert len(conflicts) == test_case.expected_conflicts

@pytest.mark.parametrize("test_case", TEMPORAL_TESTS, ids=lambda t: t.file)
def test_temporal_constraints(test_case: TestCase):
    """Test temporal constraint handling"""
    conflicts, _ = run_policy_test(test_case.file, debug=True)
    
    print(f"\n📋 {test_case.description}")
    print(f"   Expected conflicts: {test_case.expected_conflicts}")
    print(f"   Actual conflicts: {len(conflicts)}")
    
    assert len(conflicts) == test_case.expected_conflicts

@pytest.mark.parametrize("test_case", STRESS_TESTS, ids=lambda t: t.file)
def test_stress_cases(test_case: TestCase):
    """Test stress cases"""
    conflicts, _ = run_policy_test(test_case.file, debug=True)
    
    print(f"\n📋 {test_case.description}")
    assert len(conflicts) == test_case.expected_conflicts

# =============================================================================
# SEMANTIC INVARIANT TESTS
# =============================================================================

def test_and_commutativity():
    """Test AND(A,B) ≡ AND(B,A)"""
    
    conflicts_a, canon_a = run_policy_test("semantic/and_commutativity_a.ttl")
    conflicts_b, canon_b = run_policy_test("semantic/and_commutativity_b.ttl")
    
    # Same number of conflicts
    assert len(conflicts_a) == len(conflicts_b), \
        "Commutativity violation: different conflict counts"
    
    print("\n✓ AND commutativity verified")

# =============================================================================
# EDGE CASE TESTS
# =============================================================================

def test_empty_policy():
    """Test handling of empty policy"""
    # Create empty policy TTL
    empty_ttl = TEST_DATA_DIR / "edge/empty_policy.ttl"
    empty_ttl.parent.mkdir(parents=True, exist_ok=True)
    
    empty_ttl.write_text("""
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix ex: <http://example.org/> .

ex:empty_policy a odrl:Policy .
""")
    
    conflicts, _ = run_policy_test("edge/empty_policy.ttl")
    assert len(conflicts) == 0
    print("\n✓ Empty policy handled correctly")

# =============================================================================
# SUMMARY
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])