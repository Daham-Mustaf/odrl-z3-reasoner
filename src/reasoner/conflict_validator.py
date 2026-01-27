# src/reasoner/conflict_validator.py
"""
Conflict Validator - Validates that detected conflicts are real.
"""

from z3 import Solver, sat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conflict_detector import Conflict
    from ..parser.ttl_parser import Policy
    from ..encoder.z3_encoder import Z3JudgmentEngine


class ConflictValidator:
    """Validate that detected conflicts are real"""
    
    def validate_conflict(self, conflict: 'Conflict', policy: 'Policy', 
                         encoder: 'Z3JudgmentEngine') -> bool:
        """
        Check if conflict's counterexample truly satisfies both constraints.
        
        Args:
            conflict: The conflict to validate
            policy: The policy containing the constraints
            encoder: The Z3 encoder with formulas
            
        Returns:
            True if the conflict is valid (counterexample satisfies both constraints)
        """
        if not conflict.counterexample:
            return True  # No counterexample to validate
        
        if len(conflict.constraint_ids) < 2:
            return True  # Need at least 2 constraints
        
        # Get constraint formulas
        c1_id, c2_id = conflict.constraint_ids[:2]
        f1 = encoder.get_formula(c1_id)
        f2 = encoder.get_formula(c2_id)
        
        if f1 is None or f2 is None:
            return False  # Can't validate without formulas
        
        # Create solver and bind counterexample
        s = Solver()
        for operand, value in conflict.counterexample.items():
            var = encoder.var_manager.get_variable(operand)
            s.add(var == value)
        
        # Check if both constraints are satisfied
        s.add(f1)
        s.add(f2)
        
        return s.check() == sat