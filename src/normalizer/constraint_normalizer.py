# src/normalizer/constraint_normalizer.py
"""
Normalize complete constraints with semantic validation.
Applies unit normalization and prepares for Z3 encoding.

Implementation Plan Alignment:
- Constraint normalization pipeline
- Full metadata handling (unit, unitOfCount, status, dataType)
- Prepares constraints for SMT encoding
"""

from typing import Dict, Union, List, Optional, Any
import logging

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, NormalizedValue,
    ODRLMetadata, SemanticInfo, ValueDomain, Z3Sort,
    get_operand_semantics, get_z3_sort_for_datatype,
    debug_print, is_debug_mode
)
from ..semantics.units import get_value_normalizer

logger = logging.getLogger(__name__)


class ConstraintNormalizer:
    """
    Normalize constraints from RDF extraction to Z3-ready form.
    
    Pipeline:
    1. Extract raw constraint data
    2. Apply semantic typing based on leftOperand
    3. Handle ODRL metadata (unit, unitOfCount, status, dataType)
    4. Normalize values with unit conversion
    5. Determine Z3 sort from dataType
    6. Validate semantic correctness
    7. Prepare for Z3 encoding
    
    Implementation:
    - Complete normalization
    - Metadata-aware normalization
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize normalizer.
        
        Args:
            debug: Enable debug output (--dev mode)
        """
        self.debug = debug
        self.normalizer = get_value_normalizer(debug=debug)
        self._stats = {
            'total': 0,
            'atomic': 0,
            'composite': 0,
            'with_unit': 0,
            'with_unit_of_count': 0,
            'with_status': 0,
            'with_datatype': 0,
            'errors': 0,
        }
    
    def normalize_constraint(
        self, 
        constraint: Union[AtomicConstraint, CompositeConstraint]
    ) -> Union[AtomicConstraint, CompositeConstraint]:
        """
        Normalize a constraint (atomic or composite).
        
        Args:
            constraint: Raw constraint from RDF extraction
            
        Returns:
            Normalized constraint ready for Z3
        """
        self._stats['total'] += 1
        
        if isinstance(constraint, CompositeConstraint):
            self._stats['composite'] += 1
            return self._normalize_composite(constraint)
        
        elif isinstance(constraint, AtomicConstraint):
            self._stats['atomic'] += 1
            return self._normalize_atomic(constraint)
        
        else:
            raise ValueError(f"Unknown constraint type: {type(constraint)}")
    
    def _normalize_composite(
        self, 
        constraint: CompositeConstraint
    ) -> CompositeConstraint:
        """
        Normalize composite constraint.
        
        Composite constraints (AND/OR/XONE/ANDSEQUENCE) don't need value
        normalization, but we track metadata and handle ANDSEQUENCE specially.
        """
        self._debug(f"Composite constraint: {constraint.id} ({constraint.constraint_type.value})")
        
        # Mark ANDSEQUENCE as sequential (preserved, not flattened)
        if constraint.is_sequential():
            constraint.metadata['is_sequential'] = True
            constraint.metadata['preserve_order'] = True
            self._debug(f"  ANDSEQUENCE preserved (no flattening)")
        
        constraint.metadata['normalized'] = True
        return constraint
    
    def _normalize_atomic(self, constraint: AtomicConstraint) -> AtomicConstraint:
        """
        Normalize atomic constraint with full ODRL metadata handling.
        
        Implementation Metadata:
        - unit: Applied to value normalization
        - unitOfCount: Stored for count-based evaluation
        - status: Stored as comparison baseline
        - dataType: Determines Z3 sort
        """
        
        # Check if already normalized
        if not constraint.metadata.get('needs_normalization', True):
            return constraint
        
        self._debug(f"Normalizing atomic constraint: {constraint.id}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 1: Get operand semantics
        # ══════════════════════════════════════════════════════════════════════
        semantics = get_operand_semantics(constraint.left_operand)
        self._debug(f"  Operand: {constraint.left_operand}", {
            'domain': semantics.domain.value,
            'z3_sort': semantics.z3_sort.value,
            'base_unit': semantics.base_unit
        })
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 2: Extract ODRL metadata
        # ══════════════════════════════════════════════════════════════════════
        odrl_meta = constraint.odrl_metadata or ODRLMetadata()
        
        # Track metadata stats
        if odrl_meta.unit:
            self._stats['with_unit'] += 1
        if odrl_meta.unit_of_count:
            self._stats['with_unit_of_count'] += 1
        if odrl_meta.status is not None:
            self._stats['with_status'] += 1
        if odrl_meta.datatype:
            self._stats['with_datatype'] += 1
        
        self._debug(f"  ODRL metadata:", odrl_meta.to_dict())
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 3: Determine effective unit
        # ══════════════════════════════════════════════════════════════════════
        # Priority: odrl_metadata.unit > right_value.original_unit > semantics.base_unit
        effective_unit = (
            odrl_meta.unit or 
            constraint.right_value.original_unit or 
            semantics.base_unit
        )
        
        self._debug(f"  Effective unit: {effective_unit}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 4: Normalize value with unit conversion
        # ══════════════════════════════════════════════════════════════════════
        original_value = constraint.right_value.original_value
        
        canonical_value, canonical_unit, value_metadata = self.normalizer.normalize(
            value=original_value,
            operand=constraint.left_operand,
            unit=effective_unit,
            semantics=semantics
        )
        
        self._debug(f"  Value normalization:", {
            'original': original_value,
            'canonical': canonical_value,
            'unit': f"{effective_unit} -> {canonical_unit}"
        })
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 5: Handle unitOfCount 
        # ══════════════════════════════════════════════════════════════════════
        if odrl_meta.unit_of_count:
            value_metadata['unit_of_count'] = odrl_meta.unit_of_count
            value_metadata['is_per_entity'] = True
            self._debug(f"  unitOfCount: {odrl_meta.unit_of_count} (per-entity constraint)")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 6: Handle status (comparison baseline)
        # ══════════════════════════════════════════════════════════════════════
        if odrl_meta.status is not None:
            value_metadata['status'] = odrl_meta.status
            value_metadata['has_baseline'] = True
            self._debug(f"  status baseline: {odrl_meta.status}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 7: Determine Z3 sort from dataType
        # ══════════════════════════════════════════════════════════════════════
        if odrl_meta.datatype:
            z3_sort = get_z3_sort_for_datatype(odrl_meta.datatype)
            value_metadata['z3_sort_override'] = z3_sort.value
            value_metadata['explicit_datatype'] = odrl_meta.datatype
            self._debug(f"  dataType -> Z3 sort: {odrl_meta.datatype} -> {z3_sort.value}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 8: Create normalized value object
        # ══════════════════════════════════════════════════════════════════════
        normalized_value = NormalizedValue(
            canonical_value=canonical_value,
            original_value=original_value,
            original_unit=effective_unit,
            canonical_unit=canonical_unit,
            conversion_factor=value_metadata.get('conversion_factor'),
            metadata=value_metadata.copy()
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 9: Update constraint
        # ══════════════════════════════════════════════════════════════════════
        constraint.right_value = normalized_value
        constraint.semantics = semantics
        
        # Update constraint metadata
        constraint.metadata['needs_normalization'] = False
        constraint.metadata['normalized'] = True
        constraint.metadata.update(value_metadata)
        
        # Store ODRL metadata reference
        if not odrl_meta.is_empty():
            constraint.metadata['has_odrl_metadata'] = True
        
        self._debug(f"  Normalization complete for {constraint.id}")
        
        return constraint
    
    def normalize_all(
        self, 
        constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
    ) -> Dict[str, Union[AtomicConstraint, CompositeConstraint]]:
        """
        Normalize all constraints in a policy.
        
        Args:
            constraints: Dict of constraint_id -> constraint
            
        Returns:
            Dict of normalized constraints
        """
        self._debug(f"Normalizing {len(constraints)} constraints")
        
        normalized = {}
        
        for constraint_id, constraint in constraints.items():
            try:
                normalized[constraint_id] = self.normalize_constraint(constraint)
                
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"Failed to normalize constraint {constraint_id}: {e}")
                self._debug(f"Normalization error for {constraint_id}: {e}")
                
                if self.debug:
                    import traceback
                    traceback.print_exc()
                
                # Keep original constraint with error flag
                constraint.metadata['normalization_error'] = str(e)
                normalized[constraint_id] = constraint
        
        self._debug(f"Normalization complete", self._stats)
        logger.info(f"Normalized {len(normalized)} constraints")
        
        return normalized
    
    def normalize_policy_constraints(self, policy) -> None:
        """
        Normalize all constraints in a Policy object in-place.
        
        Args:
            policy: Policy object with constraints dict
        """
        self._debug(f"Normalizing policy: {policy.id}")
        policy.constraints = self.normalize_all(policy.constraints)
    
    # ==========================================================================
    # DEBUG & STATS
    # ==========================================================================
    
    def _debug(self, message: str, data: Any = None):
        """Print debug message if debug mode enabled"""
        if self.debug:
            debug_print("NORMALIZER", message, data)
            logger.debug(f"[NORMALIZER] {message}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get normalization statistics"""
        return self._stats.copy()
    
    def print_stats(self):
        """Print normalization statistics"""
        if not self.debug:
            return
        
        print("\n" + "=" * 60)
        print("📊 NORMALIZATION STATISTICS")
        print("=" * 60)
        print(f"  Total constraints: {self._stats['total']}")
        print(f"  Atomic: {self._stats['atomic']}")
        print(f"  Composite: {self._stats['composite']}")
        print(f"\n  Metadata coverage:")
        print(f"    With unit: {self._stats['with_unit']}")
        print(f"    With unitOfCount: {self._stats['with_unit_of_count']}")
        print(f"    With status: {self._stats['with_status']}")
        print(f"    With dataType: {self._stats['with_datatype']}")
        print(f"\n  Errors: {self._stats['errors']}")
        print("=" * 60 + "\n")
    
    def reset_stats(self):
        """Reset statistics counters"""
        self._stats = {
            'total': 0,
            'atomic': 0,
            'composite': 0,
            'with_unit': 0,
            'with_unit_of_count': 0,
            'with_status': 0,
            'with_datatype': 0,
            'errors': 0,
        }