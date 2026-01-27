#!/usr/bin/env python3
"""Quick script to discover DPV namespace and Purpose class."""

from rdflib import Graph
from rdflib.namespace import RDF, RDFS, OWL
import sys

if len(sys.argv) < 2:
    print("Usage: python discover_ns.py <ttl_file>")
    sys.exit(1)

g = Graph()
g.parse(sys.argv[1], format="turtle")

print(f"Loaded {len(g)} triples")
print()

# Find all namespaces
print("=== Namespaces ===")
for prefix, ns in g.namespaces():
    if "dpv" in str(ns).lower() or "purpose" in str(ns).lower():
        print(f"  {prefix}: {ns}")

print()

# Find anything with "Purpose" in the name
print("=== Classes containing 'Purpose' ===")
for s, p, o in g:
    if "Purpose" in str(s):
        if (s, RDF.type, OWL.Class) in g or (s, RDF.type, RDFS.Class) in g:
            print(f"  {s}")
            # Show what it's a subclass of
            for _, _, parent in g.triples((s, RDFS.subClassOf, None)):
                print(f"    rdfs:subClassOf {parent}")
            break

print()

# Find the actual root
print("=== Looking for dpv:Purpose or dpv-owl:Purpose ===")
candidates = [
    "https://w3id.org/dpv#Purpose",
    "https://w3id.org/dpv/owl#Purpose", 
    "https://w3id.org/dpv-owl#Purpose",
]
for c in candidates:
    from rdflib import URIRef
    if (URIRef(c), None, None) in g:
        print(f"  FOUND: {c}")
        # Count subclasses
        count = len(list(g.subjects(RDFS.subClassOf, URIRef(c))))
        print(f"    Direct subclasses: {count}")

print()

# Direct search for subClassOf with Purpose
print("=== Direct subClassOf search ===")
count = 0
for s, p, o in g.triples((None, RDFS.subClassOf, None)):
    if "Purpose" in str(o):
        print(f"  {s} rdfs:subClassOf {o}")
        count += 1
        if count > 10:
            print("  ...")
            break
