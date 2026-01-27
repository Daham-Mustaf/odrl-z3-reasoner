# src/__init__.py
"""
ODRL-SA: ODRL Static Analyzer

A configuration-driven static analysis engine for ODRL policies.

Modules:
    config/      - YAML configuration files (operands, operators)
    registry/    - Configuration reader (OperandRegistry)
    core/        - Core types and classification
    normalizer/  - Value normalization
    encoder/     - Z3 SMT encoding
    parser/      - ODRL TTL parsing
    reasoner/    - Conflict detection and inheritance checking
    analyzer/    - Policy analysis and explanation
    reporting/   - Report generation
    grounding/   - Semantic oracles

Quick Start:
    from src.parser import parse_ttl_file
    from src.reasoner import ConflictDetector
    from src.reporting import generate_report
    
    result = parse_ttl_file("policy.ttl")
    policy = result.policies[0]
    constraints = {c.uid: c for c in result.constraints}
    
    detector = ConflictDetector()
    conflicts = detector.detect_all_conflicts(policy, constraints)
    
    print(generate_report(policy, conflicts, constraints))
"""

__version__ = "1.0.0"
__author__ = "ODRL-SA Team"

# Core exports
from .core import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
    Judgment,
    ConstraintClass,
    classify_constraint,
)

# Parser exports
from .parser import (
    parse_ttl_file,
    parse_ttl_string,
    ParseResult,
    Policy,
    Rule,
)

# Reasoner exports
from .reasoner import (
    ConflictDetector,
    Conflict,
    ConflictSeverity,
    InheritanceChecker,
    InheritanceViolation,
)

# Reporting exports
from .reporting import (
    ReportGenerator,
    generate_report,
    print_report,
    PolicyStatus,
)

__all__ = [
    # Version
    "__version__",
    
    # Core
    "AtomicConstraint",
    "CompositeConstraint",
    "OperatorType",
    "LogicalOperator",
    "Judgment",
    "ConstraintClass",
    "classify_constraint",
    
    # Parser
    "parse_ttl_file",
    "parse_ttl_string",
    "ParseResult",
    "Policy",
    "Rule",
    
    # Reasoner
    "ConflictDetector",
    "Conflict",
    "ConflictSeverity",
    "InheritanceChecker",
    "InheritanceViolation",
    
    # Reporting
    "ReportGenerator",
    "generate_report",
    "print_report",
    "PolicyStatus",
]