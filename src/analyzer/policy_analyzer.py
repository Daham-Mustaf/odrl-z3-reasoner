# src/analyzer/policy_analyzer.py
"""
ODRL-SA Comprehensive Policy Analyzer

Multi-level conflict detection:
  Level 1: Constraint-level (tautology, domain violation)
  Level 2: Rule-level (internal conflicts, redundancy)
  Level 3: Policy-level (deontic conflicts: permission vs prohibition, duty vs prohibition)
  Level 4: Inheritance-level (child contradicts parent)

Theory Reference: ODRL-SA Formal Specification Sections 7.3-7.6
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from pathlib import Path
import logging

from z3 import Solver, And, Or, Not, sat, unsat

# Core imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.constraint_types import (
    AtomicConstraint,
    CompositeConstraint,
    LogicalOperator,
    Judgment,
    Constraint,
    OperatorType,
)
from parser.ttl_parser import parse_ttl_file, ParseResult, Policy, Rule, RuleType
from encoder.z3_encoder import Z3JudgmentEngine
from normalizer import get_normalized_value

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ConflictLevel(Enum):
    """Level at which conflict was detected."""
    CONSTRAINT = "constraint"      # Single constraint issue
    RULE = "rule"                  # Within-rule conflict
    POLICY = "policy"              # Cross-rule (deontic) conflict
    INHERITANCE = "inheritance"    # Cross-policy conflict


class ConflictType(Enum):
    """Type of conflict detected."""
    # Level 1: Constraint
    TAUTOLOGY = "tautology"
    DOMAIN_VIOLATION = "domain_violation"
    
    # Level 2: Rule
    INTERNAL_CONFLICT = "internal_conflict"
    REDUNDANCY = "redundancy"
    
    # Level 3: Policy
    PERMISSION_PROHIBITION = "permission_prohibition"
    DUTY_PROHIBITION = "duty_prohibition"
    
    # Level 4: Inheritance
    INHERITANCE_CONFLICT = "inheritance_conflict"
    INHERITANCE_REDUNDANCY = "inheritance_redundancy"


class Severity(Enum):
    """Conflict severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Conflict:
    """Represents a detected conflict."""
    level: ConflictLevel
    conflict_type: ConflictType
    severity: Severity
    location: str
    description: str
    constraint_ids: List[str] = field(default_factory=list)
    witness: Optional[Dict[str, Any]] = None
    fix_suggestion: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'level': self.level.value,
            'type': self.conflict_type.value,
            'severity': self.severity.value,
            'location': self.location,
            'description': self.description,
            'constraint_ids': self.constraint_ids,
            'witness': self.witness,
            'fix_suggestion': self.fix_suggestion,
        }


@dataclass
class RuleAnalysis:
    """Analysis result for a single rule."""
    rule_id: str
    rule_type: str
    action: Optional[str]
    target: Optional[str]
    constraint_ids: List[str]
    judgment: str
    model: Optional[Dict[str, Any]] = None
    conflicts: List[Conflict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'rule_id': self.rule_id,
            'rule_type': self.rule_type,
            'action': self.action,
            'target': self.target,
            'constraint_ids': self.constraint_ids,
            'judgment': self.judgment,
            'model': self.model,
            'conflicts': [c.to_dict() for c in self.conflicts],
        }


@dataclass
class InheritanceInfo:
    """Information about resolved inheritance."""
    parent_id: str
    child_id: str
    inherited_constraints: List[str]
    own_constraints: List[str]
    effective_constraints: List[str]
    is_resolved: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PolicyAnalysis:
    """Complete policy analysis result."""
    file: str
    policy_id: str
    policy_type: Optional[str]
    
    # Inheritance
    inherits_from: Optional[str] = None
    inheritance_info: Optional[InheritanceInfo] = None
    
    # Counts
    total_constraints: int = 0
    atomic_constraints: int = 0
    composite_constraints: int = 0
    
    # Rules analysis
    permissions: List[RuleAnalysis] = field(default_factory=list)
    prohibitions: List[RuleAnalysis] = field(default_factory=list)
    duties: List[RuleAnalysis] = field(default_factory=list)
    
    # All conflicts (all levels)
    conflicts: List[Conflict] = field(default_factory=list)
    
    # Conflict counts by level
    constraint_issues: int = 0
    rule_conflicts: int = 0
    deontic_conflicts: int = 0
    inheritance_conflicts: int = 0
    
    # Overall judgment
    overall_judgment: str = "CONSISTENT"
    
    # Parse info
    parse_errors: List[str] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        result = {
            'file': self.file,
            'policy_id': self.policy_id,
            'policy_type': self.policy_type,
            'inherits_from': self.inherits_from,
            'inheritance_info': self.inheritance_info.to_dict() if self.inheritance_info else None,
            'total_constraints': self.total_constraints,
            'atomic_constraints': self.atomic_constraints,
            'composite_constraints': self.composite_constraints,
            'permissions': [r.to_dict() for r in self.permissions],
            'prohibitions': [r.to_dict() for r in self.prohibitions],
            'duties': [r.to_dict() for r in self.duties],
            'conflicts': [c.to_dict() for c in self.conflicts],
            'constraint_issues': self.constraint_issues,
            'rule_conflicts': self.rule_conflicts,
            'deontic_conflicts': self.deontic_conflicts,
            'inheritance_conflicts': self.inheritance_conflicts,
            'overall_judgment': self.overall_judgment,
            'parse_errors': self.parse_errors,
            'parse_warnings': self.parse_warnings,
        }
        return result
    
    def has_errors(self) -> bool:
        return any(c.severity == Severity.ERROR for c in self.conflicts)
    
    def get_conflicts_by_level(self, level: ConflictLevel) -> List[Conflict]:
        return [c for c in self.conflicts if c.level == level]


# =============================================================================
# INHERITANCE RESOLVER
# =============================================================================

def resolve_inheritance_in_file(
    parse_result: ParseResult, 
    verbose: bool = False
) -> Tuple[ParseResult, Dict[str, InheritanceInfo]]:
    """
    Resolve odrl:inheritFrom by merging parent constraints into child rules.
    
    ODRL Cumulative Semantics:
    - Child inherits ALL rules from parent
    - Effective constraints = parent constraints + child constraints
    - Child can only RESTRICT, never EXPAND
    
    Args:
        parse_result: Parsed policies and constraints
        verbose: Print inheritance resolution info
        
    Returns:
        Tuple of (modified ParseResult, inheritance info dict)
    """
    inheritance_info = {}
    
    if not parse_result.policies:
        return parse_result, inheritance_info
    
    # Build policy lookup by URI
    policies_by_uri = {p.uid: p for p in parse_result.policies}
    
    for policy in parse_result.policies:
        if not policy.inherits_from:
            continue
        
        parent_uri = policy.inherits_from
        parent = policies_by_uri.get(parent_uri)
        
        if not parent:
            if verbose:
                print(f"  [INHERITANCE] Warning: Parent not found: {parent_uri}")
            continue
        
        if verbose:
            print(f"  [INHERITANCE] Resolving: {policy.uid}")
            print(f"                Parent: {parent_uri}")
        
        # Track constraints
        inherited_ids = []
        own_ids = set()
        
        # Get child's own constraint IDs before merge
        for rule in policy.rules:
            own_ids.update(rule.constraint_ids)
        
        # Merge parent constraints into child rules
        # Match by BOTH action AND rule_type
        for child_rule in policy.rules:
            for parent_rule in parent.rules:
                if (child_rule.action == parent_rule.action and 
                    child_rule.rule_type == parent_rule.rule_type):
                    for pc_id in parent_rule.constraint_ids:
                        if pc_id not in child_rule.constraint_ids:
                            child_rule.constraint_ids.append(pc_id)
                            inherited_ids.append(pc_id)
                            if verbose:
                                print(f"    + Inherited ({child_rule.rule_type.value}): {pc_id}")
        
        # Get effective constraints after merge
        effective_ids = set()
        for rule in policy.rules:
            effective_ids.update(rule.constraint_ids)
        
        if verbose:
            print(f"    Own constraints: {len(own_ids)}")
            print(f"    Inherited: {len(inherited_ids)}")
            print(f"    Effective total: {len(effective_ids)}")
        
        # Store inheritance info
        inheritance_info[policy.uid] = InheritanceInfo(
            parent_id=parent_uri,
            child_id=policy.uid,
            inherited_constraints=inherited_ids,
            own_constraints=list(own_ids),
            effective_constraints=list(effective_ids),
            is_resolved=True
        )
    
    return parse_result, inheritance_info


# =============================================================================
# COMPREHENSIVE POLICY ANALYZER
# =============================================================================

class PolicyAnalyzer:
    """
    Comprehensive ODRL Policy Analyzer with multi-level conflict detection.
    
    Levels:
        1. Constraint-level: tautology, domain violation
        2. Rule-level: internal conflicts, redundancy
        3. Policy-level: deontic conflicts (perm vs prohib, duty vs prohib)
        4. Inheritance-level: child contradicts parent
    """
    
    def __init__(
        self,
        verbose: bool = False,
        debug: bool = False,
        show_policy: bool = False,
        show_normalize: bool = False,
        resolve_inheritance: bool = True
    ):
        self.verbose = verbose
        self.debug = debug
        self.show_policy = show_policy
        self.show_normalize = show_normalize
        self.resolve_inheritance = resolve_inheritance
        self.engine = Z3JudgmentEngine()
    
    def analyze_file(self, filepath: str) -> PolicyAnalysis:
        """Analyze a single policy file with all 4 levels of conflict detection."""
        filepath = Path(filepath)
        
        self._print_header(f"ANALYZING: {filepath.name}")
        
        # Parse
        parse_result = parse_ttl_file(str(filepath))
        
        # Resolve inheritance
        inheritance_info = {}
        if self.resolve_inheritance:
            parse_result, inheritance_info = resolve_inheritance_in_file(
                parse_result,
                verbose=self.verbose or self.debug
            )
        
        if parse_result.errors:
            self._print_section("Parse Errors")
            for e in parse_result.errors:
                print(f"  [ERROR] {e}")
        
        if not parse_result.policies:
            return PolicyAnalysis(
                file=str(filepath),
                policy_id="",
                policy_type=None,
                overall_judgment="ERROR",
                parse_errors=parse_result.errors or ["No policies found"],
                parse_warnings=parse_result.warnings or []
            )
        
        policy = parse_result.policies[0]
        constraints = parse_result.constraints
        
        # Count constraints
        atomics = [c for c in constraints.values() if isinstance(c, AtomicConstraint)]
        composites = [c for c in constraints.values() if isinstance(c, CompositeConstraint)]
        
        # Initialize result
        result = PolicyAnalysis(
            file=str(filepath),
            policy_id=policy.uid,
            policy_type=policy.policy_type,
            inherits_from=policy.inherits_from,
            inheritance_info=inheritance_info.get(policy.uid),
            total_constraints=len(constraints),
            atomic_constraints=len(atomics),
            composite_constraints=len(composites),
            parse_errors=parse_result.errors or [],
            parse_warnings=parse_result.warnings or []
        )
        
        # Show policy structure
        if self.show_policy:
            self._show_policy_structure(policy, constraints, inheritance_info)
        
        # Show normalization
        if self.show_normalize:
            self._show_normalization(atomics)
        
        # =====================================================================
        # LEVEL 1: Constraint-Level Analysis
        # =====================================================================
        if self.verbose:
            self._print_section("LEVEL 1: Constraint Analysis")
        
        for cid, constraint in constraints.items():
            if isinstance(constraint, AtomicConstraint):
                issues = self._check_constraint_level(cid, constraint)
                result.conflicts.extend(issues)
                result.constraint_issues += len(issues)
        
        if self.verbose and result.constraint_issues == 0:
            print("  [OK] All constraints valid")
        
        # =====================================================================
        # LEVEL 2: Rule-Level Analysis
        # =====================================================================
        if self.verbose:
            self._print_section("LEVEL 2: Rule Analysis")
        
        # Analyze permissions
        for rule in policy.permissions:
            rule_analysis = self._analyze_rule(rule, constraints, "permission")
            result.permissions.append(rule_analysis)
            result.conflicts.extend(rule_analysis.conflicts)
            if rule_analysis.judgment == "CONFLICT":
                result.rule_conflicts += 1
        
        # Analyze prohibitions
        for rule in policy.prohibitions:
            rule_analysis = self._analyze_rule(rule, constraints, "prohibition")
            result.prohibitions.append(rule_analysis)
            result.conflicts.extend(rule_analysis.conflicts)
            if rule_analysis.judgment == "CONFLICT":
                result.rule_conflicts += 1
        
        # Analyze duties
        for rule in policy.duties:
            rule_analysis = self._analyze_rule(rule, constraints, "duty")
            result.duties.append(rule_analysis)
            result.conflicts.extend(rule_analysis.conflicts)
            if rule_analysis.judgment == "CONFLICT":
                result.rule_conflicts += 1
        
        # =====================================================================
        # LEVEL 3: Policy-Level Analysis (Deontic)
        # =====================================================================
        if self.verbose:
            self._print_section("LEVEL 3: Deontic Analysis")
        
        deontic_conflicts = self._check_deontic_conflicts(policy, constraints)
        result.conflicts.extend(deontic_conflicts)
        result.deontic_conflicts = len(deontic_conflicts)
        
        if self.verbose and result.deontic_conflicts == 0:
            print("  [OK] No deontic conflicts")
        
        # =====================================================================
        # LEVEL 4: Inheritance-Level Analysis
        # =====================================================================
        if policy.inherits_from and policy.uid in inheritance_info:
            if self.verbose:
                self._print_section("LEVEL 4: Inheritance Analysis")
            
            inh_conflicts = self._check_inheritance_conflicts(
                policy, constraints, inheritance_info[policy.uid]
            )
            result.conflicts.extend(inh_conflicts)
            result.inheritance_conflicts = len(inh_conflicts)
            
            if self.verbose and result.inheritance_conflicts == 0:
                print("  [OK] No inheritance conflicts")
        
        # =====================================================================
        # Determine Overall Judgment
        # =====================================================================
        result.overall_judgment = self._determine_judgment(result)
        
        return result
    
    # =========================================================================
    # LEVEL 1: Constraint-Level Checks
    # =========================================================================
    
    def _check_constraint_level(self, cid: str, constraint: AtomicConstraint) -> List[Conflict]:
        """Check single constraint for issues (tautology, domain violation)."""
        conflicts = []
        
        # Get domain info from encoder
        left_op = constraint.left_operand
        
        # Check for domain violation using Z3
        self.engine.var_manager.clear()
        formula = self.engine.constraint_encoder.encode(constraint)
        domains = self.engine.var_manager.get_domain_constraints()
        
        solver = Solver()
        solver.add(formula)
        for d in domains:
            solver.add(d)
        
        result = solver.check()
        
        if result == unsat:
            conflicts.append(Conflict(
                level=ConflictLevel.CONSTRAINT,
                conflict_type=ConflictType.DOMAIN_VIOLATION,
                severity=Severity.ERROR,
                location=cid,
                description=f"Constraint '{cid}' violates domain bounds for '{left_op}'",
                constraint_ids=[cid],
                fix_suggestion="Adjust constraint value to be within valid domain"
            ))
            if self.verbose:
                print(f"  [DOMAIN VIOLATION] {cid}: {left_op} constraint violates domain")
        
        # TODO: Check for tautology (constraint always true)
        # This requires comparing constraint bounds with domain bounds
        
        return conflicts
    
    # =========================================================================
    # LEVEL 2: Rule-Level Checks
    # =========================================================================
    
    def _analyze_rule(
        self, 
        rule: Rule, 
        constraints: Dict[str, Constraint],
        rule_type: str
    ) -> RuleAnalysis:
        """Analyze a single rule for internal conflicts."""
        
        if self.verbose:
            self._print_section(f"{rule_type.upper()}: {rule.uid}")
            print(f"  Action: {rule.action}")
            print(f"  Constraints: {rule.constraint_ids}")
        
        rule_conflicts = []
        
        if not rule.constraint_ids:
            return RuleAnalysis(
                rule_id=rule.uid,
                rule_type=rule_type,
                action=rule.action,
                target=rule.target,
                constraint_ids=[],
                judgment="POSSIBLY-COMPATIBLE",
                model={},
                conflicts=[]
            )
        
        # Encode all constraints
        self.engine.var_manager.clear()
        
        formulas = []
        for cid in rule.constraint_ids:
            formula = self._encode_constraint(cid, constraints)
            if formula is not None:
                formulas.append((cid, formula))
                if self.debug:
                    c = constraints.get(cid)
                    if isinstance(c, AtomicConstraint):
                        print(f"    [A] {cid}: {c.left_operand} {c.operator.value} {c.right_operand.value}")
                    elif isinstance(c, CompositeConstraint):
                        print(f"    [C] {cid}: {c.operator.value}({list(c.operands)})")
                    print(f"        -> {formula}")
        
        if not formulas:
            return RuleAnalysis(
                rule_id=rule.uid,
                rule_type=rule_type,
                action=rule.action,
                target=rule.target,
                constraint_ids=rule.constraint_ids,
                judgment="UNKNOWN",
                conflicts=[]
            )
        
        # Combine formulas
        all_formulas = [f for _, f in formulas]
        combined = And(*all_formulas) if len(all_formulas) > 1 else all_formulas[0]
        domains = self.engine.var_manager.get_domain_constraints()
        
        if self.debug:
            print(f"  Formula: {combined}")
            print(f"  Domains: {domains}")
        
        # Check satisfiability
        solver = Solver()
        solver.add(combined)
        for d in domains:
            solver.add(d)
        
        result = solver.check()
        
        if result == unsat:
            rule_conflicts.append(Conflict(
                level=ConflictLevel.RULE,
                conflict_type=ConflictType.INTERNAL_CONFLICT,
                severity=Severity.ERROR,
                location=f"Rule '{rule.uid}'",
                description=f"Constraints in rule '{rule.uid}' are mutually exclusive (UNSAT)",
                constraint_ids=rule.constraint_ids,
                fix_suggestion="Adjust constraint bounds or change AND to OR"
            ))
            
            if self.verbose:
                print(f"  Result: [CONFLICT] CONFLICT")
            
            return RuleAnalysis(
                rule_id=rule.uid,
                rule_type=rule_type,
                action=rule.action,
                target=rule.target,
                constraint_ids=rule.constraint_ids,
                judgment="CONFLICT",
                conflicts=rule_conflicts
            )
        
        elif result == sat:
            # Extract model
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
            
            if self.verbose:
                print(f"  Result: [OK] POSSIBLY-COMPATIBLE")
                print(f"  Model: {model}")
            
            return RuleAnalysis(
                rule_id=rule.uid,
                rule_type=rule_type,
                action=rule.action,
                target=rule.target,
                constraint_ids=rule.constraint_ids,
                judgment="POSSIBLY-COMPATIBLE",
                model=model,
                conflicts=[]
            )
        
        else:
            if self.verbose:
                print(f"  Result: [UNKNOWN]")
            
            return RuleAnalysis(
                rule_id=rule.uid,
                rule_type=rule_type,
                action=rule.action,
                target=rule.target,
                constraint_ids=rule.constraint_ids,
                judgment="UNKNOWN",
                conflicts=[]
            )
    
    # =========================================================================
    # LEVEL 3: Policy-Level Checks (Deontic)
    # =========================================================================
    
    def _check_deontic_conflicts(self, policy: Policy, constraints: Dict) -> List[Conflict]:
        """Check for deontic conflicts between rules."""
        conflicts = []
        
        # Permission vs Prohibition
        perm_prohib = self._check_deontic_pair(
            policy.permissions, 
            policy.prohibitions, 
            constraints,
            "Permission", 
            "Prohibition",
            ConflictType.PERMISSION_PROHIBITION
        )
        conflicts.extend(perm_prohib)
        
        # Duty vs Prohibition
        duty_prohib = self._check_deontic_pair(
            policy.duties,
            policy.prohibitions,
            constraints,
            "Duty",
            "Prohibition",
            ConflictType.DUTY_PROHIBITION
        )
        conflicts.extend(duty_prohib)
        
        return conflicts
    
    def _check_deontic_pair(
        self,
        rules1: List[Rule],
        rules2: List[Rule],
        constraints: Dict,
        type1: str,
        type2: str,
        conflict_type: ConflictType
    ) -> List[Conflict]:
        """Check for overlap between two rule sets (e.g., permission vs prohibition)."""
        conflicts = []
        
        # Group by action
        by_action1 = {}
        for r in rules1:
            action = r.action or '_default_'
            by_action1.setdefault(action, []).append(r)
        
        by_action2 = {}
        for r in rules2:
            action = r.action or '_default_'
            by_action2.setdefault(action, []).append(r)
        
        # Check common actions
        common_actions = set(by_action1.keys()) & set(by_action2.keys())
        
        for action in common_actions:
            r1_list = by_action1[action]
            r2_list = by_action2[action]
            
            if self.verbose:
                self._print_section(f"Deontic Check: action={action}")
                print(f"  {type1}s: {[r.uid for r in r1_list]}")
                print(f"  {type2}s: {[r.uid for r in r2_list]}")
            
            # Encode both sets
            self.engine.var_manager.clear()
            
            # Encode rules1 (OR of all rules, AND within each rule)
            formulas1 = []
            for r in r1_list:
                rule_formulas = []
                for cid in r.constraint_ids:
                    f = self._encode_constraint(cid, constraints)
                    if f is not None:
                        rule_formulas.append(f)
                if rule_formulas:
                    formulas1.append(And(*rule_formulas) if len(rule_formulas) > 1 else rule_formulas[0])
            
            # Encode rules2
            formulas2 = []
            for r in r2_list:
                rule_formulas = []
                for cid in r.constraint_ids:
                    f = self._encode_constraint(cid, constraints)
                    if f is not None:
                        rule_formulas.append(f)
                if rule_formulas:
                    formulas2.append(And(*rule_formulas) if len(rule_formulas) > 1 else rule_formulas[0])
            
            if not formulas1 or not formulas2:
                continue
            
            phi1 = Or(*formulas1) if len(formulas1) > 1 else formulas1[0]
            phi2 = Or(*formulas2) if len(formulas2) > 1 else formulas2[0]
            
            if self.debug:
                print(f"  Phi_{type1.lower()}: {phi1}")
                print(f"  Phi_{type2.lower()}: {phi2}")
            
            # Check overlap: SAT(phi1 AND phi2)
            overlap = And(phi1, phi2)
            domains = self.engine.var_manager.get_domain_constraints()
            
            if self.debug:
                print(f"  Deontic check: {overlap}")
                print(f"  Domains: {domains}")
            
            solver = Solver()
            solver.add(overlap)
            for d in domains:
                solver.add(d)
            
            result = solver.check()
            
            if result == sat:
                # Extract witness
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
                
                conflicts.append(Conflict(
                    level=ConflictLevel.POLICY,
                    conflict_type=conflict_type,
                    severity=Severity.ERROR,
                    location=f"Action '{action}'",
                    description=f"{type1} and {type2} overlap for action '{action}'",
                    constraint_ids=[cid for r in r1_list + r2_list for cid in r.constraint_ids],
                    witness=witness,
                    fix_suggestion=f"Make {type1.lower()} and {type2.lower()} constraints mutually exclusive"
                ))
                
                if self.verbose:
                    print(f"  [DEONTIC CONFLICT DETECTED]")
                    print(f"     Witness: {witness}")
            else:
                if self.verbose:
                    print(f"  [OK] No deontic conflict for action '{action}'")
        
        return conflicts
    
    # =========================================================================
    # LEVEL 4: Inheritance-Level Checks
    # =========================================================================
    
    def _check_inheritance_conflicts(
        self, 
        policy: Policy, 
        constraints: Dict,
        inh_info: InheritanceInfo
    ) -> List[Conflict]:
        """Check for inheritance conflicts (child contradicts parent)."""
        conflicts = []
        
        inherited_ids = set(inh_info.inherited_constraints)
        own_ids = set(inh_info.own_constraints)
        
        if not inherited_ids:
            return conflicts
        
        # For each rule, check if inherited + own creates conflict
        for rule in policy.rules:
            rule_inherited = [cid for cid in rule.constraint_ids if cid in inherited_ids]
            rule_own = [cid for cid in rule.constraint_ids if cid in own_ids]
            
            if not rule_inherited or not rule_own:
                continue
            
            # Check if inherited AND own is UNSAT
            self.engine.var_manager.clear()
            
            inherited_formulas = []
            for cid in rule_inherited:
                f = self._encode_constraint(cid, constraints)
                if f is not None:
                    inherited_formulas.append(f)
            
            own_formulas = []
            for cid in rule_own:
                f = self._encode_constraint(cid, constraints)
                if f is not None:
                    own_formulas.append(f)
            
            if not inherited_formulas or not own_formulas:
                continue
            
            phi_inherited = And(*inherited_formulas) if len(inherited_formulas) > 1 else inherited_formulas[0]
            phi_own = And(*own_formulas) if len(own_formulas) > 1 else own_formulas[0]
            
            combined = And(phi_inherited, phi_own)
            domains = self.engine.var_manager.get_domain_constraints()
            
            solver = Solver()
            solver.add(combined)
            for d in domains:
                solver.add(d)
            
            result = solver.check()
            
            if result == unsat:
                conflicts.append(Conflict(
                    level=ConflictLevel.INHERITANCE,
                    conflict_type=ConflictType.INHERITANCE_CONFLICT,
                    severity=Severity.ERROR,
                    location=f"Rule '{rule.uid}' (inherits from {inh_info.parent_id})",
                    description=f"Child constraints contradict inherited parent constraints",
                    constraint_ids=rule_inherited + rule_own,
                    fix_suggestion="Adjust child constraints to be compatible with parent"
                ))
                
                if self.verbose:
                    print(f"  [INHERITANCE CONFLICT] Rule '{rule.uid}'")
                    print(f"    Inherited: {rule_inherited}")
                    print(f"    Own: {rule_own}")
                    print(f"    Combined: UNSAT")
        
        return conflicts
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _encode_constraint(self, cid: str, constraints: Dict) -> Any:
        """Recursively encode a constraint."""
        if cid not in constraints:
            return None
        
        c = constraints[cid]
        
        if isinstance(c, AtomicConstraint):
            return self.engine.constraint_encoder.encode(c)
        
        elif isinstance(c, CompositeConstraint):
            children = [self._encode_constraint(child_id, constraints) 
                       for child_id in c.operands]
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
    
    def _determine_judgment(self, result: PolicyAnalysis) -> str:
        """Determine overall policy judgment based on all conflicts."""
        
        # Check by priority (most severe first)
        inheritance_errors = [c for c in result.conflicts 
                            if c.level == ConflictLevel.INHERITANCE 
                            and c.severity == Severity.ERROR]
        if inheritance_errors:
            return "INHERITANCE-CONFLICT"
        
        rule_errors = [c for c in result.conflicts 
                      if c.level == ConflictLevel.RULE 
                      and c.severity == Severity.ERROR]
        if rule_errors:
            return "INTERNAL-CONFLICT"
        
        deontic_errors = [c for c in result.conflicts 
                        if c.level == ConflictLevel.POLICY 
                        and c.severity == Severity.ERROR]
        if deontic_errors:
            return "DEONTIC-CONFLICT"
        
        constraint_errors = [c for c in result.conflicts 
                           if c.level == ConflictLevel.CONSTRAINT 
                           and c.severity == Severity.ERROR]
        if constraint_errors:
            return "CONSTRAINT-ERROR"
        
        # Check for warnings
        warnings = [c for c in result.conflicts if c.severity == Severity.WARNING]
        if warnings:
            return "CONSISTENT-WITH-WARNINGS"
        
        return "CONSISTENT"
    
    # =========================================================================
    # Display Methods
    # =========================================================================
    
    def _show_policy_structure(self, policy: Policy, constraints: Dict, 
                               inheritance_info: Dict[str, InheritanceInfo] = None):
        """Display full policy structure."""
        self._print_section("POLICY STRUCTURE")
        
        print(f"  Policy ID: {policy.uid}")
        print(f"  Type: {policy.policy_type}")
        
        # Show inheritance info
        if policy.inherits_from:
            print(f"  Inherits from: {policy.inherits_from}")
            if inheritance_info and policy.uid in inheritance_info:
                info = inheritance_info[policy.uid]
                print(f"  [INHERITANCE RESOLVED]")
                print(f"    Own constraints: {len(info.own_constraints)}")
                print(f"    Inherited: {len(info.inherited_constraints)}")
                print(f"    Effective total: {len(info.effective_constraints)}")
        
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
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Enums
    'ConflictLevel',
    'ConflictType',
    'Severity',
    
    # Data classes
    'Conflict',
    'RuleAnalysis',
    'InheritanceInfo',
    'PolicyAnalysis',
    
    # Functions
    'resolve_inheritance_in_file',
    
    # Classes
    'PolicyAnalyzer',
]