# src/encoder/z3_encoder.py
"""
Z3 Encoder: Translate normalized ODRL constraints to Z3 formulas.

UPDATED to integrate with new semantics module:
- Uses is_self_contained() to filter analyzable constraints
- Uses validate_constraint() before encoding
- Uses get_z3_domain_assertions() for proper bounds
- Uses are_units_compatible() for unit checking

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
from typing import Dict, Union, List, Optional, Any, Set as PySet, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, ConstraintType,
    OperatorType, Z3Sort, ValueDomain
)

# Import NEW semantics module functions
from ..semantics import (
    # Grounding checks
    is_self_contained,
    is_statically_analyzable,
    get_grounding_requirement,
    GroundingRequirement,
    
    # Operand info
    get_operand_info,
    OperandCategory,
    
    # Domain bounds
    get_domain_bounds,
    get_z3_domain_assertions,
    validate_value_in_domain,
    
    # Operators
    parse_operator,
    is_relational_operator,
    is_set_operator,
    is_taxonomic_operator,
    Operator,
    
    # Units
    are_units_compatible,
    check_unit_compatibility,
    
    # Validation
    validate_constraint,
    ValidationResult,
    ValidationSeverity,
)


logger = logging.getLogger(__name__)


# ==============================================================================
# ENCODING RESULT TYPES
# ==============================================================================

class SkipReason(Enum):
    """Reasons why a constraint was skipped"""
    SEMANTIC_GROUNDING_REQUIRED = "semantic_grounding_required"
    RUNTIME_ONLY = "runtime_only"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_OPERAND = "unknown_operand"
    ENCODING_ERROR = "encoding_error"


@dataclass
class SkippedConstraint:
    """Information about a skipped constraint"""
    constraint_id: str
    operand: str
    reason: SkipReason
    message: str
    
    def __str__(self) -> str:
        return f"Skipped '{self.constraint_id}' ({self.operand}): {self.message}"


@dataclass
class EncodingResult:
    """Result of encoding a policy"""
    formulas: Dict[str, BoolRef] = field(default_factory=dict)
    skipped: List[SkippedConstraint] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def encoded_count(self) -> int:
        return len(self.formulas)
    
    @property
    def skipped_count(self) -> int:
        return len(self.skipped)
    
    def summary(self) -> str:
        lines = [
            f"Encoded: {self.encoded_count} constraints",
            f"Skipped: {self.skipped_count} constraints",
        ]
        if self.skipped:
            lines.append("Skipped details:")
            for s in self.skipped:
                lines.append(f"  - {s}")
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)
    
    # Backwards compatibility: allow dict-like access
    def __contains__(self, key: str) -> bool:
        return key in self.formulas
    
    def __getitem__(self, key: str) -> BoolRef:
        return self.formulas[key]
    
    def __iter__(self):
        return iter(self.formulas)
    
    def items(self):
        return self.formulas.items()
    
    def keys(self):
        return self.formulas.keys()
    
    def values(self):
        return self.formulas.values()
    
    def get(self, key: str, default=None):
        return self.formulas.get(key, default)


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
        
        classes = set()
        for s, p, o in self.graph.triples((None, RDFS.subClassOf, None)):
            s_str = self._normalize_uri(str(s))
            o_str = self._normalize_uri(str(o))
            classes.add(s_str)
            classes.add(o_str)
        
        for cls in classes:
            self.superclass_cache[cls] = self._get_superclasses(cls)
        
        for cls, supers in self.superclass_cache.items():
            for super_cls in supers:
                if super_cls not in self.subclass_cache:
                    self.subclass_cache[super_cls] = set()
                self.subclass_cache[super_cls].add(cls)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Hierarchy loaded: {len(classes)} classes")
    
    def _get_superclasses(self, cls: str) -> PySet[str]:
        """Get all superclasses of cls (transitive)"""
        from rdflib import RDFS
        
        superclasses = set()
        cls_uri = None
        
        for s, p, o in self.graph.triples((None, RDFS.subClassOf, None)):
            s_norm = self._normalize_uri(str(s))
            if s_norm == cls:
                cls_uri = s
                break
        
        if not cls_uri:
            return superclasses
        
        for super_cls in self.graph.objects(cls_uri, RDFS.subClassOf):
            super_str = self._normalize_uri(str(super_cls))
            superclasses.add(super_str)
            superclasses.update(self._get_superclasses(super_str))
        
        return superclasses
    
    def _normalize_uri(self, uri: str) -> str:
        """Normalize URI to lowercase for comparison"""
        uri = uri.lower()
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def is_a(self, instance_cls: str, target_cls: str) -> bool:
        """Check if instance_cls is-a target_cls (with transitivity)"""
        instance_norm = self._normalize_uri(str(instance_cls))
        target_norm = self._normalize_uri(str(target_cls))
        
        if instance_norm == target_norm:
            return True
        
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
    
    NEW: Integrates with semantics module for:
    - Constraint filtering (self-contained only by default)
    - Domain bounds enforcement
    - Unit compatibility checking
    - Validation before encoding
    
    Multi-valued operands use Z3 Arrays: Array[String, Bool]
    where array[key] = True means key is in the set.
    """
    
    def __init__(self, 
                 hierarchy: Optional[ClassHierarchy] = None, 
                 debug: bool = False,
                 strict_mode: bool = False,
                 include_reference_point: bool = False):
        """
        Initialize encoder.
        
        Args:
            hierarchy: Optional class hierarchy for isA reasoning
            debug: Enable debug logging
            strict_mode: If True, raise errors instead of skipping invalid constraints
            include_reference_point: If True, also encode reference-point constraints
                                    (elapsedTime, delayPeriod) with assumed t₀
        """
        self.debug = debug
        self.strict_mode = strict_mode
        self.include_reference_point = include_reference_point
        self.hierarchy = hierarchy
        
        # State
        self.variables: Dict[str, ExprRef] = {}
        self.formulas: Dict[str, BoolRef] = {}
        self.constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]] = {}
        self.domain_constraints: List[BoolRef] = []
        
        # Tracking
        self._encoding_result: Optional[EncodingResult] = None
    
    # ==========================================================================
    # MAIN ENCODING METHODS
    # ==========================================================================
    
    def encode_policy(self, 
                     constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
                    ) -> EncodingResult:
        """
        Encode all constraints in a policy.
        
        NEW: Returns EncodingResult with both encoded formulas and skipped constraints.
        
        Args:
            constraints: Dictionary of constraint_id -> constraint
            
        Returns:
            EncodingResult with formulas, skipped constraints, and warnings
        """
        self.constraints = constraints
        self._encoding_result = EncodingResult()
        
        if self.debug:
            logger.debug(f"Encoding {len(constraints)} constraints")
        
        for constraint_id, constraint in constraints.items():
            try:
                # Check if constraint can be encoded
                if isinstance(constraint, AtomicConstraint):
                    can_encode, skip_info = self._can_encode_constraint(constraint)
                    
                    if not can_encode:
                        self._encoding_result.skipped.append(SkippedConstraint(
                            constraint_id=constraint_id,
                            operand=constraint.left_operand,
                            reason=skip_info[0],
                            message=skip_info[1]
                        ))
                        continue
                
                # Encode the constraint
                formula = self.encode_constraint(constraint_id)
                self.formulas[constraint_id] = formula
                self._encoding_result.formulas[constraint_id] = formula
                
                if self.debug:
                    logger.debug(f"Encoded {constraint_id}: {formula}")
                    
            except Exception as e:
                if self.strict_mode:
                    raise
                
                logger.error(f"Failed to encode constraint {constraint_id}: {e}")
                self._encoding_result.skipped.append(SkippedConstraint(
                    constraint_id=constraint_id,
                    operand=getattr(constraint, 'left_operand', 'unknown'),
                    reason=SkipReason.ENCODING_ERROR,
                    message=str(e)
                ))
                
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        logger.info(f"Encoded {self._encoding_result.encoded_count} constraints, "
                   f"skipped {self._encoding_result.skipped_count}")
        
        return self._encoding_result
    
    def _can_encode_constraint(self, constraint: AtomicConstraint) -> Tuple[bool, Optional[Tuple[SkipReason, str]]]:
        """
        Check if a constraint can be encoded.
        
        NEW: Uses semantics module for grounding checks.
        
        Returns:
            Tuple of (can_encode, (reason, message) if cannot encode)
        """
        operand = constraint.left_operand
        operator = constraint.operator
        
        # Check grounding requirement
        grounding = get_grounding_requirement(operand)
        
        if grounding == GroundingRequirement.RUNTIME_ONLY:
            return (False, (SkipReason.RUNTIME_ONLY, 
                          f"Operand '{operand}' requires runtime data (meteredTime)"))
        
        if grounding == GroundingRequirement.SEMANTIC:
            # Semantic operands CAN be encoded with set operators (isAnyOf, isAllOf, isNoneOf)
            # Only isA/hasPart/isPartOf require hierarchy
            op_val = operator.value if hasattr(operator, 'value') else str(operator)
            taxonomic_operators = {'isA', 'hasPart', 'isPartOf'}
            
            if op_val in taxonomic_operators:
                if self.hierarchy is None:
                    return (False, (SkipReason.SEMANTIC_GROUNDING_REQUIRED,
                                  f"Operator '{op_val}' on '{operand}' requires semantic grounding (no hierarchy loaded)"))
            # For non-taxonomic operators (eq, isAnyOf, etc.), allow encoding
        
        if grounding == GroundingRequirement.REFERENCE_POINT:
            if not self.include_reference_point:
                return (False, (SkipReason.SEMANTIC_GROUNDING_REQUIRED,
                              f"Operand '{operand}' requires reference point (enable with include_reference_point=True)"))
        
        # Validate constraint
        validation = validate_constraint(
            operand=operand,
            operator=operator.value if hasattr(operator, 'value') else str(operator),
            value=constraint.right_value.canonical_value,
            unit=constraint.odrl_metadata.unit if constraint.odrl_metadata else None
        )
        
        if not validation.is_valid:
            error_msgs = [m.message for m in validation.messages if m.severity == ValidationSeverity.ERROR]
            return (False, (SkipReason.VALIDATION_ERROR, "; ".join(error_msgs)))
        
        # Add warnings to result
        if validation.has_warnings:
            for msg in validation.messages:
                if msg.severity == ValidationSeverity.WARNING:
                    if self._encoding_result:
                        self._encoding_result.warnings.append(f"{operand}: {msg.message}")
        
        return (True, None)
    
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
        
        # Special handling for monetary (currency-specific variables)
        if constraint.semantics.domain == ValueDomain.MONETARY:
            currency = constraint.metadata.get('currency', 'UNKNOWN')
            var_name = f"{var_name}_{currency}"
            var = self._get_or_create_variable_with_name(
                var_name, 
                constraint.semantics,
                operand,  # Pass original operand for domain bounds
                is_multi_valued=False
            )
        else:
            is_multi = operand in MULTI_VALUED_OPERANDS
            var = self._get_or_create_variable_with_name(
                var_name,
                constraint.semantics,
                operand,
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
        
        def to_z3_value(val, var_sort):
            """Convert Python value to Z3 value based on variable sort"""
            sort_str = str(var_sort)
            
            if 'String' in sort_str:
                return StringVal(str(val))
            elif 'Int' in sort_str:
                # Handle datetime strings
                if isinstance(val, str):
                    # Check if it's a datetime string
                    if 'T' in val or val.endswith('Z'):
                        try:
                            from datetime import datetime
                            # Try parsing ISO datetime
                            dt_str = val.replace('Z', '+00:00')
                            if '+' in dt_str or '-' in dt_str[8:]:  # Has timezone
                                # Remove timezone for parsing
                                if '+' in dt_str:
                                    dt_str = dt_str[:dt_str.rfind('+')]
                                elif '-' in dt_str[8:]:
                                    dt_str = dt_str[:dt_str.rfind('-')]
                            dt = datetime.fromisoformat(dt_str.replace('Z', ''))
                            return int(dt.timestamp())
                        except Exception:
                            pass
                    # Try direct int conversion
                    try:
                        return int(val)
                    except ValueError:
                        # Can't convert, use hash as fallback
                        return hash(val) % (2**31)
                return int(val)
            elif 'Real' in sort_str:
                return float(val)
            else:
                return val
        
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
            if not isinstance(value, list):
                value = [value]
            return Or([Select(var_array, StringVal(str(v))) for v in value])
        
        elif operator == OperatorType.IS_ALL_OF:
            if not isinstance(value, list):
                value = [value]
            return And([Select(var_array, StringVal(str(v))) for v in value])
        
        elif operator == OperatorType.IS_NONE_OF:
            if not isinstance(value, list):
                value = [value]
            return And([Not(Select(var_array, StringVal(str(v)))) for v in value])
        
        elif operator == OperatorType.HAS_PART:
            if isinstance(value, list):
                return Or([Select(var_array, StringVal(str(v))) for v in value])
            else:
                return Select(var_array, StringVal(str(value)))
        
        elif operator == OperatorType.IS_PART_OF:
            if isinstance(value, list):
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
            if isinstance(value, list):
                return Or([var == StringVal(str(v)) for v in value])
            else:
                return var == StringVal(str(value))
        
        else:
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
            if isinstance(value, list):
                return Or([Select(var_array, StringVal(str(v))) for v in value])
            else:
                return Select(var_array, StringVal(str(value)))
        
        else:
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
            # Check if child was skipped
            if child_id not in self.constraints:
                continue
            
            child_constraint = self.constraints[child_id]
            
            # For atomic children, check if they can be encoded
            if isinstance(child_constraint, AtomicConstraint):
                can_encode, _ = self._can_encode_constraint(child_constraint)
                if not can_encode:
                    continue
            
            try:
                child_formula = self.encode_constraint(child_id)
                child_formulas.append(child_formula)
            except Exception as e:
                logger.warning(f"Skipping child {child_id} in composite: {e}")
                continue
        
        if not child_formulas:
            logger.warning(f"Composite constraint has no encodable children, returning True")
            return BoolVal(True)
        
        if self.debug:
            logger.debug(f"  Encoding {constraint.constraint_type.value} with {len(child_formulas)} children")
        
        if constraint.constraint_type == ConstraintType.AND:
            return And(child_formulas)
        elif constraint.constraint_type == ConstraintType.OR:
            return Or(child_formulas)
        elif constraint.constraint_type == ConstraintType.XONE:
            return PbEq([(f, 1) for f in child_formulas], 1)
        elif constraint.constraint_type == ConstraintType.ANDSEQUENCE:
            # Preserve structure: treat as AND for static analysis
            # (temporal ordering not analyzed)
            logger.info("andSequence treated as AND for static analysis")
            return And(child_formulas)
        else:
            raise ValueError(f"Unknown composite type: {constraint.constraint_type}")
    
    # ==========================================================================
    # VARIABLE MANAGEMENT
    # ==========================================================================
    
    def _get_or_create_variable_with_name(self, var_name: str, semantics: Any,
                                          operand: str,
                                          is_multi_valued: bool = False) -> ExprRef:
        """
        Create Z3 variable with specific name.
        
        NEW: Uses get_z3_domain_assertions() from semantics module.
        """
        if var_name in self.variables:
            return self.variables[var_name]
        
        if self.debug:
            logger.debug(f"  Creating variable '{var_name}' (multi={is_multi_valued})")
        
        if is_multi_valued:
            # Create Z3 Array[String, Bool]
            var = Array(var_name, StringSort(), BoolSort())
        
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
            
            # NEW: Use semantics module for domain constraints
            try:
                domain_assertions = get_z3_domain_assertions(operand, var)
                self.domain_constraints.extend(domain_assertions)
                
                if self.debug and domain_assertions:
                    logger.debug(f"    Added domain constraints: {domain_assertions}")
                    
            except Exception as e:
                # Fallback to old behavior if semantics module fails
                if semantics.value_range and z3_sort in [Z3Sort.INT, Z3Sort.REAL]:
                    min_val, max_val = semantics.value_range
                    if min_val is not None:
                        self.domain_constraints.append(var >= min_val)
                    if max_val is not None:
                        self.domain_constraints.append(var <= max_val)
        
        self.variables[var_name] = var
        return var
    
    # ==========================================================================
    # UNIT COMPATIBILITY CHECKING
    # ==========================================================================
    
    def check_constraint_pair_units(self, 
                                    c1: AtomicConstraint, 
                                    c2: AtomicConstraint) -> Tuple[bool, Optional[str]]:
        """
        Check if two constraints have compatible units for comparison.
        
        NEW: Uses are_units_compatible() from semantics module.
        
        Returns:
            Tuple of (compatible, warning_message)
        """
        if c1.left_operand != c2.left_operand:
            return (True, None)  # Different operands, no unit comparison needed
        
        unit1 = c1.odrl_metadata.unit if c1.odrl_metadata else None
        unit2 = c2.odrl_metadata.unit if c2.odrl_metadata else None
        
        return check_unit_compatibility(unit1, unit2)
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def get_domain_constraints(self) -> List[BoolRef]:
        """Get all domain constraints"""
        return self.domain_constraints
    
    def get_variable(self, operand: str) -> Optional[ExprRef]:
        """Get Z3 variable for operand"""
        return self.variables.get(operand)
    
    def create_variable(self, operand: str, semantics: Any) -> ExprRef:
        """
        Create a Z3 variable for an operand.
        
        Backwards compatibility method - now delegates to internal method.
        
        Args:
            operand: Operand name
            semantics: SemanticInfo for the operand
            
        Returns:
            Z3 variable (scalar or array depending on operand)
        """
        is_multi = operand in MULTI_VALUED_OPERANDS
        return self._get_or_create_variable_with_name(
            operand, semantics, operand, is_multi_valued=is_multi
        )
    
    def encode_set_operator(self, operator: OperatorType, var: ExprRef, 
                           values: List[Any]) -> BoolRef:
        """
        Encode a set operator for backwards compatibility.
        
        Args:
            operator: The operator (IS_ANY_OF, IS_ALL_OF, IS_NONE_OF)
            var: Z3 variable (array or scalar)
            values: List of values
            
        Returns:
            Z3 formula
        """
        # Check if var is an array
        var_sort = str(var.sort())
        is_array = 'Array' in var_sort
        
        if is_array:
            if operator == OperatorType.IS_ANY_OF:
                return Or([Select(var, StringVal(str(v))) for v in values])
            elif operator == OperatorType.IS_ALL_OF:
                return And([Select(var, StringVal(str(v))) for v in values])
            elif operator == OperatorType.IS_NONE_OF:
                return And([Not(Select(var, StringVal(str(v)))) for v in values])
        else:
            if operator == OperatorType.IS_ANY_OF:
                return Or([var == StringVal(str(v)) for v in values])
            elif operator == OperatorType.IS_ALL_OF:
                if len(values) == 1:
                    return var == StringVal(str(values[0]))
                else:
                    return BoolVal(False)  # Single-valued can't be all of multiple
            elif operator == OperatorType.IS_NONE_OF:
                return And([var != StringVal(str(v)) for v in values])
        
        raise ValueError(f"Unsupported operator: {operator}")
    
    def _create_set_from_list(self, values: List[str]) -> ExprRef:
        """
        Create an array with the given values set to True.
        
        Backwards compatibility method for tests.
        
        Args:
            values: List of string values to include in set
            
        Returns:
            Z3 Array with values[i] -> True
        """
        # Create a base array with all False
        arr = K(StringSort(), BoolVal(False))
        
        # Store True for each value
        for v in values:
            arr = Store(arr, StringVal(str(v)), BoolVal(True))
        
        return arr
    
    def get_formula(self, constraint_id: str) -> Optional[BoolRef]:
        """Get Z3 formula for constraint"""
        return self.formulas.get(constraint_id)
    
    def get_encoding_result(self) -> Optional[EncodingResult]:
        """Get the last encoding result"""
        return self._encoding_result
    
    def reset(self):
        """Clear all encoded formulas and variables"""
        self.variables.clear()
        self.formulas.clear()
        self.constraints.clear()
        self.domain_constraints.clear()
        self._encoding_result = None
    
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
        
        if self._encoding_result and self._encoding_result.skipped:
            print(f"\nSkipped Constraints ({len(self._encoding_result.skipped)}):")
            for s in self._encoding_result.skipped:
                print(f"  {s}")
        
        if self._encoding_result and self._encoding_result.warnings:
            print(f"\nWarnings ({len(self._encoding_result.warnings)}):")
            for w in self._encoding_result.warnings:
                print(f"  {w}")
        
        print("="*70 + "\n")