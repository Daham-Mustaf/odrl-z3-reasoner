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

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from z3 import Solver, Not, And, Or, sat, unsat, BoolVal


@dataclass
class InheritanceViolation:
    """Represents an inheritance violation"""
    parent_id: str
    child_id: str
    violation_type: str  # 'expansion', 'inconsistent', 'redundant', 'new_action'
    action: Optional[str]  # The action this violation applies to
    counterexample: Optional[Dict[str, Any]]
    description: str


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
    
    def check_inheritance(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """
        Check if child policy validly inherits from parent.
        
        This method checks inheritance across ALL constraints combined.
        For per-action checking, use check_inheritance_per_action().
        """
        violations = []
        
        parent_id = self._get_policy_id(parent_policy)
        child_id = self._get_policy_id(child_policy)
        
        if self.debug:
            print(f"\n{'='*60}")
            print(f"Checking inheritance: {child_id} → {parent_id}")
            print(f"{'='*60}")
        
        # Encode both policies
        parent_formula, parent_domains = self._encode_policy(parent_policy, "parent")
        child_formula, child_domains = self._encode_policy(child_policy, "child")
        
        if self.debug:
            print(f"\nParent formula: {parent_formula}")
            print(f"Child formula: {child_formula}")
        
        # Handle None cases
        if child_formula is None:
            if parent_formula is not None:
                # Child has no constraints = allows everything = EXPANSION
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
            violations.append(inconsistency)
            return violations
        
        # 2. Check expansion violation
        expansion = self._check_expansion_violation(
            parent_formula, child_formula, 
            parent_domains + child_domains,
            parent_id, child_id
        )
        if expansion:
            violations.append(expansion)
        
        # 3. Check redundancy (only if no expansion)
        if not violations:
            redundancy = self._check_redundancy(
                parent_formula, child_formula,
                parent_domains + child_domains,
                parent_id, child_id
            )
            if redundancy:
                violations.append(redundancy)
        
        return violations
    
    def check_inheritance_per_action(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """
        Check inheritance for each action separately.
        
        Formal:
            ∀ action a: ⟦child⟧ₐ ⇒ ⟦parent⟧ₐ
        
        Violation:
            ∃ action a: SAT(⟦child⟧ₐ ∧ ¬⟦parent⟧ₐ)
        
        This ensures sound reasoning by treating actions as symbolic labels
        that partition the constraint space.
        """
        violations = []
        
        parent_id = self._get_policy_id(parent_policy)
        child_id = self._get_policy_id(child_policy)
        
        if self.debug:
            print(f"\n{'='*60}")
            print(f"Checking per-action inheritance: {child_id} → {parent_id}")
            print(f"{'='*60}")
        
        # Get all actions from both policies
        parent_actions = self._get_actions(parent_policy)
        child_actions = self._get_actions(child_policy)
        all_actions = parent_actions | child_actions
        
        if self.debug:
            print(f"Parent actions: {parent_actions}")
            print(f"Child actions: {child_actions}")
            print(f"All actions: {all_actions}")
        
        for action in all_actions:
            if self.debug:
                print(f"\n--- Checking action: {action} ---")
            
            # Case 1: Child has action not in parent → expansion
            if action in child_actions and action not in parent_actions:
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
                if self.debug:
                    print(f"  Action '{action}' in parent only - valid restriction")
                continue
            
            # Case 3: Both have action → check constraint inheritance
            parent_formula, parent_domains = self._encode_policy_for_action(
                parent_policy, action, "parent"
            )
            child_formula, child_domains = self._encode_policy_for_action(
                child_policy, action, "child"
            )

            # Check per-action consistency FIRST
            if child_formula is not None:
                inconsistency = self._check_internal_consistency(
                    child_formula, child_domains, child_id, action=str(action)
                )
                if inconsistency:
                    violations.append(inconsistency)
                    continue  # Skip further checks for this action

            # Check expansion for this action
            if child_formula is not None and parent_formula is not None:
                expansion = self._check_expansion_violation(
                    parent_formula, child_formula,
                    parent_domains + child_domains,
                    parent_id, child_id,
                    action=str(action)
                )
                if expansion:
                    violations.append(expansion)
            elif child_formula is not None and parent_formula is None:
                # Child has constraints for action, parent doesn't
                # This means parent allows everything for this action
                # Child restricting is valid
                pass
            elif child_formula is None and parent_formula is not None:
                # Child has no constraints for action parent constrains
                # This is expansion!
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
    
    def _get_actions(self, policy) -> Set[str]:
        """Extract all actions from a policy"""
        actions = set()
        for rule in policy.rules:
            action = getattr(rule, 'action', None)
            if action:
                actions.add(str(action))
        return actions
    
    def _encode_policy_for_action(self, policy, action: str, label: str):
        """Encode only the constraints for a specific action"""
        
        self.encoder.reset()
        self.encoder.constraints = policy.constraints
        
        formulas = []
        
        for rule in policy.rules:
            rule_action = getattr(rule, 'action', None)
            if rule_action and str(rule_action) == str(action):
                constraint_id = getattr(rule, 'constraint_id', None)
                
                if self.debug:
                    print(f"  [{label}] Rule for action {action}, constraint: {constraint_id}")
                
                if constraint_id and constraint_id in policy.constraints:
                    try:
                        formula = self.encoder.encode_constraint(constraint_id)
                        if formula is not None:
                            formulas.append(formula)
                    except Exception as e:
                        if self.debug:
                            print(f"    Warning: Could not encode {constraint_id}: {e}")
        
        domains = list(self.encoder.domain_constraints)
        
        if not formulas:
            return None, domains
        
        combined = And(formulas) if len(formulas) > 1 else formulas[0]
        return combined, domains
    
    def _get_policy_id(self, policy) -> str:
        """Safely get policy ID"""
        for attr in ['id', 'uri', 'policy_id']:
            if hasattr(policy, attr):
                val = getattr(policy, attr)
                if val:
                    return str(val)
        return "unknown"
    
    def _encode_policy(self, policy, label: str):
        """Encode policy to Z3 formula (all rules combined)"""
        
        self.encoder.reset()
        self.encoder.constraints = policy.constraints
        
        formulas = []
        
        for rule in policy.rules:
            constraint_id = getattr(rule, 'constraint_id', None)
            
            if self.debug:
                print(f"\n[{label}] Rule constraint_id: {constraint_id}")
            
            if constraint_id and constraint_id in policy.constraints:
                try:
                    formula = self.encoder.encode_constraint(constraint_id)
                    if formula is not None:
                        formulas.append(formula)
                        if self.debug:
                            print(f"    Encoded: {formula}")
                except Exception as e:
                    if self.debug:
                        print(f"    Warning: Could not encode {constraint_id}: {e}")
        
        domains = list(self.encoder.domain_constraints)
        
        if not formulas:
            if self.debug:
                print(f"[{label}] No formulas encoded!")
            return None, domains
        
        combined = And(formulas) if len(formulas) > 1 else formulas[0]
        return combined, domains
    
    def _check_internal_consistency(self, formula, domains, policy_id: str, 
                                    action: str = None) -> Optional[InheritanceViolation]:
        """Check if policy constraints are satisfiable"""
        
        if self.debug:
            print(f"\n[1] Checking internal consistency")
        
        solver = Solver()
        solver.add(formula)
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if self.debug:
            print(f"    Result: {result}")
        
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
        
        if self.debug:
            print(f"\n[2] Checking expansion: SAT(child ∧ ¬parent)")
        
        solver = Solver()
        solver.add(child_formula)
        solver.add(Not(parent_formula))
        
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if self.debug:
            print(f"    Result: {result}")
        
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
        
        if self.debug:
            print(f"\n[3] Checking redundancy: UNSAT(parent ∧ ¬child)")
        
        solver = Solver()
        solver.add(parent_formula)
        solver.add(Not(child_formula))
        
        for dc in domains:
            solver.add(dc)
        
        result = solver.check()
        
        if self.debug:
            print(f"    Result: {result}")
        
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
    
    def _extract_counterexample(self, model) -> Dict[str, Any]:
        """Extract variable assignments from Z3 model"""
        result = {}
        for decl in model.decls():
            name = decl.name()
            if not name.startswith('_'):
                value = model[decl]
                if hasattr(value, 'as_long'):
                    result[name] = value.as_long()
                else:
                    result[name] = str(value)
        return result
    
    def print_inheritance_report(self, violations: List[InheritanceViolation]):
        """Print inheritance analysis report with violations and warnings separated"""
        
        print("\n" + "="*70)
        print("📋 INHERITANCE ANALYSIS REPORT")
        print("="*70)
        
        if not violations:
            print("\nOur Valid inheritance - child properly restricts parent")
            print("="*70)
            return
        
        # Separate violations from warnings
        hard_violations = [v for v in violations if v.violation_type in 
                        ('expansion', 'inconsistent', 'new_action')]
        warnings = [v for v in violations if v.violation_type in 
                    ('redundant',)]
        
        # Report hard violations
        if hard_violations:
            print(f"\n❌ Found {len(hard_violations)} inheritance VIOLATION(s):\n")
            for i, v in enumerate(hard_violations, 1):
                self._print_violation(i, v)
        
        # Report warnings
        if warnings:
            print(f"\n⚠️  Found {len(warnings)} WARNING(s):\n")
            for i, v in enumerate(warnings, 1):
                self._print_violation(i, v)
        
        # Summary
        print("\n" + "="*70)
        if hard_violations:
            print("❌ INHERITANCE INVALID - violations must be resolved")
        else:
            print("Our INHERITANCE VALID (with warnings)")
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