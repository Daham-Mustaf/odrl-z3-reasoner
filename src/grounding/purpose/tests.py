"""
DPV Purpose Grounding - SPARQL Verification Tests

Comprehensive tests to verify the DPV Purpose ontology is loaded correctly
and contains everything needed for ODRL constraint reasoning:

1. Hierarchy Structure - rdfs:subClassOf relationships
2. Purpose Concepts - dpv:Purpose and its descendants  
3. Transitive Closure - Can we reach all ancestors?
4. Disjointness - Are purpose branches semantically distinct?
5. Labels & Definitions - Human-readable metadata
6. Cross-References - Links to other vocabularies (SPECIAL, etc.)

Usage:
    python sparql_tests.py data/dpv/dpv-owl.ttl [additional files...]
    
Or programmatically:
    from sparql_tests import PurposeReasoningTests
    tests = PurposeReasoningTests(loader)
    tests.run_all()
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
import sys

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, SKOS

try:
    from .loader import DPVPurposeLoader, DPVNamespaces
except ImportError:
    from loader import DPVPurposeLoader, DPVNamespaces


# =============================================================================
# Namespaces
# =============================================================================

# The correct namespace for DPV-OWL is https://w3id.org/dpv/owl#
DPV_OWL = Namespace("https://w3id.org/dpv/owl#")


# =============================================================================
# Test Results
# =============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str
    details: Optional[List[str]] = None
    count: Optional[int] = None


# =============================================================================
# SPARQL Queries for Reasoning Verification
# =============================================================================

SPARQL_QUERIES = {
    # 1. Find the root Purpose class
    "root_purpose": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?root WHERE {
            VALUES ?root { dpv-owl:Purpose }
            ?root a ?type .
        }
        LIMIT 1
    """,
    
    # 2. Direct children of Purpose
    "direct_purpose_children": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?child ?label WHERE {
            ?child rdfs:subClassOf dpv-owl:Purpose .
            OPTIONAL { ?child skos:prefLabel ?label }
            FILTER(isIRI(?child))
        }
        ORDER BY ?label
    """,
    
    # 3. All purposes (transitive closure)
    "all_purposes_transitive": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT DISTINCT ?purpose WHERE {
            ?purpose rdfs:subClassOf+ dpv-owl:Purpose .
            FILTER(isIRI(?purpose))
        }
    """,
    
    # 4. Hierarchy depth (max levels)
    "hierarchy_depth_sample": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT ?leaf ?parent ?grandparent ?label WHERE {
            ?leaf rdfs:subClassOf ?parent .
            ?parent rdfs:subClassOf ?grandparent .
            ?grandparent rdfs:subClassOf+ dpv-owl:Purpose .
            OPTIONAL { ?leaf skos:prefLabel ?label }
            FILTER(isIRI(?leaf) && isIRI(?parent) && isIRI(?grandparent))
        }
        LIMIT 20
    """,
    
    # 5. Leaf purposes (no children)
    "leaf_purposes": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?leaf ?label WHERE {
            ?leaf rdfs:subClassOf+ dpv-owl:Purpose .
            FILTER NOT EXISTS { ?child rdfs:subClassOf ?leaf }
            OPTIONAL { ?leaf skos:prefLabel ?label }
            FILTER(isIRI(?leaf))
        }
        ORDER BY ?label
    """,
    
    # 6. Purposes with definitions
    "purposes_with_definitions": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dct: <http://purl.org/dc/terms/>
        
        SELECT ?purpose ?label ?definition WHERE {
            ?purpose rdfs:subClassOf+ dpv-owl:Purpose .
            OPTIONAL { ?purpose skos:prefLabel ?label }
            OPTIONAL { 
                ?purpose skos:definition ?definition .
            }
            FILTER(isIRI(?purpose) && BOUND(?definition))
        }
        LIMIT 20
    """,
    
    # 7. Cross-vocabulary references (SPECIAL, etc.)
    "cross_vocab_references": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?dpv_concept ?relation ?external WHERE {
            ?dpv_concept rdfs:subClassOf+ dpv-owl:Purpose .
            ?dpv_concept ?relation ?external .
            FILTER(
                ?relation IN (skos:related, skos:exactMatch, skos:closeMatch, skos:broadMatch, skos:narrowMatch, owl:equivalentClass)
                && !STRSTARTS(STR(?external), "https://w3id.org/dpv")
            )
        }
    """,
    
    # 8. Sector-specific purposes
    "sector_purposes": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?sector ?purpose ?label WHERE {
            ?purpose rdfs:subClassOf+ dpv-owl:Purpose .
            OPTIONAL { ?purpose skos:prefLabel ?label }
            BIND(
                IF(STRSTARTS(STR(?purpose), "https://w3id.org/dpv/sector/law"), "law",
                IF(STRSTARTS(STR(?purpose), "https://w3id.org/dpv/sector/health"), "health",
                IF(STRSTARTS(STR(?purpose), "https://w3id.org/dpv/sector/finance"), "finance",
                IF(STRSTARTS(STR(?purpose), "https://w3id.org/dpv/sector/education"), "education",
                IF(STRSTARTS(STR(?purpose), "https://w3id.org/dpv/sector/infra"), "infra",
                "core")))))
                AS ?sector
            )
            FILTER(?sector != "core")
        }
        ORDER BY ?sector ?label
    """,
    
    # 9. Multiple inheritance check
    "multiple_parents": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?concept ?label (COUNT(?parent) AS ?parent_count) WHERE {
            ?concept rdfs:subClassOf+ dpv-owl:Purpose .
            ?concept rdfs:subClassOf ?parent .
            FILTER(isIRI(?parent))
            OPTIONAL { ?concept skos:prefLabel ?label }
        }
        GROUP BY ?concept ?label
        HAVING (COUNT(?parent) > 1)
        ORDER BY DESC(?parent_count)
    """,
    
    # 10. Check for explicit disjointness assertions
    "disjoint_assertions": """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?class1 ?class2 WHERE {
            {
                ?class1 owl:disjointWith ?class2 .
            } UNION {
                ?class1 a owl:AllDisjointClasses ;
                    owl:members ?list .
            }
            FILTER(
                STRSTARTS(STR(?class1), "https://w3id.org/dpv") ||
                STRSTARTS(STR(?class2), "https://w3id.org/dpv")
            )
        }
    """,
}


# =============================================================================
# Test Runner
# =============================================================================

class PurposeReasoningTests:
    """
    Comprehensive tests for DPV Purpose reasoning readiness.
    """
    
    def __init__(self, loader: DPVPurposeLoader):
        self.loader = loader
        self.graph = loader.get_graph()
        self.results: List[TestResult] = []
    
    def run_all(self) -> List[TestResult]:
        """Run all verification tests."""
        self.results = []
        
        # Print comprehensive statistics first
        self._print_ontology_statistics()
        
        print("\n" + "=" * 70)
        print("DPV PURPOSE REASONING VERIFICATION")
        print("=" * 70 + "\n")
        
        # Run each test
        self._test_root_purpose()
        self._test_direct_children()
        self._test_transitive_closure()
        self._test_hierarchy_depth()
        self._test_leaf_purposes()
        self._test_labels_and_definitions()
        self._test_cross_vocab()
        self._test_sector_purposes()
        self._test_multiple_inheritance()
        self._test_disjointness()
        
        # Summary
        self._print_summary()
        
        return self.results
    
    def _print_ontology_statistics(self) -> None:
        """Print comprehensive ontology statistics."""
        print("\n" + "=" * 70)
        print("ONTOLOGY STATISTICS")
        print("=" * 70)
        
        # Basic counts
        total_triples = len(self.graph)
        
        # Count classes (owl:Class)
        classes_query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT (COUNT(DISTINCT ?c) AS ?count) WHERE {
                { ?c a owl:Class } UNION { ?c a rdfs:Class }
                FILTER(isIRI(?c))
            }
        """
        class_count = list(self.graph.query(classes_query))[0][0]
        
        # Count subClassOf relationships
        subclass_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT (COUNT(*) AS ?count) WHERE {
                ?s rdfs:subClassOf ?o .
                FILTER(isIRI(?s) && isIRI(?o))
            }
        """
        subclass_count = list(self.graph.query(subclass_query))[0][0]
        
        # Count properties (owl:ObjectProperty, owl:DatatypeProperty)
        props_query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE {
                { ?p a owl:ObjectProperty } UNION 
                { ?p a owl:DatatypeProperty } UNION
                { ?p a rdf:Property }
            }
        """
        prop_count = list(self.graph.query(props_query))[0][0]
        
        # Count individuals (owl:NamedIndividual)
        individuals_query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT (COUNT(DISTINCT ?i) AS ?count) WHERE {
                ?i a owl:NamedIndividual .
            }
        """
        individual_count = list(self.graph.query(individuals_query))[0][0]
        
        # Count disjoint assertions
        disjoint_query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT (COUNT(*) AS ?count) WHERE {
                { ?a owl:disjointWith ?b } UNION
                { ?x a owl:AllDisjointClasses }
            }
        """
        disjoint_count = list(self.graph.query(disjoint_query))[0][0]
        
        # Count equivalent class assertions
        equiv_query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT (COUNT(*) AS ?count) WHERE {
                ?a owl:equivalentClass ?b .
                FILTER(isIRI(?a) && isIRI(?b))
            }
        """
        equiv_count = list(self.graph.query(equiv_query))[0][0]
        
        # Purpose-specific stats
        purpose_direct_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE {
                ?p rdfs:subClassOf dpv-owl:Purpose .
            }
        """
        purpose_direct = list(self.graph.query(purpose_direct_query))[0][0]
        
        purpose_all_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE {
                ?p rdfs:subClassOf+ dpv-owl:Purpose .
            }
        """
        purpose_all = list(self.graph.query(purpose_all_query))[0][0]
        
        # Hierarchy depth estimation
        depth_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT ?p (COUNT(?mid) AS ?depth) WHERE {
                ?p rdfs:subClassOf+ ?mid .
                ?mid rdfs:subClassOf* dpv-owl:Purpose .
            }
            GROUP BY ?p
            ORDER BY DESC(?depth)
            LIMIT 1
        """
        max_depth_results = list(self.graph.query(depth_query))
        max_depth = max_depth_results[0][1] if max_depth_results else 0
        
        # Multiple inheritance count
        multi_inherit_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT (COUNT(DISTINCT ?c) AS ?count) WHERE {
                ?c rdfs:subClassOf+ dpv-owl:Purpose .
                ?c rdfs:subClassOf ?p1 .
                ?c rdfs:subClassOf ?p2 .
                FILTER(?p1 != ?p2 && isIRI(?p1) && isIRI(?p2))
            }
        """
        multi_inherit = list(self.graph.query(multi_inherit_query))[0][0]
        
        # Leaf nodes (no children)
        leaf_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT (COUNT(DISTINCT ?leaf) AS ?count) WHERE {
                ?leaf rdfs:subClassOf+ dpv-owl:Purpose .
                FILTER NOT EXISTS { ?child rdfs:subClassOf ?leaf }
            }
        """
        leaf_count = list(self.graph.query(leaf_query))[0][0]
        
        # Labels count
        labels_query = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE {
                ?p rdfs:subClassOf+ dpv-owl:Purpose .
                { ?p skos:prefLabel ?l } UNION { ?p rdfs:label ?l }
            }
        """
        with_labels = list(self.graph.query(labels_query))[0][0]
        
        # Definitions count
        defs_query = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
            SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE {
                ?p rdfs:subClassOf+ dpv-owl:Purpose .
                ?p skos:definition ?d .
            }
        """
        with_defs = list(self.graph.query(defs_query))[0][0]
        
        # Print all stats - convert to int for formatting
        total_triples = int(total_triples) if total_triples else 0
        class_count = int(class_count) if class_count else 0
        subclass_count = int(subclass_count) if subclass_count else 0
        prop_count = int(prop_count) if prop_count else 0
        individual_count = int(individual_count) if individual_count else 0
        disjoint_count = int(disjoint_count) if disjoint_count else 0
        equiv_count = int(equiv_count) if equiv_count else 0
        purpose_direct = int(purpose_direct) if purpose_direct else 0
        purpose_all = int(purpose_all) if purpose_all else 0
        max_depth = int(max_depth) if max_depth else 0
        multi_inherit = int(multi_inherit) if multi_inherit else 0
        leaf_count = int(leaf_count) if leaf_count else 0
        with_labels = int(with_labels) if with_labels else 0
        with_defs = int(with_defs) if with_defs else 0
        
        # Print all stats
        print()
        print("┌─────────────────────────────────────────────────────────────────┐")
        print("│                    GENERAL ONTOLOGY METRICS                     │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print(f"│  Total RDF Triples            │ {total_triples:>28,} │")
        print(f"│  OWL/RDFS Classes             │ {class_count:>28,} │")
        print(f"│  Properties                   │ {prop_count:>28,} │")
        print(f"│  Named Individuals            │ {individual_count:>28,} │")
        print(f"│  rdfs:subClassOf edges        │ {subclass_count:>28,} │")
        print(f"│  owl:disjointWith assertions  │ {disjoint_count:>28,} │")
        print(f"│  owl:equivalentClass          │ {equiv_count:>28,} │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print("│                    PURPOSE HIERARCHY METRICS                    │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print(f"│  Direct children of Purpose   │ {purpose_direct:>28,} │")
        print(f"│  All Purpose descendants      │ {purpose_all:>28,} │")
        print(f"│  Leaf purposes (most specific)│ {leaf_count:>28,} │")
        print(f"│  Max hierarchy depth          │ {max_depth:>28,} │")
        print(f"│  Multi-parent concepts        │ {multi_inherit:>28,} │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print("│                    ANNOTATION COVERAGE                          │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print(f"│  Purposes with labels         │ {with_labels:>28,} │")
        print(f"│  Purposes with definitions    │ {with_defs:>28,} │")
        coverage = (with_defs / purpose_all * 100) if purpose_all > 0 else 0
        print(f"│  Definition coverage          │ {coverage:>27.1f}% │")
        print("└─────────────────────────────────────────────────────────────────┘")
        print()
        self._test_direct_children()
        self._test_transitive_closure()
        self._test_hierarchy_depth()
        self._test_leaf_purposes()
        self._test_labels_and_definitions()
        self._test_cross_vocab()
        self._test_sector_purposes()
        self._test_multiple_inheritance()
        self._test_disjointness()
        
        # Summary
        self._print_summary()
        
        return self.results
    
    def _run_query(self, name: str) -> List[dict]:
        """Run a named SPARQL query."""
        query = SPARQL_QUERIES[name]
        results = []
        for row in self.graph.query(query):
            results.append({str(k): v for k, v in row.asdict().items()})
        return results
    
    def _add_result(self, result: TestResult) -> None:
        """Add and print a test result."""
        self.results.append(result)
        
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{status}: {result.name}")
        print(f"       {result.message}")
        if result.count is not None:
            print(f"       Count: {result.count}")
        if result.details:
            for detail in result.details[:5]:
                print(f"         - {detail}")
            if len(result.details) > 5:
                print(f"         ... and {len(result.details) - 5} more")
        print()
    
    # -------------------------------------------------------------------------
    # Individual Tests
    # -------------------------------------------------------------------------
    
    def _test_root_purpose(self) -> None:
        """Test 1: Verify root Purpose class exists."""
        results = self._run_query("root_purpose")
        
        # Also try direct check
        has_dpv_owl = (DPV_OWL.Purpose, None, None) in self.graph
        
        self._add_result(TestResult(
            name="Root Purpose Class",
            passed=len(results) > 0 or has_dpv_owl,
            message="dpv-owl:Purpose exists in graph" if (len(results) > 0 or has_dpv_owl) else "Root Purpose class not found!",
            details=[str(r.get('root', '')) for r in results] if results else None,
        ))
    
    def _test_direct_children(self) -> None:
        """Test 2: Verify direct children of Purpose exist."""
        results = self._run_query("direct_purpose_children")
        
        labels = [
            str(r.get('label', r.get('child', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Direct Purpose Children",
            passed=len(results) >= 5,  # Should have at least 5 top-level purposes
            message=f"Found {len(results)} direct subclasses of Purpose",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_transitive_closure(self) -> None:
        """Test 3: Verify transitive closure works."""
        results = self._run_query("all_purposes_transitive")
        
        self._add_result(TestResult(
            name="Transitive Closure (All Purposes)",
            passed=len(results) >= 20,  # Should have many purposes
            message=f"Found {len(results)} total purpose concepts via rdfs:subClassOf+",
            count=len(results),
        ))
    
    def _test_hierarchy_depth(self) -> None:
        """Test 4: Verify hierarchy has depth > 2."""
        results = self._run_query("hierarchy_depth_sample")
        
        samples = []
        for r in results[:5]:
            leaf = str(r.get('leaf', '')).split('#')[-1].split('/')[-1]
            parent = str(r.get('parent', '')).split('#')[-1].split('/')[-1]
            grandparent = str(r.get('grandparent', '')).split('#')[-1].split('/')[-1]
            samples.append(f"{grandparent} > {parent} > {leaf}")
        
        self._add_result(TestResult(
            name="Hierarchy Depth",
            passed=len(results) > 0,
            message=f"Found {len(results)} purposes at depth 3+",
            count=len(results),
            details=samples,
        ))
    
    def _test_leaf_purposes(self) -> None:
        """Test 5: Verify leaf purposes exist (no children)."""
        results = self._run_query("leaf_purposes")
        
        labels = [
            str(r.get('label', r.get('leaf', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Leaf Purposes (Most Specific)",
            passed=len(results) > 0,
            message=f"Found {len(results)} leaf purpose concepts",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_labels_and_definitions(self) -> None:
        """Test 6: Verify labels and definitions exist."""
        results = self._run_query("purposes_with_definitions")
        
        samples = []
        for r in results[:5]:
            label = str(r.get('label', 'No label'))
            definition = str(r.get('definition', ''))[:60] + "..."
            samples.append(f"{label}: {definition}")
        
        self._add_result(TestResult(
            name="Labels & Definitions",
            passed=len(results) > 0,
            message=f"Found {len(results)} purposes with definitions",
            count=len(results),
            details=samples,
        ))
    
    def _test_cross_vocab(self) -> None:
        """Test 7: Check cross-vocabulary references."""
        results = self._run_query("cross_vocab_references")
        
        samples = []
        for r in results[:5]:
            dpv = str(r.get('dpv_concept', '')).split('#')[-1].split('/')[-1]
            rel = str(r.get('relation', '')).split('#')[-1]
            ext = str(r.get('external', ''))
            samples.append(f"{dpv} --{rel}--> {ext}")
        
        self._add_result(TestResult(
            name="Cross-Vocabulary References",
            passed=True,  # Optional, not required
            message=f"Found {len(results)} cross-vocabulary links (SPECIAL, etc.)",
            count=len(results),
            details=samples if samples else ["No external vocab links found (OK)"],
        ))
    
    def _test_sector_purposes(self) -> None:
        """Test 8: Check sector-specific purposes."""
        results = self._run_query("sector_purposes")
        
        # Group by sector
        sectors: Dict[str, int] = {}
        for r in results:
            sector = str(r.get('sector', 'unknown'))
            sectors[sector] = sectors.get(sector, 0) + 1
        
        samples = [f"{s}: {c} purposes" for s, c in sorted(sectors.items())]
        
        self._add_result(TestResult(
            name="Sector-Specific Purposes",
            passed=True,  # Optional depending on loaded files
            message=f"Found {len(results)} sector-specific purposes across {len(sectors)} sectors",
            count=len(results),
            details=samples,
        ))
    
    def _test_multiple_inheritance(self) -> None:
        """Test 9: Check for multiple inheritance."""
        results = self._run_query("multiple_parents")
        
        samples = []
        for r in results[:5]:
            label = str(r.get('label', r.get('concept', '').split('#')[-1].split('/')[-1]))
            count = r.get('parent_count', 0)
            samples.append(f"{label} has {count} parents")
        
        self._add_result(TestResult(
            name="Multiple Inheritance",
            passed=True,  # Just informational
            message=f"Found {len(results)} concepts with multiple parents (poly-hierarchy)",
            count=len(results),
            details=samples if samples else ["No multiple inheritance found"],
        ))
    
    def _test_disjointness(self) -> None:
        """Test 10: Check explicit disjointness assertions."""
        results = self._run_query("disjoint_assertions")
        
        self._add_result(TestResult(
            name="Explicit Disjointness",
            passed=True,  # Just informational
            message=f"Found {len(results)} explicit owl:disjointWith assertions",
            count=len(results),
            details=[
                "⚠️  DPV rarely asserts disjointness explicitly",
                "→  Oracle must derive disjointness from branch analysis",
            ] if len(results) == 0 else None,
        ))
    
    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    
    def _print_summary(self) -> None:
        """Print test summary."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print("\n" + "=" * 70)
        print(f"SUMMARY: {passed}/{total} tests passed")
        print("=" * 70)
        
        # Reasoning readiness assessment
        critical_tests = [
            "Direct Purpose Children",
            "Transitive Closure (All Purposes)",
        ]
        
        critical_passed = all(
            r.passed for r in self.results if r.name in critical_tests
        )
        
        if critical_passed:
            print("\n✓ READY FOR REASONING")
            print("  The DPV Purpose ontology is loaded correctly.")
            print("  You can proceed to implement the PurposeOracle.")
        else:
            print("\n✗ NOT READY")
            print("  Critical tests failed. Check:")
            for r in self.results:
                if r.name in critical_tests and not r.passed:
                    print(f"    - {r.name}")
        
        print()


# =============================================================================
# Standalone Test Utilities
# =============================================================================

def test_isa_relationship(graph: Graph, child: str, ancestor: str) -> bool:
    """
    Test if child isA ancestor (transitive subClassOf).
    
    This is the core reasoning operation for ODRL purpose constraints.
    
    Args:
        graph: RDF graph with DPV loaded
        child: Full IRI or local name of child concept
        ancestor: Full IRI or local name of ancestor concept
        
    Returns:
        True if child rdfs:subClassOf+ ancestor
    """
    # Normalize to URIRef - use dpv-owl namespace
    if not child.startswith("http"):
        child = f"https://w3id.org/dpv/owl#{child}"
    if not ancestor.startswith("http"):
        ancestor = f"https://w3id.org/dpv/owl#{ancestor}"
    
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        ASK {{
            <{child}> rdfs:subClassOf* <{ancestor}> .
        }}
    """
    
    return bool(graph.query(query))


def get_ancestors(graph: Graph, concept: str) -> Set[str]:
    """Get all ancestors of a concept."""
    if not concept.startswith("http"):
        concept = f"https://w3id.org/dpv/owl#{concept}"
    
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?ancestor WHERE {{
            <{concept}> rdfs:subClassOf+ ?ancestor .
            FILTER(isIRI(?ancestor))
        }}
    """
    
    return {str(row.ancestor) for row in graph.query(query)}


def get_descendants(graph: Graph, concept: str) -> Set[str]:
    """Get all descendants of a concept."""
    if not concept.startswith("http"):
        concept = f"https://w3id.org/dpv/owl#{concept}"
    
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?descendant WHERE {{
            ?descendant rdfs:subClassOf+ <{concept}> .
            FILTER(isIRI(?descendant))
        }}
    """
    
    return {str(row.descendant) for row in graph.query(query)}


# =============================================================================
# Main
# =============================================================================

def main():
    """Run tests from command line."""
    if len(sys.argv) < 2:
        print("Usage: python sparql_tests.py <ttl_file> [additional files...]")
        print()
        print("Example:")
        print("  python sparql_tests.py data/dpv/dpv-owl.ttl data/dpv/sector-law-owl.ttl")
        sys.exit(1)
    
    # Load files
    loader = DPVPurposeLoader()
    for path in sys.argv[1:]:
        loader.load(path)
    
    loader.print_summary()
    
    # Run tests
    tests = PurposeReasoningTests(loader)
    results = tests.run_all()
    
    # Demo: Test specific isA relationships
    print("\n" + "=" * 70)
    print("DEMO: isA Relationship Tests")
    print("=" * 70 + "\n")
    
    graph = loader.get_graph()
    
    # Test cases
    test_cases = [
        ("AcademicResearch", "Purpose"),
        ("AcademicResearch", "ResearchAndDevelopment"),
        ("Marketing", "Purpose"),
        ("FraudPreventionAndDetection", "Purpose"),
    ]
    
    for child, ancestor in test_cases:
        result = test_isa_relationship(graph, child, ancestor)
        status = "✓" if result else "✗"
        print(f"  {status} {child} isA {ancestor}: {result}")
    
    # Exit with appropriate code
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 2 else 0)  # Allow some informational "failures"


if __name__ == "__main__":
    main()
    
    
# python3 -m src.grounding.purpose.sparql_tests \
#     data/dpv/dpv-owl.ttl \
#     data/dpv/sector-law-owl.ttl \
#     data/dpv/sector-health-owl.ttl \
#     data/dpv/sector-finance-owl.ttl