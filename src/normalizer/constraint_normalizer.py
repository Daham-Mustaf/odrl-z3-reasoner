# src/normalizer/constraint_normalizer.py
"""
Normalize complete constraints with semantic validation.
Applies unit normalization and prepares for Z3 encoding.
"""

from typing import Dict, Union, List
import logging

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, NormalizedValue,
    get_operand_semantics
)
from ..semantics.units import VALUE_NORMALIZER

logger = logging.getLogger(__name__)

# src/normalizer/constraint_normalizer.py
# Update the import and __init__:

from ..semantics.units import get_value_normalizer

class ConstraintNormalizer:
    """
    Normalize constraints from RDF extraction to Z3-ready form.
    
    Pipeline:
    1. Extract raw constraint data
    2. Apply semantic typing
    3. Normalize values with unit conversion
    4. Validate semantic correctness
    5. Prepare for Z3 encoding
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.normalizer = get_value_normalizer(debug=debug)
    
    def normalize_constraint(self, 
                            constraint: Union[AtomicConstraint, CompositeConstraint]
                           ) -> Union[AtomicConstraint, CompositeConstraint]:
        """
        Normalize a constraint (atomic or composite).
        
        Args:
            constraint: Raw constraint from RDF extraction
            
        Returns:
            Normalized constraint ready for Z3
        """
        if isinstance(constraint, CompositeConstraint):
            # Composite constraints don't need normalization
            return constraint
        
        elif isinstance(constraint, AtomicConstraint):
            return self._normalize_atomic(constraint)
        
        else:
            raise ValueError(f"Unknown constraint type: {type(constraint)}")

    def _normalize_atomic(self, constraint: AtomicConstraint) -> AtomicConstraint:
        """Normalize atomic constraint"""
        
        # Check if already normalized
        if not constraint.metadata.get('needs_normalization', True):
            return constraint
        
        # Get operand semantics
        semantics = get_operand_semantics(constraint.left_operand)
        
        # Extract original value and unit
        original_value = constraint.right_value.original_value
        original_unit = constraint.right_value.original_unit
        
        if self.debug:
            logger.debug(f"Normalizing constraint {constraint.id}:")
            logger.debug(f"  Operand: {constraint.left_operand}")
            logger.debug(f"  Operator: {constraint.operator}")
            logger.debug(f"  Original value: {original_value}")
            logger.debug(f"  Original unit: {original_unit}")
        
        # Normalize value
        canonical_value, canonical_unit, value_metadata = self.normalizer.normalize(
            value=original_value,
            operand=constraint.left_operand,
            unit=original_unit,
            semantics=semantics
        )
        
        if self.debug:
            logger.debug(f"  Canonical value: {canonical_value}")
            logger.debug(f"  Canonical unit: {canonical_unit}")
            logger.debug(f"  Value metadata: {value_metadata}")
        
        # Create normalized value object
        normalized_value = NormalizedValue(
            canonical_value=canonical_value,
            original_value=original_value,
            original_unit=original_unit,
            canonical_unit=canonical_unit,
            conversion_factor=value_metadata.get('conversion_factor'),
            metadata=value_metadata.copy()  # Store complete metadata
        )
        
        # Update constraint
        constraint.right_value = normalized_value
        constraint.semantics = semantics
        
        # Update constraint metadata
        constraint.metadata['needs_normalization'] = False
        constraint.metadata['normalized'] = True
        
        # CRITICAL FIX: Copy ALL fields from value_metadata to constraint.metadata
        # This ensures tests can access conversion_factor, conversion_applied, etc.
        constraint.metadata.update(value_metadata)
        
        if self.debug:
            logger.debug(f"  Final constraint.metadata: {constraint.metadata}")
        
        return constraint
    
    def normalize_all(self, 
                     constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
                    ) -> Dict[str, Union[AtomicConstraint, CompositeConstraint]]:
        """Normalize all constraints in a policy"""
        normalized = {}
        
        for constraint_id, constraint in constraints.items():
            try:
                normalized[constraint_id] = self.normalize_constraint(constraint)
                
            except Exception as e:
                logger.error(f"Failed to normalize constraint {constraint_id}: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                
                # Keep original constraint with error flag
                constraint.metadata['normalization_error'] = str(e)
                normalized[constraint_id] = constraint
        
        logger.info(f"Normalized {len(normalized)} constraints")
        return normalized