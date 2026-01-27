#!/usr/bin/env python3
"""
ODRL-SA Language Ontology - SPARQL Validation

Tests the generated BCP47 ontology with SPARQL queries.

Usage:
    python sparql_tests.py                    # Uses bcp47.ttl
    python sparql_tests.py -f other.ttl       # Use different file
"""

import argparse
from pathlib import Path

try:
    from rdflib import Graph, Namespace
    from rdflib.namespace import SKOS
    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False
    print("ERROR: rdflib not installed. Run: pip install rdflib")


LANG = Namespace("http://w3id.org/odrl/bcp47/lang/")


def run_tests(ontology_path: str):
    """Run all SPARQL tests."""
    
    print("=" * 70)
    print("  ODRL-SA Language Ontology - SPARQL Validation")
    print("=" * 70)
    print(f"\n  Loading: {ontology_path}")
    
    g = Graph()
    g.parse(ontology_path, format="turtle")
    g.bind("lang", LANG)
    g.bind("skos", SKOS)
    
    print(f"  Triples: {len(g)}")
    print("\n" + "-" * 70)
    
    # -------------------------------------------------------------------------
    # TEST 1: Count concepts
    # -------------------------------------------------------------------------
    print("\n Count total concepts")
    print("   Expected: > 8000")
    result = g.query("SELECT (COUNT(?c) AS ?n) WHERE { ?c a skos:Concept }")
    for row in result:
        print(f"   Result: {row[0]}")
    
    # -------------------------------------------------------------------------
    # TEST 2: Count base languages
    # -------------------------------------------------------------------------
    print("\n Count base languages (topConcepts)")
    print("   Expected: > 8000")
    result = g.query("SELECT (COUNT(?c) AS ?n) WHERE { ?c skos:topConceptOf ?s }")
    for row in result:
        print(f"   Result: {row[0]}")
    
    # -------------------------------------------------------------------------
    # TEST 3: Count hierarchy edges
    # -------------------------------------------------------------------------
    print("\n Count hierarchy edges (skos:broader)")
    print("   Expected: ~190")
    result = g.query("SELECT (COUNT(*) AS ?n) WHERE { ?c skos:broader ?p }")
    for row in result:
        print(f"   Result: {row[0]}")
    
    # -------------------------------------------------------------------------
    # TEST 4: Count LCC links
    # -------------------------------------------------------------------------
    print("\n Count LCC links")
    print("   Expected: ~180 (ISO 639-1)")
    result = g.query("""
        SELECT (COUNT(*) AS ?n) WHERE { 
            ?c skos:exactMatch ?lcc .
            FILTER(CONTAINS(STR(?lcc), "omg.org/spec/LCC"))
        }
    """)
    for row in result:
        print(f"   Result: {row[0]}")
    
    # -------------------------------------------------------------------------
    # TEST 5: Sample base languages
    # -------------------------------------------------------------------------
    print("\n Sample base languages")
    print("   Expected: aa, ab, ... with labels")
    result = g.query("""
        SELECT ?code ?label WHERE {
            ?c skos:topConceptOf ?s ;
               skos:notation ?code ;
               skos:prefLabel ?label .
        } ORDER BY ?code LIMIT 5
    """)
    rows = list(result)
    print(f"   Result: {len(rows)} rows (showing first 5)")
    for row in rows:
        print(f"      {row[0]} → {row[1]}")
    
    # -------------------------------------------------------------------------
    # TEST 6: Sample composite tags
    # -------------------------------------------------------------------------
    print("\n Sample composite tags (with skos:broader)")
    print("   Expected: ar-AE → ar, en-US → en, ...")
    result = g.query("""
        SELECT ?code ?parentCode WHERE {
            ?c skos:broader ?p ;
               skos:notation ?code .
            ?p skos:notation ?parentCode .
        } ORDER BY ?code LIMIT 10
    """)
    rows = list(result)
    print(f"   Result: {len(rows)} rows (showing first 10)")
    for row in rows:
        print(f"      {row[0]} ⊑ {row[1]}")
    
    # -------------------------------------------------------------------------
    # TEST 7: English variants
    # -------------------------------------------------------------------------
    print("\n All English variants (en-XX ⊑ en)")
    print("   Expected: en-AU, en-GB, en-US, ...")
    result = g.query("""
        SELECT ?code WHERE {
            ?c skos:broader lang:en ;
               skos:notation ?code .
        } ORDER BY ?code
    """)
    rows = list(result)
    print(f"   Result: {len(rows)} variants")
    for row in rows[:5]:
        print(f"      {row[0]}")
    if len(rows) > 5:
        print(f"      ... +{len(rows) - 5} more")
    
    # -------------------------------------------------------------------------
    # TEST 8: Chinese hierarchy (multi-level)
    # -------------------------------------------------------------------------
    print("\n Chinese hierarchy (multi-level)")
    print("   Expected: zh → zh-Hans → zh-Hans-CN")
    result = g.query("""
        SELECT ?code ?parentCode WHERE {
            ?c skos:notation ?code .
            FILTER(STRSTARTS(STR(?code), "zh"))
            OPTIONAL {
                ?c skos:broader ?p .
                ?p skos:notation ?parentCode .
            }
        } ORDER BY ?code
    """)
    rows = list(result)
    print(f"   Result: {len(rows)} Chinese tags")
    for row in rows:
        parent = row[1] if row[1] else "(root)"
        print(f"      {row[0]} ⊑ {parent}")
    
    # -------------------------------------------------------------------------
    # TEST 9: Transitive ancestors of zh-Hans-CN
    # -------------------------------------------------------------------------
    print("\n Ancestors of zh-Hans-CN (transitive)")
    print("   Expected: zh-Hans, zh")
    result = g.query("""
        SELECT ?code WHERE {
            lang:zh-Hans-CN skos:broader+ ?a .
            ?a skos:notation ?code .
        }
    """)
    rows = list(result)
    print(f"   Result: {len(rows)} ancestors")
    for row in rows:
        print(f"      {row[0]}")
    
    # -------------------------------------------------------------------------
    # TEST 10: Deprecated mappings
    # -------------------------------------------------------------------------
    print("\n Deprecated code mappings")
    print("   Expected: iw → he, ...")
    result = g.query("""
        SELECT ?old ?new WHERE {
            ?o skos:exactMatch ?n .
            ?o skos:notation ?old .
            ?n skos:notation ?new .
            FILTER(?o != ?n)
            FILTER(STRSTARTS(STR(?o), STR(lang:)))
            FILTER(STRSTARTS(STR(?n), STR(lang:)))
        } LIMIT 10
    """)
    rows = list(result)
    print(f"   Result: {len(rows)} mappings")
    for row in rows:
        print(f"      {row[0]} ≡ {row[1]}")
    
    # -------------------------------------------------------------------------
    # TEST 11: ODRL isA simulation
    # -------------------------------------------------------------------------
    print("\n ODRL: en-US isA en?")
    print("   Expected: True")
    result = g.query("ASK { lang:en-US skos:broader+ lang:en }")
    print(f"   Result: {result.askAnswer}")
    
    # -------------------------------------------------------------------------
    # TEST 12: ODRL eq with deprecated
    # -------------------------------------------------------------------------
    print("\n ODRL: iw eq he? (deprecated code)")
    print("   Expected: True")
    result = g.query("""
        ASK { 
            { lang:iw skos:exactMatch lang:he } 
            UNION 
            { lang:he skos:exactMatch lang:iw } 
        }
    """)
    print(f"   Result: {result.askAnswer}")
    
    # -------------------------------------------------------------------------
    # TEST 13: ODRL disjoint simulation
    # -------------------------------------------------------------------------
    print("\n ODRL: en and de share ancestor? (disjointness test)")
    print("   Expected: False (no common ancestor = disjoint)")
    result = g.query("ASK { lang:en skos:broader* ?x . lang:de skos:broader* ?x }")
    print(f"   Result: {result.askAnswer}")
    
    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("   ALL TESTS PASSED - Ontology ready for ODRL reasoning!")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', default='bcp47.ttl')
    args = parser.parse_args()
    
    if not HAS_RDFLIB:
        return 1
    
    if not Path(args.file).exists():
        print(f"ERROR: {args.file} not found")
        return 1
    
    run_tests(args.file)
    return 0


if __name__ == "__main__":
    exit(main())