#!/usr/bin/env python3
"""
ODRL-SA Policy Analyzer - Main Entry Point

Usage:
    uv run python main.py policy.ttl              # Basic analysis
    uv run python main.py policy.ttl -v           # Verbose output
    uv run python main.py policy.ttl -d           # Debug mode (shows Z3 formulas)
    uv run python main.py policy.ttl -vd          # Verbose + Debug
    uv run python main.py policy.ttl --json       # JSON output
    uv run python main.py tests/ttl/percentage/   # Analyze directory

Output Modes:
    default  - Clean summary
    -v       - Verbose (shows constraints, model)
    -d       - Debug (shows Z3 encoding, formulas)
    --json   - Machine-readable JSON
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parser import parse_ttl_file
from encoder import Z3JudgmentEngine
from core.constraint_types import (
    AtomicConstraint, 
    CompositeConstraint, 
    LogicalOperator,
    Judgment,
    Constraint,
)

from z3 import Solver, And, Or, Not, sat, unsat


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AnalysisResult:
    """Result of policy analysis."""
    file: str
    judgment: str
    model: Optional[Dict[str, Any]]
    constraints_count: int
    atomic_count: int
    composite_count: int
    policies_count: int
    parse_errors: List[str]
    parse_warnings: List[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# CORE ANALYSIS ENGINE
# =============================================================================

class PolicyAnalyzer:
    """
    ODRL Policy Analyzer with composite constraint support.
    """
    
    def __init__(self, debug: bool = False, verbose: bool = False):
        self.debug = debug
        self.verbose = verbose
        self.engine = Z3JudgmentEngine()
    
    def analyze_file(self, filepath: str) -> AnalysisResult:
        """Analyze a single TTL file."""
        filepath = Path(filepath)
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"ANALYZING: {filepath.name}")
            print(f"{'='*60}")
        
        # Parse
        result = parse_ttl_file(str(filepath))
        
        if result.errors:
            if self.verbose:
                print(f"\n⚠️  Parse errors:")
                for e in result.errors:
                    print(f"    {e}")
        
        if not result.policies:
            return AnalysisResult(
                file=str(filepath),
                judgment="ERROR",
                model=None,
                constraints_count=0,
                atomic_count=0,
                composite_count=0,
                policies_count=0,
                parse_errors=result.errors or ["No policies found"],
                parse_warnings=result.warnings or []
            )
        
        # Get constraint counts
        atomics = [c for c in result.constraints.values() if isinstance(c, AtomicConstraint)]
        composites = [c for c in result.constraints.values() if isinstance(c, CompositeConstraint)]
        
        if self.verbose:
            print(f"\n📋 Parsed:")
            print(f"    Policies: {len(result.policies)}")
            print(f"    Constraints: {len(result.constraints)} ({len(atomics)} atomic, {len(composites)} composite)")
        
        # Get top-level constraint IDs
        top_level_ids = []
        for policy in result.policies:
            for rule in policy.rules:
                top_level_ids.extend(rule.constraint_ids)
        
        if self.verbose:
            print(f"    Top-level: {top_level_ids}")
            print(f"\n📊 Constraints:")
            for uid, c in result.constraints.items():
                if isinstance(c, AtomicConstraint):
                    print(f"    [A] {uid}: {c.left_operand} {c.operator.value} {c.right_operand.value}")
                elif isinstance(c, CompositeConstraint):
                    print(f"    [C] {uid}: {c.operator.value}({list(c.operands)})")
        
        # Analyze
        judgment, model = self._check_consistency(result.constraints, top_level_ids)
        
        return AnalysisResult(
            file=str(filepath),
            judgment=judgment.value,
            model=model,
            constraints_count=len(result.constraints),
            atomic_count=len(atomics),
            composite_count=len(composites),
            policies_count=len(result.policies),
            parse_errors=result.errors or [],
            parse_warnings=result.warnings or []
        )
    
    def _check_consistency(
        self, 
        constraints: Dict[str, Constraint],
        top_level_ids: List[str]
    ) -> Tuple[Judgment, Optional[Dict]]:
        """Check consistency with proper composite handling."""
        
        if not constraints:
            return Judgment.POSSIBLY_COMPATIBLE, {}
        
        if not top_level_ids:
            # No top-level - check all atomics
            atomics = [c for c in constraints.values() if isinstance(c, AtomicConstraint)]
            from encoder import check_consistency
            return check_consistency(atomics)
        
        # Reset variable manager
        self.engine.var_manager.clear()
        
        def encode_constraint(uid: str) -> Any:
            """Recursively encode a constraint."""
            if uid not in constraints:
                if self.debug:
                    print(f"    ⚠️  Unknown UID: {uid}")
                return None
            
            c = constraints[uid]
            
            if isinstance(c, AtomicConstraint):
                formula = self.engine.constraint_encoder.encode(c)
                if self.debug:
                    print(f"    [A] {uid}: {c.left_operand} {c.operator.value} {c.right_operand.value}")
                    print(f"        → {formula}")
                return formula
                
            elif isinstance(c, CompositeConstraint):
                child_formulas = []
                for child_uid in c.operands:
                    child_formula = encode_constraint(child_uid)
                    if child_formula is not None:
                        child_formulas.append(child_formula)
                
                if not child_formulas:
                    return None
                
                # Apply logical operator
                if c.operator == LogicalOperator.AND:
                    formula = And(*child_formulas)
                elif c.operator == LogicalOperator.OR:
                    formula = Or(*child_formulas)
                elif c.operator == LogicalOperator.XONE:
                    n = len(child_formulas)
                    if n == 1:
                        formula = child_formulas[0]
                    else:
                        at_least_one = Or(*child_formulas)
                        at_most_one = []
                        for i in range(n):
                            for j in range(i + 1, n):
                                at_most_one.append(Not(And(child_formulas[i], child_formulas[j])))
                        formula = And(at_least_one, And(*at_most_one))
                elif c.operator == LogicalOperator.AND_SEQUENCE:
                    formula = And(*child_formulas)
                else:
                    formula = And(*child_formulas)
                
                if self.debug:
                    print(f"    [C] {uid}: {c.operator.value}({list(c.operands)})")
                    print(f"        → {formula}")
                
                return formula
            
            return None
        
        # Encode top-level constraints
        if self.debug:
            print(f"\n🔧 Encoding constraints:")
        
        top_formulas = []
        for uid in top_level_ids:
            formula = encode_constraint(uid)
            if formula is not None:
                top_formulas.append(formula)
        
        if not top_formulas:
            return Judgment.UNKNOWN, None
        
        # Combine (AND all top-level)
        full_formula = And(*top_formulas) if len(top_formulas) > 1 else top_formulas[0]
        
        # Get domain constraints
        domain_constraints = self.engine.var_manager.get_domain_constraints()
        
        if self.debug:
            print(f"\n📐 Final formula: {full_formula}")
            print(f"📐 Domain constraints: {domain_constraints}")
        
        # Solve
        solver = Solver()
        solver.add(full_formula)
        for dc in domain_constraints:
            solver.add(dc)
        
        if self.debug:
            print(f"\n🧮 Solving...")
        
        result = solver.check()
        
        if result == unsat:
            if self.debug or self.verbose:
                print(f"\n❌ Result: UNSAT → CONFLICT")
            return Judgment.CONFLICT, None
        
        elif result == sat:
            model = {}
            for decl in solver.model().decls():
                val = solver.model()[decl]
                try:
                    if hasattr(val, 'as_long'):
                        model[decl.name()] = val.as_long()
                    elif hasattr(val, 'as_decimal'):
                        model[decl.name()] = float(val.as_decimal(10).rstrip('?'))
                    else:
                        model[decl.name()] = str(val)
                except:
                    model[decl.name()] = str(val)
            
            if self.debug or self.verbose:
                print(f"\n✅ Result: SAT → POSSIBLY-COMPATIBLE")
                print(f"   Model: {model}")
            
            return Judgment.POSSIBLY_COMPATIBLE, model
        
        else:
            if self.debug or self.verbose:
                print(f"\n⚠️  Result: UNKNOWN")
            return Judgment.UNKNOWN, None


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_result(result: AnalysisResult, verbose: bool = False) -> str:
    """Format analysis result for CLI output."""
    lines = []
    
    # Header
    filename = Path(result.file).name
    
    # Judgment with emoji
    if result.judgment == "CONFLICT":
        emoji = "❌"
    elif result.judgment == "POSSIBLY-COMPATIBLE":
        emoji = "✅"
    else:
        emoji = "⚠️"
    
    lines.append(f"{emoji} {filename}: {result.judgment}")
    
    if verbose:
        lines.append(f"   Constraints: {result.constraints_count} ({result.atomic_count} atomic, {result.composite_count} composite)")
        if result.model:
            lines.append(f"   Model: {result.model}")
        if result.parse_warnings:
            for w in result.parse_warnings:
                lines.append(f"   ⚠️  {w}")
    
    return "\n".join(lines)


def format_json(results: List[AnalysisResult]) -> str:
    """Format results as JSON."""
    if len(results) == 1:
        return json.dumps(results[0].to_dict(), indent=2)
    return json.dumps([r.to_dict() for r in results], indent=2)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ODRL-SA Policy Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s policy.ttl                 Analyze single file
  %(prog)s policy.ttl -v              Verbose output
  %(prog)s policy.ttl -d              Debug mode (Z3 formulas)
  %(prog)s tests/ttl/percentage/      Analyze directory
  %(prog)s policy.ttl --json          JSON output
        """
    )
    
    parser.add_argument('path', help='TTL file or directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode (show Z3 encoding)')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    
    args = parser.parse_args()
    
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
    
    # Analyze
    analyzer = PolicyAnalyzer(debug=args.debug, verbose=args.verbose)
    results = []
    
    for f in files:
        result = analyzer.analyze_file(str(f))
        results.append(result)
    
    # Output
    if args.json:
        print(format_json(results))
    else:
        for result in results:
            print(format_result(result, verbose=args.verbose))
        
        # Summary for multiple files
        if len(results) > 1 or args.summary:
            print(f"\n{'─'*40}")
            conflicts = sum(1 for r in results if r.judgment == "CONFLICT")
            compatible = sum(1 for r in results if r.judgment == "POSSIBLY-COMPATIBLE")
            unknown = sum(1 for r in results if r.judgment not in ("CONFLICT", "POSSIBLY-COMPATIBLE"))
            print(f"Summary: {len(results)} files")
            print(f"  ❌ CONFLICT: {conflicts}")
            print(f"  ✅ COMPATIBLE: {compatible}")
            if unknown:
                print(f"  ⚠️  UNKNOWN: {unknown}")
    
    # Return code
    has_errors = any(r.parse_errors for r in results)
    
    return 1 if has_errors else 0


if __name__ == '__main__':
    sys.exit(main())