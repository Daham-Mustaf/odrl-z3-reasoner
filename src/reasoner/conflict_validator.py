# src/reasoner/conflict_validator.py
from z3 import *
class ConflictValidator:
    """Validate that detected conflicts are real"""
    
    def validate_conflict(self, conflict: Conflict, policy: Policy, 
                         encoder: Z3Encoder) -> bool:
        """
        Check if conflict's counterexample truly satisfies both constraints.
        """
        if not conflict.counterexample:
            return True  # No counterexample to validate
        
        # Get constraint formulas
        c1_id, c2_id = conflict.constraint_ids[:2]
        f1 = encoder.get_formula(c1_id)
        f2 = encoder.get_formula(c2_id)
        
        # Create solver and bind counterexample
        s = Solver()
        for operand, value in conflict.counterexample.items():
            var = encoder.get_variable(operand)
            s.add(var == value)
        
        # Check if both constraints are satisfied
        s.add(f1)
        s.add(f2)
        
        return s.check() == sat