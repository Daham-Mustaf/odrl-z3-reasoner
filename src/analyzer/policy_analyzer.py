# src/analyzer/policy_analyzer.py
"""
Policy Analyzer: Detailed explanation of policy structure and conflicts.

Purpose:
- Provides detailed, explanatory output for --dev mode
- Generates fix suggestions for conflicts
- Complements the clean report_generator.py output

Use Cases:
- Understanding WHY conflicts exist
- Getting actionable fix suggestions
- Debugging policy issues
- Learning about ODRL constraint semantics
"""

from typing import Dict, List, Union, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

# NEW IMPORTS - Using new module structure
from ..core.types import (
    AtomicConstraint, 
    CompositeConstraint, 
    OperatorType,
    LogicalOperator,
    Judgment,
)
from ..parser.ttl_parser import Policy, Rule, RuleType
from ..reasoner.conflict_detector import Conflict, ConflictSeverity

logger = logging.getLogger(__name__)


# =============================================================================
# DEBUG UTILITIES
# =============================================================================

def debug_print(category: str, message: str, data: Any = None):
    """Print debug message."""
    print(f"[{category}] {message}")
    if data:
        print(f"         {data}")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RuleInfo:
    """Information about a single rule"""
    rule_id: str
    rule_type: str
    action: str
    constraint_ids: List[str]
    constraint_summary: str
    target: Optional[str] = None
    assigner: Optional[str] = None
    assignee: Optional[str] = None


@dataclass
class ConstraintDetail:
    """Detailed constraint information"""
    constraint_id: str
    constraint_type: str  # 'atomic', 'and', 'or', 'xone', 'andSequence'
    human_readable: str
    left_operand: Optional[str] = None
    operator: Optional[str] = None
    right_value: Optional[str] = None
    unit: Optional[str] = None
    unit_of_count: Optional[str] = None
    domain: Optional[str] = None
    children: List[str] = field(default_factory=list)


@dataclass
class PolicyAnalysis:
    """Complete policy analysis result"""
    policy_id: str = ""
    policy_type: str = "Policy"
    
    # Rules by type
    permissions: List[RuleInfo] = field(default_factory=list)
    prohibitions: List[RuleInfo] = field(default_factory=list)
    duties: List[RuleInfo] = field(default_factory=list)
    
    # Constraints
    all_constraints: Dict[str, str] = field(default_factory=dict)
    constraint_details: Dict[str, ConstraintDetail] = field(default_factory=dict)
    
    # Conflicts
    conflicts: List[Conflict] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)
    
    # Statistics
    stats: Dict[str, int] = field(default_factory=dict)
    
    # Inheritance
    inherits_from: Optional[str] = None


# =============================================================================
# POLICY ANALYZER
# =============================================================================

class PolicyAnalyzer:
    """
    Analyze and explain ODRL policies with detailed output.
    
    This analyzer provides:
    - Human-readable constraint expressions
    - Detailed conflict explanations
    - Actionable fix suggestions
    - ODRL metadata display (unit, unitOfCount, status, dataType)
    
    Use for --dev mode and debugging.
    """
    
    # Operator symbols for display
    OP_SYMBOLS = {
        OperatorType.EQ: '=',
        OperatorType.NEQ: '!=',
        OperatorType.LT: '<',
        OperatorType.LTEQ: '<=',
        OperatorType.GT: '>',
        OperatorType.GTEQ: '>=',
        OperatorType.IS_ANY_OF: 'in',
        OperatorType.IS_ALL_OF: 'contains-all',
        OperatorType.IS_NONE_OF: 'not-in',
        OperatorType.HAS_PART: 'contains',
        OperatorType.IS_PART_OF: 'part-of',
        OperatorType.IS_A: 'is-a',
    }
    
    # Composite constraint type display
    COMPOSITE_SYMBOLS = {
        LogicalOperator.AND: 'AND',
        LogicalOperator.OR: 'OR',
        LogicalOperator.XONE: 'XONE',
        LogicalOperator.AND_SEQUENCE: 'SEQ',
    }
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _debug(self, message: str, data: Any = None):
        """Debug output"""
        if self.debug:
            debug_print("ANALYZER", message, data)
    
    # =========================================================================
    # MAIN ANALYSIS
    # =========================================================================
    
    def analyze(self, policy: Policy, conflicts: List[Conflict], constraints: Dict[str, Any]) -> PolicyAnalysis:
        """
        Generate complete policy analysis.
        
        Args:
            policy: Policy object to analyze
            conflicts: List of detected conflicts
            constraints: Dict of constraint_id -> constraint
            
        Returns:
            PolicyAnalysis with all details
        """
        self._debug(f"Analyzing policy: {policy.uid}")
        
        # Categorize rules
        permissions = []
        prohibitions = []
        duties = []
        
        for rule in policy.rules:
            rule_info = self._analyze_rule(rule, constraints)
            
            rule_type = self._get_rule_type(rule)
            if rule_type == 'permission':
                permissions.append(rule_info)
            elif rule_type == 'prohibition':
                prohibitions.append(rule_info)
            elif rule_type in ('duty', 'obligation'):
                duties.append(rule_info)
        
        # Analyze constraints
        all_constraints_summary = {}
        constraint_details = {}
        
        for cid, constraint in constraints.items():
            all_constraints_summary[cid] = self._constraint_to_human(constraint, constraints)
            constraint_details[cid] = self._extract_constraint_detail(constraint, constraints)
        
        # Generate explanations
        explanations = []
        for i, conflict in enumerate(conflicts, 1):
            explanation = self._explain_conflict(
                i, conflict, policy, permissions, prohibitions, duties, all_constraints_summary
            )
            explanations.append(explanation)
        
        # Calculate statistics
        stats = self._calculate_stats(policy, conflicts, constraints)
        
        return PolicyAnalysis(
            policy_id=policy.uid,
            policy_type=policy.policy_type or 'Policy',
            permissions=permissions,
            prohibitions=prohibitions,
            duties=duties,
            all_constraints=all_constraints_summary,
            constraint_details=constraint_details,
            conflicts=conflicts,
            explanations=explanations,
            stats=stats,
            inherits_from=policy.inherits_from,
        )
    
    # =========================================================================
    # RULE ANALYSIS
    # =========================================================================
    
    def _analyze_rule(self, rule: Rule, constraints: Dict) -> RuleInfo:
        """Analyze a single rule"""
        constraint_ids = rule.constraint_ids if hasattr(rule, 'constraint_ids') else []
        
        return RuleInfo(
            rule_id=rule.uid,
            rule_type=self._get_rule_type(rule),
            action=rule.action or 'unknown',
            constraint_ids=constraint_ids,
            constraint_summary=self._summarize_constraints(constraint_ids, constraints),
            target=rule.target,
            assigner=rule.assigner,
            assignee=rule.assignee,
        )
    
    def _get_rule_type(self, rule: Rule) -> str:
        """Get rule type as string"""
        if hasattr(rule, 'rule_type'):
            if isinstance(rule.rule_type, RuleType):
                return rule.rule_type.value
            return str(rule.rule_type).lower()
        return 'unknown'
    
    # =========================================================================
    # CONSTRAINT ANALYSIS
    # =========================================================================
    
    def _extract_constraint_detail(
        self, 
        constraint: Union[AtomicConstraint, CompositeConstraint],
        all_constraints: Dict
    ) -> ConstraintDetail:
        """Extract detailed constraint information"""
        
        if isinstance(constraint, AtomicConstraint):
            # Get metadata
            metadata = constraint.metadata
            unit = metadata.unit if metadata else None
            unit_of_count = metadata.unit_of_count if metadata else None
            
            return ConstraintDetail(
                constraint_id=constraint.uid,
                constraint_type='atomic',
                human_readable=self._constraint_to_human(constraint, all_constraints),
                left_operand=constraint.left_operand,
                operator=self.OP_SYMBOLS.get(constraint.operator, str(constraint.operator.value)),
                right_value=str(constraint.right_operand.value),
                unit=unit,
                unit_of_count=unit_of_count,
                domain=None,  # Could get from registry if needed
            )
        
        elif isinstance(constraint, CompositeConstraint):
            type_name = self.COMPOSITE_SYMBOLS.get(
                constraint.operator, 
                str(constraint.operator.value)
            )
            
            return ConstraintDetail(
                constraint_id=constraint.uid,
                constraint_type=type_name.lower(),
                human_readable=self._constraint_to_human(constraint, all_constraints),
                children=list(constraint.operands),
            )
        
        return ConstraintDetail(
            constraint_id=str(constraint),
            constraint_type='unknown',
            human_readable=str(constraint),
        )
    
    def _constraint_to_human(
        self, 
        constraint: Union[AtomicConstraint, CompositeConstraint],
        all_constraints: Dict
    ) -> str:
        """Convert constraint to human-readable string"""
        
        if isinstance(constraint, AtomicConstraint):
            op_symbol = self.OP_SYMBOLS.get(constraint.operator, constraint.operator.value)
            value = str(constraint.right_operand.value)
            
            # Add unit suffix if present
            suffix = ""
            if constraint.metadata:
                if constraint.metadata.unit:
                    unit_name = self._extract_local_name(constraint.metadata.unit)
                    suffix += f" [{unit_name}]"
                if constraint.metadata.unit_of_count:
                    suffix += f" per {constraint.metadata.unit_of_count}"
            
            return f"{constraint.left_operand} {op_symbol} {value}{suffix}"
        
        elif isinstance(constraint, CompositeConstraint):
            children_str = []
            for child_id in constraint.operands:
                child = all_constraints.get(child_id)
                if child:
                    if isinstance(child, str):
                        children_str.append(child)
                    else:
                        children_str.append(self._constraint_to_human(child, all_constraints))
                else:
                    children_str.append(f"[{child_id[:20]}...]")
            
            if constraint.operator == LogicalOperator.AND:
                return f"({' AND '.join(children_str)})"
            elif constraint.operator == LogicalOperator.OR:
                return f"({' OR '.join(children_str)})"
            elif constraint.operator == LogicalOperator.XONE:
                return f"EXACTLY-ONE({', '.join(children_str)})"
            elif constraint.operator == LogicalOperator.AND_SEQUENCE:
                return f"SEQUENCE({' -> '.join(children_str)})"
        
        return str(constraint)
    
    def _summarize_constraints(self, constraint_ids: List[str], all_constraints: Dict) -> str:
        """Summarize constraints for a rule"""
        if not constraint_ids:
            return 'No constraints (unconditional)'
        
        summaries = []
        for cid in constraint_ids:
            constraint = all_constraints.get(cid)
            if constraint:
                if isinstance(constraint, str):
                    summaries.append(constraint)
                else:
                    summaries.append(self._constraint_to_human(constraint, all_constraints))
        
        return ' AND '.join(summaries) if summaries else 'No constraints'
    
    # =========================================================================
    # VALUE FORMATTING
    # =========================================================================
    
    def _format_value(self, value: Any, unit: Optional[str] = None) -> str:
        """Format value for display based on type"""
        
        # Timestamp to datetime
        if unit == 'seconds_since_epoch' or unit == 'unix_timestamp':
            try:
                dt = datetime.fromtimestamp(int(value))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # Duration in seconds
        if unit == 'seconds' and isinstance(value, (int, float)):
            v = float(value)
            if v >= 86400:
                return f"{v/86400:.1f} days"
            elif v >= 3600:
                return f"{v/3600:.1f} hours"
            elif v >= 60:
                return f"{v/60:.1f} minutes"
            else:
                return f"{int(v)} seconds"
        
        # Bytes
        if unit == 'bytes' and isinstance(value, (int, float)):
            v = float(value)
            if v >= 1e9:
                return f"{v/1e9:.2f} GB"
            elif v >= 1e6:
                return f"{v/1e6:.2f} MB"
            elif v >= 1e3:
                return f"{v/1e3:.2f} KB"
            else:
                return f"{int(v)} bytes"
        
        # Currency (cents to dollars)
        if unit and 'cent' in str(unit).lower():
            try:
                return f"${float(value)/100:.2f}"
            except:
                pass
        
        # List of values
        if isinstance(value, list):
            items = [str(v) for v in value[:5]]  # Max 5 items
            if len(value) > 5:
                items.append(f"...+{len(value)-5} more")
            return f"[{', '.join(items)}]"
        
        return str(value)
    
    def _extract_local_name(self, uri: str) -> str:
        """Extract local name from URI"""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    # =========================================================================
    # CONFLICT EXPLANATION
    # =========================================================================
    
    def _explain_conflict(
        self,
        num: int,
        conflict: Conflict,
        policy: Policy,
        permissions: List[RuleInfo],
        prohibitions: List[RuleInfo],
        duties: List[RuleInfo],
        constraint_summaries: Dict[str, str]
    ) -> str:
        """Generate detailed explanation for a conflict"""
        
        lines = []
        
        # Header with severity
        severity_marker = {
            ConflictSeverity.CRITICAL: '[CRITICAL]',
            ConflictSeverity.WARNING: '[WARNING]',
            ConflictSeverity.INFO: '[INFO]',
        }.get(conflict.severity, '[?]')
        
        lines.append(f"\n{'='*60}")
        lines.append(f"{severity_marker} CONFLICT #{num}: {conflict.conflict_type.replace('_', ' ').upper()}")
        lines.append(f"   Severity: {conflict.severity.value}")
        if conflict.action and conflict.action != 'none':
            lines.append(f"   Action: {conflict.action}")
        lines.append(f"{'='*60}")
        
        # Type-specific explanation
        if conflict.conflict_type == 'permission_prohibition':
            lines.extend(self._explain_permission_prohibition(
                conflict, permissions, prohibitions, constraint_summaries
            ))
        
        elif conflict.conflict_type == 'duty_prohibition':
            lines.extend(self._explain_duty_prohibition(
                conflict, duties, prohibitions, constraint_summaries
            ))
        
        elif conflict.conflict_type in ('xone_overlap', 'xone_unsatisfiable', 'xone_trivial'):
            lines.extend(self._explain_xone(conflict, constraint_summaries))
        
        elif conflict.conflict_type in ('and_contradiction', 'unsatisfiable', 'or_unsatisfiable'):
            lines.extend(self._explain_inconsistency(conflict, constraint_summaries))
        
        elif conflict.conflict_type == 'tautology':
            lines.extend(self._explain_tautology(conflict, constraint_summaries))
        
        elif conflict.conflict_type in ('permission_subsumption', 'prohibition_redundancy'):
            lines.extend(self._explain_redundancy(conflict, constraint_summaries))
        
        elif conflict.conflict_type == 'unreachable_permission':
            lines.extend(self._explain_unreachable(conflict, constraint_summaries))
        
        elif conflict.conflict_type == 'andsequence_ordering':
            lines.extend(self._explain_andsequence(conflict, constraint_summaries))
        
        else:
            # Generic explanation
            lines.append(f"\n{conflict.description}")
            if conflict.constraint_ids:
                lines.append("\nConstraints involved:")
                for cid in conflict.constraint_ids:
                    summary = constraint_summaries.get(cid, cid)
                    lines.append(f"  - {summary}")
            if conflict.counterexample:
                lines.append("\nCounterexample:")
                for k, v in conflict.counterexample.items():
                    lines.append(f"  - {k} = {v}")
        
        return '\n'.join(lines)
    
    def _explain_permission_prohibition(
        self, conflict: Conflict, permissions: List[RuleInfo], 
        prohibitions: List[RuleInfo], summaries: Dict
    ) -> List[str]:
        """Explain permission-prohibition conflict"""
        lines = []
        
        involved_perms = [p for p in permissions if conflict.action == p.action]
        involved_prohibs = [p for p in prohibitions if conflict.action == p.action]
        
        lines.append(f"\n[!] Action '{conflict.action}' has conflicting rules:")
        
        if involved_perms:
            lines.append(f"\n  PERMISSION allows '{conflict.action}' when:")
            for perm in involved_perms:
                lines.append(f"     {perm.constraint_summary}")
        
        if involved_prohibs:
            lines.append(f"\n  PROHIBITION blocks '{conflict.action}' when:")
            for prohib in involved_prohibs:
                lines.append(f"     {prohib.constraint_summary}")
        
        if conflict.counterexample:
            lines.append(f"\n  CONFLICT OCCURS when:")
            for var, val in conflict.counterexample.items():
                formatted = self._format_counterexample_value(var, val)
                lines.append(f"     - {var} = {formatted}")
            lines.append(f"\n  With these values, BOTH permission AND prohibition are satisfied.")
        
        # Fix suggestions
        lines.append(f"\n  SUGGESTED FIXES:")
        lines.extend(self._suggest_fixes_for_perm_prohib(conflict))
        
        return lines
    
    def _explain_duty_prohibition(
        self, conflict: Conflict, duties: List[RuleInfo],
        prohibitions: List[RuleInfo], summaries: Dict
    ) -> List[str]:
        """Explain duty-prohibition conflict"""
        lines = []
        
        involved_duties = [d for d in duties if conflict.action == d.action]
        involved_prohibs = [p for p in prohibitions if conflict.action == p.action]
        
        lines.append(f"\n[!] Action '{conflict.action}' is REQUIRED but also PROHIBITED:")
        
        if involved_duties:
            lines.append(f"\n  DUTY requires '{conflict.action}' when:")
            for duty in involved_duties:
                lines.append(f"     {duty.constraint_summary}")
        
        if involved_prohibs:
            lines.append(f"\n  PROHIBITION blocks '{conflict.action}' when:")
            for prohib in involved_prohibs:
                lines.append(f"     {prohib.constraint_summary}")
        
        lines.append(f"\n  This creates an IMPOSSIBLE obligation - the action is both required and forbidden!")
        
        lines.append(f"\n  SUGGESTED FIXES:")
        lines.append(f"     1. Remove either the duty or the prohibition")
        lines.append(f"     2. Make their conditions mutually exclusive")
        
        return lines
    
    def _explain_xone(self, conflict: Conflict, summaries: Dict) -> List[str]:
        """Explain XONE violation"""
        lines = []
        
        if 'overlap' in conflict.conflict_type:
            lines.append(f"\n[!] XONE constraint has OVERLAPPING branches:")
            lines.append(f"\n  XONE requires EXACTLY ONE branch to be true.")
            lines.append(f"  But multiple branches can be true simultaneously:")
            
            for cid in conflict.constraint_ids[1:]:  # Skip XONE itself
                summary = summaries.get(cid, cid)
                lines.append(f"  - {summary}")
            
            if conflict.counterexample:
                lines.append(f"\n  OVERLAP when:")
                for k, v in conflict.counterexample.items():
                    lines.append(f"     - {k} = {v}")
            
            lines.append(f"\n  FIX: Make XONE branches mutually exclusive")
        
        elif 'unsatisfiable' in conflict.conflict_type:
            lines.append(f"\n[!] XONE constraint has NO satisfiable branches:")
            lines.append(f"  None of the branches can be true, making XONE unsatisfiable.")
            lines.append(f"\n  FIX: Ensure at least one branch is satisfiable")
        
        elif 'trivial' in conflict.conflict_type:
            lines.append(f"\n[!] XONE constraint has only ONE satisfiable branch:")
            lines.append(f"  This makes the XONE trivial (not really a choice).")
            lines.append(f"\n  FIX: Add more satisfiable options or simplify to regular constraint")
        
        return lines
    
    def _explain_inconsistency(self, conflict: Conflict, summaries: Dict) -> List[str]:
        """Explain constraint inconsistency"""
        lines = []
        
        lines.append(f"\n[!] Constraints are CONTRADICTORY:")
        
        for cid in conflict.constraint_ids:
            summary = summaries.get(cid, cid)
            lines.append(f"  - {summary}")
        
        lines.append(f"\n These constraints cannot ALL be true at the same time.")
        lines.append(f"  -> No valid value exists that satisfies all constraints.")
        
        lines.append(f"\n SUGGESTED FIXES:")
        lines.append(f"     1. Adjust constraint bounds to be compatible")
        lines.append(f"     2. Remove one of the conflicting constraints")
        lines.append(f"     3. Change AND to OR if alternatives are intended")
        
        return lines
    
    def _explain_tautology(self, conflict: Conflict, summaries: Dict) -> List[str]:
        """Explain tautology"""
        lines = []
        
        lines.append(f"\n[!] Constraint is ALWAYS TRUE (tautology):")
        
        for cid in conflict.constraint_ids:
            summary = summaries.get(cid, cid)
            lines.append(f"  - {summary}")
        
        lines.append(f"\n  This constraint provides no restriction - it's always satisfied.")
        lines.append(f"\n  FIX: Remove the constraint or adjust to add meaningful restriction")
        
        return lines
    
    def _explain_redundancy(self, conflict: Conflict, summaries: Dict) -> List[str]:
        """Explain redundancy"""
        lines = []
        
        lines.append(f"\n[!] REDUNDANT constraint detected:")
        
        if len(conflict.constraint_ids) >= 2:
            stronger = summaries.get(conflict.constraint_ids[0], conflict.constraint_ids[0])
            weaker = summaries.get(conflict.constraint_ids[1], conflict.constraint_ids[1])
            
            lines.append(f"\n  Stronger: {stronger}")
            lines.append(f"  Weaker:   {weaker} <- REDUNDANT")
            lines.append(f"\n  The weaker constraint is implied by the stronger one.")
        
        lines.append(f"\n  FIX: Remove the redundant (weaker) constraint")
        
        return lines
    
    def _explain_unreachable(self, conflict: Conflict, summaries: Dict) -> List[str]:
        """Explain unreachable permission"""
        lines = []
        
        lines.append(f"\n[!] Permission is UNREACHABLE:")
        lines.append(f"  A prohibition completely blocks this permission.")
        
        for cid in conflict.constraint_ids:
            summary = summaries.get(cid, cid)
            lines.append(f"  - {summary}")
        
        lines.append(f"\n  The permission can never be exercised because the prohibition")
        lines.append(f"     always applies when the permission would.")
        
        lines.append(f"\n  SUGGESTED FIXES:")
        lines.append(f"     1. Narrow the prohibition scope")
        lines.append(f"     2. Broaden the permission scope")
        lines.append(f"     3. Remove the unreachable permission")
        
        return lines
    
    def _explain_andsequence(self, conflict: Conflict, summaries: Dict) -> List[str]:
        """Explain ANDSEQUENCE info"""
        lines = []
        
        lines.append(f"\n[i] SEQUENTIAL constraint (andSequence):")
        lines.append(f"  Order is preserved but not enforced in static analysis.")
        
        if conflict.metadata and 'sequence_order' in conflict.metadata:
            lines.append(f"\n  Execution order:")
            for i, cid in enumerate(conflict.metadata['sequence_order'], 1):
                summary = summaries.get(cid, cid)
                lines.append(f"     {i}. {summary}")
        
        return lines
    
    # =========================================================================
    # FIX SUGGESTIONS
    # =========================================================================
    
    def _suggest_fixes_for_perm_prohib(self, conflict: Conflict) -> List[str]:
        """Generate fix suggestions for permission-prohibition conflict"""
        fixes = []
        
        if conflict.counterexample:
            for var, val in conflict.counterexample.items():
                if 'datetime' in var.lower() or 'time' in var.lower():
                    fixes.append(f"     1. Adjust time windows to not overlap")
                    fixes.append(f"        (e.g., permission ends before prohibition starts)")
                    break
                elif var.lower() == 'count':
                    fixes.append(f"     1. Adjust count ranges to be mutually exclusive")
                    fixes.append(f"        (e.g., permission: count < 5, prohibition: count >= 5)")
                    break
                elif 'amount' in var.lower() or 'pay' in var.lower():
                    fixes.append(f"     1. Adjust payment ranges to not overlap")
                    break
                elif 'language' in var.lower():
                    fixes.append(f"     1. Ensure language sets are disjoint")
                    break
                elif 'format' in var.lower() or 'media' in var.lower():
                    fixes.append(f"     1. Ensure format/media sets are disjoint")
                    break
                else:
                    fixes.append(f"     1. Adjust '{var}' constraints to be mutually exclusive")
                    break
        
        if not fixes:
            fixes.append(f"     1. Make permission and prohibition conditions non-overlapping")
        
        fixes.append(f"     2. Add additional constraints to narrow scope")
        fixes.append(f"     3. Remove one of the conflicting rules")
        
        return fixes
    
    def _format_counterexample_value(self, var: str, val: Any) -> str:
        """Format counterexample value for display"""
        val_str = str(val)
        
        # Temporal
        if 'datetime' in var.lower() or 'time' in var.lower():
            try:
                if isinstance(val, int) and val > 1000000000:
                    dt = datetime.fromtimestamp(val)
                    return f"{val} ({dt.strftime('%Y-%m-%d %H:%M:%S')})"
            except:
                pass
        
        # Currency
        if 'amount' in var.lower() or 'pay' in var.lower():
            try:
                cents = int(val)
                return f"{cents} cents (${cents/100:.2f})"
            except:
                pass
        
        return val_str
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def _calculate_stats(self, policy: Policy, conflicts: List[Conflict], constraints: Dict) -> Dict[str, int]:
        """Calculate analysis statistics"""
        atomic = sum(1 for c in constraints.values() if isinstance(c, AtomicConstraint))
        composite = sum(1 for c in constraints.values() if isinstance(c, CompositeConstraint))
        
        critical = sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)
        warnings = sum(1 for c in conflicts if c.severity == ConflictSeverity.WARNING)
        info = sum(1 for c in conflicts if c.severity == ConflictSeverity.INFO)
        
        return {
            'total_rules': len(policy.rules),
            'permissions': len(policy.permissions),
            'prohibitions': len(policy.prohibitions),
            'duties': len(policy.duties),
            'total_constraints': len(constraints),
            'atomic_constraints': atomic,
            'composite_constraints': composite,
            'total_conflicts': len(conflicts),
            'critical': critical,
            'warnings': warnings,
            'info': info,
        }
    
    # =========================================================================
    # REPORT OUTPUT
    # =========================================================================
    
    def print_full_report(self, analysis: PolicyAnalysis):
        """Print comprehensive policy report"""
        
        print("\n" + "=" * 70)
        print(" ODRL POLICY ANALYSIS REPORT (Detailed)")
        print("=" * 70)
        
        # Policy info
        print(f"\n Policy: {analysis.policy_id}")
        print(f"   Type: {analysis.policy_type}")
        if analysis.inherits_from:
            print(f"   Inherits from: {analysis.inherits_from}")
        
        # Statistics
        s = analysis.stats
        print(f"\n Statistics:")
        print(f"   Rules: {s.get('total_rules', 0)}")
        print(f"     - Permissions:  {s.get('permissions', 0)}")
        print(f"     - Prohibitions: {s.get('prohibitions', 0)}")
        print(f"     - Duties:       {s.get('duties', 0)}")
        print(f"   Constraints: {s.get('total_constraints', 0)}")
        print(f"     - Atomic:    {s.get('atomic_constraints', 0)}")
        print(f"     - Composite: {s.get('composite_constraints', 0)}")
        
        # Permissions
        if analysis.permissions:
            print(f"\n{'-' * 70}")
            print("PERMISSIONS")
            print(f"{'-' * 70}")
            for perm in analysis.permissions:
                print(f"\n  Action: {perm.action}")
                if perm.target:
                    print(f"  Target: {perm.target}")
                print(f"  When:   {perm.constraint_summary}")
        
        # Prohibitions
        if analysis.prohibitions:
            print(f"\n{'-' * 70}")
            print("PROHIBITIONS")
            print(f"{'-' * 70}")
            for prohib in analysis.prohibitions:
                print(f"\n  Action: {prohib.action}")
                if prohib.target:
                    print(f"  Target: {prohib.target}")
                print(f"  When:   {prohib.constraint_summary}")
        
        # Duties
        if analysis.duties:
            print(f"\n{'-' * 70}")
            print("DUTIES")
            print(f"{'-' * 70}")
            for duty in analysis.duties:
                print(f"\n  Action: {duty.action}")
                if duty.target:
                    print(f"  Target: {duty.target}")
                print(f"  When:   {duty.constraint_summary}")
        
        # Constraint details (debug mode)
        if self.debug and analysis.constraint_details:
            print(f"\n{'-' * 70}")
            print("CONSTRAINT DETAILS")
            print(f"{'-' * 70}")
            for cid, detail in analysis.constraint_details.items():
                print(f"\n  ID: {cid[:40]}{'...' if len(cid) > 40 else ''}")
                print(f"  Type: {detail.constraint_type}")
                print(f"  Expression: {detail.human_readable}")
                if detail.unit:
                    print(f"  Unit: {detail.unit}")
                if detail.unit_of_count:
                    print(f"  Per: {detail.unit_of_count}")
                if detail.domain:
                    print(f"  Domain: {detail.domain}")
        
        # Conflicts
        print(f"\n{'-' * 70}")
        print(f"CONFLICT ANALYSIS: {s.get('total_conflicts', 0)} issue(s)")
        print(f"   ({s.get('critical', 0)} critical, {s.get('warnings', 0)} warnings, {s.get('info', 0)} info)")
        print(f"{'-' * 70}")
        
        if not analysis.conflicts:
            print("\n  No conflicts detected! Policy is logically consistent.")
        else:
            for explanation in analysis.explanations:
                print(explanation)
        
        # Final summary
        print("\n" + "=" * 70)
        if s.get('critical', 0) > 0:
            print("[CRITICAL] POLICY HAS CRITICAL ISSUES - Must fix before deployment")
        elif s.get('warnings', 0) > 0:
            print("[WARNING] POLICY HAS WARNINGS - Review recommended")
        else:
            print("[OK] POLICY IS VALID")
        print("=" * 70 + "\n")