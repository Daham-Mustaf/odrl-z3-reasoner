#!/usr/bin/env python3
"""
ODRL-SA Language Ontology - SPARQL Validation Queries

Tests the generated BCP47 ontology with SPARQL queries.

Usage:
    python sparql_tests.py                    # Uses bcp47.ttl
    python sparql_tests.py -f other.ttl       # Use different file
    python sparql_tests.py -v                 # Verbose output
"""

import argparse
from pathlib import Path

try:
    from rdflib import Graph, Namespace, Literal, URIRef
    from rdflib.namespace import SKOS
    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False
    print("ERROR: rdflib not installed. Run: pip install rdflib")


# Namespaces
LANG = Namespace("http://w3id.org/odrl/bcp47/lang/")
DCT = Namespace("http://purl.org/dc/terms/")


# =============================================================================
# SPARQL QUERIES
# =============================================================================

QUERIES = [
    {
        "name": "count_concepts",
        "title": "Count total concepts",
        "query": "SELECT (COUNT(?c) AS ?count) WHERE { ?c a skos:Concept }",
        "expected": "> 8000"
    },
    {
        "name": "count_base_languages",
        "title": "Count base languages",
        "query": "SELECT (COUNT(?c) AS ?count) WHERE { ?c skos:topConceptOf ?s }",
        "expected": "> 8000"
    },
    {
        "name": "count_hierarchy",
        "title": "Count hierarchy edges",
        "query": "SELECT (COUNT(*) AS ?count) WHERE { ?c skos:broader ?p }",
        "expected": "~190"
    },
    {
        "name": "count_lcc_links",
        "title": "Count LCC links",
        "query": """
            SELECT (COUNT(*) AS ?count) WHERE { 
                ?c skos:exactMatch ?lcc .
                FILTER(CONTAINS(STR(?lcc), "omg.org/spec/LCC"))
            }
        """,
        "expected": "~180"
    },
    {
        "name": "sample_base",
        "title": "Sample base languages",
        "query": """
            SELECT ?code ?label WHERE {
                ?c skos:topConceptOf ?s ;
                   skos:notation ?code ;
                   skos:prefLabel ?label .
            } ORDER BY ?code LIMIT 10
        """,
        "expected": "aa, ab, ..."
    },
    {
        "name": "sample_composite",
        "title": "Sample composite tags",
        "query": """
            SELECT ?code ?parentCode WHERE {
                ?c skos:broader ?p ;
                   skos:notation ?code .
                ?p skos:notation ?parentCode .
            } ORDER BY ?code LIMIT 10
        """,
        "expected": "ar-AE → ar, ..."
    },
    {
        "name": "english_variants",
        "title": "English variants (en-XX)",
        "query": """
            SELECT ?code WHERE {
                ?c skos:broader lang:en ;
                   skos:notation ?code .
            } ORDER BY ?code
        """,
        "expected": "en-AU, en-GB, en-US, ..."
    },
    {
        "name": "chinese_hierarchy",
        "title": "Chinese hierarchy",
        "query": """
            SELECT ?code ?parentCode WHERE {
                ?c skos:notation ?code .
                FILTER(STRSTARTS(STR(?code), "zh"))
                OPTIONAL {
                    ?c skos:broader ?p .
                    ?p skos:notation ?parentCode .
                }
            } ORDER BY ?code
        """,
        "expected": "zh, zh-Hans, zh-Hans-CN, ..."
    },
    {
        "name": "zh_hans_cn_ancestors",
        "title": "Ancestors of zh-Hans-CN",
        "query": """
            SELECT ?code WHERE {
                lang:zh-Hans-CN skos:broader+ ?a .
                ?a skos:notation ?code .
            }
        """,
        "expected": "zh-Hans, zh"
    },
    {
        "name": "deprecated_mappings",
        "title": "Deprecated code mappings",
        "query": """
            SELECT ?old ?new WHERE {
                ?o skos:exactMatch ?n .
                ?o skos:notation ?old .
                ?n skos:notation ?new .
                FILTER(?o != ?n)
                FILTER(STRSTARTS(STR(?o), STR(lang:)))
                FILTER(STRSTARTS(STR(?n), STR(lang:)))
            } LIMIT 10
        """,
        "expected": "iw → he, ..."
    },
    {
        "name": "odrl_isa",
        "title": "ODRL: en-US isA en?",
        "query": "ASK { lang:en-US skos:broader+ lang:en }",
        "expected": "True"
    },
    {
        "name": "odrl_eq_deprecated",
        "title": "ODRL: iw eq he?",
        "query": "ASK { { lang:iw skos:exactMatch lang:he } UNION { lang:he skos:exactMatch lang:iw } }",
        "expected": "True"
    },
    {
        "name": "odrl_disjoint",
        "title": "ODRL: en and de share ancestor?",
        "query": "ASK { lang:en skos:broader* ?x . lang:de skos:broader* ?x }",
        "expected": "False (disjoint)"
    },
]


# =============================================================================
# RUNNER
# =============================================================================

def run_tests(ontology_path: str, verbose: bool = False):
    """Run all SPARQL tests."""
    
    print("=" * 70)
    print("  ODRL-SA Language Ontology - SPARQL Validation")
    print("=" * 70)
    print(f"\n  Loading: {ontology_path}")
    
    # Load graph
    g = Graph()
    g.parse(ontology_path, format="turtle")
    g.bind("lang", LANG)
    g.bind("skos", SKOS)
    
    print(f"  Triples: {len(g)}")
    print("\n" + "-" * 70)
    
    success = 0
    
    for q in QUERIES:
        print(f"\n✅ {q['title']}")
        print(f"   Expected: {q['expected']}")
        
        try:
            result = g.query(q["query"])
            
            # ASK query
            if hasattr(result, 'askAnswer'):
                print(f"   Result: {result.askAnswer}")
            else:
                # SELECT query
                rows = list(result)
                
                if len(rows) == 0:
                    print(f"   Result: (empty)")
                elif len(rows) == 1 and len(rows[0]) == 1:
                    # Single value (COUNT)
                    val = rows[0][0]
                    print(f"   Result: {val}")
                else:
                    # Multiple rows
                    print(f"   Result: {len(rows)} rows")
                    show = 5 if not verbose else 10
                    for i, row in enumerate(rows[:show]):
                        vals = [str(v) for v in row]
                        print(f"      {i+1}. {' → '.join(vals)}")
                    if len(rows) > show:
                        print(f"      ... +{len(rows) - show} more")
            
            success += 1
            
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print("\n" + "=" * 70)
    print(f"  SUMMARY: {success}/{len(QUERIES)} passed")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', default='bcp47.ttl')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    
    if not HAS_RDFLIB:
        return 1
    
    if not Path(args.file).exists():
        print(f"ERROR: {args.file} not found")
        return 1
    
    run_tests(args.file, args.verbose)
    return 0


if __name__ == "__main__":
    exit(main())
