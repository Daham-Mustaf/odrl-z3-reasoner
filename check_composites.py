#!/usr/bin/env python3
"""
Enhanced Consistency Checker

Properly handles composite constraints (AND, OR, XONE) in addition to atomics.

The key insight: when a policy has composite constraints, we should NOT just
AND all atomic constraints together. Instead, we should:
1. Find the TOP-LEVEL constraint(s) referenced by rules
2. Recursively encode those, respecting AND/OR/XONE structure
3. Check satisfiability of the properly structured formula
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).parent / "src"))

from z3 import Solver, And, Or, Not, sat, unsat, IntVal, RealVal

from core.types import (
    AtomicConstraint, 
    CompositeConstraint, 
    LogicalOperator,
    Judgment,
    Constraint,
)
from encoder import Z3JudgmentEngine


def check_with_composites(
    constraints: Dict[str, Constraint],
    top_level_ids: List[str],
    debug: bool = False
) -> Tuple[Judgment, Optional[Dict]]:
    """
    Check consistency respecting composite structure.
    
    Args:
        constraints: Dict mapping uid -> Constraint (atomic or composite)
        top_level_ids: List of constraint UIDs that are directly referenced by rules
        debug: Print debug info
        
    Returns:
        (Judgment, model_or_none)
    """
    if not constraints:
        return Judgment.POSSIBLY_COMPATIBLE, {}
    
    if not top_level_ids:
        # No top-level constraints specified - check all atomics
        atomics = [c for c in constraints.values() if isinstance(c, AtomicConstraint)]
        from encoder import check_consistency
        return check_consistency(atomics)
    
    # Build encoder
    engine = Z3JudgmentEngine()
    engine.var_manager.clear()
    
    def encode_constraint(uid: str) -> Any:
        """Recursively encode a constraint by UID."""
        if uid not in constraints:
            if debug:
                print(f"  WARNING: Unknown constraint UID: {uid}")
            return None
        
        c = constraints[uid]
        
        if isinstance(c, AtomicConstraint):
            formula = engine.constraint_encoder.encode(c)
            if debug:
                print(f"  Encoded atomic {uid}: {formula}")
            return formula
            
        elif isinstance(c, CompositeConstraint):
            # Recursively encode children
            child_formulas = []
            for child_uid in c.operands:
                child_formula = encode_constraint(child_uid)
                if child_formula is not None:
                    child_formulas.append(child_formula)
            
            if not child_formulas:
                if debug:
                    print(f"  WARNING: Composite {uid} has no valid children")
                return None
            
            # Apply logical operator
            if c.operator == LogicalOperator.AND:
                formula = And(*child_formulas)
            elif c.operator == LogicalOperator.OR:
                formula = Or(*child_formulas)
            elif c.operator == LogicalOperator.XONE:
                # Exactly one: at least one AND at most one
                n = len(child_formulas)
                if n == 0:
                    formula = None
                elif n == 1:
                    formula = child_formulas[0]
                else:
                    at_least_one = Or(*child_formulas)
                    # At most one: no two are both true
                    at_most_one_clauses = []
                    for i in range(n):
                        for j in range(i + 1, n):
                            at_most_one_clauses.append(
                                Not(And(child_formulas[i], child_formulas[j]))
                            )
                    at_most_one = And(*at_most_one_clauses)
                    formula = And(at_least_one, at_most_one)
            elif c.operator == LogicalOperator.AND_SEQUENCE:
                # Treat as AND for static analysis
                formula = And(*child_formulas)
            else:
                formula = And(*child_formulas)
            
            if debug:
                print(f"  Encoded composite {uid} ({c.operator.value}): {formula}")
            return formula
        
        return None
    
    # Encode all top-level constraints
    if debug:
        print(f"\nEncoding {len(top_level_ids)} top-level constraints:")
    
    top_formulas = []
    for uid in top_level_ids:
        formula = encode_constraint(uid)
        if formula is not None:
            top_formulas.append(formula)
    
    if not top_formulas:
        if debug:
            print("  No valid formulas to check!")
        return Judgment.UNKNOWN, None
    
    # All top-level constraints must be satisfied (AND them)
    if len(top_formulas) == 1:
        full_formula = top_formulas[0]
    else:
        full_formula = And(*top_formulas)
    
    if debug:
        print(f"\nFinal formula: {full_formula}")
    
    # Get domain constraints
    domain_constraints = engine.var_manager.get_domain_constraints()
    if debug and domain_constraints:
        print(f"Domain constraints: {domain_constraints}")
    
    # Solve
    solver = Solver()
    solver.add(full_formula)
    for dc in domain_constraints:
        solver.add(dc)
    
    result = solver.check()
    
    if result == unsat:
        if debug:
            print("Result: UNSAT")
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
        if debug:
            print(f"Result: SAT - Model: {model}")
        return Judgment.POSSIBLY_COMPATIBLE, model
    else:
        if debug:
            print("Result: UNKNOWN")
        return Judgment.UNKNOWN, None


def analyze_policy_file(filepath: str, debug: bool = False):
    """Analyze a TTL file with proper composite handling."""
    from parser import parse_ttl_file
    
    print(f"\n{'='*60}")
    print(f"FILE: {Path(filepath).name}")
    print('='*60)
    
    result = parse_ttl_file(filepath)
    
    if not result.policies:
        print("ERROR: No policies found")
        return
    
    print(f"Policies: {len(result.policies)}")
    print(f"Constraints: {len(result.constraints)}")
    
    # Get top-level constraint IDs from rules
    top_level_ids = []
    for policy in result.policies:
        for rule in policy.rules:
            top_level_ids.extend(rule.constraint_ids)
    
    print(f"Top-level constraints: {top_level_ids}")
    
    # Show constraint structure
    print("\nConstraint Structure:")
    for uid, c in result.constraints.items():
        if isinstance(c, AtomicConstraint):
            print(f"  [A] {uid}: {c.left_operand} {c.operator.value} {c.right_operand.value}")
        elif isinstance(c, CompositeConstraint):
            print(f"  [C] {uid}: {c.operator.value}({c.operands})")
    
    # Check with proper composite handling
    print("\nChecking consistency (with composite support)...")
    judgment, model = check_with_composites(
        result.constraints,
        top_level_ids,
        debug=debug
    )
    
    print(f"\nRESULT: {judgment.value}")
    if model:
        print(f"Model: {model}")
    
    return judgment


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='*', help='TTL files to analyze')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug output')
    parser.add_argument('--dir', default='tests/ttl/adversarial', help='Test directory')
    args = parser.parse_args()
    
    if args.files:
        files = args.files
    else:
        test_dir = Path(args.dir)
        if test_dir.exists():
            files = sorted(test_dir.glob('*.ttl'))
        else:
            print(f"Directory not found: {args.dir}")
            sys.exit(1)
    
    results = {'CONFLICT': [], 'POSSIBLY-COMPATIBLE': [], 'UNKNOWN': []}
    
    for f in files:
        try:
            j = analyze_policy_file(str(f), debug=args.debug)
            if j:
                results[j.value].append(Path(f).name)
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            results['UNKNOWN'].append(Path(f).name)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for status, files in results.items():
        if files:
            print(f"\n{status} ({len(files)}):")
            for f in files:
                print(f"  - {f}")
