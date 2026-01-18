# tests/test_z3_encoder.py
"""
Test Z3 encoding of ODRL constraints.
"""

import pytest
from z3 import (
    Bool,
    Int,
    Real,
    String,
    ExprRef,
    BoolRef,
    Solver,        # ← add
    sat,           # ← add
    is_bool,       # ← add (used in test_encode_simple_numeric)
)

from src.semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, NormalizedValue,
    OperatorType, ConstraintType, get_operand_semantics
)
from src.encoder.z3_encoder import Z3Encoder

def test_encode_simple_numeric():
    """Test encoding simple numeric constraint"""
    encoder = Z3Encoder(debug=True)
    
    # count <= 5
    constraint = AtomicConstraint(
        id='c1',
        left_operand='count',
        operator=OperatorType.LTEQ,
        right_value=NormalizedValue(
            canonical_value=5,
            original_value=5,
            original_unit=None,
            canonical_unit='none'
        ),
        semantics=get_operand_semantics('count')
    )
    
    # Encode
    constraints = {'c1': constraint}
    formulas = encoder.encode_policy(constraints)
    
    # Check
    assert 'c1' in formulas
    formula = formulas['c1']
    
    # Verify it's a valid Z3 formula
    assert is_bool(formula)
    
    # Check satisfiability
    s = Solver()
    s.add(formula)
    assert s.check() == sat
    
    # Get model
    m = s.model()
    count_val = m[encoder.get_variable('count')].as_long()
    assert count_val <= 5
    
    print(f"Model: count = {count_val}")

def test_encode_temporal():
    """Test encoding temporal constraint"""
    encoder = Z3Encoder(debug=True)
    
    # elapsedTime <= 10800 seconds (3 hours normalized)
    constraint = AtomicConstraint(
        id='c2',
        left_operand='elapsedTime',
        operator=OperatorType.LTEQ,
        right_value=NormalizedValue(
            canonical_value=10800,
            original_value=3,
            original_unit='hours',
            canonical_unit='seconds'
        ),
        semantics=get_operand_semantics('elapsedTime')
    )
    
    # Encode
    constraints = {'c2': constraint}
    formulas = encoder.encode_policy(constraints)
    
    # Check satisfiability
    s = Solver()
    s.add(formulas['c2'])
    assert s.check() == sat
    
    m = s.model()
    elapsed_val = m[encoder.get_variable('elapsedTime')].as_long()
    assert elapsed_val <= 10800
    
    print(f"Model: elapsedTime = {elapsed_val} seconds")

def test_encode_set_operator():
    """Test encoding set membership"""
    encoder = Z3Encoder(debug=True)
    
    # language isAnyOf [en, fr, de]
    constraint = AtomicConstraint(
        id='c3',
        left_operand='language',
        operator=OperatorType.IS_ANY_OF,
        right_value=NormalizedValue(
            canonical_value=['en', 'fr', 'de'],
            original_value=['en', 'fr', 'de'],
            original_unit=None,
            canonical_unit='iso639-1'
        ),
        semantics=get_operand_semantics('language')
    )
    
    # Encode
    constraints = {'c3': constraint}
    formulas = encoder.encode_policy(constraints)
    
    # Check
    s = Solver()
    s.add(formulas['c3'])
    assert s.check() == sat
    
    m = s.model()
    lang_val = str(m[encoder.get_variable('language')])
    print(f"Model: language = {lang_val}")
    # Note: Z3 String values are printed with quotes

def test_encode_and_composite():
    """Test encoding AND composite constraint"""
    encoder = Z3Encoder(debug=True)
    
    # count > 5
    c1 = AtomicConstraint(
        id='c1',
        left_operand='count',
        operator=OperatorType.GT,
        right_value=NormalizedValue(
            canonical_value=5,
            original_value=5,
            original_unit=None,
            canonical_unit='none'
        ),
        semantics=get_operand_semantics('count')
    )
    
    # count < 10
    c2 = AtomicConstraint(
        id='c2',
        left_operand='count',
        operator=OperatorType.LT,
        right_value=NormalizedValue(
            canonical_value=10,
            original_value=10,
            original_unit=None,
            canonical_unit='none'
        ),
        semantics=get_operand_semantics('count')
    )
    
    # AND(c1, c2)
    c_and = CompositeConstraint(
        id='c_and',
        constraint_type=ConstraintType.AND,
        children=['c1', 'c2']
    )
    
    # Encode
    constraints = {'c1': c1, 'c2': c2, 'c_and': c_and}
    formulas = encoder.encode_policy(constraints)
    
    # Check satisfiability of AND
    s = Solver()
    s.add(formulas['c_and'])
    assert s.check() == sat
    
    m = s.model()
    count_val = m[encoder.get_variable('count')].as_long()
    assert 5 < count_val < 10
    
    print(f"Model: count = {count_val} (satisfies 5 < count < 10)")

def test_encode_xone_composite():
    """Test encoding XONE (exactly one) composite constraint"""
    encoder = Z3Encoder(debug=True)
    
    # count < 5
    c1 = AtomicConstraint(
        id='c1',
        left_operand='count',
        operator=OperatorType.LT,
        right_value=NormalizedValue(
            canonical_value=5,
            original_value=5,
            original_unit=None,
            canonical_unit='none'
        ),
        semantics=get_operand_semantics('count')
    )
    
    # count > 10
    c2 = AtomicConstraint(
        id='c2',
        left_operand='count',
        operator=OperatorType.GT,
        right_value=NormalizedValue(
            canonical_value=10,
            original_value=10,
            original_unit=None,
            canonical_unit='none'
        ),
        semantics=get_operand_semantics('count')
    )
    
    # XONE(c1, c2) - exactly one must be true
    c_xone = CompositeConstraint(
        id='c_xone',
        constraint_type=ConstraintType.XONE,
        children=['c1', 'c2']
    )
    
    # Encode
    constraints = {'c1': c1, 'c2': c2, 'c_xone': c_xone}
    formulas = encoder.encode_policy(constraints)
    
    # Check satisfiability
    s = Solver()
    s.add(formulas['c_xone'])
    assert s.check() == sat
    
    m = s.model()
    count_val = m[encoder.get_variable('count')].as_long()
    
    # Must satisfy exactly one: either count < 5 OR count > 10
    assert (count_val < 5) or (count_val > 10)
    assert not ((count_val < 5) and (count_val > 10))  # Not both
    
    print(f"Model: count = {count_val}")

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])