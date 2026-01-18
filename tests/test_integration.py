# tests/test_integration.py
"""
End-to-end integration tests: TTL → Z3 → Conflict Detection
"""

import pytest
import os
from pathlib import Path

from src.parser.ttl_parser import TTLParser
from src.parser.rdf_extractor import RDFExtractor
from src.normalizer.constraint_normalizer import ConstraintNormalizer
from src.reasoner.conflict_detector import ConflictDetector, ConflictSeverity

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"

def parse_and_detect(ttl_file: str, debug: bool = False):
    """
    Complete pipeline: TTL → Policy → Conflicts
    
    Returns:
        (policy, conflicts)
    """
    # Step 1: Parse TTL
    parser = TTLParser(debug=debug)
    graph = parser.parse_file(str(TEST_DATA_DIR / ttl_file))
    
    # Step 2: Extract ODRL structures
    policies = parser.get_policies()
    assert len(policies) > 0, "No policies found in TTL"
    
    policy_uri = policies[0]
    extractor = RDFExtractor(graph, debug=debug)
    policy = extractor.extract_policy(policy_uri)
    
    if debug:
        print(f"\nExtracted policy: {policy.id}")
        print(f"  Rules: {len(policy.rules)}")
        print(f"  Constraints: {len(policy.constraints)}")
    
    # Step 3: Normalize constraints
    normalizer = ConstraintNormalizer(debug=debug)
    policy.constraints = normalizer.normalize_all(policy.constraints)
    
    # Step 4: Detect conflicts
    detector = ConflictDetector(debug=debug)
    conflicts = detector.detect_all_conflicts(policy)
    
    if debug:
        detector.print_conflict_report()
    
    return policy, conflicts

def test_ttl_permission_prohibition_conflict():
    """Test TTL with permission-prohibition conflict"""
    policy, conflicts = parse_and_detect("conflict_permission_prohibition.ttl", debug=True)
    
    # Should detect permission-prohibition conflict
    critical = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
    assert len(critical) > 0
    
    pp_conflicts = [c for c in critical if c.conflict_type == 'permission_prohibition']
    assert len(pp_conflicts) == 1
    
    # Check counterexample
    conflict = pp_conflicts[0]
    assert conflict.counterexample is not None
    count_val = conflict.counterexample['count']
    assert 3 <= count_val <= 5
    
    print(f"\n✓ Correctly detected conflict with counterexample: count={count_val}")

def test_ttl_no_conflict():
    """Test TTL with no conflicts"""
    policy, conflicts = parse_and_detect("no_conflict.ttl", debug=True)
    
    # Should have no permission-prohibition conflicts
    pp_conflicts = [c for c in conflicts if c.conflict_type == 'permission_prohibition']
    assert len(pp_conflicts) == 0
    
    print(f"\n✓ Correctly detected no conflicts")

def test_ttl_temporal_conflict():
    """Test TTL with temporal constraints (unit conversion)"""
    policy, conflicts = parse_and_detect("temporal_conflict.ttl", debug=True)
    
    # Permission: elapsedTime <= 3 hours (10800 seconds)
    # Prohibition: elapsedTime >= 7200 seconds (2 hours)
    # These overlap in range [7200, 10800]
    
    critical = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
    pp_conflicts = [c for c in critical if c.conflict_type == 'permission_prohibition']
    
    assert len(pp_conflicts) == 1
    
    conflict = pp_conflicts[0]
    assert conflict.counterexample is not None
    elapsed_val = conflict.counterexample['elapsedTime']
    
    # Counterexample should be in [7200, 10800] seconds
    assert 7200 <= elapsed_val <= 10800
    
    print(f"\n✓ Correctly detected temporal conflict with counterexample: elapsedTime={elapsed_val}s")

def test_ttl_xone_overlap():
    """Test TTL with XONE having overlapping branches"""
    policy, conflicts = parse_and_detect("xone_overlap.ttl", debug=True)
    
    # XONE with two overlapping branches should be detected
    xone_conflicts = [c for c in conflicts if c.conflict_type == 'xone_overlap']
    
    assert len(xone_conflicts) == 1
    
    conflict = xone_conflicts[0]
    assert conflict.severity == ConflictSeverity.CRITICAL
    
    print(f"\n✓ Correctly detected XONE overlap")

def test_ttl_and_composite():
    """Test TTL with AND composite constraint (no conflict)"""
    policy, conflicts = parse_and_detect("and_composite.ttl", debug=True)
    
    # AND(count > 5, count < 10) is satisfiable, no conflict
    and_conflicts = [c for c in conflicts if c.conflict_type == 'and_contradiction']
    assert len(and_conflicts) == 0
    
    print(f"\n✓ Correctly detected no AND contradiction")

def test_full_pipeline_summary():
    """Test all TTL files and print summary"""
    
    test_files = [
        "conflict_permission_prohibition.ttl",
        "no_conflict.ttl",
        "temporal_conflict.ttl",
        "xone_overlap.ttl",
        "and_composite.ttl"
    ]
    
    print("\n" + "="*70)
    print("FULL PIPELINE TEST SUMMARY")
    print("="*70)
    
    for ttl_file in test_files:
        if not (TEST_DATA_DIR / ttl_file).exists():
            print(f"⚠ Skipping {ttl_file} (file not found)")
            continue
        
        try:
            policy, conflicts = parse_and_detect(ttl_file, debug=False)
            
            critical = len([c for c in conflicts if c.severity == ConflictSeverity.CRITICAL])
            warnings = len([c for c in conflicts if c.severity == ConflictSeverity.WARNING])
            info = len([c for c in conflicts if c.severity == ConflictSeverity.INFO])
            
            print(f"\n{ttl_file}:")
            print(f"  Rules: {len(policy.rules)}")
            print(f"  Constraints: {len(policy.constraints)}")
            print(f"  Conflicts: {critical} critical, {warnings} warnings, {info} info")
            
        except Exception as e:
            print(f"\n{ttl_file}: ERROR - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])