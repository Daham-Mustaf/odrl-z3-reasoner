"""
Monotonic Constraint Inheritance Checker

Formal Model:
- Parent policy P₀ defines constraints ⟦P₀⟧
- Child policy P₁ defines constraints ⟦P₁⟧  
- Valid inheritance: ⟦P₁⟧ ⇒ ⟦P₀⟧
- Violation: SAT(⟦P₁⟧ ∧ ¬⟦P₀⟧)

Assumption:
All rule constraints within a policy are conjunctively combined.
Disjunctive semantics must be expressed explicitly via OR/XONE constraints.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from z3 import Solver, Not, And, Or, sat, unsat, BoolVal

@dataclass
class InheritanceViolation:
    """Represents an inheritance violation"""
    parent_id: str
    child_id: str
    violation_type: str  # 'expansion', 'inconsistent', 'redundant', 'choice_collapse'
    counterexample: Optional[Dict[str, Any]]
    description: str

class InheritanceChecker:
    """
    Check monotonic constraint inheritance between policies.
    
    Formal semantics:
    - Valid inheritance: ∀v: child(v) → parent(v)
    - Expansion violation: SAT(child ∧ ¬parent)
    - Internal inconsistency: UNSAT(child)
    - Redundancy: UNSAT(parent ∧ ¬child) - child adds no restriction
    """
    
    def __init__(self, encoder, debug: bool = False):
        self.encoder = encoder
        self.debug = debug
    
    def check_inheritance(self, parent_policy, child_policy) -> List[InheritanceViolation]:
        """Check if child policy validly inherits from parent."""
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
        
        # Handle None cases - CORRECTED LOGIC
        if child_formula is None:
            if parent_formula is not None:
                # Child has no constraints = child is ⊤ (allows everything)
                # This is EXPANSION, not redundancy!
                # SAT(child ∧ ¬parent) = SAT(⊤ ∧ ¬parent) = SAT(¬parent)
                return [InheritanceViolation(
                    parent_id=parent_id,
                    child_id=child_id,
                    violation_type="expansion",
                    counterexample=None,
                    description=(
                        f"Child '{child_id}' has no effective constraints and therefore "
                        f"admits all valuations, including those forbidden by parent '{parent_id}'."
                    )
                )]
            # Both None - trivially valid
            return []
        
        if parent_formula is None:
            # Parent has no constraints, child has some - always valid (child restricts)
            return []
        
        # 1. Check child internal consistency
        inconsistency = self._check_internal_consistency(child_formula, child_domains, child_id)
        if inconsistency:
            violations.append(inconsistency)
            return violations
        
        # 2. Check expansion violation: SAT(child ∧ ¬parent)
        expansion = self._check_expansion_violation(
            parent_formula, child_formula, 
            parent_domains + child_domains,
            parent_id, child_id
        )
        if expansion:
            violations.append(expansion)
        
        # 3. Check redundancy (only if no expansion): UNSAT(parent ∧ ¬child)
        if not violations:
            redundancy = self._check_redundancy(
                parent_formula, child_formula,
                parent_domains + child_domains,
                parent_id, child_id
            )
            if redundancy:
                violations.append(redundancy)
        
        return violations
    
    def _get_policy_id(self, policy) -> str:
        """Safely get policy ID"""
        for attr in ['id', 'uri', 'policy_id']:
            if hasattr(policy, attr):
                val = getattr(policy, attr)
                if val:
                    return str(val)
        return "unknown"
    
    def _encode_policy(self, policy, label: str):
        """
        Encode policy to Z3 formula.
        
        Assumption: All rule constraints are conjunctively combined.
        """
        
        # Reset encoder and set constraints
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
    
    def _check_internal_consistency(self, formula, domains, policy_id: str) -> Optional[InheritanceViolation]:
        """
        Check if policy constraints are satisfiable.
        
        UNSAT(child) → inconsistent child (hard error)
        """
        
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
            return InheritanceViolation(
                parent_id="",
                child_id=policy_id,
                violation_type="inconsistent",
                counterexample=None,
                description=f"Child policy '{policy_id}' has unsatisfiable constraints"
            )
        
        return None
    
    def _check_expansion_violation(self, parent_formula, child_formula, 
                                   domains, parent_id: str, child_id: str) -> Optional[InheritanceViolation]:
        """
        Check: SAT(child ∧ ¬parent)
        
        If satisfiable, child allows valuations that parent forbids.
        This is the core inheritance violation check.
        """
        
        if self.debug:
            print(f"\n[2] Checking expansion: SAT(child ∧ ¬parent)")
            print(f"    child: {child_formula}")
            print(f"    ¬parent: {Not(parent_formula)}")
        
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
            
            if self.debug:
                print(f"    Counterexample: {counterexample}")
            
            return InheritanceViolation(
                parent_id=parent_id,
                child_id=child_id,
                violation_type="expansion",
                counterexample=counterexample,
                description=(
                    f"Child '{child_id}' allows valuations forbidden by parent '{parent_id}'. "
                    f"Counterexample: {counterexample}"
                )
            )
        
        return None
    
    def _check_redundancy(self, parent_formula, child_formula,
                         domains, parent_id: str, child_id: str) -> Optional[InheritanceViolation]:
        """
        Check: UNSAT(parent ∧ ¬child)
        
        If unsatisfiable, child adds no new restriction beyond parent.
        This is a warning, not an error.
        """
        
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
            return InheritanceViolation(
                parent_id=parent_id,
                child_id=child_id,
                violation_type="redundant",
                counterexample=None,
                description=(
                    f"Child '{child_id}' adds no restriction beyond parent '{parent_id}'. "
                    f"This may indicate redundant policy definition."
                )
            )
        
        return None
    
    def _extract_counterexample(self, model) -> Dict[str, Any]:
        """Extract variable assignments from Z3 model"""
        result = {}
        for decl in model.decls():
            name = decl.name()
            # Skip internal helper variables
            if not name.startswith('_'):
                value = model[decl]
                # Normalize integers
                if hasattr(value, 'as_long'):
                    result[name] = value.as_long()
                else:
                    result[name] = str(value)
        return result
    
    def print_inheritance_report(self, violations: List[InheritanceViolation]):
        """Print inheritance analysis report"""
        
        print("\n" + "="*70)
        print("📋 INHERITANCE ANALYSIS REPORT")
        print("="*70)
        
        if not violations:
            print("\n✅ Valid inheritance - child properly restricts parent")
            print("="*70)
            return
        
        print(f"\n⚠️  Found {len(violations)} inheritance issue(s):\n")
        
        for i, v in enumerate(violations, 1):
            print(f"{'─'*60}")
            print(f"Issue #{i}: {v.violation_type.upper()}")
            print(f"{'─'*60}")
            print(f"  {v.description}")
            
            if v.counterexample:
                print(f"\n  Counterexample:")
                for var, val in v.counterexample.items():
                    print(f"    • {var} = {val}")
        
        print("\n" + "="*70)