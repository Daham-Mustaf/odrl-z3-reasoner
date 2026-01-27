#!/usr/bin/env python3
"""
ODRL-SA Language Ontology Builder

Builds BCP47 language hierarchy for ODRL policy reasoning.

Usage:
    python builder.py                           # Uses local IANA file
    python builder.py --output bcp47.ttl        # Specify output
    python builder.py --online                  # Fetch from IANA

First-time setup:
    mkdir -p data/iana
    curl -o data/iana/language-subtag-registry.txt \\
      https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry

Components:
    - iana_parser.py: Parse IANA Language Subtag Registry
    - hierarchy.py: Build BCP47 hierarchy from composition rules  
    - rdf_generator.py: Generate SKOS RDF (Turtle)
"""

import argparse
import sys
from pathlib import Path

# Import modules (refactored names)
from iana_parser import IANARegistryParser, IANARegistry, DEFAULT_REGISTRY_PATH, load_registry
from hierarchy import HierarchyBuilder, LanguageHierarchy
from rdf_generator import TurtleGenerator, Namespaces


def build_ontology(
    registry_path: str = None,
    online: bool = False,
    output_path: str = None
) -> str:
    """
    Build the complete language ontology.
    
    Args:
        registry_path: Path to local IANA registry file
        online: If True, fetch from IANA instead of local file
        output_path: Where to save the output (None = don't save)
        
    Returns:
        Generated Turtle string
    """
    
    print("="*70)
    print("  ODRL-SA Language Ontology Builder")
    print("="*70)
    print()
    print("  Building BCP47 language hierarchy for ODRL policy reasoning")
    print("  Based on: RFC 5646, ISO 639, ISO 15924, ISO 3166-1")
    print()
    
    # =========================================================================
    # STEP 1: Parse IANA Registry
    # =========================================================================
    
    print("-"*70)
    print("  STEP 1: Parse IANA Language Subtag Registry")
    print("-"*70)
    
    parser = IANARegistryParser()
    
    if online:
        print("  Mode: ONLINE (fetching from IANA)")
        try:
            content = parser.fetch_registry()
        except Exception as e:
            print(f"  ERROR: Could not fetch registry: {e}")
            return None
    else:
        # Use provided path or default
        path = registry_path or DEFAULT_REGISTRY_PATH
        
        # Handle relative path from script location
        script_dir = Path(__file__).parent
        
        # Try multiple locations
        possible_paths = [
            Path(path),                                    # As provided
            script_dir / path,                             # Relative to script
            script_dir.parent.parent.parent / path,        # Project root
            Path.home() / "Desktop/odrl-z3-reasoner" / path  # Absolute fallback
        ]
        
        found_path = None
        for p in possible_paths:
            if p.exists():
                found_path = p
                break
        
        if found_path:
            print(f"  Mode: LOCAL ({found_path})")
            content = parser.load_from_file(str(found_path))
        else:
            print(f"  ERROR: Registry file not found!")
            print(f"  Searched:")
            for p in possible_paths:
                print(f"    - {p}")
            print()
            print(f"  To download the registry:")
            print(f"    mkdir -p data/iana")
            print(f"    curl -o data/iana/language-subtag-registry.txt \\")
            print(f"      https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry")
            print()
            print(f"  Or run with --online to fetch directly")
            return None
    
    registry = parser.parse(content)
    
    stats = registry.get_statistics()
    print()
    print(f"  Parsed registry (File-Date: {registry.file_date}):")
    print(f"    • Languages: {stats['languages']}")
    print(f"    • Scripts: {stats['scripts']}")
    print(f"    • Regions: {stats['regions']}")
    print(f"    • Deprecated (with preferred): {stats['deprecated_with_preferred']}")
    print()
    
    # =========================================================================
    # STEP 2: Build Hierarchy
    # =========================================================================
    
    print("-"*70)
    print("  STEP 2: Build BCP47 Hierarchy")
    print("-"*70)
    
    builder = HierarchyBuilder()
    hierarchy = builder.build_from_registry(registry)
    
    stats = hierarchy.get_statistics()
    print()
    print(f"  Built hierarchy:")
    print(f"    • Total tags: {stats['total_tags']}")
    print(f"    • Base languages: {stats['base_languages']}")
    print(f"    • Hierarchy edges: {stats['hierarchy_edges']}")
    print(f"    • Tags with script: {stats['tags_with_script']}")
    print(f"    • Tags with region: {stats['tags_with_region']}")
    print()
    
    # Show some example hierarchies
    print("  Example hierarchies:")
    examples = ["zh-Hans-CN", "en-US", "sr-Latn", "de-AT"]
    for tag in examples:
        ancestors = hierarchy.get_ancestors(tag)
        if ancestors:
            chain = f"{tag} ⊑ " + " ⊑ ".join(ancestors)
            print(f"    • {chain}")
    print()
    
    # =========================================================================
    # STEP 3: Generate RDF/SKOS
    # =========================================================================
    
    print("-"*70)
    print("  STEP 3: Generate RDF/SKOS Ontology")
    print("-"*70)
    
    generator = TurtleGenerator()
    deprecated_mappings = registry.get_deprecated_mappings()
    
    turtle = generator.generate(hierarchy, registry, deprecated_mappings)
    
    line_count = turtle.count('\n') + 1
    concept_count = turtle.count('a skos:Concept')
    broader_count = turtle.count('skos:broader')
    exactmatch_count = turtle.count('skos:exactMatch')
    
    print()
    print(f"  Generated ontology:")
    print(f"    • Size: {len(turtle):,} characters")
    print(f"    • Lines: {line_count:,}")
    print(f"    • Concepts: {concept_count}")
    print(f"    • skos:broader edges: {broader_count}")
    print(f"    • skos:exactMatch links: {exactmatch_count}")
    print()
    
    # =========================================================================
    # SAVE OUTPUT
    # =========================================================================
    
    if output_path:
        print("-"*70)
        print("  OUTPUT")
        print("-"*70)
        
        # Create parent directories if needed
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(turtle)
        
        print()
        print(f"  ✓ Saved to: {output_path}")
        print()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    print("="*70)
    print("  BUILD COMPLETE")
    print("="*70)
    print()
    print("  The generated ontology provides:")
    print()
    print("    1. SUBSUMPTION (skos:broader)")
    print("       → en-US skos:broader en")
    print("       → zh-Hans-CN skos:broader zh-Hans skos:broader zh")
    print()
    print("    2. EQUIVALENCE (skos:exactMatch)")
    print("       → iw skos:exactMatch he (deprecated codes)")
    print("       → lang:en skos:exactMatch lcc-639-1:English (to LCC)")
    print()
    print("    3. DISJOINTNESS (derived)")
    print("       → Different base languages are disjoint (en ⊥ de)")
    print("       → Different scripts are disjoint (zh-Hans ⊥ zh-Hant)")
    print()
    print("  Use with ODRL-SA HybridLanguageOracle for policy reasoning.")
    print()
    
    return turtle


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Build BCP47 language ontology for ODRL-SA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python builder.py                        # Use local IANA file
  python builder.py --online               # Fetch from IANA
  python builder.py -o bcp47.ttl           # Specify output file
  python builder.py -f my-registry.txt     # Use custom registry file

First-time setup:
  mkdir -p data/iana
  curl -o data/iana/language-subtag-registry.txt \\
    https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
        """
    )
    parser.add_argument(
        '--output', '-o',
        default='bcp47.ttl',
        help='Output file path (default: bcp47.ttl)'
    )
    parser.add_argument(
        '--file', '-f',
        default=None,
        help=f'Local IANA registry file (default: {DEFAULT_REGISTRY_PATH})'
    )
    parser.add_argument(
        '--online',
        action='store_true',
        help='Fetch registry from IANA instead of local file'
    )
    
    args = parser.parse_args()
    
    turtle = build_ontology(
        registry_path=args.file,
        online=args.online,
        output_path=args.output
    )
    
    if turtle is None:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())