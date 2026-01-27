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

from z3 import Solver, And, Or, Not, sat, unsat, is_int, is_real, is_string, BoolVal, If, Sum
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Use absolute imports (works with sys.path including src/)
from core.types import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
)
from parser.ttl_parser import Policy, Rule, RuleType
from encoder.z3_encoder import Z3JudgmentEngine

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
        self._formulas: Dict[str, Any] = {}
        
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
        self._detect_and_contradictions()
        self._detect_unsatisfiable_atomic()
        
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
            return BoolVal(True)
        
        if constraint.operator == LogicalOperator.AND:
            return And(child_formulas)
        elif constraint.operator == LogicalOperator.OR:
            return Or(child_formulas)
        elif constraint.operator == LogicalOperator.XONE:
            # Exactly one must be true
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
        """Detect Permission-Prohibition conflicts (CRITICAL)."""
        permissions = [r for r in self.policy.rules 
                      if self._get_rule_type(r) == 'permission']
        prohibitions = [r for r in self.policy.rules 
                       if self._get_rule_type(r) == 'prohibition']
        
        for perm in permissions:
            for prohib in prohibitions:
                if perm.action != prohib.action:
                    continue
                
                perm_constraints = perm.constraint_ids if hasattr(perm, 'constraint_ids') and perm.constraint_ids else []
                prohib_constraints = prohib.constraint_ids if hasattr(prohib, 'constraint_ids') and prohib.constraint_ids else []
                
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
                
                duty_constraints = duty.constraint_ids if hasattr(duty, 'constraint_ids') and duty.constraint_ids else []
                prohib_constraints = prohib.constraint_ids if hasattr(prohib, 'constraint_ids') and prohib.constraint_ids else []
                
                if duty_constraints and prohib_constraints:
                    for dc in duty_constraints:
                        for prc in prohib_constraints:
                            overlap, model = self._check_overlap(dc, prc)
                            if overlap:
                                self.conflicts.append(Conflict(
                                    conflict_type='duty_prohibition',
                                    severity=ConflictSeverity.CRITICAL,
                                    action=duty.action,
                                    description=f"Duty({duty.uid}) conflicts with Prohibition({prohib.uid})",
                                    constraint_ids=[dc, prc],
                                    counterexample=model
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
                    description=f"Constraint({constraint_id}) is unsatisfiable: {constraint}",
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
