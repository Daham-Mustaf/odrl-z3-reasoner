#!/usr/bin/env python3
"""
ODRL-SA Test File Analyzer

Analyzes all test TTL files and classifies them by constraint class.
Run from: ~/Desktop/odrl-z3-reasoner/

Usage:
    python analyze_test_files.py
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# =============================================================================
# LeftOperand Partitions (from ODRL-SA Specification)
# =============================================================================

# L_xsd: FULL class - XSD-typed, fully analyzable via SMT
L_XSD = {
    "count", "percentage", "payAmount", "resolution",
    "dateTime", "timeInterval",
    "relativePosition", "relativeSize", "relativeSpatialPosition", "relativeTemporalPosition",
    "absolutePosition", "absoluteSize", "absoluteSpatialPosition", "absoluteTemporalPosition",
}

# L_ref: PARTIAL class - Reference-point dependent
L_REF = {"elapsedTime", "delayPeriod"}

# L_kb: GROUNDED class - Requires KB reasoning
L_KB = {
    "language", "purpose", "fileFormat", "media", "deliveryChannel",
    "event", "industry", "product", "recipient", "spatial",
    "spatialCoordinates", "systemDevice", "virtualLocation", "version",
}

# L_run: RUNTIME class - Cannot analyze statically
L_RUN = {"meteredTime"}

# Set operators (require semantic interpretation)
SET_OPERATORS = {"isA", "hasPart", "isPartOf", "isAllOf", "isAnyOf", "isNoneOf"}

# Comparison operators (XSD-compatible)
CMP_OPERATORS = {"eq", "neq", "lt", "lteq", "gt", "gteq"}


def classify_operand(op):
    """Classify a single LeftOperand."""
    op_clean = op.split(":")[-1].split("/")[-1]
    if op_clean in L_XSD:
        return "FULL", op_clean
    elif op_clean in L_REF:
        return "PARTIAL", op_clean
    elif op_clean in L_KB:
        return "GROUNDED", op_clean
    elif op_clean in L_RUN:
        return "RUNTIME", op_clean
    else:
        return "UNKNOWN", op_clean


def extract_from_ttl(filepath):
    """Extract leftOperand, operator, and rightOperand values from a TTL file."""
    operands = []
    operators = []
    right_operands = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Find leftOperand references
        patterns = [
            r'odrl:leftOperand\s+odrl:(\w+)',
            r'odrl:leftOperand\s+<[^>]*[#/](\w+)>',
            r':leftOperand\s+:(\w+)',
            r':leftOperand\s+odrl:(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            operands.extend(matches)
        
        # Find operators
        op_patterns = [
            r'odrl:operator\s+odrl:(\w+)',
            r':operator\s+:(\w+)',
            r':operator\s+odrl:(\w+)',
        ]
        for pattern in op_patterns:
            matches = re.findall(pattern, content)
            operators.extend(matches)
        
        # Find rightOperand (to check for set-based values)
        right_patterns = [
            r'odrl:rightOperand\s+"([^"]+)"',
            r'odrl:rightOperand\s+<([^>]+)>',
            r':rightOperand\s+"([^"]+)"',
        ]
        for pattern in right_patterns:
            matches = re.findall(pattern, content)
            right_operands.extend(matches)
            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return list(set(operands)), list(set(operators)), right_operands


def analyze_file(filepath):
    """Analyze a single TTL file and determine its constraint class."""
    operands, operators, right_ops = extract_from_ttl(filepath)
    
    # Classify each operand
    operand_classes = {}
    for op in operands:
        cls, clean_op = classify_operand(op)
        operand_classes[clean_op] = cls
    
    # Check if file uses set operators (which might elevate to GROUNDED)
    uses_set_ops = any(op in SET_OPERATORS for op in operators)
    
    # Determine overall class (most restrictive)
    classes = set(operand_classes.values())
    
    if "RUNTIME" in classes:
        file_class = "RUNTIME"
    elif "GROUNDED" in classes:
        file_class = "GROUNDED"
    elif "PARTIAL" in classes:
        file_class = "PARTIAL"
    elif uses_set_ops and any(c in ["FULL", "UNKNOWN"] for c in classes):
        # Set operators on FULL operands might still need KB for hierarchy
        # But if the rightOperand is a literal value, it's still FULL
        file_class = "FULL+SET"  # Needs review
    elif "FULL" in classes:
        file_class = "FULL"
    elif "UNKNOWN" in classes:
        file_class = "UNKNOWN"
    else:
        file_class = "EMPTY"
    
    return {
        'operands': operand_classes,
        'operators': operators,
        'right_operands': right_ops,
        'file_class': file_class,
        'uses_set_ops': uses_set_ops,
    }


def analyze_directory(test_dir):
    """Analyze all TTL files in a directory tree."""
    results = []
    
    test_path = Path(test_dir)
    if not test_path.exists():
        print(f"ERROR: Directory not found: {test_dir}")
        return results
    
    for filepath in test_path.rglob("*.ttl"):
        analysis = analyze_file(filepath)
        analysis['file'] = str(filepath.relative_to(test_path))
        analysis['full_path'] = str(filepath)
        results.append(analysis)
    
    return results


def print_results(results, test_dir):
    """Print analysis results."""
    print("=" * 70)
    print("ODRL-SA Test File Analysis")
    print("=" * 70)
    print(f"\nDirectory: {test_dir}")
    print(f"Total files: {len(results)}")
    
    # Group by class
    by_class = defaultdict(list)
    for r in results:
        by_class[r['file_class']].append(r)
    
    # Print each class
    for cls in ["FULL", "FULL+SET", "PARTIAL", "GROUNDED", "RUNTIME", "UNKNOWN", "EMPTY"]:
        files = by_class.get(cls, [])
        if files:
            print(f"\n{'='*70}")
            print(f"CLASS: {cls} ({len(files)} files)")
            print("="*70)
            
            if cls == "FULL":
                print("✓ These should work with current Z3 encoder (no oracle needed)")
            elif cls == "FULL+SET":
                print("⚠ Uses set operators - check if values need KB lookup")
            elif cls == "PARTIAL":
                print("⚠ Reference-point dependent - needs aligned contexts")
            elif cls == "GROUNDED":
                print("⚠ Requires KB oracle - LanguageOracle/PurposeOracle/etc.")
            elif cls == "RUNTIME":
                print("✗ Cannot analyze statically - should return UNKNOWN")
            
            for r in sorted(files, key=lambda x: x['file']):
                print(f"\n  📄 {r['file']}")
                if r['operands']:
                    for op, op_cls in sorted(r['operands'].items()):
                        marker = "✓" if op_cls == "FULL" else "⚠" if op_cls in ["PARTIAL", "GROUNDED"] else "✗"
                        print(f"      {marker} {op} [{op_cls}]")
                if r['operators']:
                    ops_str = ', '.join(sorted(r['operators']))
                    set_marker = " ⚠(set)" if r['uses_set_ops'] else ""
                    print(f"      Operators: {ops_str}{set_marker}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    total = 0
    for cls in ["FULL", "FULL+SET", "PARTIAL", "GROUNDED", "RUNTIME", "UNKNOWN", "EMPTY"]:
        count = len(by_class.get(cls, []))
        if count > 0:
            pct = count / len(results) * 100 if results else 0
            status = {
                "FULL": "✓ Ready",
                "FULL+SET": "⚠ Review",
                "PARTIAL": "⚠ Needs context",
                "GROUNDED": "⚠ Needs oracle",
                "RUNTIME": "✗ UNKNOWN result",
                "UNKNOWN": "? Check operands",
                "EMPTY": "- No constraints",
            }.get(cls, "")
            print(f"  {cls:12} {count:3} files ({pct:5.1f}%) {status}")
            total += count
    
    print(f"\n  {'TOTAL':12} {total:3} files")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    if by_class.get("FULL"):
        print(f"\n1. FULL class ({len(by_class['FULL'])} files):")
        print("   → Run: pytest tests/ -k 'self_contained' -v")
        print("   → These should ALL PASS with current engine")
    
    if by_class.get("GROUNDED"):
        print(f"\n2. GROUNDED class ({len(by_class['GROUNDED'])} files):")
        print("   → Need to connect oracles to Z3 encoder")
        print("   → Files using: language, purpose, fileFormat, recipient, etc.")
        grounded_ops = set()
        for r in by_class["GROUNDED"]:
            for op, cls in r['operands'].items():
                if cls == "GROUNDED":
                    grounded_ops.add(op)
        print(f"   → Operands used: {', '.join(sorted(grounded_ops))}")
    
    if by_class.get("PARTIAL"):
        print(f"\n3. PARTIAL class ({len(by_class['PARTIAL'])} files):")
        print("   → Need reference point alignment")
    
    if by_class.get("RUNTIME"):
        print(f"\n4. RUNTIME class ({len(by_class['RUNTIME'])} files):")
        print("   → Should return UNKNOWN (by design)")


def main():
    """Main entry point."""
    # Find test directory
    test_dirs = [
        "tests/test_data",
        "../tests/test_data",
        "../../tests/test_data",
    ]
    
    test_dir = None
    for d in test_dirs:
        if Path(d).exists():
            test_dir = d
            break
    
    if test_dir is None:
        print("ERROR: Cannot find tests/test_data directory")
        print("Run this script from the odrl-z3-reasoner root directory")
        return 1
    
    results = analyze_directory(test_dir)
    print_results(results, test_dir)
    
    return 0


if __name__ == "__main__":
    exit(main())
