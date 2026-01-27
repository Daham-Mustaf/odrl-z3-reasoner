# tests/conftest.py
"""
Pytest fixtures for ODRL-SA tests.

Provides common fixtures for testing the new architecture.
"""

import pytest
import sys
from pathlib import Path

# Add src to path BEFORE any other imports
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Also add project root for 'src' imports
_root_path = str(Path(__file__).parent.parent)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)


@pytest.fixture
def registry():
    """Get the operand registry."""
    from registry import get_registry, reset_registry
    reset_registry()  # Ensure fresh registry
    return get_registry()


@pytest.fixture
def sample_atomic_constraint():
    """Create a sample atomic constraint."""
    from core.types import AtomicConstraint, OperatorType, RightOperand
    
    return AtomicConstraint(
        uid="test_constraint_1",
        left_operand="count",
        operator=OperatorType.LTEQ,
        right_operand=RightOperand.literal(10)
    )


@pytest.fixture
def sample_constraints():
    """Create a set of sample constraints for testing."""
    from core.types import AtomicConstraint, OperatorType, RightOperand
    
    return [
        AtomicConstraint(
            uid="c1",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(10)
        ),
        AtomicConstraint(
            uid="c2",
            left_operand="count",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(5)
        ),
    ]


@pytest.fixture
def conflicting_constraints():
    """Create conflicting constraints for testing."""
    from core.types import AtomicConstraint, OperatorType, RightOperand
    
    return [
        AtomicConstraint(
            uid="conflict_c1",
            left_operand="count",
            operator=OperatorType.LTEQ,
            right_operand=RightOperand.literal(5)
        ),
        AtomicConstraint(
            uid="conflict_c2",
            left_operand="count",
            operator=OperatorType.GTEQ,
            right_operand=RightOperand.literal(10)
        ),
    ]


@pytest.fixture
def encoder():
    """Get Z3 encoder."""
    from encoder import Z3JudgmentEngine
    return Z3JudgmentEngine()


@pytest.fixture
def sample_ttl():
    """Sample TTL policy for parsing tests."""
    return '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:testPolicy a odrl:Set ;
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


@pytest.fixture
def conflict_ttl():
    """TTL with conflicting constraints."""
    return '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:conflictPolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "5"^^xsd:integer
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:count ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "10"^^xsd:integer
        ]
    ] .
'''


@pytest.fixture
def duration_ttl():
    """TTL with duration constraints."""
    return '''
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:durationPolicy a odrl:Set ;
    odrl:permission [
        a odrl:Permission ;
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "PT1H"^^xsd:duration
        ] ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:gteq ;
            odrl:rightOperand "PT2H"^^xsd:duration
        ]
    ] .
'''
