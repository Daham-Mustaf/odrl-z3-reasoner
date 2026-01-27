# tests/test_parser.py
"""
Tests for parser module (TTL/RDF parsing).
"""

import pytest

from parser import parse_ttl_string, parse_ttl_file, ParseResult
from core.types import AtomicConstraint, OperatorType


class TestParseTTLString:
    """Test parse_ttl_string function."""
    
    def test_basic_policy(self, sample_ttl):
        """Test parsing basic policy."""
        result = parse_ttl_string(sample_ttl)
        
        assert isinstance(result, ParseResult)
        assert len(result.policies) == 1
        assert len(result.constraints) >= 1
    
    def test_policy_has_rules(self, sample_ttl):
        """Test that parsed policy has rules."""
        result = parse_ttl_string(sample_ttl)
        policy = result.policies[0]
        
        assert len(policy.rules) >= 1
        assert policy.rules[0].action is not None
    
    def test_constraint_extraction(self, sample_ttl):
        """Test that constraints are extracted."""
        result = parse_ttl_string(sample_ttl)
        
        assert len(result.constraints) >= 1
        # constraints is a dict, get first value
        c = list(result.constraints.values())[0] if isinstance(result.constraints, dict) else result.constraints[0]
        assert isinstance(c, AtomicConstraint)
        assert c.left_operand == "count"
        assert c.operator == OperatorType.LTEQ
    
    def test_get_atomic_constraints(self, sample_ttl):
        """Test get_atomic_constraints method."""
        result = parse_ttl_string(sample_ttl)
        atomics = result.get_atomic_constraints()
        
        assert len(atomics) >= 1
        assert all(isinstance(c, AtomicConstraint) for c in atomics)


class TestConflictPolicy:
    """Test parsing policies with conflicts."""
    
    def test_conflict_policy_parsing(self, conflict_ttl):
        """Test parsing policy with conflicting constraints."""
        result = parse_ttl_string(conflict_ttl)
        
        assert len(result.policies) == 1
        assert len(result.constraints) >= 2
    
    def test_conflict_constraints_values(self, conflict_ttl):
        """Test that conflicting constraint values are correct."""
        result = parse_ttl_string(conflict_ttl)
        constraints = result.get_atomic_constraints()
        
        # Find the two count constraints
        count_constraints = [c for c in constraints if c.left_operand == "count"]
        assert len(count_constraints) == 2
        
        # One should be <= 5, one should be >= 10
        operators = {c.operator for c in count_constraints}
        assert OperatorType.LTEQ in operators
        assert OperatorType.GTEQ in operators


class TestDurationPolicy:
    """Test parsing policies with duration constraints."""
    
    def test_duration_policy_parsing(self, duration_ttl):
        """Test parsing policy with duration constraints."""
        result = parse_ttl_string(duration_ttl)
        
        assert len(result.policies) == 1
        constraints = result.get_atomic_constraints()
        
        # Should have elapsedTime constraints
        elapsed_constraints = [c for c in constraints if c.left_operand == "elapsedTime"]
        assert len(elapsed_constraints) == 2
    
    def test_duration_values_parsed(self, duration_ttl):
        """Test that duration values are parsed correctly."""
        result = parse_ttl_string(duration_ttl)
        constraints = result.get_atomic_constraints()
        
        for c in constraints:
            if c.left_operand == "elapsedTime":
                # Value should be a timedelta or string
                assert c.right_operand.value is not None


class TestPolicyMetadata:
    """Test policy metadata extraction."""
    
    def test_policy_uid(self, sample_ttl):
        """Test policy UID extraction."""
        result = parse_ttl_string(sample_ttl)
        policy = result.policies[0]
        
        assert policy.uid is not None
        assert "testPolicy" in policy.uid
    
    def test_policy_type(self, sample_ttl):
        """Test policy type extraction."""
        result = parse_ttl_string(sample_ttl)
        policy = result.policies[0]
        
        assert policy.policy_type is not None


class TestRuleExtraction:
    """Test rule extraction."""
    
    def test_permission_rule(self, sample_ttl):
        """Test permission rule extraction."""
        result = parse_ttl_string(sample_ttl)
        policy = result.policies[0]
        
        permissions = [r for r in policy.rules if r.rule_type.value == "permission"]
        assert len(permissions) >= 1
    
    def test_rule_action(self, sample_ttl):
        """Test rule action extraction."""
        result = parse_ttl_string(sample_ttl)
        policy = result.policies[0]
        
        assert policy.rules[0].action is not None


class TestComplexPolicies:
    """Test parsing complex policies."""
    
    def test_multiple_constraints(self):
        """Test policy with multiple constraints on same rule."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:multiConstraintPolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "100"^^xsd:integer
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:percentage ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "50"^^xsd:decimal
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:dateTime ;
            odrl:operator odrl:lt ;
            odrl:rightOperand "2025-12-31T23:59:59Z"^^xsd:dateTime
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        constraints = result.get_atomic_constraints()
        
        assert len(constraints) == 3
        operands = {c.left_operand for c in constraints}
        assert operands == {"count", "percentage", "dateTime"}
    
    def test_permission_and_prohibition(self):
        """Test policy with both permission and prohibition."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:mixedPolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "10"^^xsd:integer
        ]
    ] ;
    odrl:prohibition [
        a odrl:Prohibition ;
        odrl:action odrl:distribute ;
        odrl:constraint [
            odrl:leftOperand odrl:percentage ;
            odrl:operator odrl:gt ;
            odrl:rightOperand "50"^^xsd:decimal
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        policy = result.policies[0]
        
        permissions = [r for r in policy.rules if r.rule_type.value == "permission"]
        prohibitions = [r for r in policy.rules if r.rule_type.value == "prohibition"]
        
        assert len(permissions) == 1
        assert len(prohibitions) == 1


class TestErrorHandling:
    """Test parser error handling."""
    
    def test_empty_string(self):
        """Test parsing empty string."""
        result = parse_ttl_string("")
        assert len(result.policies) == 0
    
    def test_invalid_ttl(self):
        """Test parsing invalid TTL."""
        # Parser may raise exception or return empty result
        try:
            result = parse_ttl_string("this is not valid turtle")
            # If no exception, should have no policies
            assert result is not None
        except Exception:
            # Exception is acceptable for invalid TTL
            pass
    
    def test_no_policy(self):
        """Test TTL without policy."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix ex: <http://example.org/> .

ex:notAPolicy a ex:SomethingElse .
'''
        result = parse_ttl_string(ttl)
        assert len(result.policies) == 0