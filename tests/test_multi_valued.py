# tests/test_multi_valued.py
# tests/test_multi_valued.py
from z3 import BitVecVal, Solver, sat
import pytest
from src.encoder.z3_encoder import Z3Encoder   # your class
from src.semantics.constraint_types import get_operand_semantics, OperatorType
from src.encoder.z3_encoder import Z3Encoder

def test_multi_valued_language():
    """Test multi-valued language operand"""
    encoder = Z3Encoder()
    
    # Asset has languages: {en, fr, de}
    language_set = encoder.create_variable('language', get_operand_semantics('language'))
    
    # Constraint: language isAnyOf [en, es]
    constraint_formula = encoder.encode_set_operator(
        OperatorType.IS_ANY_OF,
        language_set,
        ['en', 'es']
    )
    
    # Context: asset has {en, fr, de}
    s = Solver()
    asset_languages = encoder._create_set_from_list(['en', 'fr', 'de'])
    s.add(language_set == asset_languages)
    s.add(constraint_formula)
    
    # Should be SAT (en is in both sets)
    assert s.check() == sat
    print("✓ Multi-valued language works!")

def test_is_all_of():
    """Test isAllOf with multi-valued operand"""
    encoder = Z3Encoder()
    
    # Asset purposes: {education, research, commercial}
    purpose_set = encoder.create_variable('purpose', get_operand_semantics('purpose'))
    
    # Constraint: purpose isAllOf [education, research]
    constraint_formula = encoder.encode_set_operator(
        OperatorType.IS_ALL_OF,
        purpose_set,
        ['education', 'research']
    )
    
    # Context: asset has {education, research, commercial}
    s = Solver()
    asset_purposes = encoder._create_set_from_list(['education', 'research', 'commercial'])
    s.add(purpose_set == asset_purposes)
    s.add(constraint_formula)
    
    # Should be SAT (education AND research are both present)
    assert s.check() == sat
    print("✓ isAllOf works!")