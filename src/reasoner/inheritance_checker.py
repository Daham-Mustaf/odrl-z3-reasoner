# src/reasoner/inheritance_checker.py
"""
Monotonic Constraint Inheritance Checker (ODRL Spec Compliant)

ODRL CUMULATIVE SEMANTICS:
- Child INHERITS all rules from parent
- Effective child = parent rules AND child's own rules
- Adding constraints can only RESTRICT, never EXPAND

Formal Model:
- Parent policy P has constraints [[P]]
- Child policy C has own constraints [[C_own]]
- Effective child: [[C_eff]] = [[P]] AND [[C_own]]
- Valid inheritance: [[C_eff]] => [[P]] (always true by construction!)
- Violation: [[P]] AND [[C_own]] is UNSAT (contradiction)

Violation Types:
- inconsistent: Child contradicts parent (combined is UNSAT)
- redundant: Child adds no restriction beyond parent (WARNING)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from z3 import Solver, Not, And, Or, sat, unsat, BoolVal, is_int, is_real, is_string
import logging

logger = logging.getLogger(__name__)


def debug_print(category: str, message: str, data: Any = None):
    """Debug print helper."""
    print(f"[{category}] {message}")
    if data:
        print(f"         {data}")


@dataclass
class InheritanceViolation:
    """Represents an inheritance violation"""
    parent_id: str
    child_id: str
    violation_type: str  # 'inconsistent', 'redundant', 'new_action'
    action: Optional[str]
    counterexample: Optional[Dict[str, Any]]
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class InheritanceChecker:
    """
    Check monotonic constraint inheritance between policies.
    
    ODRL Cumulative Semantics:
    - Effective child = parent constraints AND child's own constraints
    - Under this model, EXPANSION IS IMPOSSIBLE
    - Only violation is when child contradicts parent (inconsistent)
    """
    
    def __init__(self, encoder, debug: bool = False):
        self.encoder = encoder
        self.debug = debug
        self._stats = {
            'total_checks': 0,
            'actions_checked': 0,
            'sat_results': 0,
            'unsat_results': 0,
            'violations_found': 0,
            'warnings_found': 0,
        }
    
    def _debug(self, message: str, data: Any = None):
        if self.debug:
            debug_print("INHERITANCE", message, data)
            logger.debug(f"[INHERITANCE] {message}")
    
    # =========================================================================
    # MAIN CHECK METHODS
    # =========================================================================
    
    def check_inheritance(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """
        Check if child policy validly inherits from parent.
        
        ODRL CUMULATIVE SEMANTICS:
        - Effective child = parent AND child_own
        - Expansion is IMPOSSIBLE (cumulative only restricts)
        - Check for: inconsistency (contradiction) and redundancy
        """
        violations = []
        
        parent_id = self._get_policy_id(parent_policy)
        child_id = self._get_policy_id(child_policy)
        
        self._debug(f"Checking ODRL inheritance: {child_id} -> {parent_id}")
        self._debug("Using cumulative semantics: effective_child = parent AND child_own")
        
        # Encode both policies in the SAME encoder context (share variables)
        self.encoder.reset()
        
        # Encode parent constraints
        parent_formula = None
        if hasattr(parent_policy, 'constraints') and parent_policy.constraints:
            parent_result = self.encoder.encode_policy(parent_policy.constraints)
            parent_formulas = parent_result.formulas if hasattr(parent_result, 'formulas') else parent_result
            if parent_formulas:
                parent_formula = And(list(parent_formulas.values())) if len(parent_formulas) > 1 else list(parent_formulas.values())[0]
        
        # Encode child's OWN constraints (same encoder = shared variables)
        child_own_formula = None
        if hasattr(child_policy, 'constraints') and child_policy.constraints:
            child_result = self.encoder.encode_policy(child_policy.constraints)
            child_formulas = child_result.formulas if hasattr(child_result, 'formulas') else child_result
            if child_formulas:
                child_own_formula = And(list(child_formulas.values())) if len(child_formulas) > 1 else list(child_formulas.values())[0]
        
        # Get domain constraints
        domains = list(self.encoder.get_domain_constraints())
        
        self._debug(f"Parent formula: {parent_formula}")
        self._debug(f"Child own formula: {child_own_formula}")
        
        # =================================================================
        # ODRL CUMULATIVE SEMANTICS LOGIC
        # =================================================================
        
        # Case 1: Child has no constraints of its own
        if child_own_formula is None:
            # Effective child = parent (just inherits)
            self._debug("Child has no own constraints - valid pure inheritance")
            return []
        
        # Case 2: Parent has no constraints
        if parent_formula is None:
            # Effective child = child_own
            self._debug("Parent has no constraints - valid (child adds restrictions)")
            return []
        
        # Case 3: Both have constraints
        # Effective child = parent AND child_own
        effective_child = And(parent_formula, child_own_formula)
        
        # Check 1: Is effective child consistent?
        # If UNSAT(parent AND child_own), child contradicts parent
        inconsistency = self._check_combined_consistency(
            effective_child, domains, parent_id, child_id
        )
        if inconsistency:
            self._stats['violations_found'] += 1
            violations.append(inconsistency)
            return violations
        
        # Check 2: Redundancy - does child_own add any restriction?
        # If parent => child_own, then child_own is implied by parent (redundant)
        redundancy = self._check_redundancy(
            parent_formula, child_own_formula,
            domains,
            parent_id, child_id
        )
        if redundancy:
            self._stats['warnings_found'] += 1
            violations.append(redundancy)
        
        return violations
    
    def check_inheritance_per_action(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """Check inheritance for each action separately."""
        violations = []
        
        parent_id = self._get_policy_id(parent_policy)
        child_id = self._get_policy_id(child_policy)
        
        self._debug(f"Checking per-action inheritance: {child_id} -> {parent_id}")
        
        parent_actions = self._get_actions(parent_policy)
        child_actions = self._get_actions(child_policy)
        all_actions = parent_actions | child_actions
        
        self._debug(f"Actions: parent={parent_actions}, child={child_actions}")
        
        for action in all_actions:
            self._stats['actions_checked'] += 1
            
            # New action check (child adds action not in parent)
            if action in child_actions and action not in parent_actions:
                self._stats['violations_found'] += 1
                violations.append(InheritanceViolation(
                    parent_id=parent_id,
                    child_id=child_id,
                    violation_type="new_action",
                    action=str(action),
                    counterexample=None,
                    description=f"Child permits action '{action}' not in parent"
                ))
                continue
            
            if action not in child_actions:
                continue
            
            # Encode per action
            parent_formula, parent_domains = self._encode_policy_for_action(
                parent_policy, action, "parent"
            )
            child_formula, child_domains = self._encode_policy_for_action(
                child_policy, action, "child"
            )
            
            if parent_formula is None or child_formula is None:
                continue
            
            all_domains = parent_domains + child_domains
            
            # Check combined consistency
            effective_child = And(parent_formula, child_formula)
            inconsistency = self._check_combined_consistency(
                effective_child, all_domains, parent_id, child_id, action
            )
            if inconsistency:
                self._stats['violations_found'] += 1
                violations.append(inconsistency)
        
        return violations
    
    # =========================================================================
    # CHECK METHODS
    # =========================================================================
    
    def _check_combined_consistency(self, effective_formula, domains, 
                                   parent_id: str, child_id: str,
                                   action: str = None) -> Optional[InheritanceViolation]:
        """
        Check if combined (parent AND child_own) is satisfiable.
        
        If UNSAT, child contradicts parent.
        """
        self._stats['total_checks'] += 1
        
        solver = Solver()
        solver.add(effective_formula)
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if result == unsat:
            self._stats['unsat_results'] += 1
            desc = f"Child '{child_id}' constraints contradict parent '{parent_id}' (combined is unsatisfiable)"
            if action:
                desc = f"Action '{action}': " + desc
            
            return InheritanceViolation(
                parent_id=parent_id,
                child_id=child_id,
                violation_type="inconsistent",
                action=action,
                counterexample=None,
                description=desc
            )
        
        self._stats['sat_results'] += 1
        return None
    
    def _check_redundancy(self, parent_formula, child_formula,
                         domains, parent_id: str, child_id: str,
                         action: str = None) -> Optional[InheritanceViolation]:
        """
        Check if child is redundant (parent already implies child).
        
        Redundant: UNSAT(parent AND NOT child) - parent implies child
        This means child's constraint doesn't add any new restriction.
        
        Note: True equivalence (child = parent) is also redundant.
        """
        self._stats['total_checks'] += 1
        
        # Check if parent => child (parent implies child's constraint)
        solver = Solver()
        solver.add(parent_formula)
        solver.add(Not(child_formula))
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if result == unsat:
            # parent => child, so child adds no restriction
            self._stats['unsat_results'] += 1
            desc = f"Child '{child_id}' constraint is implied by parent '{parent_id}' (adds no restriction)"
            if action:
                desc = f"Action '{action}': " + desc
            
            return InheritanceViolation(
                parent_id=parent_id,
                child_id=child_id,
                violation_type="redundant",
                action=action,
                counterexample=None,
                description=desc
            )
        
        self._stats['sat_results'] += 1
        return None
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_policy_id(self, policy) -> str:
        """Extract policy ID from policy object or dict."""
        if hasattr(policy, 'uid'):
            return str(policy.uid)
        if hasattr(policy, 'id'):
            return str(policy.id)
        if isinstance(policy, dict):
            return policy.get('id', policy.get('@id', 'unknown'))
        return str(policy)
    
    def _get_actions(self, policy) -> Set[str]:
        """Get all actions from policy rules."""
        actions = set()
        if hasattr(policy, 'rules'):
            for rule in policy.rules:
                if hasattr(rule, 'action') and rule.action:
                    actions.add(str(rule.action))
        return actions
    
    def _get_top_level_constraint_ids(self, policy) -> Set[str]:
        """Get constraint IDs that are directly attached to rules."""
        top_level = set()
        if hasattr(policy, 'rules'):
            for rule in policy.rules:
                if hasattr(rule, 'constraint_ids') and rule.constraint_ids:
                    top_level.update(rule.constraint_ids)
                elif hasattr(rule, 'constraint_id') and rule.constraint_id:
                    top_level.add(rule.constraint_id)
        return top_level
    
    def _encode_policy(self, policy, prefix: str) -> Tuple[Any, List]:
        """Encode all policy constraints."""
        self.encoder.reset()
        
        if hasattr(policy, 'constraints') and policy.constraints:
            result = self.encoder.encode_policy(policy.constraints)
            
            if hasattr(result, 'formulas'):
                formulas = result.formulas
            else:
                formulas = result
            
            if not formulas:
                return None, []
            
            combined = And(list(formulas.values())) if len(formulas) > 1 else list(formulas.values())[0]
            domains = list(self.encoder.get_domain_constraints())
            return combined, domains
        
        return None, []
    
    def _encode_policy_for_action(self, policy, action: str, prefix: str) -> Tuple[Any, List]:
        """Encode constraints for a specific action."""
        self.encoder.reset()
        
        if not hasattr(policy, 'rules') or not hasattr(policy, 'constraints'):
            return None, []
        
        action_constraint_ids = set()
        for rule in policy.rules:
            if hasattr(rule, 'action') and str(rule.action) == str(action):
                if hasattr(rule, 'constraint_ids') and rule.constraint_ids:
                    action_constraint_ids.update(rule.constraint_ids)
                elif hasattr(rule, 'constraint_id') and rule.constraint_id:
                    action_constraint_ids.add(rule.constraint_id)
        
        if not action_constraint_ids:
            return None, []
        
        relevant_constraints = {
            cid: c for cid, c in policy.constraints.items()
            if cid in action_constraint_ids or self._is_child_of(cid, action_constraint_ids, policy.constraints)
        }
        
        if not relevant_constraints:
            return None, []
        
        result = self.encoder.encode_policy(relevant_constraints)
        
        if hasattr(result, 'formulas'):
            formulas = result.formulas
        else:
            formulas = result
        
        if not formulas:
            return None, []
        
        top_level = [formulas[cid] for cid in action_constraint_ids if cid in formulas]
        if not top_level:
            return None, []
        
        combined = And(top_level) if len(top_level) > 1 else top_level[0]
        domains = list(self.encoder.get_domain_constraints())
        return combined, domains
    
    def _is_child_of(self, constraint_id: str, parent_ids: Set[str], 
                     constraints: Dict) -> bool:
        """Check if constraint is a child of any parent constraint."""
        for pid in parent_ids:
            if pid in constraints:
                parent = constraints[pid]
                # Check for operands (new CompositeConstraint) or children (old)
                children = getattr(parent, 'operands', None) or getattr(parent, 'children', None)
                if children:
                    if constraint_id in children:
                        return True
                    for child_id in children:
                        if self._is_child_of(constraint_id, {child_id}, constraints):
                            return True
        return False
    
    def _extract_counterexample(self, model) -> Dict[str, Any]:
        """Extract counterexample from Z3 model."""
        counterexample = {}
        for decl in model.decls():
            name = str(decl.name())
            val = model[decl]
            
            if is_int(val):
                counterexample[name] = val.as_long()
            elif is_real(val):
                counterexample[name] = float(val.as_decimal(10))
            elif is_string(val):
                counterexample[name] = str(val)
            else:
                counterexample[name] = str(val)
        
        return counterexample
    
    # =========================================================================
    # STATS AND SUMMARY
    # =========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """Get checker statistics."""
        return self._stats.copy()
    
    def print_summary(self):
        """Print check summary."""
        if not self.debug:
            return
        
        print("\n" + "=" * 70)
        print("INHERITANCE CHECK SUMMARY (ODRL Cumulative)")
        print("=" * 70)
        print(f"  Total checks: {self._stats['total_checks']}")
        print(f"  Actions checked: {self._stats['actions_checked']}")
        print(f"  SAT results: {self._stats['sat_results']}")
        print(f"  UNSAT results: {self._stats['unsat_results']}")
        print(f"  Violations: {self._stats['violations_found']}")
        print(f"  Warnings: {self._stats['warnings_found']}")
        print("=" * 70 + "\n")