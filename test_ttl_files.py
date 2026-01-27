#!/usr/bin/env python3
"""
Test ODRL-SA with TTL files.

Usage:
    python test_ttl_files.py                    # Test all files
    python test_ttl_files.py tests/test_data/self_contained/count_conflict.ttl  # Test specific file
    python test_ttl_files.py --verbose          # Verbose output
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parser import parse_ttl_file, parse_ttl_string
from encoder import check_consistency
from core.types import Judgment, AtomicConstraint
from core.classifier import classify_constraint
from registry import ConstraintClass


def analyze_ttl_file(filepath: str, verbose: bool = False) -> dict:
    """Analyze a single TTL file."""
    result = {
        'file': filepath,
        'success': False,
        'policies': 0,
        'constraints': 0,
        'judgment': None,
        'errors': [],
    }
    
    try:
        # Parse
        parse_result = parse_ttl_file(filepath)
        result['policies'] = len(parse_result.policies)
        result['constraints'] = len(parse_result.constraints)
        
        if not parse_result.policies:
            result['errors'].append("No policies found")
            return result
        
        # Get atomic constraints
        atomic_constraints = []
        for c in parse_result.constraints.values():
            if isinstance(c, AtomicConstraint):
                atomic_constraints.append(c)
        
        if verbose:
            print(f"\n  Policies: {len(parse_result.policies)}")
            print(f"  Constraints: {len(parse_result.constraints)}")
            print(f"  Atomic: {len(atomic_constraints)}")
            
            # Show constraint details
            for c in atomic_constraints[:5]:  # Show first 5
                classification = classify_constraint(c)
                print(f"    - {c.left_operand} {c.operator.value} {c.right_operand.value} [{classification.constraint_class.value}]")
            if len(atomic_constraints) > 5:
                print(f"    ... and {len(atomic_constraints) - 5} more")
        
        # Check consistency
        if atomic_constraints:
            judgment, model = check_consistency(atomic_constraints)
            result['judgment'] = judgment.value
            
            if verbose and model:
                print(f"  Model: {model}")
        else:
            result['judgment'] = "NO_CONSTRAINTS"
        
        result['success'] = True
        
    except Exception as e:
        result['errors'].append(str(e))
        if verbose:
            import traceback
            traceback.print_exc()
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ODRL-SA with TTL files")
    parser.add_argument('files', nargs='*', help='TTL files to test')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-d', '--dir', default='tests/test_data/self_contained', 
                        help='Directory to scan for TTL files')
    args = parser.parse_args()
    
    # Get files to test
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        # Scan directory
        test_dir = Path(args.dir)
        if test_dir.exists():
            files = sorted(test_dir.glob('*.ttl'))
        else:
            print(f"Directory not found: {args.dir}")
            return 1
    
    if not files:
        print("No TTL files found")
        return 1
    
    print("=" * 70)
    print("ODRL-SA TTL File Tester")
    print("=" * 70)
    print()
    
    # Track results
    results = {
        'total': 0,
        'success': 0,
        'conflict': 0,
        'compatible': 0,
        'unknown': 0,
        'errors': 0,
    }
    
    for filepath in files:
        results['total'] += 1
        print(f"[{results['total']:2d}] {filepath.name}", end='')
        
        result = analyze_ttl_file(str(filepath), verbose=args.verbose)
        
        if result['success']:
            results['success'] += 1
            judgment = result['judgment']
            
            if judgment == 'CONFLICT':
                results['conflict'] += 1
                status = "[CONFLICT]"
            elif judgment == 'POSSIBLY-COMPATIBLE':
                results['compatible'] += 1
                status = "[OK]"
            elif judgment == 'NO_CONSTRAINTS':
                status = "[NO CONSTRAINTS]"
            else:
                results['unknown'] += 1
                status = f"[{judgment}]"
            
            print(f" ... {status}")
        else:
            results['errors'] += 1
            print(f" ... [ERROR] {result['errors']}")
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total files:  {results['total']}")
    print(f"  Successful:   {results['success']}")
    print(f"  Conflicts:    {results['conflict']}")
    print(f"  Compatible:   {results['compatible']}")
    print(f"  Unknown:      {results['unknown']}")
    print(f"  Errors:       {results['errors']}")
    print()
    
    return 0 if results['errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())