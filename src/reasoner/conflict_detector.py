# src/reasoner/conflict_detector.py
"""
Conflict Detection using Z3 SMT Solver.

Detects:
- Permission-Prohibition conflicts
- Duty-Prohibition conflicts
- Redundancy and subsumption
- Unsatisfiable constraints
- XONE overlaps
- ANDSEQUENCE issues
"""

from z3 import Solver, And, Not, sat, unsat, is_int, is_real, is_string
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# NEW IMPORTS - Using new module structure
from ..core.types import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
)
from ..parser.ttl_parser import Policy, Rule, RuleType
from ..encoder.z3_encoder import Z3JudgmentEngine

logger = logging.getLogger(__name__)


def debug_print(category: str, message: str, data: Any = None):
    """Debug print helper."""
    print(f"[{category}] {message}")
    if data:
        print(f"         {data}")


# =============================================================================
# CONFLICT TYPES
# =============================================================================

class ConflictSeverity(Enum):
    """Severity levels for conflicts"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Conflict:
    """Represents a detected conflict"""
    conflict_type: str
    severity: ConflictSeverity
    action: str
    description: str
    constraint_ids: List[str]
    counterexample: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


# =============================================================================
# CONFLICT DETECTOR
# =============================================================================

class ConflictDetector:
    """
    Detect conflicts in ODRL policies using Z3.
    
    Strategy:
    1. Encode all constraints to Z3
    2. Query Z3 for various conflict patterns
    3. Extract counterexamples from models
    4. Generate human-readable reports
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.encoder = Z3JudgmentEngine(debug=debug)
        self.policy: Optional[Policy] = None
        self.constraints: Dict[str, Any] = {}
        self.conflicts: List[Conflict] = []
        
        # Statistics
        self._stats = {
            'total_checks': 0,
            'sat_checks': 0,
            'unsat_checks': 0,
        }
    
    def _debug(self, message: str, data: Any = None):
        """Debug output helper"""
        if self.debug:
            debug_print("DETECTOR", message, data)
            logger.debug(f"[DETECTOR] {message}")
    
    def detect_all_conflicts(self, policy: Policy, constraints: Dict[str, Any]) -> List[Conflict]:
        """
        Main entry point: detect all conflicts in a policy.
        
        Args:
            policy: ODRL policy with rules
            constraints: Dict of constraint_id -> constraint
            
        Returns:
            List of detected conflicts
        """
        self.policy = policy
        self.constraints = constraints
        self.conflicts = []
        
        self._debug(f"Detecting conflicts in policy: {policy.uid}")
        logger.info(f"Detecting conflicts in policy: {policy.uid}")
        
        # Encode all constraints
        self._encode_all_constraints()
        
        # Run all conflict detection checks
        self._debug("Running conflict detection checks...")
        
        self._detect_permission_prohibition_conflicts()
        self._detect_duty_prohibition_conflicts()
        self._detect_prohibition_redundancy()
        self._detect_permission_ambiguity()
        self._detect_permission_subsumption()
        self._detect_unreachable_permissions()
        self._detect_duty_incompatibility()
        self._detect_xone_overlaps()
        self._detect_xone_trivial()
        self._detect_and_contradictions()
        self._detect_or_unsatisfiable()
        self._detect_andsequence_issues()
        self._detect_unsatisfiable_atomic()
        self._detect_tautologies()
        
        self._debug(f"Detection complete: {len(self.conflicts)} conflicts found")
        logger.info(f"Detected {len(self.conflicts)} conflicts")
        
        return self.conflicts
    
    def _encode_all_constraints(self):
        """Encode all constraints to Z3."""
        self.encoder.var_manager.clear()
        self._formulas = {}
        
        for cid, constraint in self.constraints.items():
            if isinstance(constraint, AtomicConstraint):
                formula = self.encoder.encode(constraint)
                self._formulas[cid] = formula
            elif isinstance(constraint, CompositeConstraint):
                formula = self._encode_composite(constraint)
                self._formulas[cid] = formula
    
    def _encode_composite(self, constraint: CompositeConstraint) -> Any:
        """Encode a composite constraint."""
        child_formulas = []
        for child_id in constraint.operands:
            child = self.constraints.get(child_id)
            if child:
                if isinstance(child, AtomicConstraint):
                    child_formulas.append(self.encoder.encode(child))
                elif isinstance(child, CompositeConstraint):
                    child_formulas.append(self._encode_composite(child))
        
        if not child_formulas:
            from z3 import BoolVal
            return BoolVal(True)
        
        if constraint.operator == LogicalOperator.AND:
            return And(child_formulas)
        elif constraint.operator == LogicalOperator.OR:
            from z3 import Or
            return Or(child_formulas)
        elif constraint.operator == LogicalOperator.XONE:
            # Exactly one must be true
            from z3 import Sum, If, BoolVal
            return Sum([If(f, 1, 0) for f in child_formulas]) == 1
        elif constraint.operator == LogicalOperator.AND_SEQUENCE:
            # For static analysis, treat as AND
            return And(child_formulas)
        
        return And(child_formulas)
    
    def get_formula(self, constraint_id: str) -> Optional[Any]:
        """Get encoded formula for a constraint."""
        return self._formulas.get(constraint_id)
    
    # =========================================================================
    # RULE-LEVEL CONFLICTS
    # =========================================================================
    
    def _detect_permission_prohibition_conflicts(self):
        """
        Detect Permission-Prohibition conflicts (CRITICAL).
        
        A permission and prohibition for the same action conflict if
        their constraints can be simultaneously satisfied.
        """
        permissions = [r for r in self.policy.rules 
                      if self._get_rule_type(r) == 'permission']
        prohibitions = [r for r in self.policy.rules 
                       if self._get_rule_type(r) == 'prohibition']
        
        for perm in permissions:
            for prohib in prohibitions:
                # Check if same action
                if perm.action != prohib.action:
                    continue
                
                perm_constraints = perm.constraint_ids if hasattr(perm, 'constraint_ids') else []
                prohib_constraints = prohib.constraint_ids if hasattr(prohib, 'constraint_ids') else []
                
                # Check if constraints overlap
                if perm_constraints and prohib_constraints:
                    for pc in perm_constraints:
                        for prc in prohib_constraints:
                            overlap, model = self._check_overlap(pc, prc)
                            
                            if overlap:
                                self.conflicts.append(Conflict(
                                    conflict_type='permission_prohibition',
                                    severity=ConflictSeverity.CRITICAL,
                                    action=perm.action,
                                    description=f"Permission({perm.uid}) conflicts with Prohibition({prohib.uid})",
                                    constraint_ids=[pc, prc],
                                    counterexample=model
                                ))
                
                elif not perm_constraints and not prohib_constraints:
                    # Both unconditional - always conflict
                    self.conflicts.append(Conflict(
                        conflict_type='permission_prohibition',
                        severity=ConflictSeverity.CRITICAL,
                        action=perm.action,
                        description=f"Unconditional Permission({perm.uid}) conflicts with unconditional Prohibition({prohib.uid})",
                        constraint_ids=[]
                    ))
    
    def _detect_duty_prohibition_conflicts(self):
        """Detect Duty-Prohibition conflicts (CRITICAL)"""
        duties = [r for r in self.policy.rules 
                 if self._get_rule_type(r) in ('duty', 'obligation')]
        prohibitions = [r for r in self.policy.rules 
                       if self._get_rule_type(r) == 'prohibition']
        
        for duty in duties:
            for prohib in prohibitions:
                if duty.action != prohib.action:
                    continue
                
                duty_constraints = duty.constraint_ids if hasattr(duty, 'constraint_ids') else []
                prohib_constraints = prohib.constraint_ids if hasattr(prohib, 'constraint_ids') else []
                
                if duty_constraints and prohib_constraints:
                    for dc in duty_constraints:
                        for prc in prohib_constraints:
                            overlap, model = self._check_overlap(dc, prc)
                            
                            if overlap:
                                self.conflicts.append(Conflict(
                                    conflict_type='duty_prohibition',
                                    severity=ConflictSeverity.CRITICAL,
                                    action=duty.action,
                                    description=f"Duty({duty.uid}) conflicts with Prohibition({prohib.uid}) - required action is prohibited",
                                    constraint_ids=[dc, prc],
                                    counterexample=model
                                ))
                
                elif not duty_constraints and not prohib_constraints:
                    self.conflicts.append(Conflict(
                        conflict_type='duty_prohibition',
                        severity=ConflictSeverity.CRITICAL,
                        action=duty.action,
                        description=f"Unconditional Duty({duty.uid}) conflicts with unconditional Prohibition({prohib.uid})",
                        constraint_ids=[]
                    ))
    
    def _detect_prohibition_redundancy(self):
        """Detect redundant prohibitions (WARNING)"""
        prohibitions = [r for r in self.policy.rules 
                       if self._get_rule_type(r) == 'prohibition']
        
        for i, prohib1 in enumerate(prohibitions):
            for prohib2 in prohibitions[i+1:]:
                if prohib1.action != prohib2.action:
                    continue
                
                p1_constraints = prohib1.constraint_ids if hasattr(prohib1, 'constraint_ids') else []
                p2_constraints = prohib2.constraint_ids if hasattr(prohib2, 'constraint_ids') else []
                
                if p1_constraints and p2_constraints:
                    for c1 in p1_constraints:
                        for c2 in p2_constraints:
                            if self._check_subsumption(c1, c2):
                                self.conflicts.append(Conflict(
                                    conflict_type='prohibition_redundancy',
                                    severity=ConflictSeverity.WARNING,
                                    action=prohib1.action,
                                    description=f"Prohibition({prohib2.uid}) is subsumed by Prohibition({prohib1.uid}) - redundant",
                                    constraint_ids=[c1, c2]
                                ))
    
    def _detect_permission_ambiguity(self):
        """Detect ambiguous permissions (WARNING)"""
        permissions = [r for r in self.policy.rules 
                      if self._get_rule_type(r) == 'permission']
        
        for i, perm1 in enumerate(permissions):
            for perm2 in permissions[i+1:]:
                if perm1.action != perm2.action:
                    continue
                
                p1_constraints = perm1.constraint_ids if hasattr(perm1, 'constraint_ids') else []
                p2_constraints = perm2.constraint_ids if hasattr(perm2, 'constraint_ids') else []
                
                if p1_constraints and p2_constraints:
                    for c1 in p1_constraints:
                        for c2 in p2_constraints:
                            overlap, model = self._check_overlap(c1, c2)
                            
                            if overlap:
                                subsumes_1_2 = self._check_subsumption(c1, c2)
                                subsumes_2_1 = self._check_subsumption(c2, c1)
                                
                                if not subsumes_1_2 and not subsumes_2_1:
                                    self.conflicts.append(Conflict(
                                        conflict_type='permission_ambiguity',
                                        severity=ConflictSeverity.WARNING,
                                        action=perm1.action,
                                        description=f"Ambiguous permissions: Permission({perm1.uid}) and Permission({perm2.uid}) overlap without subsumption",
                                        constraint_ids=[c1, c2],
                                        counterexample=model
                                    ))
    
    def _detect_permission_subsumption(self):
        """Detect permission subsumption (INFO)"""
        permissions = [r for r in self.policy.rules 
                      if self._get_rule_type(r) == 'permission']
        
        for i, perm1 in enumerate(permissions):
            for perm2 in permissions[i+1:]:
                if perm1.action != perm2.action:
                    continue
                
                p1_constraints = perm1.constraint_ids if hasattr(perm1, 'constraint_ids') else []
                p2_constraints = perm2.constraint_ids if hasattr(perm2, 'constraint_ids') else []
                
                if p1_constraints and p2_constraints:
                    for c1 in p1_constraints:
                        for c2 in p2_constraints:
                            if self._check_subsumption(c1, c2):
                                self.conflicts.append(Conflict(
                                    conflict_type='permission_subsumption',
                                    severity=ConflictSeverity.INFO,
                                    action=perm1.action,
                                    description=f"Permission({perm1.uid}) subsumes Permission({perm2.uid}) - latter is redundant",
                                    constraint_ids=[c1, c2]
                                ))
    
    def _detect_unreachable_permissions(self):
        """Detect permissions blocked by prohibitions (WARNING)"""
        permissions = [r for r in self.policy.rules 
                      if self._get_rule_type(r) == 'permission']
        prohibitions = [r for r in self.policy.rules 
                       if self._get_rule_type(r) == 'prohibition']
        
        for perm in permissions:
            for prohib in prohibitions:
                if perm.action != prohib.action:
                    continue
                
                perm_constraints = perm.constraint_ids if hasattr(perm, 'constraint_ids') else []
                prohib_constraints = prohib.constraint_ids if hasattr(prohib, 'constraint_ids') else []
                
                if perm_constraints and prohib_constraints:
                    for pc in perm_constraints:
                        for prc in prohib_constraints:
                            if self._check_subsumption(prc, pc):
                                self.conflicts.append(Conflict(
                                    conflict_type='unreachable_permission',
                                    severity=ConflictSeverity.WARNING,
                                    action=perm.action,
                                    description=f"Permission({perm.uid}) is unreachable - always blocked by Prohibition({prohib.uid})",
                                    constraint_ids=[pc, prc]
                                ))
    
    def _detect_duty_incompatibility(self):
        """Detect incompatible duties (CRITICAL)"""
        duties = [r for r in self.policy.rules 
                 if self._get_rule_type(r) in ('duty', 'obligation')]
        
        for i, duty1 in enumerate(duties):
            for duty2 in duties[i+1:]:
                if duty1.action != duty2.action:
                    continue
                
                d1_constraints = duty1.constraint_ids if hasattr(duty1, 'constraint_ids') else []
                d2_constraints = duty2.constraint_ids if hasattr(duty2, 'constraint_ids') else []
                
                if d1_constraints and d2_constraints:
                    for c1 in d1_constraints:
                        for c2 in d2_constraints:
                            overlap, _ = self._check_overlap(c1, c2)
                            
                            if not overlap:
                                self.conflicts.append(Conflict(
                                    conflict_type='duty_incompatibility',
                                    severity=ConflictSeverity.CRITICAL,
                                    action=duty1.action,
                                    description=f"Incompatible duties: Duty({duty1.uid}) and Duty({duty2.uid}) cannot both be satisfied",
                                    constraint_ids=[c1, c2]
                                ))
    
    # =========================================================================
    # CONSTRAINT-LEVEL CONFLICTS
    # =========================================================================
    
    def _detect_xone_overlaps(self):
        """Detect XONE constraints with overlapping branches (CRITICAL)"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.operator != LogicalOperator.XONE:
                continue
            
            overlaps = []
            children = list(constraint.operands)
            for i, child1_id in enumerate(children):
                for child2_id in children[i+1:]:
                    overlap, model = self._check_overlap(child1_id, child2_id)
                    if overlap:
                        overlaps.append((child1_id, child2_id, model))
            
            if overlaps:
                self.conflicts.append(Conflict(
                    conflict_type='xone_overlap',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"XONE({constraint_id}) has {len(overlaps)} overlapping branch pairs - may satisfy multiple branches simultaneously",
                    constraint_ids=[constraint_id] + [c for pair in overlaps for c in pair[:2]],
                    metadata={'overlapping_pairs': len(overlaps)}
                ))
    
    def _detect_xone_trivial(self):
        """Detect XONE with only one satisfiable child (WARNING)"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.operator != LogicalOperator.XONE:
                continue
            
            satisfiable_count = 0
            for child_id in constraint.operands:
                if self._check_satisfiable(child_id):
                    satisfiable_count += 1
            
            if satisfiable_count == 1:
                self.conflicts.append(Conflict(
                    conflict_type='xone_trivial',
                    severity=ConflictSeverity.WARNING,
                    action='none',
                    description=f"XONE({constraint_id}) has only one satisfiable child - trivial",
                    constraint_ids=[constraint_id]
                ))
            elif satisfiable_count == 0:
                self.conflicts.append(Conflict(
                    conflict_type='xone_unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"XONE({constraint_id}) has no satisfiable children - unsatisfiable",
                    constraint_ids=[constraint_id]
                ))
    
    def _detect_and_contradictions(self):
        """Detect AND constraints with contradictory children (CRITICAL)"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.operator != LogicalOperator.AND:
                continue
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='and_contradiction',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"AND({constraint_id}) has contradictory children - unsatisfiable",
                    constraint_ids=[constraint_id] + list(constraint.operands)
                ))
    
    def _detect_or_unsatisfiable(self):
        """Detect OR constraints with all unsatisfiable children (CRITICAL)"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.operator != LogicalOperator.OR:
                continue
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='or_unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"OR({constraint_id}) has no satisfiable children - unsatisfiable",
                    constraint_ids=[constraint_id] + list(constraint.operands)
                ))
    
    def _detect_andsequence_issues(self):
        """Detect ANDSEQUENCE constraints and check satisfiability"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.operator != LogicalOperator.AND_SEQUENCE:
                continue
            
            self._debug(f"Found ANDSEQUENCE constraint: {constraint_id}")
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='andsequence_unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"ANDSEQUENCE({constraint_id}) has contradictory children - unsatisfiable regardless of ordering",
                    constraint_ids=[constraint_id] + list(constraint.operands)
                ))
            else:
                self.conflicts.append(Conflict(
                    conflict_type='andsequence_ordering',
                    severity=ConflictSeverity.INFO,
                    action='none',
                    description=f"ANDSEQUENCE({constraint_id}) has {len(constraint.operands)} ordered constraints. Temporal ordering preserved but not enforced.",
                    constraint_ids=[constraint_id],
                    metadata={'sequence_order': list(constraint.operands), 'is_satisfiable': True}
                ))
    
    def _detect_unsatisfiable_atomic(self):
        """Detect unsatisfiable atomic constraints (CRITICAL)"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, AtomicConstraint):
                continue
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"Constraint({constraint_id}) is unsatisfiable: {constraint.left_operand} {constraint.operator.value} {constraint.right_operand.value}",
                    constraint_ids=[constraint_id]
                ))
    
    def _detect_tautologies(self):
        """Detect tautological constraints (WARNING)"""
        for constraint_id, constraint in self.constraints.items():
            if not isinstance(constraint, AtomicConstraint):
                continue
            
            if self._check_tautology(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='tautology',
                    severity=ConflictSeverity.WARNING,
                    action='none',
                    description=f"Constraint({constraint_id}) is always true - tautology: {constraint.left_operand} {constraint.operator.value} {constraint.right_operand.value}",
                    constraint_ids=[constraint_id]
                ))
    
    # =========================================================================
    # Z3 QUERY PRIMITIVES
    # =========================================================================
    
    def _check_overlap(self, c1_id: str, c2_id: str) -> Tuple[bool, Optional[Dict]]:
        """Check if two constraints can be simultaneously true."""
        self._stats['total_checks'] += 1
        
        s = Solver()
        
        for dc in self.encoder.var_manager.get_domain_constraints():
            s.add(dc)
        
        f1 = self.get_formula(c1_id)
        f2 = self.get_formula(c2_id)
        
        if f1 is None or f2 is None:
            self._debug(f"Missing formula for {c1_id} or {c2_id}")
            return False, None
        
        s.add(And(f1, f2))
        result = s.check()
        
        if result == sat:
            self._stats['sat_checks'] += 1
            model = self._extract_model(s.model())
            return True, model
        else:
            self._stats['unsat_checks'] += 1
            return False, None
    
    def _check_subsumption(self, general_id: str, specific_id: str) -> bool:
        """Check if general subsumes specific."""
        self._stats['total_checks'] += 1
        
        s = Solver()
        
        for dc in self.encoder.var_manager.get_domain_constraints():
            s.add(dc)
        
        f_general = self.get_formula(general_id)
        f_specific = self.get_formula(specific_id)
        
        if f_general is None or f_specific is None:
            return False
        
        s.add(And(f_specific, Not(f_general)))
        result = s.check()
        
        if result == unsat:
            self._stats['unsat_checks'] += 1
            return True
        else:
            self._stats['sat_checks'] += 1
            return False
    
    def _check_satisfiable(self, constraint_id: str) -> bool:
        """Check if constraint can be satisfied."""
        self._stats['total_checks'] += 1
        
        s = Solver()
        
        for dc in self.encoder.var_manager.get_domain_constraints():
            s.add(dc)
        
        formula = self.get_formula(constraint_id)
        
        if formula is None:
            return False
        
        s.add(formula)
        result = s.check()
        
        if result == sat:
            self._stats['sat_checks'] += 1
            return True
        else:
            self._stats['unsat_checks'] += 1
            return False
    
    def _check_tautology(self, constraint_id: str) -> bool:
        """Check if constraint is always true."""
        self._stats['total_checks'] += 1
        
        s = Solver()
        
        for dc in self.encoder.var_manager.get_domain_constraints():
            s.add(dc)
        
        formula = self.get_formula(constraint_id)
        
        if formula is None:
            return False
        
        s.add(Not(formula))
        result = s.check()
        
        if result == unsat:
            self._stats['unsat_checks'] += 1
            return True
        else:
            self._stats['sat_checks'] += 1
            return False
    
    def _extract_model(self, z3_model) -> Dict:
        """Extract variable assignments from Z3 model"""
        model = {}
        
        for var_name, var in self.encoder.var_manager._variables.items():
            try:
                val = z3_model[var]
                if val is not None:
                    if is_int(var):
                        model[var_name] = val.as_long()
                    elif is_real(var):
                        try:
                            model[var_name] = float(val.as_decimal(10))
                        except:
                            model[var_name] = str(val)
                    elif is_string(var):
                        model[var_name] = str(val)
                    else:
                        model[var_name] = str(val)
            except:
                pass
        
        return model
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _get_rule_type(self, rule: Rule) -> str:
        """Get rule type as lowercase string"""
        if hasattr(rule, 'rule_type'):
            if isinstance(rule.rule_type, RuleType):
                return rule.rule_type.value
            return str(rule.rule_type).lower()
        return 'unknown'
    
    # =========================================================================
    # REPORTING
    # =========================================================================
    
    def get_conflicts_by_severity(self, severity: ConflictSeverity) -> List[Conflict]:
        """Get conflicts of a specific severity"""
        return [c for c in self.conflicts if c.severity == severity]
    
    def get_conflicts_by_type(self, conflict_type: str) -> List[Conflict]:
        """Get conflicts of a specific type"""
        return [c for c in self.conflicts if c.conflict_type == conflict_type]
    
    def get_stats(self) -> Dict:
        """Get detection statistics"""
        return {
            **self._stats,
            'total_conflicts': len(self.conflicts),
        }
    
    def print_conflict_report(self):
        """Print human-readable conflict report"""
        print("\n" + "="*70)
        print("ODRL CONFLICT DETECTION REPORT")
        print("="*70)
        print()
        
        critical = self.get_conflicts_by_severity(ConflictSeverity.CRITICAL)
        warnings = self.get_conflicts_by_severity(ConflictSeverity.WARNING)
        info = self.get_conflicts_by_severity(ConflictSeverity.INFO)
        
        print(f"Summary: {len(critical)} Critical | {len(warnings)} Warnings | {len(info)} Info")
        print()
        
        if critical:
            print("[CRITICAL] CONFLICTS:")
            print("-" * 70)
            for i, conflict in enumerate(critical, 1):
                print(f"{i}. [{conflict.conflict_type}] {conflict.action}")
                print(f"   {conflict.description}")
                if conflict.counterexample:
                    print(f"   Counterexample: {conflict.counterexample}")
            print()
        
        if warnings:
            print("[WARNING] WARNINGS:")
            print("-" * 70)
            for i, conflict in enumerate(warnings, 1):
                print(f"{i}. [{conflict.conflict_type}] {conflict.action}")
                print(f"   {conflict.description}")
            print()
        
        if info:
            print("[INFO] INFORMATIONAL:")
            print("-" * 70)
            for i, conflict in enumerate(info, 1):
                print(f"{i}. [{conflict.conflict_type}] {conflict.action}")
                print(f"   {conflict.description}")
            print()
        
        if not self.conflicts:
            print("[OK] No conflicts detected - policy is valid")
            print()
        
        print("="*70)