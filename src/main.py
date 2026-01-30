#!/usr/bin/env python3
# src/main.py
"""
ODRL-SA Policy Analyzer - Command Line Interface

Multi-level conflict detection:
  Level 1: Constraint-level (tautology, domain violation)
  Level 2: Rule-level (internal conflicts, redundancy)
  Level 3: Policy-level (deontic conflicts: permission vs prohibition, duty vs prohibition)
  Level 4: Inheritance-level (child contradicts parent)

Usage:
    uv run python main.py policy.ttl                    # Basic analysis
    uv run python main.py policy.ttl -v                 # Verbose (show all levels)
    uv run python main.py policy.ttl -d                 # Debug (show Z3 formulas)
    uv run python main.py policy.ttl --show-policy      # Show policy structure
    uv run python main.py policy.ttl --show-normalize   # Show normalization
    uv run python main.py policy.ttl --all              # Show everything
    uv run python main.py tests/ttl/percentage/         # Analyze directory
    uv run python main.py policy.ttl --json             # JSON output
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import from analyzer module
from src.analyzer import (
    PolicyAnalyzer,
    PolicyAnalysis,
    ConflictLevel,
    ConflictType,
    Severity,
)


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_summary(result: PolicyAnalysis) -> str:
    """Format single-line summary."""
    filename = Path(result.file).name
    
    status_map = {
        "INHERITANCE-CONFLICT": "[INHERITANCE]",
        "INTERNAL-CONFLICT": "[CONFLICT]",
        "DEONTIC-CONFLICT": "[DEONTIC]",
        "CONSTRAINT-ERROR": "[CONSTRAINT]",
        "CONSISTENT-WITH-WARNINGS": "[WARNING]",
        "CONSISTENT": "[OK]",
        "UNKNOWN": "[UNKNOWN]",
        "ERROR": "[ERROR]",
    }
    status = status_map.get(result.overall_judgment, "[???]")
    
    return f"{status} {filename}: {result.overall_judgment}"


def format_detailed(result: PolicyAnalysis) -> str:
    """Format detailed output."""
    lines = [format_summary(result)]
    
    lines.append(f"   Policy: {result.policy_id} ({result.policy_type})")
    
    # Show inheritance info
    if result.inherits_from:
        lines.append(f"   Inherits from: {result.inherits_from}")
        if result.inheritance_info:
            lines.append(f"   [Inheritance resolved - constraints merged]")
    
    lines.append(f"   Constraints: {result.total_constraints} ({result.atomic_constraints} atomic, {result.composite_constraints} composite)")
    
    # Show rules
    if result.permissions:
        lines.append(f"   Permissions: {len(result.permissions)}")
        for p in result.permissions:
            status = "[CONFLICT]" if p.judgment == "CONFLICT" else "[OK]"
            lines.append(f"     {status} {p.rule_id} ({p.action}): {p.judgment}")
    
    if result.prohibitions:
        lines.append(f"   Prohibitions: {len(result.prohibitions)}")
        for p in result.prohibitions:
            status = "[CONFLICT]" if p.judgment == "CONFLICT" else "[OK]"
            lines.append(f"     {status} {p.rule_id} ({p.action}): {p.judgment}")
    
    if result.duties:
        lines.append(f"   Duties: {len(result.duties)}")
        for d in result.duties:
            status = "[CONFLICT]" if d.judgment == "CONFLICT" else "[OK]"
            lines.append(f"     {status} {d.rule_id} ({d.action}): {d.judgment}")
    
    # Show conflicts by level
    if result.conflicts:
        # Group by level
        by_level = {}
        for c in result.conflicts:
            by_level.setdefault(c.level, []).append(c)
        
        # Deontic conflicts (Level 3)
        deontic = by_level.get(ConflictLevel.POLICY, [])
        if deontic:
            lines.append(f"   Deontic Conflicts: {len(deontic)}")
            for c in deontic:
                lines.append(f"     {c.location}: {c.conflict_type.value}")
                if c.witness:
                    lines.append(f"       Witness: {c.witness}")
        
        # Inheritance conflicts (Level 4)
        inheritance = by_level.get(ConflictLevel.INHERITANCE, [])
        if inheritance:
            lines.append(f"   Inheritance Conflicts: {len(inheritance)}")
            for c in inheritance:
                lines.append(f"     {c.location}")
                lines.append(f"       {c.description}")
    
    return "\n".join(lines)


def format_conflicts_detail(result: PolicyAnalysis) -> str:
    """Format detailed conflict information."""
    if not result.conflicts:
        return ""
    
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append("CONFLICT DETAILS")
    lines.append(f"{'='*60}")
    
    # Group by level
    for level in [ConflictLevel.CONSTRAINT, ConflictLevel.RULE, 
                  ConflictLevel.POLICY, ConflictLevel.INHERITANCE]:
        level_conflicts = [c for c in result.conflicts if c.level == level]
        if not level_conflicts:
            continue
        
        lines.append(f"\n[LEVEL: {level.value.upper()}]")
        lines.append(f"{'-'*40}")
        
        for i, c in enumerate(level_conflicts, 1):
            severity_icon = "❌" if c.severity == Severity.ERROR else "⚠️"
            lines.append(f"\n  {severity_icon} Conflict #{i}: {c.conflict_type.value}")
            lines.append(f"     Location: {c.location}")
            lines.append(f"     Description: {c.description}")
            if c.constraint_ids:
                lines.append(f"     Constraints: {c.constraint_ids}")
            if c.witness:
                lines.append(f"     Witness: {c.witness}")
            if c.fix_suggestion:
                lines.append(f"     Fix: {c.fix_suggestion}")
    
    return "\n".join(lines)


def print_summary(results: List[PolicyAnalysis]):
    """Print summary for multiple files."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    # Count by judgment
    judgments = {}
    for r in results:
        judgments[r.overall_judgment] = judgments.get(r.overall_judgment, 0) + 1
    
    print(f"  Total files: {len(results)}")
    
    # Print in order
    order = [
        ("CONSISTENT", "[OK]"),
        ("CONSISTENT-WITH-WARNINGS", "[WARNING]"),
        ("CONSTRAINT-ERROR", "[CONSTRAINT]"),
        ("INTERNAL-CONFLICT", "[CONFLICT]"),
        ("DEONTIC-CONFLICT", "[DEONTIC]"),
        ("INHERITANCE-CONFLICT", "[INHERITANCE]"),
        ("UNKNOWN", "[UNKNOWN]"),
        ("ERROR", "[ERROR]"),
    ]
    
    for judgment, label in order:
        count = judgments.get(judgment, 0)
        if count > 0:
            print(f"  {label} {judgment}: {count}")
    
    # Conflict breakdown
    total_conflicts = sum(len(r.conflicts) for r in results)
    if total_conflicts > 0:
        print(f"\n  Total conflicts detected: {total_conflicts}")
        
        # By level
        by_level = {level: 0 for level in ConflictLevel}
        for r in results:
            for c in r.conflicts:
                by_level[c.level] += 1
        
        for level in ConflictLevel:
            if by_level[level] > 0:
                print(f"    - {level.value}: {by_level[level]}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ODRL-SA Policy Analyzer - Multi-Level Conflict Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Conflict Levels:
  Level 1: Constraint - tautology, domain violation
  Level 2: Rule       - internal conflicts within a rule
  Level 3: Policy     - deontic conflicts (permission vs prohibition)
  Level 4: Inheritance- child policy contradicts parent

Examples:
  %(prog)s policy.ttl                    Basic analysis
  %(prog)s policy.ttl -v                 Verbose output (all levels)
  %(prog)s policy.ttl -d                 Debug mode (Z3 formulas)
  %(prog)s policy.ttl --show-policy      Show policy structure
  %(prog)s policy.ttl --all              All debug output
  %(prog)s tests/ttl/percentage/         Analyze directory
  %(prog)s policy.ttl --json             JSON output
        """
    )
    
    parser.add_argument('path', help='TTL file or directory')
    
    # Output modes
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='Verbose output (show all analysis levels)')
    parser.add_argument('-d', '--debug', action='store_true', 
                        help='Debug mode (show Z3 formulas)')
    parser.add_argument('--show-policy', action='store_true', 
                        help='Show policy structure')
    parser.add_argument('--show-normalize', action='store_true', 
                        help='Show normalization')
    parser.add_argument('--show-conflicts', action='store_true',
                        help='Show detailed conflict information')
    parser.add_argument('--all', action='store_true', 
                        help='Enable all output')
    parser.add_argument('--json', action='store_true', 
                        help='JSON output')
    parser.add_argument('--summary', action='store_true', 
                        help='Summary only (for directories)')
    
    # Inheritance control
    parser.add_argument('--no-inheritance', action='store_true',
                        help='Disable automatic inheritance resolution')
    
    args = parser.parse_args()
    
    # --all enables everything
    if args.all:
        args.verbose = True
        args.debug = True
        args.show_policy = True
        args.show_normalize = True
        args.show_conflicts = True
    
    path = Path(args.path)
    
    # Collect files
    if path.is_dir():
        files = sorted(path.glob('*.ttl'))
        if not files:
            print(f"No TTL files found in {path}")
            return 1
    elif path.is_file():
        files = [path]
    else:
        print(f"Path not found: {path}")
        return 1
    
    # Create analyzer
    analyzer = PolicyAnalyzer(
        verbose=args.verbose,
        debug=args.debug,
        show_policy=args.show_policy,
        show_normalize=args.show_normalize,
        resolve_inheritance=not args.no_inheritance
    )
    
    # Analyze all files
    results = []
    for f in files:
        result = analyzer.analyze_file(str(f))
        results.append(result)
    
    # =========================================================================
    # OUTPUT
    # =========================================================================
    
    if args.json:
        if len(results) == 1:
            print(json.dumps(results[0].to_dict(), indent=2, default=str))
        else:
            print(json.dumps([r.to_dict() for r in results], indent=2, default=str))
    else:
        for result in results:
            if args.verbose or len(files) == 1:
                print(format_detailed(result))
                if args.show_conflicts and result.conflicts:
                    print(format_conflicts_detail(result))
            else:
                print(format_summary(result))
        
        # Summary for multiple files
        if len(results) > 1:
            print_summary(results)
    
    # Return code
    has_errors = any(r.overall_judgment in (
        "INTERNAL-CONFLICT", 
        "DEONTIC-CONFLICT", 
        "INHERITANCE-CONFLICT",
        "CONSTRAINT-ERROR",
        "ERROR"
    ) for r in results)
    
    return 1 if has_errors else 0


if __name__ == '__main__':
    sys.exit(main())