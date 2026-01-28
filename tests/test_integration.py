# tests/test_integration.py
"""
Integration tests - end-to-end testing of the full pipeline.
"""

import pytest

from parser import parse_ttl_string
from encoder import check_consistency
from reasoner import ConflictDetector, ConflictSeverity
from core.constraint_types import Judgment


class TestEndToEndPipeline:
    """Test complete pipeline from TTL to judgment."""
    
    def test_simple_valid_policy(self, sample_ttl):
        """Test analyzing a simple valid policy."""
        # Parse
        result = parse_ttl_string(sample_ttl)
        assert len(result.policies) == 1
        
        # Get constraints
        constraints = result.get_atomic_constraints()
        
        # Check consistency
        judgment, model = check_consistency(constraints)
        assert judgment == Judgment.POSSIBLY_COMPATIBLE
    
    def test_conflicting_policy(self, conflict_ttl):
        """Test detecting conflict in policy."""
        # Parse
        result = parse_ttl_string(conflict_ttl)
        constraints = result.get_atomic_constraints()
        
        # Check consistency
        judgment, model = check_consistency(constraints)
        assert judgment == Judgment.CONFLICT
    
    def test_duration_conflict(self, duration_ttl):
        """Test detecting duration-based conflict."""
        # Parse
        result = parse_ttl_string(duration_ttl)
        constraints = result.get_atomic_constraints()
        
        # Check consistency
        judgment, model = check_consistency(constraints)
        assert judgment == Judgment.CONFLICT


class TestConflictDetector:
    """Test ConflictDetector integration."""
    
    def test_detect_and_contradiction(self):
        """Test detecting AND contradiction."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:andConflict a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            a odrl:Constraint ;
            odrl:and (
                [
                    odrl:leftOperand odrl:count ;
                    odrl:operator odrl:lteq ;
                    odrl:rightOperand "5"^^xsd:integer
                ]
                [
                    odrl:leftOperand odrl:count ;
                    odrl:operator odrl:gteq ;
                    odrl:rightOperand "10"^^xsd:integer
                ]
            )
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        policy = result.policies[0]
        # constraints is a dict {uid: constraint}
        constraints = result.constraints if isinstance(result.constraints, dict) else {c.uid: c for c in result.constraints}
        
        detector = ConflictDetector()
        conflicts = detector.detect_all_conflicts(policy, constraints)
        
        # Should detect the AND contradiction
        critical = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
        assert len(critical) > 0


class TestRealWorldScenarios:
    """Test real-world policy scenarios."""
    
    def test_time_window_conflict(self):
        """Test conflicting time windows."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:timeConflict a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:dateTime ;
            odrl:operator odrl:lt ;
            odrl:rightOperand "2024-01-01T00:00:00Z"^^xsd:dateTime
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:dateTime ;
            odrl:operator odrl:gt ;
            odrl:rightOperand "2024-12-31T23:59:59Z"^^xsd:dateTime
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        constraints = result.get_atomic_constraints()
        
        judgment, _ = check_consistency(constraints)
        assert judgment == Judgment.CONFLICT
    
    def test_time_window_valid(self):
        """Test valid time window (overlapping)."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:timeValid a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:dateTime ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "2024-01-01T00:00:00Z"^^xsd:dateTime
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:dateTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "2024-12-31T23:59:59Z"^^xsd:dateTime
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        constraints = result.get_atomic_constraints()
        
        judgment, model = check_consistency(constraints)
        assert judgment == Judgment.POSSIBLY_COMPATIBLE
    
    def test_usage_limit_valid(self):
        """Test valid usage limits."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:usageLimit a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "100"^^xsd:integer
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "1"^^xsd:integer
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        constraints = result.get_atomic_constraints()
        
        judgment, model = check_consistency(constraints)
        assert judgment == Judgment.POSSIBLY_COMPATIBLE
        # Should have a satisfying value between 1 and 100
    
    def test_percentage_bounds(self):
        """Test percentage within bounds."""
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:percentagePolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:percentage ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "25"^^xsd:decimal
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:percentage ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "75"^^xsd:decimal
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        constraints = result.get_atomic_constraints()
        
        judgment, model = check_consistency(constraints)
        assert judgment == Judgment.POSSIBLY_COMPATIBLE


class TestClassificationIntegration:
    """Test that classification works in the pipeline."""
    
    def test_full_class_analyzed(self):
        """Test that FULL class constraints are analyzed."""
        from core.classifier import classify_constraint
        from registry import ConstraintClass
        
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:fullClassPolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "10"^^xsd:integer
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        # constraints is a dict, get first value
        constraint = list(result.constraints.values())[0]
        
        classification = classify_constraint(constraint)
        assert classification.constraint_class == ConstraintClass.FULL
        assert classification.can_analyze
    
    def test_grounded_class_identified(self):
        """Test that GROUNDED class constraints are identified."""
        from core.classifier import classify_constraint
        from registry import ConstraintClass
        
        ttl = '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:groundedClassPolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:language ;
            odrl:operator odrl:eq ;
            odrl:rightOperand <http://example.org/en>
        ]
    ] .
'''
        result = parse_ttl_string(ttl)
        # constraints is a dict, get first value
        constraint = list(result.constraints.values())[0]
        
        classification = classify_constraint(constraint)
        assert classification.constraint_class == ConstraintClass.GROUNDED
        assert classification.oracle_needed == "LanguageOracle"