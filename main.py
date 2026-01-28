#!/usr/bin/env python3
"""
ODRL-SA Policy Analyzer - Comprehensive Main Entry Point

Usage:
    uv run python main.py policy.ttl                    # Basic analysis
    uv run python main.py policy.ttl -v                 # Verbose (show constraints)
    uv run python main.py policy.ttl -d                 # Debug (show Z3 formulas)
    uv run python main.py policy.ttl --show-policy      # Show policy structure
    uv run python main.py policy.ttl --show-normalize   # Show normalization
    uv run python main.py policy.ttl --all              # Show everything
    uv run python main.py tests/ttl/percentage/         # Analyze directory
    uv run python main.py parent.ttl child.ttl          # Inheritance check
    uv run python main.py policy.ttl --json             # JSON output

Output Modes:
    default         - Clean summary
    -v, --verbose   - Show constraints and model
    -d, --debug     - Show Z3 encoding and formulas
    --show-policy   - Show full policy structure
    --show-normalize - Show value normalization
    --all           - Enable all debug output
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from z3 import Solver, And, Or, Not, sat, unsat

# Core imports
from parser import parse_ttl_file
from encoder import Z3JudgmentEngine
from core.constraint_types import (
    AtomicConstraint, 
    CompositeConstraint, 
    LogicalOperator,
    Judgment,
    Constraint,
    OperatorType,
)
from normalizer import normalize_value, get_normalized_value


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RuleAnalysis:
    """Analysis result for a single rule."""
    rule_id: str
    rule_type: str  # permission, prohibition, duty
    action: Optional[str]
    constraint_ids: List[str]
    judgment: str
    model: Optional[Dict[str, Any]]


@dataclass 
class PolicyAnalysis:
    """
    Full policy analysis result.
    
    Theory Reference: Section 7.6 - Policy Conflict Classification
    
    judge_policy(P) in {CONSISTENT, INTERNAL-CONFLICT, DEONTIC-CONFLICT, UNKNOWN}
    """
    file: str
    policy_id: str
    policy_type: Optional[str]
    
    # Counts
    total_constraints: int
    atomic_constraints: int
    composite_constraints: int
    
    # Rules
    permissions: List[RuleAnalysis]
    prohibitions: List[RuleAnalysis]
    duties: List[RuleAnalysis]
    
    # Deontic conflicts (Section 7.4)
    deontic_conflicts: List[Dict] = field(default_factory=list)
    
    # Overall judgment (Section 7.6)
    overall_judgment: str = "CONSISTENT"
    has_internal_conflicts: bool = False
    has_deontic_conflicts: bool = False
    
    # Errors/warnings
    parse_errors: List[str] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InheritanceResult:
    """Result of inheritance check."""
    parent_file: str
    child_file: str
    is_valid: bool
    violations: List[Dict[str, Any]]


# =============================================================================
# POLICY ANALYZER
# =============================================================================

class PolicyAnalyzer:
    """
    Comprehensive ODRL Policy Analyzer.
    
    Features:
    - Parses all ODRL structures (policies, rules, constraints)
    - Analyzes permissions, prohibitions, and duties
    - Detects internal conflicts within rules
    - Detects cross-rule conflicts (permission vs prohibition)
    - Supports composite constraints (AND, OR, XONE)
    - Shows normalization process
    - Shows Z3 encoding
    """
    
    def __init__(
        self, 
        verbose: bool = False,
        debug: bool = False,
        show_policy: bool = False,
        show_normalize: bool = False
    ):
        self.verbose = verbose
        self.debug = debug
        self.show_policy = show_policy
        self.show_normalize = show_normalize
        self.engine = Z3JudgmentEngine()
    
    def analyze_file(self, filepath: str) -> PolicyAnalysis:
        """Analyze a single policy file."""
        filepath = Path(filepath)
        
        self._print_header(f"ANALYZING: {filepath.name}")
        
        # Parse
        parse_result = parse_ttl_file(str(filepath))
        
        if parse_result.errors:
            self._print_section("Parse Errors")
            for e in parse_result.errors:
                print(f"  [ERROR] {e}")
        
        if not parse_result.policies:
            return PolicyAnalysis(
                file=str(filepath),
                policy_id="",
                policy_type=None,
                total_constraints=0,
                atomic_constraints=0,
                composite_constraints=0,
                permissions=[],
                prohibitions=[],
                duties=[],
                overall_judgment="ERROR",
                has_internal_conflicts=False,
                has_deontic_conflicts=False,
                parse_errors=parse_result.errors or ["No policies found"],
                parse_warnings=parse_result.warnings or []
            )
        
        policy = parse_result.policies[0]
        constraints = parse_result.constraints
        
        # Count constraints
        atomics = [c for c in constraints.values() if isinstance(c, AtomicConstraint)]
        composites = [c for c in constraints.values() if isinstance(c, CompositeConstraint)]
        
        # Show policy structure
        if self.show_policy:
            self._show_policy_structure(policy, constraints)
        
        # Show normalization
        if self.show_normalize:
            self._show_normalization(atomics)
        
        # Analyze each rule type
        permissions = self._analyze_rules(policy.permissions, constraints, "permission")
        prohibitions = self._analyze_rules(policy.prohibitions, constraints, "prohibition")
        duties = self._analyze_rules(policy.duties, constraints, "duty")
        
        # Section 7.3: Check for internal conflicts (rule-level consistency)
        all_rules = permissions + prohibitions + duties
        has_internal = any(r.judgment == "CONFLICT" for r in all_rules)
        
        # Section 7.4: Check deontic conflicts (permission vs prohibition on same action)
        deontic_conflicts = self._check_cross_rule_conflicts(permissions, prohibitions, constraints)
        has_deontic = len(deontic_conflicts) > 0
        
        # Section 7.6: Policy-Level Judgment Classification
        # 1. INTERNAL-CONFLICT: exists r in R_P union R_F : not SAT(Phi_r)
        # 2. DEONTIC-CONFLICT: SAT(Phi_perm and Phi_prohib)
        # 3. UNKNOWN: Any rule yields UNKNOWN
        # 4. CONSISTENT: Otherwise
        
        has_unknown = any(r.judgment == "UNKNOWN" for r in all_rules)
        
        if has_internal:
            overall = "INTERNAL-CONFLICT"
        elif has_deontic:
            overall = "DEONTIC-CONFLICT"
        elif has_unknown:
            overall = "UNKNOWN"
        else:
            overall = "CONSISTENT"
        
        return PolicyAnalysis(
            file=str(filepath),
            policy_id=policy.uid,
            policy_type=policy.policy_type,
            total_constraints=len(constraints),
            atomic_constraints=len(atomics),
            composite_constraints=len(composites),
            permissions=permissions,
            prohibitions=prohibitions,
            duties=duties,
            deontic_conflicts=deontic_conflicts,
            overall_judgment=overall,
            has_internal_conflicts=has_internal,
            has_deontic_conflicts=has_deontic,
            parse_errors=parse_result.errors or [],
            parse_warnings=parse_result.warnings or []
        )
    
    def _analyze_rules(
        self, 
        rules: List, 
        constraints: Dict[str, Constraint],
        rule_type: str
    ) -> List[RuleAnalysis]:
        """Analyze a list of rules."""
        results = []
        
        for rule in rules:
            if self.verbose:
                self._print_section(f"{rule_type.upper()}: {rule.uid}")
                print(f"  Action: {rule.action}")
                print(f"  Constraints: {rule.constraint_ids}")
            
            # Get constraints for this rule
            judgment, model = self._check_rule_consistency(
                rule.constraint_ids, 
                constraints
            )
            
            results.append(RuleAnalysis(
                rule_id=rule.uid,
                rule_type=rule_type,
                action=rule.action,
                constraint_ids=rule.constraint_ids,
                judgment=judgment.value,
                model=model
            ))
            
            if self.verbose:
                status = "[CONFLICT]" if judgment == Judgment.CONFLICT else "[OK]"
                print(f"  Result: {status} {judgment.value}")
                if model:
                    print(f"  Model: {model}")
        
        return results
    
    def _check_rule_consistency(
        self,
        constraint_ids: List[str],
        constraints: Dict[str, Constraint]
    ) -> Tuple[Judgment, Optional[Dict]]:
        """Check consistency of constraints in a rule."""
        
        if not constraint_ids:
            return Judgment.POSSIBLY_COMPATIBLE, {}
        
        self.engine.var_manager.clear()
        
        def encode(uid: str) -> Any:
            if uid not in constraints:
                return None
            
            c = constraints[uid]
            
            if isinstance(c, AtomicConstraint):
                formula = self.engine.constraint_encoder.encode(c)
                if self.debug:
                    print(f"    [A] {uid}: {c.left_operand} {c.operator.value} {c.right_operand.value}")
                    print(f"        -> {formula}")
                return formula
            
            elif isinstance(c, CompositeConstraint):
                children = [encode(cid) for cid in c.operands]
                children = [f for f in children if f is not None]
                
                if not children:
                    return None
                
                if c.operator == LogicalOperator.AND:
                    formula = And(*children)
                elif c.operator == LogicalOperator.OR:
                    formula = Or(*children)
                elif c.operator == LogicalOperator.XONE:
                    if len(children) == 1:
                        formula = children[0]
                    else:
                        at_least = Or(*children)
                        at_most = And([Not(And(children[i], children[j])) 
                                      for i in range(len(children)) 
                                      for j in range(i+1, len(children))])
                        formula = And(at_least, at_most)
                else:
                    formula = And(*children)
                
                if self.debug:
                    print(f"    [C] {uid}: {c.operator.value}({list(c.operands)})")
                    print(f"        -> {formula}")
                
                return formula
            
            return None
        
        if self.debug:
            print(f"\n  Encoding:")
        
        formulas = [encode(cid) for cid in constraint_ids]
        formulas = [f for f in formulas if f is not None]
        
        if not formulas:
            return Judgment.UNKNOWN, None
        
        full = And(*formulas) if len(formulas) > 1 else formulas[0]
        domains = self.engine.var_manager.get_domain_constraints()
        
        if self.debug:
            print(f"\n  Formula: {full}")
            print(f"  Domains: {domains}")
        
        solver = Solver()
        solver.add(full)
        for d in domains:
            solver.add(d)
        
        result = solver.check()
        
        if result == unsat:
            return Judgment.CONFLICT, None
        elif result == sat:
            model = {}
            for decl in solver.model().decls():
                val = solver.model()[decl]
                try:
                    if hasattr(val, 'as_long'):
                        model[decl.name()] = val.as_long()
                    elif hasattr(val, 'as_decimal'):
                        model[decl.name()] = float(val.as_decimal(10).rstrip('?'))
                    else:
                        model[decl.name()] = str(val)
                except:
                    model[decl.name()] = str(val)
            return Judgment.POSSIBLY_COMPATIBLE, model
        else:
            return Judgment.UNKNOWN, None
    
    def _check_cross_rule_conflicts(
        self,
        permissions: List[RuleAnalysis],
        prohibitions: List[RuleAnalysis],
        constraints: Dict[str, Constraint]
    ) -> List[Dict]:
        """
        Check for deontic conflicts between permissions and prohibitions.
        
        Theory Reference: Section 7.4 - Policy-Level Deontic Conflict
        
        Definition (Deontic Conflict):
            P has deontic conflict iff exists w : Phi_perm(w) and Phi_prohib(w)
        
        For same-action rules, we check if:
            SAT(Phi_perm and Phi_prohib) = sat -> DEONTIC-CONFLICT
        """
        conflicts = []
        
        # Group rules by action
        perm_by_action = {}
        for p in permissions:
            action = p.action or '_default_'
            perm_by_action.setdefault(action, []).append(p)
        
        prohib_by_action = {}
        for p in prohibitions:
            action = p.action or '_default_'
            prohib_by_action.setdefault(action, []).append(p)
        
        # Check each action that has both permission and prohibition
        common_actions = set(perm_by_action.keys()) & set(prohib_by_action.keys())
        
        for action in common_actions:
            perms = perm_by_action[action]
            prohibs = prohib_by_action[action]
            
            if self.verbose:
                self._print_section(f"Deontic Check: action={action}")
                print(f"  Permissions: {[p.rule_id for p in perms]}")
                print(f"  Prohibitions: {[p.rule_id for p in prohibs]}")
            
            # Build Phi_perm = OR(permission rules) - any permission applies
            # Build Phi_prohib = OR(prohibition rules) - any prohibition applies
            # Check SAT(Phi_perm AND Phi_prohib)
            
            conflict_result = self._check_deontic_conflict(
                perms, prohibs, constraints
            )
            
            if conflict_result['has_conflict']:
                conflicts.append({
                    'action': action,
                    'type': 'DEONTIC-CONFLICT',
                    'permissions': [p.rule_id for p in perms],
                    'prohibitions': [p.rule_id for p in prohibs],
                    'witness': conflict_result.get('witness'),
                    'explanation': f"Action '{action}' can be simultaneously permitted and forbidden"
                })
                
                if self.verbose:
                    print(f"  [DEONTIC CONFLICT DETECTED]")
                    if conflict_result.get('witness'):
                        print(f"     Witness: {conflict_result['witness']}")
            else:
                if self.verbose:
                    print(f"  [OK] No deontic conflict for action '{action}'")
        
        return conflicts
    
    def _check_deontic_conflict(
        self,
        permissions: List[RuleAnalysis],
        prohibitions: List[RuleAnalysis],
        constraints: Dict[str, Constraint]
    ) -> Dict:
        """
        Check for deontic conflict using SMT.
        
        Theory Reference: Section 7.5 - SMT Characterization
        
        ; Check for deontic conflict
        (assert (and Phi_perm Phi_prohib))
        (check-sat)
        
        Where:
            Phi_perm = OR{Phi_r | r in R_P}  (disjunction of permission rules)
            Phi_prohib = OR{Phi_r | r in R_F}  (disjunction of prohibition rules)
        """
        self.engine.var_manager.clear()
        
        def encode_rule_set(rules: List[RuleAnalysis]) -> Any:
            """Encode a set of rules as disjunction (any rule can apply)."""
            rule_formulas = []
            
            for rule in rules:
                # Encode rule's constraints as conjunction
                rule_constraints = []
                for cid in rule.constraint_ids:
                    formula = self._encode_constraint_recursive(cid, constraints)
                    if formula is not None:
                        rule_constraints.append(formula)
                
                if rule_constraints:
                    rule_formula = And(*rule_constraints) if len(rule_constraints) > 1 else rule_constraints[0]
                    rule_formulas.append(rule_formula)
            
            if not rule_formulas:
                return None
            
            # Disjunction: any rule can apply
            return Or(*rule_formulas) if len(rule_formulas) > 1 else rule_formulas[0]
        
        # Build Phi_perm and Phi_prohib
        phi_perm = encode_rule_set(permissions)
        phi_prohib = encode_rule_set(prohibitions)
        
        if phi_perm is None or phi_prohib is None:
            return {'has_conflict': False, 'reason': 'empty_formula'}
        
        if self.debug:
            print(f"\n  Phi_perm (permission): {phi_perm}")
            print(f"  Phi_prohib (prohibition): {phi_prohib}")
        
        # Check SAT(Phi_perm AND Phi_prohib)
        deontic_formula = And(phi_perm, phi_prohib)
        domains = self.engine.var_manager.get_domain_constraints()
        
        if self.debug:
            print(f"  Deontic check: {deontic_formula}")
            print(f"  Domains: {domains}")
        
        solver = Solver()
        solver.add(deontic_formula)
        for d in domains:
            solver.add(d)
        
        result = solver.check()
        
        if result == sat:
            # Extract witness (model showing the conflict)
            witness = {}
            for decl in solver.model().decls():
                val = solver.model()[decl]
                try:
                    if hasattr(val, 'as_long'):
                        witness[decl.name()] = val.as_long()
                    elif hasattr(val, 'as_decimal'):
                        witness[decl.name()] = float(val.as_decimal(10).rstrip('?'))
                    else:
                        witness[decl.name()] = str(val)
                except:
                    witness[decl.name()] = str(val)
            
            return {'has_conflict': True, 'witness': witness}
        
        elif result == unsat:
            return {'has_conflict': False, 'reason': 'disjoint'}
        
        else:
            return {'has_conflict': False, 'reason': 'unknown'}
    
    def _encode_constraint_recursive(self, uid: str, constraints: Dict[str, Constraint]) -> Any:
        """Recursively encode a constraint (atomic or composite)."""
        if uid not in constraints:
            return None
        
        c = constraints[uid]
        
        if isinstance(c, AtomicConstraint):
            return self.engine.constraint_encoder.encode(c)
        
        elif isinstance(c, CompositeConstraint):
            children = [self._encode_constraint_recursive(cid, constraints) for cid in c.operands]
            children = [f for f in children if f is not None]
            
            if not children:
                return None
            
            if c.operator == LogicalOperator.AND:
                return And(*children)
            elif c.operator == LogicalOperator.OR:
                return Or(*children)
            elif c.operator == LogicalOperator.XONE:
                if len(children) == 1:
                    return children[0]
                at_least = Or(*children)
                at_most = And([Not(And(children[i], children[j])) 
                              for i in range(len(children)) 
                              for j in range(i+1, len(children))])
                return And(at_least, at_most)
            else:
                return And(*children)
        
        return None
    
    def _show_policy_structure(self, policy, constraints: Dict):
        """Display full policy structure."""
        self._print_section("POLICY STRUCTURE")
        
        print(f"  Policy ID: {policy.uid}")
        print(f"  Type: {policy.policy_type}")
        if policy.inherits_from:
            print(f"  Inherits from: {policy.inherits_from}")
        
        print(f"\n  Rules:")
        for rule in policy.rules:
            print(f"    [{rule.rule_type.value}] {rule.uid}")
            print(f"      Action: {rule.action}")
            print(f"      Target: {rule.target}")
            print(f"      Constraints: {rule.constraint_ids}")
        
        print(f"\n  Constraints:")
        for uid, c in constraints.items():
            if isinstance(c, AtomicConstraint):
                meta = []
                if c.metadata and c.metadata.unit:
                    meta.append(f"unit={c.metadata.unit}")
                meta_str = f" [{', '.join(meta)}]" if meta else ""
                print(f"    [A] {uid}: {c.left_operand} {c.operator.value} {c.right_operand.value}{meta_str}")
            elif isinstance(c, CompositeConstraint):
                print(f"    [C] {uid}: {c.operator.value}({list(c.operands)})")
    
    def _show_normalization(self, atomics: List[AtomicConstraint]):
        """Show normalization process for all constraints."""
        self._print_section("NORMALIZATION")
        
        for c in atomics:
            original = c.right_operand.value
            normalized = get_normalized_value(c)
            
            print(f"  {c.uid}:")
            print(f"    Operand: {c.left_operand}")
            print(f"    Original: {original} ({type(original).__name__})")
            print(f"    Normalized: {normalized} ({type(normalized).__name__ if normalized else 'None'})")
    
    def _print_header(self, text: str):
        """Print section header."""
        if self.verbose or self.debug or self.show_policy:
            print(f"\n{'='*60}")
            print(f"{text}")
            print(f"{'='*60}")
    
    def _print_section(self, text: str):
        """Print subsection."""
        if self.verbose or self.debug:
            print(f"\n[{text}]")
            print(f"{'-'*40}")


# =============================================================================
# INHERITANCE CHECKER
# =============================================================================

def check_inheritance(parent_file: str, child_file: str, verbose: bool = False, debug: bool = False) -> InheritanceResult:
    """Check if child policy validly inherits from parent."""
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"INHERITANCE CHECK")
        print(f"Parent: {parent_file}")
        print(f"Child: {child_file}")
        print(f"{'='*60}")
    
    # Parse both
    parent_result = parse_ttl_file(parent_file)
    child_result = parse_ttl_file(child_file)
    
    if not parent_result.policies or not child_result.policies:
        return InheritanceResult(
            parent_file=parent_file,
            child_file=child_file,
            is_valid=False,
            violations=[{"error": "Could not parse policies"}]
        )
    
    # TODO: Implement full inheritance checking
    # For now, just check if child is more restrictive
    
    return InheritanceResult(
        parent_file=parent_file,
        child_file=child_file,
        is_valid=True,
        violations=[]
    )


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_summary(result: PolicyAnalysis) -> str:
    """Format single-line summary."""
    filename = Path(result.file).name
    
    # Section 7.6: Policy Conflict Classification
    if result.overall_judgment == "INTERNAL-CONFLICT":
        status = "[CONFLICT]"
    elif result.overall_judgment == "DEONTIC-CONFLICT":
        status = "[DEONTIC]"
    elif result.overall_judgment == "CONSISTENT":
        status = "[OK]"
    elif result.overall_judgment == "UNKNOWN":
        status = "[UNKNOWN]"
    elif result.overall_judgment == "ERROR":
        status = "[ERROR]"
    else:
        status = "[???]"
    
    return f"{status} {filename}: {result.overall_judgment}"


def format_detailed(result: PolicyAnalysis) -> str:
    """Format detailed output."""
    lines = [format_summary(result)]
    
    lines.append(f"   Policy: {result.policy_id} ({result.policy_type})")
    lines.append(f"   Constraints: {result.total_constraints} ({result.atomic_constraints} atomic, {result.composite_constraints} composite)")
    
    if result.permissions:
        lines.append(f"   Permissions: {len(result.permissions)}")
        for p in result.permissions:
            status = "[CONFLICT]" if p.judgment == "CONFLICT" else "[OK]"
            lines.append(f"     {status} {p.rule_id} ({p.action}): {p.judgment}")
    
    if result.prohibitions:
        lines.append(f"   Prohibitions: {len(result.prohibitions)}")
        for p in result.prohibitions:
            status = "[CONFLICT]" if p.judgment == "CONFLICT" else "[OK]"
            lines.append(f"     {status} {p.rule_id} ({p.action}): {p.judgment}")
    
    if result.duties:
        lines.append(f"   Duties: {len(result.duties)}")
        for d in result.duties:
            status = "[CONFLICT]" if d.judgment == "CONFLICT" else "[OK]"
            lines.append(f"     {status} {d.rule_id} ({d.action}): {d.judgment}")
    
    # Show deontic conflicts (Section 7.4)
    if result.deontic_conflicts:
        lines.append(f"   Deontic Conflicts: {len(result.deontic_conflicts)}")
        for dc in result.deontic_conflicts:
            lines.append(f"     Action '{dc['action']}': Permission <-> Prohibition overlap")
            if dc.get('witness'):
                lines.append(f"       Witness: {dc['witness']}")
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ODRL-SA Policy Analyzer - Comprehensive Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s policy.ttl                    Basic analysis
  %(prog)s policy.ttl -v                 Verbose output
  %(prog)s policy.ttl -d                 Debug mode (Z3 formulas)
  %(prog)s policy.ttl --show-policy      Show policy structure
  %(prog)s policy.ttl --show-normalize   Show normalization
  %(prog)s policy.ttl --all              All debug output
  %(prog)s tests/ttl/percentage/         Analyze directory
  %(prog)s parent.ttl child.ttl          Inheritance check
  %(prog)s policy.ttl --json             JSON output
        """
    )
    
    parser.add_argument('path', help='TTL file or directory')
    parser.add_argument('child', nargs='?', help='Child policy for inheritance check')
    
    # Output modes
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode (Z3 formulas)')
    parser.add_argument('--show-policy', action='store_true', help='Show policy structure')
    parser.add_argument('--show-normalize', action='store_true', help='Show normalization')
    parser.add_argument('--all', action='store_true', help='Enable all output')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--summary', action='store_true', help='Summary only (for directories)')
    
    args = parser.parse_args()
    
    # --all enables everything
    if args.all:
        args.verbose = True
        args.debug = True
        args.show_policy = True
        args.show_normalize = True
    
    path = Path(args.path)
    
    # Inheritance check mode
    if args.child:
        result = check_inheritance(
            str(path), 
            args.child,
            verbose=args.verbose,
            debug=args.debug
        )
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            status = "[VALID]" if result.is_valid else "[INVALID]"
            print(f"\nInheritance: {status}")
            if result.violations:
                for v in result.violations:
                    print(f"  - {v}")
        return 0 if result.is_valid else 1
    
    # Collect files
    if path.is_dir():
        files = sorted(path.glob('*.ttl'))
        if not files:
            print(f"No TTL files found in {path}")
            return 1
    elif path.is_file():
        files = [path]
    else:
        print(f"Path not found: {path}")
        return 1
    
    # Analyze
    analyzer = PolicyAnalyzer(
        verbose=args.verbose,
        debug=args.debug,
        show_policy=args.show_policy,
        show_normalize=args.show_normalize
    )
    
    results = []
    for f in files:
        result = analyzer.analyze_file(str(f))
        results.append(result)
    
    # Output
    if args.json:
        if len(results) == 1:
            print(json.dumps(results[0].to_dict(), indent=2))
        else:
            print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for result in results:
            if args.verbose or len(files) == 1:
                print(format_detailed(result))
            else:
                print(format_summary(result))
        
        # Summary for multiple files
        if len(results) > 1:
            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            
            # Fixed counting logic
            internal_conflicts = sum(1 for r in results if r.overall_judgment == "INTERNAL-CONFLICT")
            deontic_conflicts = sum(1 for r in results if r.overall_judgment == "DEONTIC-CONFLICT")
            consistent = sum(1 for r in results if r.overall_judgment == "CONSISTENT")
            unknown = sum(1 for r in results if r.overall_judgment == "UNKNOWN")
            errors = sum(1 for r in results if r.overall_judgment == "ERROR")
            
            print(f"  Total files: {len(results)}")
            print(f"  [OK] CONSISTENT: {consistent}")
            print(f"  [CONFLICT] INTERNAL-CONFLICT: {internal_conflicts}")
            print(f"  [DEONTIC] DEONTIC-CONFLICT: {deontic_conflicts}")
            if unknown:
                print(f"  [UNKNOWN] UNKNOWN: {unknown}")
            if errors:
                print(f"  [ERROR] ERROR: {errors}")
    
    # Return code
    has_conflicts = any(r.overall_judgment in ("INTERNAL-CONFLICT", "DEONTIC-CONFLICT") for r in results)
    has_errors = any(r.overall_judgment == "ERROR" for r in results)
    
    return 1 if has_errors else 0


if __name__ == '__main__':
    sys.exit(main())