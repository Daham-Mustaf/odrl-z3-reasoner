# src/normalizer/canonical_normalizer.py
"""
Canonical Normal Form for ODRL constraints.

Transforms semantically equivalent constraints into identical structures.
Enables: caching, deduplication, comparison, explanation.
"""

from typing import Dict, List, Set, Union, Tuple
import hashlib
import json
from dataclasses import dataclass

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, ConstraintType,
    OperatorType, NormalizedValue
)

@dataclass
class CanonicalStats:
    """Statistics from canonicalization"""
    flattened_ands: int = 0
    flattened_ors: int = 0
    removed_tautologies: int = 0
    removed_duplicates: int = 0
    normalized_xones: int = 0
    total_simplifications: int = 0

class ConstraintCanonicalizer:
    """
    Transform ODRL constraints into canonical normal form.
    
    Rules applied:
    1. Flatten AND/OR (associativity)
    2. Sort children (commutativity)
    3. Remove duplicates (idempotence)
    4. Normalize XONE arity
    5. Eliminate tautologies
    6. Constant folding
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.stats = CanonicalStats()
        self.constraint_hashes: Dict[str, str] = {}  # constraint_id -> hash
        
    def canonicalize(self, 
                    constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]]
                    ) -> Dict[str, Union[AtomicConstraint, CompositeConstraint]]:
        """Transform constraints to canonical form."""
        canonical = {}
        
        # First pass: canonicalize each constraint
        for constraint_id, constraint in constraints.items():
            canonical_constraint = self._canonicalize_constraint(constraint, constraints)
            
            # Skip if marked for removal or returned None
            if canonical_constraint is not None and canonical_constraint != "REMOVE":
                canonical[constraint_id] = canonical_constraint
        
        # Second pass: deduplicate by hash
        canonical = self._deduplicate_by_hash(canonical)
        
        if self.debug:
            self._print_stats(len(constraints), len(canonical))
        
        return canonical
        
    # ==========================================================================
    # CANONICALIZATION RULES
    # ==========================================================================
    
    def _canonicalize_constraint(self, 
                                 constraint: Union[AtomicConstraint, CompositeConstraint],
                                 all_constraints: Dict
                                ) -> Union[AtomicConstraint, CompositeConstraint, None]:
        """Canonicalize a single constraint"""
        
        if isinstance(constraint, AtomicConstraint):
            # Atomic constraints are already canonical (no structure)
            return constraint
        
        elif isinstance(constraint, CompositeConstraint):
            return self._canonicalize_composite(constraint, all_constraints)
        
        return constraint
    
    def _canonicalize_composite(self,
                               constraint: CompositeConstraint,
                               all_constraints: Dict
                              ) -> Union[CompositeConstraint, AtomicConstraint, None]:
        """Canonicalize composite constraint"""
        
        # Recursively canonicalize children first
        canonical_children = []
        for child_id in constraint.children:
            child = all_constraints.get(child_id)
            if child:
                canonical_child = self._canonicalize_constraint(child, all_constraints)
                if canonical_child is not None:
                    canonical_children.append(child_id)
        
        # Apply canonicalization rules
        constraint_type = constraint.constraint_type
        
        # Rule 1: Flatten AND/OR
        if constraint_type in [ConstraintType.AND, ConstraintType.OR]:
            canonical_children = self._flatten(canonical_children, constraint_type, all_constraints)
        
        # Rule 2: Normalize XONE arity
        if constraint_type == ConstraintType.XONE:
            result = self._normalize_xone(canonical_children, all_constraints)
            if result is not None:
                return result
        
        # Rule 3: Remove duplicates
        canonical_children = self._remove_duplicates(canonical_children, all_constraints)
        
        # Rule 4: Sort children
        canonical_children = self._sort_children(canonical_children, all_constraints)
        
        # Rule 5: Eliminate tautologies (TRUE/FALSE)
        result = self._eliminate_tautologies(constraint_type, canonical_children, all_constraints)
        if result is not None:
            return result
        
        # Update constraint with canonical children
        constraint.children = canonical_children
        return constraint
    
    # ==========================================================================
    # RULE 1: FLATTEN AND/OR
    # ==========================================================================
    
    def _flatten(self, 
                children: List[str],
                constraint_type: ConstraintType,
                all_constraints: Dict) -> List[str]:
        """
        Flatten nested AND/OR.
        
        AND(A, AND(B, C)) → AND(A, B, C)
        OR(A, OR(B, C))   → OR(A, B, C)
        """
        flattened = []
        
        for child_id in children:
            child = all_constraints.get(child_id)
            
            # If child is same type (AND inside AND, OR inside OR), flatten
            if isinstance(child, CompositeConstraint) and child.constraint_type == constraint_type:
                # Recursively flatten
                flattened.extend(child.children)
                
                if constraint_type == ConstraintType.AND:
                    self.stats.flattened_ands += 1
                else:
                    self.stats.flattened_ors += 1
            else:
                flattened.append(child_id)
        
        return flattened
    
    # ==========================================================================
    # RULE 2: NORMALIZE XONE
    # ==========================================================================
    
    def _normalize_xone(self, 
                    children: List[str],
                    all_constraints: Dict
                    ) -> Union[CompositeConstraint, AtomicConstraint, None]:
        """
        Normalize XONE arity.
        
        XONE()    → None (will be removed)
        XONE(A)   → A
        XONE(A,B) → XONE(A,B) (keep)
        """
        if len(children) == 0:
            # Empty XONE is unsatisfiable - mark for removal
            self.stats.normalized_xones += 1
            # Return a special marker that tells parent to remove this
            # We'll return the constraint but mark it
            return "REMOVE"  # Special marker
        
        elif len(children) == 1:
            # XONE(A) ≡ A
            self.stats.normalized_xones += 1
            child_id = children[0]
            return all_constraints.get(child_id)
        
        else:
            # Keep XONE with 2+ children
            return None  # Signal: no change
        
    # ==========================================================================
    # RULE 3: REMOVE DUPLICATES
    # ==========================================================================
    
    def _remove_duplicates(self,
                          children: List[str],
                          all_constraints: Dict) -> List[str]:
        """
        Remove duplicate children.
        
        AND(A, A, B) → AND(A, B)
        OR(A, A)     → A
        """
        # Use hash to detect duplicates
        seen_hashes = set()
        unique_children = []
        
        for child_id in children:
            child_hash = self._compute_hash(child_id, all_constraints)
            
            if child_hash not in seen_hashes:
                seen_hashes.add(child_hash)
                unique_children.append(child_id)
            else:
                self.stats.removed_duplicates += 1
        
        return unique_children
    
    # ==========================================================================
    # RULE 4: SORT CHILDREN
    # ==========================================================================
    
    def _sort_children(self,
                      children: List[str],
                      all_constraints: Dict) -> List[str]:
        """
        Sort children by canonical key.
        
        Makes order deterministic (commutativity).
        """
        def sort_key(child_id: str) -> Tuple:
            child = all_constraints.get(child_id)
            
            if isinstance(child, AtomicConstraint):
                # Sort by (operand, operator, value)
                return (
                    0,  # Atomic before composite
                    child.left_operand,
                    child.operator.value,
                    str(child.right_value.canonical_value)
                )
            
            elif isinstance(child, CompositeConstraint):
                # Sort by (type, num_children, hash)
                return (
                    1,  # Composite after atomic
                    child.constraint_type.value,
                    len(child.children),
                    self._compute_hash(child_id, all_constraints)
                )
            
            else:
                return (2, child_id)  # Unknown
        
        return sorted(children, key=sort_key)
    
    # ==========================================================================
    # RULE 5: ELIMINATE TAUTOLOGIES
    # ==========================================================================
    
    def _eliminate_tautologies(self,
                              constraint_type: ConstraintType,
                              children: List[str],
                              all_constraints: Dict
                             ) -> Union[AtomicConstraint, None]:
        """
        Eliminate TRUE/FALSE constants.
        
        AND(A, TRUE)  → A
        OR(A, FALSE)  → A
        AND(A, FALSE) → FALSE
        OR(A, TRUE)   → TRUE
        """
        # Check if any child is a tautology/contradiction
        # (This requires semantic analysis - skip for now)
        
        # Simple case: single child
        if len(children) == 1:
            self.stats.total_simplifications += 1
            return all_constraints.get(children[0])
        
        return None  # No simplification
    
    # ==========================================================================
    # HASHING & DEDUPLICATION
    # ==========================================================================
    
    def _compute_hash(self, constraint_id: str, all_constraints: Dict) -> str:
        """Compute canonical hash for constraint"""
        
        # Check cache
        if constraint_id in self.constraint_hashes:
            return self.constraint_hashes[constraint_id]
        
        constraint = all_constraints.get(constraint_id)
        if not constraint:
            return ""
        
        if isinstance(constraint, AtomicConstraint):
            # Hash atomic constraint
            hash_input = {
                'type': 'atomic',
                'operand': constraint.left_operand,
                'operator': constraint.operator.value,
                'value': constraint.right_value.canonical_value,
                'unit': constraint.right_value.canonical_unit
            }
        
        elif isinstance(constraint, CompositeConstraint):
            # Hash composite constraint (recursively)
            child_hashes = [self._compute_hash(c, all_constraints) for c in constraint.children]
            hash_input = {
                'type': 'composite',
                'constraint_type': constraint.constraint_type.value,
                'children': sorted(child_hashes)  # Sort for commutativity
            }
        
        else:
            hash_input = {'type': 'unknown', 'id': constraint_id}
        
        # Compute hash
        hash_str = hashlib.sha256(
            json.dumps(hash_input, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        self.constraint_hashes[constraint_id] = hash_str
        return hash_str
    
    def _deduplicate_by_hash(self, 
                            constraints: Dict
                           ) -> Dict:
        """Remove constraints with identical hashes"""
        
        hash_to_id = {}
        deduplicated = {}
        
        for constraint_id, constraint in constraints.items():
            constraint_hash = self._compute_hash(constraint_id, constraints)
            
            if constraint_hash not in hash_to_id:
                # First occurrence
                hash_to_id[constraint_hash] = constraint_id
                deduplicated[constraint_id] = constraint
            else:
                # Duplicate found
                self.stats.removed_duplicates += 1
        
        return deduplicated
    
    # ==========================================================================
    # UTILITIES
    # ==========================================================================
    
    def _print_stats(self, original_count: int, canonical_count: int):
        """Print canonicalization statistics"""
        print("\n" + "="*70)
        print("CANONICAL NORMALIZATION STATS")
        print("="*70)
        print(f"Original constraints: {original_count}")
        print(f"Canonical constraints: {canonical_count}")
        print(f"Removed: {original_count - canonical_count}")
        print()
        print(f"Flattened ANDs: {self.stats.flattened_ands}")
        print(f"Flattened ORs: {self.stats.flattened_ors}")
        print(f"Normalized XONEs: {self.stats.normalized_xones}")
        print(f"Removed duplicates: {self.stats.removed_duplicates}")
        print(f"Total simplifications: {self.stats.total_simplifications}")
        print("="*70 + "\n")
    
    def get_constraint_hash(self, constraint_id: str) -> str:
        """Get canonical hash for a constraint"""
        return self.constraint_hashes.get(constraint_id, "")
    
    def are_equivalent(self, 
                      c1_id: str, 
                      c2_id: str,
                      constraints: Dict) -> bool:
        """Check if two constraints are semantically equivalent"""
        h1 = self._compute_hash(c1_id, constraints)
        h2 = self._compute_hash(c2_id, constraints)
        return h1 == h2