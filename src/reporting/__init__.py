# src/reporting/__init__.py
"""
ODRL Policy Analysis Reporting Module

Provides clean, actionable output in multiple formats:
- JSON: Machine-readable
- CLI: Human-readable compact
- CLI Verbose: Human-readable detailed
"""

from .report_generator import (
    ReportGenerator,
    AnalysisResult,
    Issue,
    Summary,
    PolicyStatus,
    IssueType,
    Severity,
    ConstraintExpr,
    RuleAnalyzed,
    InheritanceCheck,
    generate_report,
    print_report,
)

__all__ = [
    'ReportGenerator',
    'AnalysisResult',
    'Issue',
    'Summary',
    'PolicyStatus',
    'IssueType',
    'Severity',
    'ConstraintExpr',
    'RuleAnalyzed',
    'InheritanceCheck',
    'generate_report',
    'print_report',
]