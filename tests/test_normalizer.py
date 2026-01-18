# tests/test_normalizer.py
"""
Test suite for value and constraint normalization.
"""

import pytest
from src.semantics.constraint_types import (
    AtomicConstraint, NormalizedValue, OperatorType,
    get_operand_semantics
)
from src.normalizer.constraint_normalizer import ConstraintNormalizer

# tests/test_normalizer.py
# Add debug output to the test:

def test_temporal_normalization():
    """Test temporal unit conversion"""
    normalizer = ConstraintNormalizer(debug=True)
    
    # Create constraint: elapsedTime <= 3 hours
    constraint = AtomicConstraint(
        id='c1',
        left_operand='elapsedTime',
        operator=OperatorType.LTEQ,
        right_value=NormalizedValue(
            canonical_value=3,
            original_value=3,
            original_unit='hours',
            canonical_unit='pending'
        ),
        semantics=get_operand_semantics('elapsedTime'),
        metadata={'needs_normalization': True}
    )
    
    # Normalize
    normalized = normalizer.normalize_constraint(constraint)
    
    # Debug output
    print("\n=== DEBUG OUTPUT ===")
    print(f"normalized.right_value.canonical_value = {normalized.right_value.canonical_value}")
    print(f"normalized.right_value.canonical_unit = {normalized.right_value.canonical_unit}")
    print(f"normalized.right_value.metadata = {normalized.right_value.metadata}")
    print(f"normalized.metadata = {normalized.metadata}")
    print("===================\n")
    
    # Check
    assert normalized.right_value.canonical_value == 10800  # 3 hours in seconds
    assert normalized.right_value.canonical_unit == 'seconds'
    assert normalized.metadata['conversion_applied'] == True
    assert normalized.metadata['conversion_factor'] == 3600.0

def test_size_normalization():
    """Test size unit conversion"""
    normalizer = ConstraintNormalizer(debug=True)
    
    # Create constraint: absoluteSize <= 5 MB
    constraint = AtomicConstraint(
        id='c2',
        left_operand='absoluteSize',
        operator=OperatorType.LTEQ,
        right_value=NormalizedValue(
            canonical_value=5,
            original_value=5,
            original_unit='MB',
            canonical_unit='pending'
        ),
        semantics=get_operand_semantics('absoluteSize'),
        metadata={'needs_normalization': True}
    )
    
    # Normalize
    normalized = normalizer.normalize_constraint(constraint)
    
    # Check
    assert normalized.right_value.canonical_value == 5_000_000  # 5 MB in bytes
    assert normalized.right_value.canonical_unit == 'bytes'

def test_monetary_normalization():
    """Test monetary normalization to minor units"""
    normalizer = ConstraintNormalizer(debug=True)
    
    # Create constraint: payAmount >= 9.99 USD
    constraint = AtomicConstraint(
        id='c3',
        left_operand='payAmount',
        operator=OperatorType.GTEQ,
        right_value=NormalizedValue(
            canonical_value=9.99,
            original_value=9.99,
            original_unit='USD',
            canonical_unit='pending'
        ),
        semantics=get_operand_semantics('payAmount'),
        metadata={'needs_normalization': True}
    )
    
    # Normalize
    normalized = normalizer.normalize_constraint(constraint)
    
    # Check
    assert normalized.right_value.canonical_value == 999  # 9.99 USD in cents
    assert normalized.right_value.canonical_unit == 'USD_cents'
    assert normalized.metadata['currency'] == 'USD'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])