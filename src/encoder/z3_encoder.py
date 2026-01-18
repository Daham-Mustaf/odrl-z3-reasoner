# src/encoder/z3_encoder.py
"""
Z3 Encoder: Translate normalized ODRL constraints to Z3 formulas.

IMPORTANT: Multi-valued operands are represented as Z3 Arrays (not Sets)
Array[String, Bool] where array[key] = True means key is in the set
"""

from z3 import (
    And, Or, Not,
    Bool, BoolRef, BoolVal,
    Int, Real, String, 
    ExprRef,
    Contains, StringVal,
    PbEq,
    # Array imports
    Array, ArraySort, StringSort, BoolSort, Select, Store, K,
    # Solver
    Solver, sat, unsat
)
from typing import Dict, Union, List, Optional, Any, Set as PySet
import logging

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, ConstraintType,
    OperatorType, Z3Sort, ValueDomain
)

logger = logging.getLogger(__name__)

# ==============================================================================
# MULTI-VALUED OPERAND REGISTRY
# ==============================================================================

MULTI_VALUED_OPERANDS = {
    'language',
    'media', 
    'fileFormat',
    'purpose',
    'industry',
    'product',
    'recipient',
    'systemDevice',
    'deliveryChannel'
}

TEMPORAL_OPERAND_ALIASES = {
    'dateTimeBefore': 'currentDateTime',
    'dateTimeAfter': 'currentDateTime', 
    'dateTime': 'currentDateTime',
}

# ==============================================================================
# CLASS HIERARCHY REASONER  
# ==============================================================================

class ClassHierarchy:
    """Manage RDFS/OWL class hierarchies for isA reasoning."""
    
    def __init__(self, graph=None):
        self.graph = graph
        self.superclass_cache: Dict[str, PySet[str]] = {}
        self.subclass_cache: Dict[str, PySet[str]] = {}
        
        if graph:
            self._compute_closure()
    
    def _compute_closure(self):
        """Compute transitive closure of subClassOf"""
        from rdflib import RDFS
        
        # Get all classes
        classes = set()
        for s, p, o in self.graph.triples((None, RDFS.subClassOf, None)):
            # Normalize URIs to strings
            s_str = self._normalize_uri(str(s))
            o_str = self._normalize_uri(str(o))
            classes.add(s_str)
            classes.add(o_str)
        
        # Compute superclasses for each class
        for cls in classes:
            self.superclass_cache[cls] = self._get_superclasses(cls)
        
        # Compute inverse (subclasses)
        for cls, supers in self.superclass_cache.items():
            for super_cls in supers:
                if super_cls not in self.subclass_cache:
                    self.subclass_cache[super_cls] = set()
                self.subclass_cache[super_cls].add(cls)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Hierarchy loaded: {len(classes)} classes")
            for cls in sorted(classes):
                supers = self.superclass_cache.get(cls, set())
                if supers:
                    logger.debug(f"  {cls} subClassOf {supers}")
    
    def _get_superclasses(self, cls: str) -> PySet[str]:
        """Get all superclasses of cls (transitive)"""
        from rdflib import RDFS, URIRef
        
        superclasses = set()
        
        # Try to find the URI in the graph
        cls_uri = None
        for s, p, o in self.graph.triples((None, RDFS.subClassOf, None)):
            s_norm = self._normalize_uri(str(s))
            if s_norm == cls:
                cls_uri = s
                break
        
        if not cls_uri:
            return superclasses
        
        # Direct superclasses
        for super_cls in self.graph.objects(cls_uri, RDFS.subClassOf):
            super_str = self._normalize_uri(str(super_cls))
            superclasses.add(super_str)
            # Recursive
            superclasses.update(self._get_superclasses(super_str))
        
        return superclasses
    
    def _normalize_uri(self, uri: str) -> str:
        """Normalize URI to lowercase for comparison"""
        # Remove common prefixes and convert to lowercase
        uri = uri.lower()
        # Extract last component
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def is_a(self, instance_cls: str, target_cls: str) -> bool:
        """Check if instance_cls is-a target_cls (with transitivity)"""
        instance_norm = self._normalize_uri(str(instance_cls))
        target_norm = self._normalize_uri(str(target_cls))
        
        # Reflexive
        if instance_norm == target_norm:
            return True
        
        # Transitive
        return target_norm in self.superclass_cache.get(instance_norm, set())
    
    def get_all_subclasses(self, cls: str) -> PySet[str]:
        """Get all subclasses of cls (transitive)"""
        cls_norm = self._normalize_uri(str(cls))
        return self.subclass_cache.get(cls_norm, set()).copy()

# ==============================================================================
# Z3 ENCODER
# ==============================================================================

class Z3Encoder:
    """
    Encode ODRL constraints as Z3 formulas with full semantic support.
    
    Multi-valued operands use Z3 Arrays: Array[String, Bool]
    where array[key] = True means key is in the set.
    """
    
    def __init__(self, hierarchy: Optional[ClassHierarchy] = None, debug: bool = False):
        self.debug = debug
        self.hierarchy = hierarchy
        self.variables: Dict[str, ExprRef] = {}
        self.formulas: Dict[str, BoolRef] = {}
        self.constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]] = {}
        self.domain_constraints: List[BoolRef] = []
    
    def encode_policy(self, 
                     constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
                    ) -> Dict[str, BoolRef]:
        """Encode all constraints in a policy."""
        self.constraints = constraints
        
        if self.debug:
            logger.debug(f"Encoding {len(constraints)} constraints")
        
        for constraint_id, constraint in constraints.items():
            try:
                formula = self.encode_constraint(constraint_id)
                self.formulas[constraint_id] = formula
                
                if self.debug:
                    logger.debug(f"Encoded {constraint_id}: {formula}")
                    
            except Exception as e:
                logger.error(f"Failed to encode constraint {constraint_id}: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        logger.info(f"Encoded {len(self.formulas)} constraints to Z3")
        return self.formulas
    
    def encode_constraint(self, constraint_id: str) -> BoolRef:
        """Encode a single constraint"""
        if constraint_id in self.formulas:
            return self.formulas[constraint_id]
        
        constraint = self.constraints.get(constraint_id)
        if not constraint:
            raise ValueError(f"Unknown constraint: {constraint_id}")
        
        if isinstance(constraint, AtomicConstraint):
            return self._encode_atomic(constraint)
        elif isinstance(constraint, CompositeConstraint):
            return self._encode_composite(constraint)
        else:
            raise ValueError(f"Unknown constraint type: {type(constraint)}")
    
    # ==========================================================================
    # ATOMIC CONSTRAINT ENCODING
    # ==========================================================================
    
    def _encode_atomic(self, constraint: AtomicConstraint) -> BoolRef:
        """Encode atomic constraint to Z3 formula"""
        
        operand = constraint.left_operand
        operator = constraint.operator
        value = constraint.right_value.canonical_value
         # Map temporal operands to same variable
        var_name = TEMPORAL_OPERAND_ALIASES.get(operand, operand)
        
        #  Special handling for monetary (currency-specific variables)
        if constraint.semantics.domain == ValueDomain.MONETARY:
            currency = constraint.metadata.get('currency', 'UNKNOWN')
            var_name = f"{var_name}_{currency}"
            var = self._get_or_create_variable_with_name(
                var_name, 
                constraint.semantics,
                is_multi_valued=False
            )
        else:
            is_multi = operand in MULTI_VALUED_OPERANDS
            var = self._get_or_create_variable_with_name(
                var_name,  # Use mapped name
                constraint.semantics,
                is_multi_valued=is_multi
            )
        
        if self.debug:
            logger.debug(f"  Encoding: {operand} {operator.value} {value}")
        
        # Check if operand is multi-valued
        is_multi_valued = operand in MULTI_VALUED_OPERANDS
        
        if is_multi_valued:
            return self._encode_multi_valued_operator(var, operator, value, constraint)
        else:
            return self._encode_single_valued_operator(var, operator, value, constraint)
    
    def _encode_single_valued_operator(self, var: ExprRef, operator: OperatorType, 
                                    value: Any, constraint: AtomicConstraint) -> BoolRef:
        """Encode operators for single-valued operands"""
        
        # Helper: Convert value to Z3 type if needed
        def to_z3_value(val, var_sort):
            """Convert Python value to Z3 value based on variable sort"""
            sort_str = str(var_sort)
            
            if 'String' in sort_str:
                return StringVal(str(val))
            elif 'Int' in sort_str:
                return int(val)
            elif 'Real' in sort_str:
                return float(val)
            else:
                return val
        
        # Convert value to Z3 type
        z3_value = to_z3_value(value, var.sort())
        
        # Relational operators
        if operator == OperatorType.EQ:
            return var == z3_value
        elif operator == OperatorType.NEQ:
            return var != z3_value
        elif operator == OperatorType.LT:
            return var < z3_value
        elif operator == OperatorType.LTEQ:
            return var <= z3_value
        elif operator == OperatorType.GT:
            return var > z3_value
        elif operator == OperatorType.GTEQ:
            return var >= z3_value
        
        # Set operators
        elif operator == OperatorType.IS_ANY_OF:
            if not isinstance(value, list):
                value = [value]
            # Convert all values to Z3 type
            z3_values = [to_z3_value(v, var.sort()) for v in value]
            return Or([var == v for v in z3_values])
        
        elif operator == OperatorType.IS_ALL_OF:
            if not isinstance(value, list):
                value = [value]
            
            if len(value) == 1:
                return var == to_z3_value(value[0], var.sort())
            else:
                logger.warning(
                    f"isAllOf with multiple values on single-valued operand '{constraint.left_operand}'. "
                    f"Treating as unsatisfiable."
                )
                return BoolVal(False)
        
        elif operator == OperatorType.IS_NONE_OF:
            if not isinstance(value, list):
                value = [value]
            z3_values = [to_z3_value(v, var.sort()) for v in value]
            return And([var != v for v in z3_values])
        
        # String operators
        elif operator == OperatorType.HAS_PART:
            if hasattr(var, 'sort') and 'String' in str(var.sort()):
                return Contains(var, StringVal(str(value)))
            else:
                logger.warning(f"hasPart on non-string single-valued operand, using equality")
                return var == z3_value
        
        elif operator == OperatorType.IS_PART_OF:
            if hasattr(var, 'sort') and 'String' in str(var.sort()):
                return Contains(StringVal(str(value)), var)
            else:
                logger.warning(f"isPartOf on non-string single-valued operand, using equality")
                return var == z3_value
        
        # isA operator
        elif operator == OperatorType.IS_A:
            return self._encode_is_a_operator(var, value)
        
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    
    def _encode_multi_valued_operator(self, var_array: ExprRef, operator: OperatorType,
                                     value: Any, constraint: AtomicConstraint) -> BoolRef:
        """
        Encode operators for multi-valued operands.
        var_array is Array[String, Bool] where var_array[key] = True means key is in set.
        """
        
        if operator == OperatorType.IS_ANY_OF:
            # At least one value is in the array
            if not isinstance(value, list):
                value = [value]
            return Or([Select(var_array, StringVal(str(v))) for v in value])
        
        elif operator == OperatorType.IS_ALL_OF:
            # All values are in the array
            if not isinstance(value, list):
                value = [value]
            return And([Select(var_array, StringVal(str(v))) for v in value])
        
        elif operator == OperatorType.IS_NONE_OF:
            # No values are in the array
            if not isinstance(value, list):
                value = [value]
            return And([Not(Select(var_array, StringVal(str(v)))) for v in value])
        
        elif operator == OperatorType.HAS_PART:
            # At least one specific value is in array
            if isinstance(value, list):
                return Or([Select(var_array, StringVal(str(v))) for v in value])
            else:
                return Select(var_array, StringVal(str(value)))
        
        elif operator == OperatorType.IS_PART_OF:
            # This is tricky for arrays - interpret as: array is subset of value_set
            # For now, just check if value is in array
            if isinstance(value, list):
                # All elements in array must be in value list (hard to express in Z3)
                # Approximate: at least one value from list is in array
                return Or([Select(var_array, StringVal(str(v))) for v in value])
            else:
                return Select(var_array, StringVal(str(value)))
        
        elif operator == OperatorType.IS_A:
            return self._encode_is_a_for_array(var_array, value)
        
        else:
            logger.warning(f"Relational operator {operator.value} on multi-valued operand, treating as false")
            return BoolVal(False)
    
    def _encode_is_a_operator(self, var: ExprRef, value: Any) -> BoolRef:
        """Encode isA for single-valued operands"""
        
        if self.hierarchy is None:
            # No hierarchy
            if isinstance(value, list):
                return Or([var == StringVal(str(v)) for v in value])
            else:
                return var == StringVal(str(value))
        
        else:
            # With hierarchy
            if isinstance(value, list):
                expanded = []
                for cls in value:
                    expanded.append(str(cls))
                    expanded.extend(self.hierarchy.get_all_subclasses(str(cls)))
                return Or([var == StringVal(c) for c in expanded])
            else:
                target_classes = [str(value)]
                target_classes.extend(self.hierarchy.get_all_subclasses(str(value)))
                return Or([var == StringVal(c) for c in target_classes])
    
    def _encode_is_a_for_array(self, var_array: ExprRef, value: Any) -> BoolRef:
        """Encode isA for multi-valued operands (array)"""
        
        if self.hierarchy is None:
            # No hierarchy
            if isinstance(value, list):
                return Or([Select(var_array, StringVal(str(v))) for v in value])
            else:
                return Select(var_array, StringVal(str(value)))
        
        else:
            # With hierarchy
            if isinstance(value, list):
                expanded = []
                for cls in value:
                    expanded.append(str(cls))
                    expanded.extend(self.hierarchy.get_all_subclasses(str(cls)))
            else:
                expanded = [str(value)]
                expanded.extend(self.hierarchy.get_all_subclasses(str(value)))
            
            return Or([Select(var_array, StringVal(c)) for c in expanded])
    
    # ==========================================================================
    # COMPOSITE CONSTRAINT ENCODING
    # ==========================================================================
    
    def _encode_composite(self, constraint: CompositeConstraint) -> BoolRef:
        """Encode composite constraint"""
        
        child_formulas = []
        for child_id in constraint.children:
            child_formula = self.encode_constraint(child_id)
            child_formulas.append(child_formula)
        
        if self.debug:
            logger.debug(f"  Encoding {constraint.constraint_type.value} with {len(child_formulas)} children")
        
        if constraint.constraint_type == ConstraintType.AND:
            return And(child_formulas)
        elif constraint.constraint_type == ConstraintType.OR:
            return Or(child_formulas)
        elif constraint.constraint_type == ConstraintType.XONE:
            return PbEq([(f, 1) for f in child_formulas], 1)
        else:
            raise ValueError(f"Unknown composite type: {constraint.constraint_type}")
    
    # ==========================================================================
    # VARIABLE MANAGEMENT
    # ==========================================================================
    
    def _get_or_create_variable_with_name(self, var_name: str, semantics: Any, 
                                         is_multi_valued: bool = False) -> ExprRef:
        """Create Z3 variable with specific name"""
        if var_name in self.variables:
            return self.variables[var_name]
        
        if self.debug:
            logger.debug(f"  Creating variable '{var_name}' (multi={is_multi_valued})")
        
        if is_multi_valued:
            # Create Z3 Array[String, Bool]
            # Default: all keys map to False (empty set)
            var = Array(var_name, StringSort(), BoolSort())
            # Initialize to empty set: K(String, False) means all strings map to False
            # We don't actually set this; Z3 assumes arrays have a default value
        
        else:
            # Create scalar
            z3_sort = semantics.z3_sort
            
            if z3_sort == Z3Sort.INT:
                var = Int(var_name)
            elif z3_sort == Z3Sort.REAL:
                var = Real(var_name)
            elif z3_sort == Z3Sort.STRING:
                var = String(var_name)
            elif z3_sort == Z3Sort.BOOL:
                var = Bool(var_name)
            else:
                logger.warning(f"Unknown Z3 sort {z3_sort}, defaulting to Int")
                var = Int(var_name)
            
            # Apply domain constraints
            if semantics.value_range and z3_sort in [Z3Sort.INT, Z3Sort.REAL]:
                min_val, max_val = semantics.value_range
                if min_val is not None:
                    self.domain_constraints.append(var >= min_val)
                if max_val is not None:
                    self.domain_constraints.append(var <= max_val)
        
        self.variables[var_name] = var
        return var
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def get_domain_constraints(self) -> List[BoolRef]:
        """Get all domain constraints"""
        return self.domain_constraints
    
    def get_variable(self, operand: str) -> Optional[ExprRef]:
        """Get Z3 variable for operand"""
        return self.variables.get(operand)
    
    def get_formula(self, constraint_id: str) -> Optional[BoolRef]:
        """Get Z3 formula for constraint"""
        return self.formulas.get(constraint_id)
    
    def reset(self):
        """Clear all encoded formulas and variables"""
        self.variables.clear()
        self.formulas.clear()
        self.constraints.clear()
        self.domain_constraints.clear()
    
    def print_encoding_summary(self):
        """Print summary of encoding"""
        print("\n" + "="*70)
        print("Z3 ENCODING SUMMARY")
        print("="*70)
        print(f"\nVariables ({len(self.variables)}):")
        for name, var in self.variables.items():
            print(f"  {name}: {var.sort()}")
        
        print(f"\nFormulas ({len(self.formulas)}):")
        for constraint_id, formula in self.formulas.items():
            print(f"  {constraint_id}: {formula}")
        
        if self.domain_constraints:
            print(f"\nDomain Constraints ({len(self.domain_constraints)}):")
            for dc in self.domain_constraints:
                print(f"  {dc}")
        
        print("="*70 + "\n")