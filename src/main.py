# src/main.py
"""
ODRL Policy Analyzer - Main Entry Point

Usage:
    python -m src policy.ttl                    # Analyze policy (CLI output)
    python -m src policy.ttl --json             # JSON output
    python -m src policy.ttl --verbose          # Verbose CLI output
    python -m src parent.ttl child.ttl          # Check inheritance
    uv run python -m src policy.ttl --dev       # Debug mode
    uv run python -m src --help                 # Show help

Output Formats:
    cli      - Compact human-readable (default)
    json     - Machine-readable JSON
    verbose  - Detailed CLI output
"""

import sys
import os
import argparse
import logging
import time
from typing import Optional, List, Dict, Any

# Version
__version__ = "1.0.0"


def setup_logging(debug: bool):
    """Configure logging"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        prog='odrl-analyze',
        description='ODRL Policy Analyzer - Static analysis for ODRL policies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s policy.ttl                    Analyze policy
  %(prog)s policy.ttl --json             Output as JSON
  %(prog)s policy.ttl --verbose          Detailed output
  %(prog)s parent.ttl child.ttl          Check inheritance
  %(prog)s policy.ttl --dev              Debug mode
  %(prog)s policy.ttl -o report.json     Save to file
        """
    )
    
    parser.add_argument(
        'policy_file',
        help='Path to ODRL policy file (TTL or JSON-LD)'
    )
    
    parser.add_argument(
        'child_policy',
        nargs='?',
        default=None,
        help='Child policy for inheritance check'
    )
    
    # Output format
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    format_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose CLI output'
    )
    format_group.add_argument(
        '--compact',
        action='store_true',
        help='Minimal CLI output'
    )
    
    # Debug
    parser.add_argument(
        '--dev', '--debug',
        action='store_true',
        dest='debug',
        help='Enable debug mode'
    )
    
    # Output file
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output file path'
    )
    
    # Inheritance options
    parser.add_argument(
        '--per-action',
        action='store_true',
        help='Per-action inheritance check (more precise)'
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    return parser


def detect_format(filepath: str) -> str:
    """Detect file format from extension"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.jsonld', '.json'):
        return 'json-ld'
    return 'turtle'


def load_policy(filepath: str, debug: bool):
    """Load and parse policy file"""
    from .parser.ttl_parser import parse_ttl_file, ParseResult
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Parse the file
    result = parse_ttl_file(filepath, debug=debug)
    
    if not result.policies:
        raise ValueError(f"No policies found in {filepath}")
    
    if result.errors:
        for error in result.errors:
            logging.warning(f"Parse warning: {error}")
    
    # Return first policy and constraints
    policy = result.policies[0]
    constraints = {c.uid: c for c in result.constraints}
    
    return policy, constraints, result


def analyze_policy(policy, constraints: Dict[str, Any], debug: bool):
    """Run conflict detection"""
    from .reasoner.conflict_detector import ConflictDetector
    
    detector = ConflictDetector(debug=debug)
    conflicts = detector.detect_all_conflicts(policy, constraints)
    
    return conflicts, detector


def check_inheritance(parent_policy, child_policy, parent_constraints, child_constraints, debug: bool, per_action: bool):
    """Check inheritance between policies"""
    from .encoder.z3_encoder import Z3JudgmentEngine
    from .reasoner.inheritance_checker import InheritanceChecker
    
    encoder = Z3JudgmentEngine(debug=debug)
    checker = InheritanceChecker(encoder, debug=debug)
    
    # Attach constraints to policies for the checker
    parent_policy.constraints = parent_constraints
    child_policy.constraints = child_constraints
    
    if per_action:
        violations = checker.check_inheritance_per_action(parent_policy, child_policy)
    else:
        violations = checker.check_inheritance(parent_policy, child_policy)
    
    return violations, checker


def main(argv: Optional[List[str]] = None):
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup
    setup_logging(args.debug)
    
    # Import report generator
    from .reporting.report_generator import ReportGenerator
    
    reporter = ReportGenerator(debug=args.debug)
    reporter.start_analysis()
    
    try:
        # =================================================================
        # INHERITANCE CHECK MODE
        # =================================================================
        if args.child_policy:
            # Load parent
            parent_policy, parent_constraints, _ = load_policy(args.policy_file, args.debug)
            
            # Load child
            child_policy, child_constraints, _ = load_policy(args.child_policy, args.debug)
            
            # Check inheritance
            violations, checker = check_inheritance(
                parent_policy, child_policy,
                parent_constraints, child_constraints,
                args.debug, args.per_action
            )
            
            # Also run conflict detection on child
            conflicts, detector = analyze_policy(child_policy, child_constraints, args.debug)
            
            # Generate report
            result = reporter.generate(
                child_policy, conflicts, child_constraints,
                inheritance_violations=violations,
                parent_policy_id=parent_policy.uid
            )
            
            # Output
            output = _format_output(reporter, result, args)
            _write_output(output, args.output)
            
            # Return code
            hard_violations = [v for v in violations if v.violation_type != 'redundant']
            return 1 if hard_violations or result.summary.errors > 0 else 0
        
        # =================================================================
        # SINGLE POLICY ANALYSIS MODE
        # =================================================================
        
        # Load
        policy, constraints, parse_result = load_policy(args.policy_file, args.debug)
        
        # Analyze
        conflicts, detector = analyze_policy(policy, constraints, args.debug)
        
        # Generate report
        result = reporter.generate(policy, conflicts, constraints)
        
        # Output
        output = _format_output(reporter, result, args)
        _write_output(output, args.output)
        
        # Return code
        return 1 if result.summary.errors > 0 else 0
    
    except FileNotFoundError as e:
        if args.json:
            print(f'{{"error": "{e}"}}')
        else:
            print(f"Error: {e}")
        return 2
    
    except ValueError as e:
        if args.json:
            print(f'{{"error": "{e}"}}')
        else:
            print(f"Error: {e}")
        return 3
    
    except Exception as e:
        if args.debug:
            import traceback
            traceback.print_exc()
        if args.json:
            print(f'{{"error": "{e}"}}')
        else:
            print(f"Error: {e}")
        return 4


def _format_output(reporter, result, args) -> str:
    """Format output based on args"""
    if args.json:
        return reporter.format_json(result)
    elif args.compact:
        return reporter.format_cli_compact(result)
    else:
        return reporter.format_cli(result, verbose=args.verbose)


def _write_output(output: str, filepath: Optional[str]):
    """Write output to file or stdout"""
    if filepath:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Report saved to: {filepath}")
    else:
        print(output)


if __name__ == '__main__':
    sys.exit(main())