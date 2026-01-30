# src/analyzer/__init__.py
"""
ODRL-SA Analyzer Module

Provides comprehensive policy analysis with multi-level conflict detection:
  - Level 1: Constraint-level (tautology, domain violation)
  - Level 2: Rule-level (internal conflicts, redundancy)
  - Level 3: Policy-level (deontic conflicts)
  - Level 4: Inheritance-level (parent-child conflicts)

Usage:
    from analyzer import PolicyAnalyzer, PolicyAnalysis
    
    analyzer = PolicyAnalyzer(verbose=True)
    result = analyzer.analyze_file("policy.ttl")
    
    if result.overall_judgment != "CONSISTENT":
        for conflict in result.conflicts:
            print(f"[{conflict.level.value}] {conflict.description}")
"""

from .policy_analyzer import (
    # Enums
    ConflictLevel,
    ConflictType,
    Severity,
    
    # Data classes
    Conflict,
    RuleAnalysis,
    InheritanceInfo,
    PolicyAnalysis,
    
    # Functions
    resolve_inheritance_in_file,
    
    # Main class
    PolicyAnalyzer,
)

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

__version__ = '1.0.0'