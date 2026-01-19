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

from z3 import *
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..semantics.constraint_types import (
    Policy, PolicyRule, PolicyRuleType,
    AtomicConstraint, CompositeConstraint, ConstraintType,
    debug_print, is_debug_mode
)
from ..encoder.z3_encoder import Z3Encoder

logger = logging.getLogger(__name__)


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
        self.encoder = Z3Encoder(debug=debug)
        self.policy: Optional[Policy] = None
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
    
    def detect_all_conflicts(self, policy: Policy) -> List[Conflict]:
        """
        Main entry point: detect all conflicts in a policy.
        
        Args:
            policy: ODRL policy with rules and constraints
            
        Returns:
            List of detected conflicts
        """
        self.policy = policy
        self.conflicts = []
        
        self._debug(f"Detecting conflicts in policy: {policy.id}")
        logger.info(f"Detecting conflicts in policy: {policy.id}")
        
        # Encode all constraints
        self.encoder.encode_policy(policy.constraints)
        
        if self.debug:
            self.encoder.print_encoding_summary()
        
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
                
                # Check if constraints overlap
                if perm.constraint_id and prohib.constraint_id:
                    overlap, model = self._check_overlap(
                        perm.constraint_id, 
                        prohib.constraint_id
                    )
                    
                    if overlap:
                        self.conflicts.append(Conflict(
                            conflict_type='permission_prohibition',
                            severity=ConflictSeverity.CRITICAL,
                            action=perm.action,
                            description=f"Permission({perm.id}) conflicts with Prohibition({prohib.id})",
                            constraint_ids=[perm.constraint_id, prohib.constraint_id],
                            counterexample=model
                        ))
                
                elif not perm.constraint_id and not prohib.constraint_id:
                    # Both unconditional - always conflict
                    self.conflicts.append(Conflict(
                        conflict_type='permission_prohibition',
                        severity=ConflictSeverity.CRITICAL,
                        action=perm.action,
                        description=f"Unconditional Permission({perm.id}) conflicts with unconditional Prohibition({prohib.id})",
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
                
                if duty.constraint_id and prohib.constraint_id:
                    overlap, model = self._check_overlap(
                        duty.constraint_id,
                        prohib.constraint_id
                    )
                    
                    if overlap:
                        self.conflicts.append(Conflict(
                            conflict_type='duty_prohibition',
                            severity=ConflictSeverity.CRITICAL,
                            action=duty.action,
                            description=f"Duty({duty.id}) conflicts with Prohibition({prohib.id}) - required action is prohibited",
                            constraint_ids=[duty.constraint_id, prohib.constraint_id],
                            counterexample=model
                        ))
                
                elif not duty.constraint_id and not prohib.constraint_id:
                    self.conflicts.append(Conflict(
                        conflict_type='duty_prohibition',
                        severity=ConflictSeverity.CRITICAL,
                        action=duty.action,
                        description=f"Unconditional Duty({duty.id}) conflicts with unconditional Prohibition({prohib.id})",
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
                
                if prohib1.constraint_id and prohib2.constraint_id:
                    if self._check_subsumption(prohib1.constraint_id, prohib2.constraint_id):
                        self.conflicts.append(Conflict(
                            conflict_type='prohibition_redundancy',
                            severity=ConflictSeverity.WARNING,
                            action=prohib1.action,
                            description=f"Prohibition({prohib2.id}) is subsumed by Prohibition({prohib1.id}) - redundant",
                            constraint_ids=[prohib1.constraint_id, prohib2.constraint_id]
                        ))
    
    def _detect_permission_ambiguity(self):
        """Detect ambiguous permissions (WARNING)"""
        permissions = [r for r in self.policy.rules 
                      if self._get_rule_type(r) == 'permission']
        
        for i, perm1 in enumerate(permissions):
            for perm2 in permissions[i+1:]:
                if perm1.action != perm2.action:
                    continue
                
                if perm1.constraint_id and perm2.constraint_id:
                    overlap, model = self._check_overlap(
                        perm1.constraint_id,
                        perm2.constraint_id
                    )
                    
                    if overlap:
                        subsumes_1_2 = self._check_subsumption(perm1.constraint_id, perm2.constraint_id)
                        subsumes_2_1 = self._check_subsumption(perm2.constraint_id, perm1.constraint_id)
                        
                        if not subsumes_1_2 and not subsumes_2_1:
                            self.conflicts.append(Conflict(
                                conflict_type='permission_ambiguity',
                                severity=ConflictSeverity.WARNING,
                                action=perm1.action,
                                description=f"Ambiguous permissions: Permission({perm1.id}) and Permission({perm2.id}) overlap without subsumption",
                                constraint_ids=[perm1.constraint_id, perm2.constraint_id],
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
                
                if perm1.constraint_id and perm2.constraint_id:
                    if self._check_subsumption(perm1.constraint_id, perm2.constraint_id):
                        self.conflicts.append(Conflict(
                            conflict_type='permission_subsumption',
                            severity=ConflictSeverity.INFO,
                            action=perm1.action,
                            description=f"Permission({perm1.id}) subsumes Permission({perm2.id}) - latter is redundant",
                            constraint_ids=[perm1.constraint_id, perm2.constraint_id]
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
                
                if perm.constraint_id and prohib.constraint_id:
                    if self._check_subsumption(prohib.constraint_id, perm.constraint_id):
                        self.conflicts.append(Conflict(
                            conflict_type='unreachable_permission',
                            severity=ConflictSeverity.WARNING,
                            action=perm.action,
                            description=f"Permission({perm.id}) is unreachable - always blocked by Prohibition({prohib.id})",
                            constraint_ids=[perm.constraint_id, prohib.constraint_id]
                        ))
    
    def _detect_duty_incompatibility(self):
        """Detect incompatible duties (CRITICAL)"""
        duties = [r for r in self.policy.rules 
                 if self._get_rule_type(r) in ('duty', 'obligation')]
        
        for i, duty1 in enumerate(duties):
            for duty2 in duties[i+1:]:
                if duty1.action != duty2.action:
                    continue
                
                if duty1.constraint_id and duty2.constraint_id:
                    overlap, _ = self._check_overlap(duty1.constraint_id, duty2.constraint_id)
                    
                    if not overlap:
                        self.conflicts.append(Conflict(
                            conflict_type='duty_incompatibility',
                            severity=ConflictSeverity.CRITICAL,
                            action=duty1.action,
                            description=f"Incompatible duties: Duty({duty1.id}) and Duty({duty2.id}) cannot both be satisfied",
                            constraint_ids=[duty1.constraint_id, duty2.constraint_id]
                        ))
    
    # =========================================================================
    # CONSTRAINT-LEVEL CONFLICTS
    # =========================================================================
    
    def _detect_xone_overlaps(self):
        """Detect XONE constraints with overlapping branches (CRITICAL)"""
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.constraint_type != ConstraintType.XONE:
                continue
            
            overlaps = []
            for i, child1_id in enumerate(constraint.children):
                for child2_id in constraint.children[i+1:]:
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
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.constraint_type != ConstraintType.XONE:
                continue
            
            satisfiable_count = 0
            for child_id in constraint.children:
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
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.constraint_type != ConstraintType.AND:
                continue
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='and_contradiction',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"AND({constraint_id}) has contradictory children - unsatisfiable",
                    constraint_ids=[constraint_id] + list(constraint.children)
                ))
    
    def _detect_or_unsatisfiable(self):
        """Detect OR constraints with all unsatisfiable children (CRITICAL)"""
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.constraint_type != ConstraintType.OR:
                continue
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='or_unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"OR({constraint_id}) has no satisfiable children - unsatisfiable",
                    constraint_ids=[constraint_id] + list(constraint.children)
                ))
    
    def _detect_andsequence_issues(self):
        """Detect ANDSEQUENCE constraints and check satisfiability"""
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, CompositeConstraint):
                continue
            
            if constraint.constraint_type != ConstraintType.ANDSEQUENCE:
                continue
            
            self._debug(f"Found ANDSEQUENCE constraint: {constraint_id}")
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='andsequence_unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"ANDSEQUENCE({constraint_id}) has contradictory children - unsatisfiable regardless of ordering",
                    constraint_ids=[constraint_id] + list(constraint.children)
                ))
            else:
                self.conflicts.append(Conflict(
                    conflict_type='andsequence_ordering',
                    severity=ConflictSeverity.INFO,
                    action='none',
                    description=f"ANDSEQUENCE({constraint_id}) has {len(constraint.children)} ordered constraints. Temporal ordering preserved but not enforced.",
                    constraint_ids=[constraint_id],
                    metadata={'sequence_order': list(constraint.children), 'is_satisfiable': True}
                ))
    
    def _detect_unsatisfiable_atomic(self):
        """Detect unsatisfiable atomic constraints (CRITICAL)"""
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, AtomicConstraint):
                continue
            
            if not self._check_satisfiable(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='unsatisfiable',
                    severity=ConflictSeverity.CRITICAL,
                    action='none',
                    description=f"Constraint({constraint_id}) is unsatisfiable: {constraint.left_operand} {constraint.operator.value} {constraint.right_value.canonical_value}",
                    constraint_ids=[constraint_id]
                ))
    
    def _detect_tautologies(self):
        """Detect tautological constraints (WARNING)"""
        for constraint_id, constraint in self.policy.constraints.items():
            if not isinstance(constraint, AtomicConstraint):
                continue
            
            if self._check_tautology(constraint_id):
                self.conflicts.append(Conflict(
                    conflict_type='tautology',
                    severity=ConflictSeverity.WARNING,
                    action='none',
                    description=f"Constraint({constraint_id}) is always true - tautology: {constraint.left_operand} {constraint.operator.value} {constraint.right_value.canonical_value}",
                    constraint_ids=[constraint_id]
                ))
    
    # =========================================================================
    # Z3 QUERY PRIMITIVES
    # =========================================================================
    
    def _check_overlap(self, c1_id: str, c2_id: str) -> Tuple[bool, Optional[Dict]]:
        """Check if two constraints can be simultaneously true."""
        self._stats['total_checks'] += 1
        
        s = Solver()
        
        for dc in self.encoder.get_domain_constraints():
            s.add(dc)
        
        f1 = self.encoder.get_formula(c1_id)
        f2 = self.encoder.get_formula(c2_id)
        
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
        
        for dc in self.encoder.get_domain_constraints():
            s.add(dc)
        
        f_general = self.encoder.get_formula(general_id)
        f_specific = self.encoder.get_formula(specific_id)
        
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
        
        for dc in self.encoder.get_domain_constraints():
            s.add(dc)
        
        formula = self.encoder.get_formula(constraint_id)
        
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
        
        for dc in self.encoder.get_domain_constraints():
            s.add(dc)
        
        formula = self.encoder.get_formula(constraint_id)
        
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
        
        for var_name, var in self.encoder.variables.items():
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
    
    def _get_rule_type(self, rule) -> str:
        """Get rule type as lowercase string"""
        rule_type = getattr(rule, 'rule_type', None)
        if rule_type is None:
            return 'unknown'
        if isinstance(rule_type, PolicyRuleType):
            return rule_type.value
        return str(rule_type).lower()
    
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
        print("📋 ODRL CONFLICT DETECTION REPORT")
        print("="*70)
        print()
        
        critical = self.get_conflicts_by_severity(ConflictSeverity.CRITICAL)
        warnings = self.get_conflicts_by_severity(ConflictSeverity.WARNING)
        info = self.get_conflicts_by_severity(ConflictSeverity.INFO)
        
        print(f"📊 Summary: {len(critical)} Critical | {len(warnings)} Warnings | {len(info)} Info")
        print()
        
        if critical:
            print("❌ CRITICAL CONFLICTS:")
            print("-" * 70)
            for i, conflict in enumerate(critical, 1):
                print(f"{i}. [{conflict.conflict_type}] {conflict.action}")
                print(f"   {conflict.description}")
                if conflict.counterexample:
                    print(f"   Counterexample: {conflict.counterexample}")
            print()
        
        if warnings:
            print("⚠️  WARNINGS:")
            print("-" * 70)
            for i, conflict in enumerate(warnings, 1):
                print(f"{i}. [{conflict.conflict_type}] {conflict.action}")
                print(f"   {conflict.description}")
            print()
        
        if info:
            print("ℹ️  INFORMATIONAL:")
            print("-" * 70)
            for i, conflict in enumerate(info, 1):
                print(f"{i}. [{conflict.conflict_type}] {conflict.action}")
                print(f"   {conflict.description}")
            print()
        
        if not self.conflicts:
            print(" No conflicts detected - policy is valid")
            print()
        
        print("="*70)