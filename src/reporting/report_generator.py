# src/reporting/report_generator.py
"""
ODRL Policy Analysis Report Generator

Implements the approved Output Design Specification:
- Clear, Actionable, Concise
- JSON (machine) + Compact CLI (human)
- No verbose explanations, just facts

Output Formats:
- JSON: Machine-readable, full details
- CLI: Human-readable, compact
- CLI Verbose: Human-readable, full details
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime

from ..semantics.constraint_types import (
    AtomicConstraint, CompositeConstraint, ConstraintType, OperatorType,
    PolicyRuleType, Policy
)
from ..reasoner.conflict_detector import Conflict, ConflictSeverity
from ..reasoner.inheritance_checker import InheritanceViolation


# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class PolicyStatus(Enum):
    """Policy validation status"""
    VALID = "VALID"
    INVALID = "INVALID"
    WARNING = "WARNING"


class IssueType(Enum):
    """Issue types matching output spec"""
    INCONSISTENCY = "INCONSISTENCY"
    PERMISSION_PROHIBITION_CONFLICT = "PERMISSION_PROHIBITION_CONFLICT"
    DUTY_PROHIBITION_CONFLICT = "DUTY_PROHIBITION_CONFLICT"
    XONE_VIOLATION = "XONE_VIOLATION"
    EXPANSION = "EXPANSION"
    REDUNDANCY = "REDUNDANCY"
    NEW_ACTION = "NEW_ACTION"
    TAUTOLOGY = "TAUTOLOGY"
    UNREACHABLE = "UNREACHABLE"


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# Operator display symbols
OP_SYMBOLS = {
    OperatorType.EQ: 'eq',
    OperatorType.NEQ: 'neq',
    OperatorType.LT: 'lt',
    OperatorType.LTEQ: 'lteq',
    OperatorType.GT: 'gt',
    OperatorType.GTEQ: 'gteq',
    OperatorType.IS_ANY_OF: 'isAnyOf',
    OperatorType.IS_ALL_OF: 'isAllOf',
    OperatorType.IS_NONE_OF: 'isNoneOf',
    OperatorType.HAS_PART: 'hasPart',
    OperatorType.IS_PART_OF: 'isPartOf',
    OperatorType.IS_A: 'isA',
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ConstraintExpr:
    """Constraint expression for output"""
    id: str
    left_operand: str
    operator: str
    right_operand: Any
    
    def to_string(self) -> str:
        """Convert to readable string"""
        if isinstance(self.right_operand, list):
            return f"{self.left_operand} {self.operator} {self.right_operand}"
        return f"{self.left_operand} {self.operator} {self.right_operand}"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "leftOperand": self.left_operand,
            "operator": self.operator,
            "rightOperand": self.right_operand
        }


@dataclass
class Issue:
    """Single issue in analysis"""
    id: str
    type: IssueType
    severity: Severity
    message: str
    rule_id: Optional[str] = None
    constraint_ids: List[str] = field(default_factory=list)
    constraints: List[ConstraintExpr] = field(default_factory=list)
    counterexample: Optional[Dict[str, Any]] = None
    
    # For permission-prohibition conflicts
    permission_id: Optional[str] = None
    prohibition_id: Optional[str] = None
    permission_constraint: Optional[str] = None
    prohibition_constraint: Optional[str] = None
    
    # For inheritance
    parent_policy_id: Optional[str] = None
    child_policy_id: Optional[str] = None
    parent_constraint: Optional[str] = None
    child_constraint: Optional[str] = None
    
    # For redundancy
    redundant_constraint: Optional[str] = None
    implied_by: Optional[str] = None
    suggestion: Optional[str] = None
    
    # For XONE
    satisfied_count: Optional[int] = None
    expected_count: Optional[int] = None
    satisfied_constraints: List[str] = field(default_factory=list)
    
    # Extra metadata
    action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleAnalyzed:
    """Rule analysis result"""
    rule_id: str
    rule_type: str
    action: str
    target: Optional[str]
    constraint_count: int
    status: str  # "OK", "INCONSISTENT", "CONFLICT"


@dataclass
class Summary:
    """Analysis summary"""
    total_rules: int = 0
    total_constraints: int = 0
    consistent: bool = True
    inheritance_valid: Optional[bool] = None
    errors: int = 0
    warnings: int = 0
    analysis_time_ms: int = 0


@dataclass
class InheritanceCheck:
    """Inheritance check result"""
    parent_policy_id: str
    child_policy_id: str
    inheritance_valid: bool
    violations: List[Issue] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    policy_id: str
    status: PolicyStatus
    timestamp: str
    analyzer_version: str
    summary: Summary
    rules_analyzed: List[RuleAnalyzed] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    inheritance_check: Optional[InheritanceCheck] = None


# =============================================================================
# REPORT GENERATOR
# =============================================================================

class ReportGenerator:
    """
    Generate analysis reports in multiple formats.
    
    Implements the approved Output Design Specification:
    - Clear, Actionable, Concise
    - No verbose explanations
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._start_time: Optional[float] = None
    
    def start_analysis(self):
        """Mark analysis start time"""
        self._start_time = time.time()
    
    def _get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds"""
        if self._start_time is None:
            return 0
        return int((time.time() - self._start_time) * 1000)
    
    # =========================================================================
    # MAIN GENERATION
    # =========================================================================
    
    def generate(
        self,
        policy: Policy,
        conflicts: List[Conflict],
        inheritance_violations: Optional[List[InheritanceViolation]] = None,
        parent_policy_id: Optional[str] = None
    ) -> AnalysisResult:
        """
        Generate complete analysis result.
        
        Args:
            policy: Analyzed policy
            conflicts: Detected conflicts
            inheritance_violations: Optional inheritance check results
            parent_policy_id: Parent policy ID if inheritance check
            
        Returns:
            AnalysisResult ready for formatting
        """
        # Convert conflicts to issues
        issues = self._conflicts_to_issues(conflicts, policy)
        
        # Add inheritance violations
        if inheritance_violations:
            issues.extend(self._inheritance_to_issues(
                inheritance_violations, parent_policy_id, policy.id
            ))
        
        # Calculate summary
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        
        # Determine status
        if errors > 0:
            status = PolicyStatus.INVALID
        elif warnings > 0:
            status = PolicyStatus.WARNING
        else:
            status = PolicyStatus.VALID
        
        # Analyze rules
        rules_analyzed = self._analyze_rules(policy, issues)
        
        # Build inheritance check result
        inheritance_check = None
        if inheritance_violations is not None:
            hard_violations = [v for v in inheritance_violations 
                             if v.violation_type != 'redundant']
            inheritance_check = InheritanceCheck(
                parent_policy_id=parent_policy_id or "unknown",
                child_policy_id=policy.id,
                inheritance_valid=len(hard_violations) == 0,
                violations=[i for i in issues if i.type == IssueType.EXPANSION 
                           or i.type == IssueType.NEW_ACTION]
            )
        
        return AnalysisResult(
            policy_id=policy.id,
            status=status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            analyzer_version=self.VERSION,
            summary=Summary(
                total_rules=len(policy.rules),
                total_constraints=len(policy.constraints),
                consistent=errors == 0,
                inheritance_valid=inheritance_check.inheritance_valid if inheritance_check else None,
                errors=errors,
                warnings=warnings,
                analysis_time_ms=self._get_elapsed_ms()
            ),
            rules_analyzed=rules_analyzed,
            issues=issues,
            inheritance_check=inheritance_check
        )
    
    # =========================================================================
    # CONFLICT → ISSUE CONVERSION
    # =========================================================================
    
    def _conflicts_to_issues(self, conflicts: List[Conflict], policy: Policy) -> List[Issue]:
        """Convert Conflict objects to Issue objects"""
        issues = []
        
        for i, conflict in enumerate(conflicts, 1):
            issue = self._conflict_to_issue(conflict, policy, f"issue-{i:03d}")
            if issue:
                issues.append(issue)
        
        # Sort: errors first, then warnings
        issues.sort(key=lambda x: (0 if x.severity == Severity.ERROR else 1, x.type.value))
        
        return issues
    
    def _conflict_to_issue(self, conflict: Conflict, policy: Policy, issue_id: str) -> Optional[Issue]:
        """Convert single Conflict to Issue"""
        
        # Map conflict types to issue types
        type_map = {
            'permission_prohibition': IssueType.PERMISSION_PROHIBITION_CONFLICT,
            'duty_prohibition': IssueType.DUTY_PROHIBITION_CONFLICT,
            'xone_overlap': IssueType.XONE_VIOLATION,
            'xone_unsatisfiable': IssueType.XONE_VIOLATION,
            'xone_trivial': IssueType.XONE_VIOLATION,
            'and_contradiction': IssueType.INCONSISTENCY,
            'or_unsatisfiable': IssueType.INCONSISTENCY,
            'unsatisfiable': IssueType.INCONSISTENCY,
            'tautology': IssueType.TAUTOLOGY,
            'unreachable_permission': IssueType.UNREACHABLE,
            'permission_subsumption': IssueType.REDUNDANCY,
            'prohibition_redundancy': IssueType.REDUNDANCY,
            'permission_ambiguity': IssueType.REDUNDANCY,
            'duty_incompatibility': IssueType.INCONSISTENCY,
        }
        
        issue_type = type_map.get(conflict.conflict_type)
        if not issue_type:
            # Unknown type, create generic issue
            issue_type = IssueType.INCONSISTENCY
        
        # Map severity
        severity_map = {
            ConflictSeverity.CRITICAL: Severity.ERROR,
            ConflictSeverity.WARNING: Severity.WARNING,
            ConflictSeverity.INFO: Severity.INFO,
        }
        severity = severity_map.get(conflict.severity, Severity.ERROR)
        
        # Build constraint expressions
        constraints = []
        for cid in conflict.constraint_ids:
            constraint = policy.constraints.get(cid)
            if constraint and isinstance(constraint, AtomicConstraint):
                constraints.append(ConstraintExpr(
                    id=cid,
                    left_operand=constraint.left_operand,
                    operator=OP_SYMBOLS.get(constraint.operator, str(constraint.operator)),
                    right_operand=constraint.right_value.canonical_value
                ))
        
        # Build message (concise)
        message = self._build_message(conflict, constraints)
        
        # Create issue based on type
        issue = Issue(
            id=issue_id,
            type=issue_type,
            severity=severity,
            message=message,
            constraint_ids=conflict.constraint_ids,
            constraints=constraints,
            counterexample=conflict.counterexample,
            action=conflict.action if conflict.action != 'none' else None,
        )
        
        # Add type-specific fields
        if issue_type == IssueType.PERMISSION_PROHIBITION_CONFLICT:
            # Extract permission and prohibition IDs from constraint IDs
            if len(conflict.constraint_ids) >= 2:
                issue.permission_id = conflict.constraint_ids[0]
                issue.prohibition_id = conflict.constraint_ids[1]
                if len(constraints) >= 2:
                    issue.permission_constraint = constraints[0].to_string()
                    issue.prohibition_constraint = constraints[1].to_string()
        
        elif issue_type == IssueType.XONE_VIOLATION:
            issue.expected_count = 1
            issue.satisfied_count = conflict.metadata.get('overlapping_pairs', 2) if conflict.metadata else 2
            issue.satisfied_constraints = [c.to_string() for c in constraints]
        
        elif issue_type == IssueType.REDUNDANCY:
            if len(constraints) >= 2:
                issue.redundant_constraint = constraints[1].to_string()
                issue.implied_by = constraints[0].to_string()
                issue.suggestion = f"Remove {conflict.constraint_ids[1]}"
        
        return issue
    
    def _inheritance_to_issues(
        self, 
        violations: List[InheritanceViolation],
        parent_id: Optional[str],
        child_id: str
    ) -> List[Issue]:
        """Convert InheritanceViolation to Issue"""
        issues = []
        
        for i, v in enumerate(violations, 1):
            if v.violation_type == 'expansion':
                issue_type = IssueType.EXPANSION
                severity = Severity.ERROR
            elif v.violation_type == 'new_action':
                issue_type = IssueType.NEW_ACTION
                severity = Severity.ERROR
            elif v.violation_type == 'inconsistent':
                issue_type = IssueType.INCONSISTENCY
                severity = Severity.ERROR
            elif v.violation_type == 'redundant':
                issue_type = IssueType.REDUNDANCY
                severity = Severity.WARNING
            else:
                continue
            
            # Build counterexample with explanation
            counterexample = v.counterexample or {}
            if counterexample:
                counterexample['explanation'] = f"Child allows values parent forbids"
            
            issues.append(Issue(
                id=f"inherit-{i:03d}",
                type=issue_type,
                severity=severity,
                message=v.description,
                parent_policy_id=v.parent_id,
                child_policy_id=v.child_id,
                counterexample=counterexample,
                action=v.action,
            ))
        
        return issues
    
    def _build_message(self, conflict: Conflict, constraints: List[ConstraintExpr]) -> str:
        """Build concise message for issue"""
        if constraints:
            parts = [c.to_string() for c in constraints[:3]]  # Max 3
            return " AND ".join(parts)
        return conflict.description[:100]  # Truncate if needed
    
    def _analyze_rules(self, policy: Policy, issues: List[Issue]) -> List[RuleAnalyzed]:
        """Analyze each rule's status"""
        rules = []
        
        # Build map of rule_id -> issues
        rule_issues: Dict[str, List[Issue]] = {}
        for issue in issues:
            if issue.rule_id:
                rule_issues.setdefault(issue.rule_id, []).append(issue)
        
        for rule in policy.rules:
            rule_id = rule.id
            
            # Determine status
            if rule_id in rule_issues:
                rule_issue_list = rule_issues[rule_id]
                if any(i.severity == Severity.ERROR for i in rule_issue_list):
                    if any(i.type == IssueType.INCONSISTENCY for i in rule_issue_list):
                        status = "INCONSISTENT"
                    else:
                        status = "CONFLICT"
                else:
                    status = "WARNING"
            else:
                status = "OK"
            
            rules.append(RuleAnalyzed(
                rule_id=rule_id,
                rule_type=rule.rule_type.value if isinstance(rule.rule_type, PolicyRuleType) else str(rule.rule_type),
                action=rule.action,
                target=getattr(rule, 'target', None),
                constraint_count=1 if rule.constraint_id else 0,
                status=status
            ))
        
        return rules
    
    # =========================================================================
    # OUTPUT FORMATTERS
    # =========================================================================
    
    def format_json(self, result: AnalysisResult, indent: int = 2) -> str:
        """Format result as JSON"""
        
        def convert(obj):
            """Convert dataclasses and enums to dict"""
            if isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dataclass_fields__'):
                d = {}
                for k, v in asdict(obj).items():
                    # Convert snake_case to camelCase for JSON
                    if v is not None:
                        d[k] = convert(v)
                return d
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items() if v is not None}
            return obj
        
        data = convert(result)
        return json.dumps(data, indent=indent, default=str)
    
    def format_cli(self, result: AnalysisResult, verbose: bool = False) -> str:
        """Format result as CLI output"""
        lines = []
        
        # Header
        status_icon = self._status_icon(result.status)
        lines.append(f"Policy: {result.policy_id}")
        lines.append(f"Status: {result.status.value} {status_icon}")
        lines.append("")
        
        # Issues
        if result.issues:
            lines.append("Issues:")
            lines.append("━" * 60)
            
            for issue in result.issues:
                lines.append(self._format_issue_cli(issue, verbose))
                lines.append("━" * 60)
        
        # Summary
        lines.append("")
        lines.append("Summary:")
        lines.append(f"  Errors:   {result.summary.errors}")
        lines.append(f"  Warnings: {result.summary.warnings}")
        lines.append(f"  Total constraints analyzed: {result.summary.total_constraints}")
        lines.append(f"  Analysis time: {result.summary.analysis_time_ms / 1000:.2f}s")
        
        return "\n".join(lines)
    
    def format_cli_compact(self, result: AnalysisResult) -> str:
        """Format minimal CLI output"""
        status_icon = self._status_icon(result.status)
        
        if result.status == PolicyStatus.VALID:
            return f"Policy: {result.policy_id}\nStatus: VALID ✓\nAnalysis time: {result.summary.analysis_time_ms}ms"
        
        lines = [
            f"Policy: {result.policy_id}",
            f"Status: {result.status.value} {status_icon}",
            f"Errors: {result.summary.errors}, Warnings: {result.summary.warnings}"
        ]
        
        # Show first error only
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        if errors:
            lines.append(f"First error: {errors[0].type.value} - {errors[0].message[:50]}...")
        
        return "\n".join(lines)
    
    def _format_issue_cli(self, issue: Issue, verbose: bool) -> str:
        """Format single issue for CLI"""
        icon = "❌" if issue.severity == Severity.ERROR else "⚠️" if issue.severity == Severity.WARNING else "ℹ️"
        
        lines = [f"[{issue.severity.value}] {issue.type.value}"]
        
        if issue.rule_id:
            lines[0] += f" in {issue.rule_id}"
        
        if issue.action:
            lines.append(f"  Action: {issue.action}")
        
        # Type-specific formatting
        if issue.type == IssueType.INCONSISTENCY:
            if issue.constraints:
                lines.append("  Constraints:")
                for i, c in enumerate(issue.constraints):
                    prefix = "├─" if i < len(issue.constraints) - 1 else "└─"
                    lines.append(f"  {prefix} {c.to_string()}")
            if issue.counterexample:
                explanation = issue.counterexample.get('explanation', 'impossible')
                lines.append(f"  → {explanation}")
        
        elif issue.type == IssueType.PERMISSION_PROHIBITION_CONFLICT:
            lines.append(f"  Permission: {issue.permission_id}")
            lines.append(f"  Prohibition: {issue.prohibition_id}")
            lines.append("")
            lines.append("  Overlap:")
            if issue.permission_constraint:
                lines.append(f"  ├─ Permission:  {issue.permission_constraint}")
            if issue.prohibition_constraint:
                lines.append(f"  └─ Prohibition: {issue.prohibition_constraint}")
            if issue.counterexample:
                lines.append("")
                lines.append("  Counterexample:")
                for k, v in issue.counterexample.items():
                    if k != 'explanation':
                        lines.append(f"  └─ {k} = {v} → both satisfied ⚠️")
        
        elif issue.type == IssueType.XONE_VIOLATION:
            lines.append(f"  Expected: exactly {issue.expected_count} constraint satisfied")
            lines.append(f"  Actual: {issue.satisfied_count} satisfied")
            if issue.satisfied_constraints:
                lines.append("")
                lines.append("  Both satisfied:")
                for c in issue.satisfied_constraints:
                    lines.append(f"  • {c}")
            if issue.counterexample:
                lines.append("")
                lines.append("  When:")
                for k, v in issue.counterexample.items():
                    if k != 'explanation':
                        lines.append(f"  └─ {k} = {v}")
        
        elif issue.type == IssueType.EXPANSION:
            lines.append(f"  Parent: {issue.parent_policy_id}")
            lines.append(f"  Child:  {issue.child_policy_id}")
            if issue.parent_constraint:
                lines.append(f"  Parent constraint: {issue.parent_constraint}")
            if issue.child_constraint:
                lines.append(f"  Child constraint:  {issue.child_constraint}")
            if issue.counterexample:
                lines.append("")
                lines.append("  Counterexample:")
                for k, v in issue.counterexample.items():
                    lines.append(f"  └─ {k} = {v}")
                lines.append("  → Child allows value parent doesn't")
        
        elif issue.type == IssueType.REDUNDANCY:
            if issue.redundant_constraint:
                lines.append(f"  Redundant:  {issue.redundant_constraint}")
            if issue.implied_by:
                lines.append(f"  Implied by: {issue.implied_by}")
            if issue.suggestion:
                lines.append(f"  → Suggestion: {issue.suggestion}")
        
        else:
            # Generic format
            lines.append(f"  {issue.message}")
            if issue.counterexample and verbose:
                lines.append("  Counterexample:")
                for k, v in issue.counterexample.items():
                    lines.append(f"    {k} = {v}")
        
        return "\n".join(lines)
    
    def _status_icon(self, status: PolicyStatus) -> str:
        """Get status icon"""
        return {
            PolicyStatus.VALID: "✓",
            PolicyStatus.INVALID: "❌",
            PolicyStatus.WARNING: "⚠️"
        }.get(status, "?")
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    def print_cli(self, result: AnalysisResult, verbose: bool = False):
        """Print CLI output to stdout"""
        print(self.format_cli(result, verbose))
    
    def save_json(self, result: AnalysisResult, filepath: str):
        """Save JSON output to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.format_json(result))
    
    def generate_and_print(
        self,
        policy: Policy,
        conflicts: List[Conflict],
        format: str = "cli",
        verbose: bool = False,
        inheritance_violations: Optional[List[InheritanceViolation]] = None,
        parent_policy_id: Optional[str] = None
    ):
        """Generate report and print immediately"""
        result = self.generate(
            policy, conflicts, inheritance_violations, parent_policy_id
        )
        
        if format == "json":
            print(self.format_json(result))
        elif format == "cli":
            print(self.format_cli(result, verbose))
        elif format == "compact":
            print(self.format_cli_compact(result))
        else:
            print(self.format_cli(result, verbose))


# =============================================================================
# QUICK ACCESS FUNCTIONS
# =============================================================================

def generate_report(
    policy: Policy,
    conflicts: List[Conflict],
    format: str = "cli",
    verbose: bool = False
) -> str:
    """Quick function to generate report string"""
    generator = ReportGenerator()
    result = generator.generate(policy, conflicts)
    
    if format == "json":
        return generator.format_json(result)
    elif format == "compact":
        return generator.format_cli_compact(result)
    else:
        return generator.format_cli(result, verbose)


def print_report(
    policy: Policy,
    conflicts: List[Conflict],
    format: str = "cli",
    verbose: bool = False
):
    """Quick function to print report"""
    print(generate_report(policy, conflicts, format, verbose))