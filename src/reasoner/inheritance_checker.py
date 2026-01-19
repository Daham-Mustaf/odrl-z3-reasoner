# src/reasoner/inheritance_checker.py
"""
Monotonic Constraint Inheritance Checker

Formal Model:
- Parent policy P₀ defines constraints ⟦P₀⟧
- Child policy P₁ defines constraints ⟦P₁⟧  
- Valid inheritance: ∀a ∈ Actions: ⟦P₁⟧ₐ ⇒ ⟦P₀⟧ₐ
- Violation: ∃a ∈ Actions: SAT(⟦P₁⟧ₐ ∧ ¬⟦P₀⟧ₐ)

Action Semantics:
- Actions are symbolic labels used to partition constraint spaces
- Inheritance is checked independently for each action
- No deontic entailment across action hierarchies (includedIn is ignored)
- No cross-action reasoning or propagation

Rule Combination Semantics:
- Multiple rules for the same action are interpreted CONJUNCTIVELY
- This corresponds to cumulative constraints rather than alternative permissions
- Disjunctive semantics must be expressed explicitly via OR/XONE constraints

Violation Types:
- expansion: Child allows valuations forbidden by parent (HARD VIOLATION)
- inconsistent: Child has unsatisfiable constraints (HARD VIOLATION)
- new_action: Child permits action not in parent (HARD VIOLATION)
- redundant: Child adds no restriction beyond parent (WARNING)

Explicit Exclusions (Out of Scope):
- Action hierarchy reasoning (includedIn)
- Permission vs prohibition conflict resolution
- Duty/obligation satisfaction
- Enforcement semantics
- Temporal execution models
"""


from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from z3 import Solver, Not, And, Or, sat, unsat, BoolVal
import logging


from ..semantics.constraint_types import debug_print, is_debug_mode

logger = logging.getLogger(__name__)


@dataclass
class InheritanceViolation:
    """Represents an inheritance violation"""
    parent_id: str
    child_id: str
    violation_type: str  # 'expansion', 'inconsistent', 'redundant', 'new_action'
    action: Optional[str]  # The action this violation applies to
    counterexample: Optional[Dict[str, Any]]
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)  # ADD: Extra metadata


class InheritanceChecker:
    """
    Check monotonic constraint inheritance between policies.
    
    Formal semantics (per-action):
    - Valid inheritance: ∀a ∈ Actions: ⟦child⟧ₐ ⇒ ⟦parent⟧ₐ
    - Expansion violation: ∃a: SAT(⟦child⟧ₐ ∧ ¬⟦parent⟧ₐ)
    - Internal inconsistency: ∃a: UNSAT(⟦child⟧ₐ)
    - Redundancy: ∀a: UNSAT(⟦parent⟧ₐ ∧ ¬⟦child⟧ₐ)
    """
    
    def __init__(self, encoder, debug: bool = False):
        self.encoder = encoder
        self.debug = debug
        
        # ADD: Statistics tracking
        self._stats = {
            'total_checks': 0,
            'actions_checked': 0,
            'sat_results': 0,
            'unsat_results': 0,
            'violations_found': 0,
            'warnings_found': 0,
        }
    
    def _debug(self, message: str, data: Any = None):
        """Debug output helper"""
        if self.debug:
            debug_print("INHERITANCE", message, data)
            logger.debug(f"[INHERITANCE] {message}")
    
    def check_inheritance(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """
        Check if child policy validly inherits from parent.
        
        This method checks inheritance across ALL constraints combined.
        For per-action checking, use check_inheritance_per_action().
        """
        violations = []
        
        parent_id = self._get_policy_id(parent_policy)
        child_id = self._get_policy_id(child_policy)
        
        self._debug(f"Checking inheritance: {child_id} → {parent_id}")
        
        # Encode both policies
        parent_formula, parent_domains = self._encode_policy(parent_policy, "parent")
        child_formula, child_domains = self._encode_policy(child_policy, "child")
        
        self._debug(f"Parent formula: {parent_formula}")
        self._debug(f"Child formula: {child_formula}")
        
        # Handle None cases
        if child_formula is None:
            if parent_formula is not None:
                # Child has no constraints = allows everything = EXPANSION
                self._stats['violations_found'] += 1
                return [InheritanceViolation(
                    parent_id=parent_id,
                    child_id=child_id,
                    violation_type="expansion",
                    action=None,
                    counterexample=None,
                    description=(
                        f"Child '{child_id}' has no effective constraints and therefore "
                        f"admits all valuations, including those forbidden by parent '{parent_id}'."
                    )
                )]
            return []
        
        if parent_formula is None:
            return []
        
        # 1. Check child internal consistency
        inconsistency = self._check_internal_consistency(child_formula, child_domains, child_id)
        if inconsistency:
            self._stats['violations_found'] += 1
            violations.append(inconsistency)
            return violations
        
        # 2. Check expansion violation
        expansion = self._check_expansion_violation(
            parent_formula, child_formula, 
            parent_domains + child_domains,
            parent_id, child_id
        )
        if expansion:
            self._stats['violations_found'] += 1
            violations.append(expansion)
        
        # 3. Check redundancy (only if no expansion)
        if not violations:
            redundancy = self._check_redundancy(
                parent_formula, child_formula,
                parent_domains + child_domains,
                parent_id, child_id
            )
            if redundancy:
                self._stats['warnings_found'] += 1
                violations.append(redundancy)
        
        return violations
    
    def check_inheritance_per_action(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """
        Check inheritance for each action separately.
        
        Formal:
            ∀ action a: ⟦child⟧ₐ ⇒ ⟦parent⟧ₐ
        
        Violation:
            ∃ action a: SAT(⟦child⟧ₐ ∧ ¬⟦parent⟧ₐ)
        """
        violations = []
        
        parent_id = self._get_policy_id(parent_policy)
        child_id = self._get_policy_id(child_policy)
        
        self._debug(f"Checking per-action inheritance: {child_id} → {parent_id}")
        
        # Get all actions from both policies
        parent_actions = self._get_actions(parent_policy)
        child_actions = self._get_actions(child_policy)
        all_actions = parent_actions | child_actions
        
        self._debug(f"Actions", {
            'parent': list(parent_actions),
            'child': list(child_actions),
            'all': list(all_actions)
        })
        
        for action in all_actions:
            self._stats['actions_checked'] += 1
            self._debug(f"Checking action: {action}")
            
            # Case 1: Child has action not in parent → expansion
            if action in child_actions and action not in parent_actions:
                self._stats['violations_found'] += 1
                violations.append(InheritanceViolation(
                    parent_id=parent_id,
                    child_id=child_id,
                    violation_type="new_action",
                    action=str(action),
                    counterexample=None,
                    description=(
                        f"Child permits action '{action}' which is not permitted by parent. "
                        f"This is an expansion violation."
                    )
                ))
                continue
            
            # Case 2: Parent has action, child doesn't → valid (child restricts)
            if action in parent_actions and action not in child_actions:
                self._debug(f"  Action '{action}' in parent only - valid restriction")
                continue
            
            # Case 3: Both have action → check constraint inheritance
            parent_formula, parent_domains = self._encode_policy_for_action(
                parent_policy, action, "parent"
            )
            child_formula, child_domains = self._encode_policy_for_action(
                child_policy, action, "child"
            )
            
            self._debug(f"  Formulas for action '{action}'", {
                'parent': str(parent_formula)[:50] if parent_formula else None,
                'child': str(child_formula)[:50] if child_formula else None,
            })
            
            # Check per-action consistency FIRST
            if child_formula is not None:
                inconsistency = self._check_internal_consistency(
                    child_formula, child_domains, child_id, action=str(action)
                )
                if inconsistency:
                    self._stats['violations_found'] += 1
                    violations.append(inconsistency)
                    continue
            
            # Check expansion for this action
            if child_formula is not None and parent_formula is not None:
                expansion = self._check_expansion_violation(
                    parent_formula, child_formula,
                    parent_domains + child_domains,
                    parent_id, child_id,
                    action=str(action)
                )
                if expansion:
                    self._stats['violations_found'] += 1
                    violations.append(expansion)
            elif child_formula is not None and parent_formula is None:
                # Child has constraints for action, parent doesn't
                # Parent allows everything, child restricting is valid
                self._debug(f"  Valid: child restricts unconstrained parent action")
            elif child_formula is None and parent_formula is not None:
                # Child has no constraints for action parent constrains = expansion
                self._stats['violations_found'] += 1
                violations.append(InheritanceViolation(
                    parent_id=parent_id,
                    child_id=child_id,
                    violation_type="expansion",
                    action=str(action),
                    counterexample=None,
                    description=(
                        f"Child has no constraints for action '{action}' while parent does. "
                        f"This allows valuations forbidden by parent."
                    )
                ))
        
        return violations
    
    # ... keep all existing helper methods (_get_actions, _encode_policy_for_action, etc.) ...
    # ... just add self._debug() calls and self._stats tracking ...
    
    def _check_internal_consistency(self, formula, domains, policy_id: str, 
                                    action: str = None) -> Optional[InheritanceViolation]:
        """Check if policy constraints are satisfiable"""
        self._stats['total_checks'] += 1
        self._debug(f"Checking internal consistency")
        
        solver = Solver()
        solver.add(formula)
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if result == sat:
            self._stats['sat_results'] += 1
        else:
            self._stats['unsat_results'] += 1
        
        self._debug(f"  Consistency result: {result}")
        
        if result != sat:
            desc = f"Child policy '{policy_id}' has unsatisfiable constraints"
            if action:
                desc += f" for action '{action}'"
            return InheritanceViolation(
                parent_id="",
                child_id=policy_id,
                violation_type="inconsistent",
                action=action,
                counterexample=None,
                description=desc
            )
        
        return None
    
    def _check_expansion_violation(self, parent_formula, child_formula, 
                                   domains, parent_id: str, child_id: str,
                                   action: str = None) -> Optional[InheritanceViolation]:
        """Check: SAT(child ∧ ¬parent)"""
        self._stats['total_checks'] += 1
        self._debug(f"Checking expansion: SAT(child ∧ ¬parent)")
        
        solver = Solver()
        solver.add(child_formula)
        solver.add(Not(parent_formula))
        
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if result == sat:
            self._stats['sat_results'] += 1
        else:
            self._stats['unsat_results'] += 1
        
        self._debug(f"  Expansion result: {result}")
        
        if result == sat:
            model = solver.model()
            counterexample = self._extract_counterexample(model)
            
            desc = f"Child '{child_id}' allows valuations forbidden by parent '{parent_id}'"
            if action:
                desc = f"For action '{action}': " + desc
            desc += f". Counterexample: {counterexample}"
            
            return InheritanceViolation(
                parent_id=parent_id,
                child_id=child_id,
                violation_type="expansion",
                action=action,
                counterexample=counterexample,
                description=desc
            )
        
        return None
    
    def _check_redundancy(self, parent_formula, child_formula,
                         domains, parent_id: str, child_id: str,
                         action: str = None) -> Optional[InheritanceViolation]:
        """Check: UNSAT(parent ∧ ¬child)"""
        self._stats['total_checks'] += 1
        self._debug(f"Checking redundancy: UNSAT(parent ∧ ¬child)")
        
        solver = Solver()
        solver.add(parent_formula)
        solver.add(Not(child_formula))
        
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if result == sat:
            self._stats['sat_results'] += 1
        else:
            self._stats['unsat_results'] += 1
        
        self._debug(f"  Redundancy result: {result}")
        
        if result != sat:
            desc = f"Child '{child_id}' adds no restriction beyond parent '{parent_id}'"
            if action:
                desc = f"For action '{action}': " + desc
            
            return InheritanceViolation(
                parent_id=parent_id,
                child_id=child_id,
                violation_type="redundant",
                action=action,
                counterexample=None,
                description=desc
            )
        
        return None
    
    # ... keep _get_actions, _encode_policy_for_action, _get_policy_id, 
    #     _encode_policy, _extract_counterexample as-is ...
    
    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """Get inheritance check statistics"""
        return self._stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            'total_checks': 0,
            'actions_checked': 0,
            'sat_results': 0,
            'unsat_results': 0,
            'violations_found': 0,
            'warnings_found': 0,
        }
    
    def print_inheritance_report(self, violations: List[InheritanceViolation]):
        """Print inheritance analysis report with violations and warnings separated"""
        
        print("\n" + "="*70)
        print("📋 INHERITANCE ANALYSIS REPORT")
        print("="*70)
        
        if not violations:
            print("\n Valid inheritance - child properly restricts parent")
            print("="*70)
            return
        
        # Separate violations from warnings
        hard_violations = [v for v in violations if v.violation_type in 
                        ('expansion', 'inconsistent', 'new_action')]
        warnings = [v for v in violations if v.violation_type in 
                    ('redundant',)]
        
        # Report hard violations
        if hard_violations:
            print(f"\nFound {len(hard_violations)} inheritance VIOLATION(s):\n")
            for i, v in enumerate(hard_violations, 1):
                self._print_violation(i, v)
        
        # Report warnings
        if warnings:
            print(f"\n⚠️  Found {len(warnings)} WARNING(s):\n")
            for i, v in enumerate(warnings, 1):
                self._print_violation(i, v)
        
        # Statistics (if debug)
        if self.debug:
            print("\n📈 Statistics:")
            for key, value in self._stats.items():
                print(f"   {key}: {value}")
        
        # Summary
        print("\n" + "="*70)
        if hard_violations:
            print("INHERITANCE INVALID - violations must be resolved")
        else:
            print(" INHERITANCE VALID (with warnings)")
        print("="*70)
    
    def _print_violation(self, index: int, v: InheritanceViolation):
        """Print a single violation/warning"""
        print(f"{'─'*60}")
        action_str = f" [Action: {v.action}]" if v.action else ""
        print(f"#{index}: {v.violation_type.upper()}{action_str}")
        print(f"{'─'*60}")
        print(f"  {v.description}")
        
        if v.counterexample:
            print(f"\n  Counterexample:")
            for var, val in v.counterexample.items():
                print(f"    • {var} = {val}")