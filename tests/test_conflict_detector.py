# tests/test_conflict_detector.py
"""
Test conflict detection with Z3.
"""

import pytest
from src.semantics.constraint_types import (
    Policy, PolicyRule, PolicyRuleType,
    AtomicConstraint, NormalizedValue, OperatorType,
    get_operand_semantics
)
from src.reasoner.conflict_detector import ConflictDetector, ConflictSeverity

def test_permission_prohibition_conflict():
    """Test detection of Permission-Prohibition conflict"""
    
    # Create constraints
    # count <= 5
    c1 = AtomicConstraint(
        id='c1',
        left_operand='count',
        operator=OperatorType.LTEQ,
        right_value=NormalizedValue(5, 5, None, 'none'),
        semantics=get_operand_semantics('count')
    )
    
    # count >= 3
    c2 = AtomicConstraint(
        id='c2',
        left_operand='count',
        operator=OperatorType.GTEQ,
        right_value=NormalizedValue(3, 3, None, 'none'),
        semantics=get_operand_semantics('count')
    )
    
    # Create rules
    permission = PolicyRule(
        id='perm1',
        rule_type=PolicyRuleType.PERMISSION,
        action='odrl:play',
        constraint_id='c1'
    )
    
    prohibition = PolicyRule(
        id='prohib1',
        rule_type=PolicyRuleType.PROHIBITION,
        action='odrl:play',
        constraint_id='c2'
    )
    
    # Create policy
    policy = Policy(
        id='policy1',
        rules=[permission, prohibition],
        constraints={'c1': c1, 'c2': c2}
    )
    
    # Detect conflicts
    detector = ConflictDetector(debug=True)
    conflicts = detector.detect_all_conflicts(policy)
    
    # Check
    critical = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
    assert len(critical) > 0
    
    # Find permission-prohibition conflict
    pp_conflicts = [c for c in critical if c.conflict_type == 'permission_prohibition']
    assert len(pp_conflicts) == 1
    
    conflict = pp_conflicts[0]
    print(f"\nDetected conflict: {conflict.description}")
    print(f"Counterexample: {conflict.counterexample}")
    
    # Counterexample should have count in [3, 5]
    assert conflict.counterexample is not None
    count_val = conflict.counterexample['count']
    assert 3 <= count_val <= 5

def test_no_conflict():
    """Test that non-overlapping constraints don't conflict"""
    
    # count < 5
    c1 = AtomicConstraint(
        id='c1',
        left_operand='count',
        operator=OperatorType.LT,
        right_value=NormalizedValue(5, 5, None, 'none'),
        semantics=get_operand_semantics('count')
    )
    
    # count > 10
    c2 = AtomicConstraint(
        id='c2',
        left_operand='count',
        operator=OperatorType.GT,
        right_value=NormalizedValue(10, 10, None, 'none'),
        semantics=get_operand_semantics('count')
    )
    
    permission = PolicyRule(
        id='perm1',
        rule_type=PolicyRuleType.PERMISSION,
        action='odrl:play',
        constraint_id='c1'
    )
    
    prohibition = PolicyRule(
        id='prohib1',
        rule_type=PolicyRuleType.PROHIBITION,
        action='odrl:play',
        constraint_id='c2'
    )
    
    policy = Policy(
        id='policy2',
        rules=[permission, prohibition],
        constraints={'c1': c1, 'c2': c2}
    )
    
    detector = ConflictDetector(debug=True)
    conflicts = detector.detect_all_conflicts(policy)
    
    # Should have no permission-prohibition conflicts
    pp_conflicts = [c for c in conflicts if c.conflict_type == 'permission_prohibition']
    assert len(pp_conflicts) == 0
    
    print(f"\nNo conflicts detected (as expected)")

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])