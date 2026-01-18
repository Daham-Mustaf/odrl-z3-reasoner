# src/encoder/variable_manager.py
"""
Manage Z3 variables with type-safe access and domain constraints.
"""

from z3 import (
    Bool,
    Int,
    Real,
    String,
    ExprRef,
    BoolRef,
)
from typing import Dict, Optional, List
from ..semantics.constraint_types import SemanticInfo, Z3Sort

class VariableManager:
    """
    Centralized management of Z3 variables.
    
    Ensures:
    - One variable per operand
    - Consistent type usage
    - Domain constraints properly tracked
    """
    
    def __init__(self):
        self.variables: Dict[str, ExprRef] = {}
        self.semantics: Dict[str, SemanticInfo] = {}
        self.domain_constraints: List[BoolRef] = []
    
    def create_variable(self, name: str, semantics: SemanticInfo) -> ExprRef:
        """Create Z3 variable with appropriate type"""
        if name in self.variables:
            return self.variables[name]
        
        # Create based on Z3 sort
        if semantics.z3_sort == Z3Sort.INT:
            var = Int(name)
        elif semantics.z3_sort == Z3Sort.REAL:
            var = Real(name)
        elif semantics.z3_sort == Z3Sort.STRING:
            var = String(name)
        elif semantics.z3_sort == Z3Sort.BOOL:
            var = Bool(name)
        else:
            var = Int(name)  # Default
        
        # Add domain constraints
        if semantics.value_range:
            min_val, max_val = semantics.value_range
            if min_val is not None:
                self.domain_constraints.append(var >= min_val)
            if max_val is not None:
                self.domain_constraints.append(var <= max_val)
        
        self.variables[name] = var
        self.semantics[name] = semantics
        
        return var
    
    def get_variable(self, name: str) -> Optional[ExprRef]:
        """Get existing variable"""
        return self.variables.get(name)
    
    def get_all_constraints(self) -> List[BoolRef]:
        """Get all domain constraints"""
        return self.domain_constraints