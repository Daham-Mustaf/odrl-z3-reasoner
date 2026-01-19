# src/main.py
"""
ODRL Policy Analyzer - Main Entry Point

Usage:
    python -m src policy.ttl                    # Analyze policy (CLI output)
    python -m src policy.ttl --json             # JSON output
    python -m src policy.ttl --verbose          # Verbose CLI output
    python -m src parent.ttl child.ttl          # Check inheritance
    uv run python -m src policy.ttl --dev              # Debug mode
    uv run python -m src --help                        # Show help

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
from typing import Optional, List

# Version
__version__ = "1.0.0"


def setup_logging(debug: bool):
    """Configure logging"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def setup_debug_mode(enabled: bool):
    """Configure debug mode globally"""
    try:
        from .semantics.constraint_types import set_debug_mode
        set_debug_mode(enabled)
    except ImportError:
        pass


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
    from .parser.ttl_parser import TTLParser
    from .parser.rdf_extractor import RDFExtractor
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    file_format = detect_format(filepath)
    
    parser = TTLParser(debug=debug)
    
    if file_format == 'json-ld':
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        graph = parser.parse_string(content, format='json-ld')
    else:
        graph = parser.parse_file(filepath)
    
    policies = parser.get_policies()
    if not policies:
        raise ValueError(f"No policies found in {filepath}")
    
    extractor = RDFExtractor(graph, debug=debug)
    policy = extractor.extract_policy(policies[0])
    
    return policy, graph


def normalize_policy(policy, debug: bool):
    """Normalize policy constraints"""
    from .normalizer.constraint_normalizer import ConstraintNormalizer
    from .normalizer.canonical_normalizer import ConstraintCanonicalizer
    
    normalizer = ConstraintNormalizer(debug=debug)
    policy.constraints = normalizer.normalize_all(policy.constraints)
    
    canonicalizer = ConstraintCanonicalizer(debug=debug)
    policy.constraints = canonicalizer.canonicalize(policy.constraints)
    
    return policy


def analyze_policy(policy, graph, debug: bool):
    """Run conflict detection"""
    from .encoder.z3_encoder import Z3Encoder, ClassHierarchy
    from .reasoner.conflict_detector import ConflictDetector
    
    hierarchy = ClassHierarchy(graph)
    encoder = Z3Encoder(hierarchy=hierarchy, debug=debug)
    
    detector = ConflictDetector(debug=debug)
    detector.encoder = encoder
    conflicts = detector.detect_all_conflicts(policy)
    
    return conflicts, detector


def check_inheritance(parent_policy, child_policy, debug: bool, per_action: bool):
    """Check inheritance between policies"""
    from .encoder.z3_encoder import Z3Encoder
    from .reasoner.inheritance_checker import InheritanceChecker
    
    encoder = Z3Encoder(debug=debug)
    checker = InheritanceChecker(encoder, debug=debug)
    
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
    setup_debug_mode(args.debug)
    
    # Import report generator
    from .reporting.report_generator import ReportGenerator
    
    reporter = ReportGenerator(debug=args.debug)
    reporter.start_analysis()
    
    try:
        # ═══════════════════════════════════════════════════════════════════
        # INHERITANCE CHECK MODE
        # ═══════════════════════════════════════════════════════════════════
        if args.child_policy:
            # Load parent
            parent_policy, parent_graph = load_policy(args.policy_file, args.debug)
            parent_policy = normalize_policy(parent_policy, args.debug)
            
            # Load child
            child_policy, child_graph = load_policy(args.child_policy, args.debug)
            child_policy = normalize_policy(child_policy, args.debug)
            
            # Check inheritance
            violations, checker = check_inheritance(
                parent_policy, child_policy, args.debug, args.per_action
            )
            
            # Also run conflict detection on child
            conflicts, detector = analyze_policy(child_policy, child_graph, args.debug)
            
            # Generate report
            result = reporter.generate(
                child_policy, conflicts,
                inheritance_violations=violations,
                parent_policy_id=parent_policy.id
            )
            
            # Output
            output = _format_output(reporter, result, args)
            _write_output(output, args.output)
            
            # Return code
            hard_violations = [v for v in violations if v.violation_type != 'redundant']
            return 1 if hard_violations or result.summary.errors > 0 else 0
        
        # ═══════════════════════════════════════════════════════════════════
        # SINGLE POLICY ANALYSIS MODE
        # ═══════════════════════════════════════════════════════════════════
        
        # Load
        policy, graph = load_policy(args.policy_file, args.debug)
        
        # Normalize
        policy = normalize_policy(policy, args.debug)
        
        # Analyze
        conflicts, detector = analyze_policy(policy, graph, args.debug)
        
        # Generate report
        result = reporter.generate(policy, conflicts)
        
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