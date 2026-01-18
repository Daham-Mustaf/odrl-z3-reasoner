# src/analyzer/policy_analyzer.py
"""
Policy Analyzer: Dynamic explanation of policy structure and conflicts.
"""

from typing import Dict, List, Union, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, ConstraintType, OperatorType
)
from ..reasoner.conflict_detector import Conflict

@dataclass
class RuleInfo:
    """Information about a single rule"""
    rule_id: str
    rule_type: str
    action: str
    constraint_ids: List[str]
    constraint_summary: str

@dataclass 
class PolicyAnalysis:
    """Complete policy analysis"""
    policy_id: str = ""
    permissions: List[RuleInfo] = field(default_factory=list)
    prohibitions: List[RuleInfo] = field(default_factory=list)
    all_constraints: Dict[str, str] = field(default_factory=dict)
    conflicts: List[Conflict] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)

class PolicyAnalyzer:
    """Analyze and explain ODRL policies dynamically"""
    
    # Operator symbols for display
    OP_SYMBOLS = {
        OperatorType.EQ: '=',
        OperatorType.NEQ: '≠',
        OperatorType.LT: '<',
        OperatorType.LTEQ: '≤',
        OperatorType.GT: '>',
        OperatorType.GTEQ: '≥',
        OperatorType.IS_ANY_OF: '∈',
        OperatorType.IS_ALL_OF: '⊇',
        OperatorType.IS_NONE_OF: '∉',
        OperatorType.HAS_PART: 'contains',
        OperatorType.IS_PART_OF: 'in',
        OperatorType.IS_A: 'is-a',
    }
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def analyze(self, policy, conflicts: List[Conflict]) -> PolicyAnalysis:
        """Generate complete policy analysis"""
        
        permissions = []
        prohibitions = []
        
        for rule in policy.rules:
            cids = self._get_constraint_ids(rule)
            
            rule_info = RuleInfo(
                rule_id=self._safe_get(rule, ['id', 'rule_id'], 'unknown'),
                rule_type=self._safe_get(rule, ['rule_type'], 'unknown'),
                action=self._safe_get(rule, ['action'], 'unknown'),
                constraint_ids=cids,
                constraint_summary=self._summarize_constraints(cids, policy.constraints)
            )
            
            if rule_info.rule_type == 'permission':
                permissions.append(rule_info)
            else:
                prohibitions.append(rule_info)
        
        # Generate constraint summaries
        all_constraints = {}
        for cid, constraint in policy.constraints.items():
            all_constraints[cid] = self._constraint_to_human(constraint, policy.constraints)
        
        # Generate dynamic explanations
        explanations = self._generate_dynamic_explanations(
            conflicts, policy, permissions, prohibitions, all_constraints
        )
        
        return PolicyAnalysis(
            policy_id=self._safe_get(policy, ['uri', 'id', 'policy_id'], 'unknown'),
            permissions=permissions,
            prohibitions=prohibitions,
            all_constraints=all_constraints,
            conflicts=conflicts,
            explanations=explanations
        )
    
    def _safe_get(self, obj, attrs: List[str], default: str) -> str:
        """Safely get attribute from object"""
        for attr in attrs:
            if hasattr(obj, attr):
                val = getattr(obj, attr)
                if val is not None:
                    return str(val)
        return default
    
    def _get_constraint_ids(self, rule) -> List[str]:
        """Get constraint IDs from rule"""
        if hasattr(rule, 'constraint_ids') and rule.constraint_ids:
            return rule.constraint_ids
        elif hasattr(rule, 'constraint_id') and rule.constraint_id:
            return [rule.constraint_id]
        return []
    
    def _format_value(self, value, unit: Optional[str] = None) -> str:
        """Format value for display based on type"""
        
        # Timestamp to datetime
        if unit == 'seconds_since_epoch':
            try:
                dt = datetime.fromtimestamp(int(value))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # Duration in seconds
        if unit == 'seconds' and isinstance(value, (int, float)):
            if value >= 86400:
                return f"{value/86400:.1f} days"
            elif value >= 3600:
                return f"{value/3600:.1f} hours"
            elif value >= 60:
                return f"{value/60:.1f} minutes"
            else:
                return f"{value} seconds"
        
        # Bytes
        if unit == 'bytes' and isinstance(value, (int, float)):
            if value >= 1e9:
                return f"{value/1e9:.2f} GB"
            elif value >= 1e6:
                return f"{value/1e6:.2f} MB"
            elif value >= 1e3:
                return f"{value/1e3:.2f} KB"
            else:
                return f"{value} bytes"
        
        # Currency (cents to dollars)
        if unit and 'cent' in unit.lower():
            return f"${value/100:.2f}"
        
        # List of values
        if isinstance(value, list):
            return f"[{', '.join(str(v) for v in value)}]"
        
        return str(value)
    
    def _constraint_to_human(self, 
                            constraint: Union[AtomicConstraint, CompositeConstraint],
                            all_constraints: Dict) -> str:
        """Convert constraint to human-readable string"""
        
        if isinstance(constraint, AtomicConstraint):
            op_symbol = self.OP_SYMBOLS.get(constraint.operator, constraint.operator.value)
            
            # Get unit for formatting
            unit = None
            if hasattr(constraint.right_value, 'canonical_unit'):
                unit = constraint.right_value.canonical_unit
            
            value = self._format_value(constraint.right_value.canonical_value, unit)
            
            return f"{constraint.left_operand} {op_symbol} {value}"
        
        elif isinstance(constraint, CompositeConstraint):
            children_str = []
            for child_id in constraint.children:
                child = all_constraints.get(child_id)
                if child:
                    if isinstance(child, str):
                        children_str.append(child)
                    else:
                        children_str.append(self._constraint_to_human(child, all_constraints))
                else:
                    children_str.append(f"[{child_id[:8]}...]")
            
            if constraint.constraint_type == ConstraintType.AND:
                return f"({' AND '.join(children_str)})"
            elif constraint.constraint_type == ConstraintType.OR:
                return f"({' OR '.join(children_str)})"
            elif constraint.constraint_type == ConstraintType.XONE:
                return f"EXACTLY-ONE({', '.join(children_str)})"
        
        return str(constraint)
    
    def _summarize_constraints(self, constraint_ids: List[str], all_constraints: Dict) -> str:
        """Summarize constraints for a rule"""
        if not constraint_ids:
            return 'No constraints'
        
        summaries = []
        for cid in constraint_ids:
            constraint = all_constraints.get(cid)
            if constraint:
                summaries.append(self._constraint_to_human(constraint, all_constraints))
        
        return ' AND '.join(summaries) if summaries else 'No constraints'
    
    def _generate_dynamic_explanations(self,
                                       conflicts: List[Conflict],
                                       policy,
                                       permissions: List[RuleInfo],
                                       prohibitions: List[RuleInfo],
                                       constraint_summaries: Dict[str, str]) -> List[str]:
        """Generate dynamic explanations based on actual policy content"""
        
        explanations = []
        
        for i, conflict in enumerate(conflicts, 1):
            exp = self._explain_single_conflict(
                i, conflict, policy, permissions, prohibitions, constraint_summaries
            )
            explanations.append(exp)
        
        return explanations
    
    def _explain_single_conflict(self,
                                 num: int,
                                 conflict: Conflict,
                                 policy,
                                 permissions: List[RuleInfo],
                                 prohibitions: List[RuleInfo],
                                 constraint_summaries: Dict[str, str]) -> str:
        """Generate dynamic explanation for a single conflict"""
        
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"CONFLICT #{num}: {conflict.conflict_type.replace('_', ' ').upper()}")
        lines.append(f"{'='*60}")
        
        # Find involved rules
        involved_perms = [p for p in permissions if conflict.action == p.action]
        involved_prohibs = [p for p in prohibitions if conflict.action == p.action]
        
        if conflict.conflict_type == 'permission_prohibition':
            lines.append(f"\n⚠️  Action '{conflict.action}' has conflicting rules:")
            
            # Show permission details
            if involved_perms:
                lines.append(f"\n  ✅ PERMISSION allows '{conflict.action}' when:")
                for perm in involved_perms:
                    lines.append(f"     {perm.constraint_summary}")
            
            # Show prohibition details
            if involved_prohibs:
                lines.append(f"\n  🚫 PROHIBITION blocks '{conflict.action}' when:")
                for prohib in involved_prohibs:
                    lines.append(f"     {prohib.constraint_summary}")
            
            # Show counterexample with interpretation
            if conflict.counterexample:
                lines.append(f"\n  📍 CONFLICT OCCURS when:")
                for var, val in conflict.counterexample.items():
                    formatted_val = self._interpret_counterexample_value(var, val)
                    lines.append(f"     • {var} = {formatted_val}")
                
                lines.append(f"\n  💡 EXPLANATION:")
                lines.append(f"     With these values, BOTH permission AND prohibition")
                lines.append(f"     conditions are satisfied simultaneously.")
            
            # Dynamic fix suggestions
            lines.append(f"\n  🔧 SUGGESTED FIXES:")
            lines.extend(self._suggest_fixes(conflict, involved_perms, involved_prohibs))
        
        elif conflict.conflict_type == 'xone_overlap':
            lines.append(f"\n⚠️  XONE constraint has overlapping branches")
            lines.append(f"\n  Problem: Multiple branches can be true at the same time")
            lines.append(f"  XONE requires EXACTLY ONE branch to be true")
            
            if conflict.counterexample:
                lines.append(f"\n  📍 OVERLAP OCCURS when:")
                for var, val in conflict.counterexample.items():
                    lines.append(f"     • {var} = {val}")
        
        elif conflict.conflict_type == 'unsatisfiable':
            lines.append(f"\n⚠️  Constraint can NEVER be satisfied")
            lines.append(f"\n  {conflict.description}")
            lines.append(f"\n  💡 This constraint is logically impossible")
        
        elif conflict.conflict_type == 'and_contradiction':
            lines.append(f"\n⚠️  AND constraint has contradictory children")
            lines.append(f"\n  The children cannot ALL be true at the same time")
            
            # Show involved constraints
            for cid in conflict.constraint_ids:
                summary = constraint_summaries.get(cid, cid)
                lines.append(f"     • {summary}")
        
        else:
            # Generic handling for any other conflict type
            lines.append(f"\n⚠️  {conflict.description}")
            
            if conflict.constraint_ids:
                lines.append(f"\n  Constraints involved:")
                for cid in conflict.constraint_ids:
                    summary = constraint_summaries.get(cid, cid)
                    lines.append(f"     • {summary}")
            
            if conflict.counterexample:
                lines.append(f"\n  Counterexample:")
                for var, val in conflict.counterexample.items():
                    lines.append(f"     • {var} = {val}")
        
        return '\n'.join(lines)
    
    def _interpret_counterexample_value(self, var: str, val) -> str:
        """Interpret counterexample value based on variable name"""
        
        val_str = str(val)
        
        # Temporal variables
        if 'datetime' in var.lower() or 'time' in var.lower():
            try:
                if isinstance(val, int) and val > 1000000000:
                    dt = datetime.fromtimestamp(val)
                    return f"{val} ({dt.strftime('%Y-%m-%d %H:%M:%S')})"
            except:
                pass
        
        # Count/numeric
        if var.lower() in ['count', 'percentage']:
            return val_str
        
        # Currency
        if 'amount' in var.lower() or 'pay' in var.lower():
            try:
                cents = int(val)
                return f"{cents} cents (${cents/100:.2f})"
            except:
                pass
        
        return val_str
    
    def _suggest_fixes(self, 
                      conflict: Conflict,
                      permissions: List[RuleInfo],
                      prohibitions: List[RuleInfo]) -> List[str]:
        """Generate dynamic fix suggestions based on conflict"""
        
        fixes = []
        
        # Analyze constraint overlap
        perm_constraints = set()
        prohib_constraints = set()
        
        for p in permissions:
            perm_constraints.update(p.constraint_ids)
        for p in prohibitions:
            prohib_constraints.update(p.constraint_ids)
        
        # Suggest based on counterexample
        if conflict.counterexample:
            for var, val in conflict.counterexample.items():
                if 'datetime' in var.lower() or 'time' in var.lower():
                    fixes.append(f"     1. Adjust time windows to not overlap")
                    fixes.append(f"        (e.g., permission ends before prohibition starts)")
                elif var.lower() == 'count':
                    fixes.append(f"     1. Adjust count ranges to be mutually exclusive")
                    fixes.append(f"        (e.g., permission: count < 5, prohibition: count >= 5)")
                elif 'amount' in var.lower():
                    fixes.append(f"     1. Adjust payment ranges to not overlap")
                elif 'language' in var.lower():
                    fixes.append(f"     1. Ensure language sets are disjoint")
                else:
                    fixes.append(f"     1. Adjust '{var}' constraints to be mutually exclusive")
        
        if not fixes:
            fixes.append(f"     1. Make permission and prohibition conditions non-overlapping")
        
        fixes.append(f"     2. Add additional constraints to narrow scope")
        fixes.append(f"     3. Remove one of the conflicting rules")
        
        return fixes
    
    def print_full_report(self, analysis: PolicyAnalysis):
        """Print comprehensive policy report"""
        
        print("\n" + "="*70)
        print("📋 ODRL POLICY ANALYSIS REPORT")
        print("="*70)
        
        print(f"\n📌 Policy: {analysis.policy_id}")
        print(f"   Permissions: {len(analysis.permissions)}")
        print(f"   Prohibitions: {len(analysis.prohibitions)}")
        print(f"   Total Constraints: {len(analysis.all_constraints)}")
        
        # Permissions
        if analysis.permissions:
            print(f"\n{'─'*70}")
            print("✅ PERMISSIONS")
            print(f"{'─'*70}")
            for perm in analysis.permissions:
                print(f"\n  [{perm.action}]")
                print(f"  Condition: {perm.constraint_summary}")
        
        # Prohibitions
        if analysis.prohibitions:
            print(f"\n{'─'*70}")
            print("🚫 PROHIBITIONS")
            print(f"{'─'*70}")
            for prohib in analysis.prohibitions:
                print(f"\n  [{prohib.action}]")
                print(f"  Condition: {prohib.constraint_summary}")
        
        # Conflicts
        print(f"\n{'─'*70}")
        print(f"⚠️  CONFLICT ANALYSIS: {len(analysis.conflicts)} issue(s) found")
        print(f"{'─'*70}")
        
        if not analysis.conflicts:
            print("\n  ✅ No conflicts detected! Policy is logically consistent.")
        else:
            for explanation in analysis.explanations:
                print(explanation)
        
        print("\n" + "="*70)
        print("END OF REPORT")
        print("="*70 + "\n")