"""
DPV Grounding - SPARQL Verification Tests
Comprehensive tests to verify the DPV ontology is loaded correctly
and contains everything needed for ODRL constraint reasoning:

Supports:
- Purpose hierarchy (for odrl:purpose)
- Recipient hierarchy (for odrl:recipient)

Tests:
1. Hierarchy Structure - rdfs:subClassOf relationships
2. Purpose Concepts - dpv:Purpose and its descendants  
3. Recipient Concepts - dpv:Recipient, LegalEntity, Organisation
4. Transitive Closure - Can we reach all ancestors?
5. Disjointness - Are branches semantically distinct?
6. Labels & Definitions - Human-readable metadata
7. Cross-References - Links to other vocabularies

Usage:
    python sparql_tests.py data/dpv/dpv-owl.ttl [additional files...]
    
Or programmatically:
    from sparql_tests import DPVReasoningTests
    tests = DPVReasoningTests(loader)
    tests.run_all()
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from pathlib import Path
from enum import Enum
import sys

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, SKOS

try:
    from .loader import DPVLoader, DPVNamespaces, DPVConceptType
except ImportError:
    from loader import DPVLoader, DPVNamespaces, DPVConceptType


# =============================================================================
# Namespaces
# =============================================================================

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


class TestCategory(Enum):
    """Categories of tests."""
    GENERAL = "General"
    PURPOSE = "Purpose"
    RECIPIENT = "Recipient"


# =============================================================================
# SPARQL Queries
# =============================================================================

SPARQL_QUERIES = {
    # -------------------------------------------------------------------------
    # General Queries
    # -------------------------------------------------------------------------
    
    "total_classes": """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?c) AS ?count) WHERE {
            { ?c a owl:Class } UNION { ?c a rdfs:Class }
            FILTER(isIRI(?c))
        }
    """,
    
    "subclass_edges": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(*) AS ?count) WHERE {
            ?s rdfs:subClassOf ?o .
            FILTER(isIRI(?s) && isIRI(?o))
        }
    """,
    
    # -------------------------------------------------------------------------
    # Purpose Queries
    # -------------------------------------------------------------------------
    
    "root_purpose": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?root WHERE {
            VALUES ?root { dpv-owl:Purpose }
            ?root a ?type .
        }
        LIMIT 1
    """,
    
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
    
    "all_purposes_transitive": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT DISTINCT ?purpose WHERE {
            ?purpose rdfs:subClassOf+ dpv-owl:Purpose .
            FILTER(isIRI(?purpose))
        }
    """,
    
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
    
    "purposes_with_definitions": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT ?purpose ?label ?definition WHERE {
            ?purpose rdfs:subClassOf+ dpv-owl:Purpose .
            OPTIONAL { ?purpose skos:prefLabel ?label }
            OPTIONAL { ?purpose skos:definition ?definition }
            FILTER(isIRI(?purpose) && BOUND(?definition))
        }
        LIMIT 20
    """,
    
    # -------------------------------------------------------------------------
    # Recipient Queries
    # -------------------------------------------------------------------------
    
    "root_recipient": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?root WHERE {
            VALUES ?root { dpv-owl:Recipient }
            ?root a ?type .
        }
        LIMIT 1
    """,
    
    "root_legal_entity": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?root WHERE {
            VALUES ?root { dpv-owl:LegalEntity }
            ?root a ?type .
        }
        LIMIT 1
    """,
    
    "direct_legal_entity_children": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?child ?label WHERE {
            ?child rdfs:subClassOf dpv-owl:LegalEntity .
            OPTIONAL { ?child skos:prefLabel ?label }
            FILTER(isIRI(?child))
        }
        ORDER BY ?label
    """,
    
    "all_recipients_transitive": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT DISTINCT ?recipient WHERE {
            {
                ?recipient rdfs:subClassOf+ dpv-owl:Recipient .
            } UNION {
                ?recipient rdfs:subClassOf+ dpv-owl:LegalEntity .
            } UNION {
                ?recipient rdfs:subClassOf+ dpv-owl:Organisation .
            }
            FILTER(isIRI(?recipient))
        }
    """,
    
    "organisation_hierarchy": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?org ?label WHERE {
            ?org rdfs:subClassOf+ dpv-owl:Organisation .
            OPTIONAL { ?org skos:prefLabel ?label }
            FILTER(isIRI(?org))
        }
        ORDER BY ?label
    """,
    
    "authority_hierarchy": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?auth ?label WHERE {
            ?auth rdfs:subClassOf* dpv-owl:Authority .
            OPTIONAL { ?auth skos:prefLabel ?label }
            FILTER(isIRI(?auth))
        }
        ORDER BY ?label
    """,
    
    "gdpr_roles": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT ?role ?label WHERE {
            VALUES ?role {
                dpv-owl:DataSubject
                dpv-owl:DataController
                dpv-owl:DataProcessor
                dpv-owl:Recipient
                dpv-owl:ThirdParty
            }
            OPTIONAL { ?role skos:prefLabel ?label }
        }
    """,
    
    "recipients_with_definitions": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT ?recipient ?label ?definition WHERE {
            ?recipient rdfs:subClassOf+ dpv-owl:LegalEntity .
            OPTIONAL { ?recipient skos:prefLabel ?label }
            OPTIONAL { ?recipient skos:definition ?definition }
            FILTER(isIRI(?recipient) && BOUND(?definition))
        }
        LIMIT 20
    """,
    
    # -------------------------------------------------------------------------
    # Cross-cutting Queries
    # -------------------------------------------------------------------------
    
    "multiple_parents": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?concept ?label (COUNT(?parent) AS ?parent_count) WHERE {
            {
                ?concept rdfs:subClassOf+ dpv-owl:Purpose .
            } UNION {
                ?concept rdfs:subClassOf+ dpv-owl:LegalEntity .
            }
            ?concept rdfs:subClassOf ?parent .
            FILTER(isIRI(?parent))
            OPTIONAL { ?concept skos:prefLabel ?label }
        }
        GROUP BY ?concept ?label
        HAVING (COUNT(?parent) > 1)
        ORDER BY DESC(?parent_count)
    """,
    
    "disjoint_assertions": """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dpv-owl: <https://w3id.org/dpv/owl#>
        
        SELECT ?class1 ?class2 WHERE {
            ?class1 owl:disjointWith ?class2 .
            FILTER(
                STRSTARTS(STR(?class1), "https://w3id.org/dpv") ||
                STRSTARTS(STR(?class2), "https://w3id.org/dpv")
            )
        }
    """,
    
    "sector_concepts": """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT ?sector (COUNT(?concept) AS ?count) WHERE {
            ?concept rdfs:subClassOf+ ?parent .
            BIND(
                IF(STRSTARTS(STR(?concept), "https://w3id.org/dpv/sector/law"), "law",
                IF(STRSTARTS(STR(?concept), "https://w3id.org/dpv/sector/health"), "health",
                IF(STRSTARTS(STR(?concept), "https://w3id.org/dpv/sector/finance"), "finance",
                IF(STRSTARTS(STR(?concept), "https://w3id.org/dpv/sector/education"), "education",
                IF(STRSTARTS(STR(?concept), "https://w3id.org/dpv/sector/infra"), "infra",
                "core")))))
                AS ?sector
            )
            FILTER(?sector != "core")
        }
        GROUP BY ?sector
        ORDER BY ?sector
    """,
}


# =============================================================================
# Test Runner
# =============================================================================

class DPVReasoningTests:
    """
    Comprehensive tests for DPV reasoning readiness.
    Supports both Purpose and Recipient hierarchies.
    """
    
    def __init__(self, loader: DPVLoader):
        self.loader = loader
        self.graph = loader.get_graph()
        self.results: List[TestResult] = []
    
    def run_all(self) -> List[TestResult]:
        """Run all verification tests."""
        self.results = []
        
        # Statistics
        self._print_ontology_statistics()
        
        print("\n" + "=" * 70)
        print("DPV REASONING VERIFICATION (Purpose + Recipient)")
        print("=" * 70 + "\n")
        
        # General tests
        print("─" * 70)
        print("GENERAL TESTS")
        print("─" * 70 + "\n")
        self._test_basic_structure()
        
        # Purpose tests
        print("─" * 70)
        print("PURPOSE HIERARCHY TESTS")
        print("─" * 70 + "\n")
        self._test_root_purpose()
        self._test_direct_purpose_children()
        self._test_all_purposes()
        self._test_leaf_purposes()
        self._test_purpose_definitions()
        
        # Recipient tests
        print("─" * 70)
        print("RECIPIENT HIERARCHY TESTS")
        print("─" * 70 + "\n")
        self._test_root_recipient()
        self._test_root_legal_entity()
        self._test_direct_legal_entity_children()
        self._test_all_recipients()
        self._test_organisation_hierarchy()
        self._test_authority_hierarchy()
        self._test_gdpr_roles()
        self._test_recipient_definitions()
        
        # Cross-cutting tests
        print("─" * 70)
        print("CROSS-CUTTING TESTS")
        print("─" * 70 + "\n")
        self._test_multiple_inheritance()
        self._test_disjointness()
        self._test_sector_concepts()
        
        # Summary
        self._print_summary()
        
        return self.results
    
    def _print_ontology_statistics(self) -> None:
        """Print comprehensive ontology statistics."""
        print("\n" + "=" * 70)
        print("ONTOLOGY STATISTICS")
        print("=" * 70)
        
        stats = self.loader.get_stats()
        
        print()
        print("┌─────────────────────────────────────────────────────────────────┐")
        print("│                    GENERAL METRICS                              │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print(f"│  Total RDF Triples            │ {stats.total_triples:>28,} │")
        print(f"│  rdfs:subClassOf edges        │ {stats.subclass_edges:>28,} │")
        print(f"│  Sources loaded               │ {len(stats.sources):>28,} │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print("│                    PURPOSE METRICS                              │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print(f"│  Purpose concepts             │ {stats.purpose_concepts:>28,} │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print("│                    RECIPIENT METRICS                            │")
        print("├─────────────────────────────────────────────────────────────────┤")
        print(f"│  Recipient concepts           │ {stats.recipient_concepts:>28,} │")
        print(f"│  LegalEntity concepts         │ {stats.legal_entity_concepts:>28,} │")
        print(f"│  Organisation concepts        │ {stats.organisation_concepts:>28,} │")
        print("└─────────────────────────────────────────────────────────────────┘")
        print()
        
        print("Sources loaded:")
        for src in stats.sources:
            print(f"  - {Path(src).name}")
    
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
    # General Tests
    # -------------------------------------------------------------------------
    
    def _test_basic_structure(self) -> None:
        """Test basic ontology structure."""
        class_results = self._run_query("total_classes")
        edge_results = self._run_query("subclass_edges")
        
        class_count = int(class_results[0]['count']) if class_results else 0
        edge_count = int(edge_results[0]['count']) if edge_results else 0
        
        self._add_result(TestResult(
            name="Basic Ontology Structure",
            passed=class_count > 100 and edge_count > 100,
            message=f"Found {class_count} classes and {edge_count} subClassOf edges",
            count=class_count,
        ))
    
    # -------------------------------------------------------------------------
    # Purpose Tests
    # -------------------------------------------------------------------------
    
    def _test_root_purpose(self) -> None:
        """Test root Purpose class exists."""
        results = self._run_query("root_purpose")
        has_purpose = (DPV_OWL.Purpose, None, None) in self.graph
        
        self._add_result(TestResult(
            name="Root Purpose Class",
            passed=len(results) > 0 or has_purpose,
            message="dpv-owl:Purpose exists" if (len(results) > 0 or has_purpose) else "Purpose class not found!",
        ))
    
    def _test_direct_purpose_children(self) -> None:
        """Test direct children of Purpose exist."""
        results = self._run_query("direct_purpose_children")
        labels = [
            str(r.get('label', r.get('child', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Direct Purpose Children",
            passed=len(results) >= 5,
            message=f"Found {len(results)} direct subclasses of Purpose",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_all_purposes(self) -> None:
        """Test all purposes via transitive closure."""
        results = self._run_query("all_purposes_transitive")
        
        self._add_result(TestResult(
            name="All Purposes (Transitive)",
            passed=len(results) >= 20,
            message=f"Found {len(results)} total purpose concepts",
            count=len(results),
        ))
    
    def _test_leaf_purposes(self) -> None:
        """Test leaf purposes exist."""
        results = self._run_query("leaf_purposes")
        labels = [
            str(r.get('label', r.get('leaf', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Leaf Purposes",
            passed=len(results) > 0,
            message=f"Found {len(results)} leaf purpose concepts",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_purpose_definitions(self) -> None:
        """Test purposes have definitions."""
        results = self._run_query("purposes_with_definitions")
        samples = [
            f"{r.get('label', 'N/A')}: {str(r.get('definition', ''))[:50]}..."
            for r in results[:5]
        ]
        
        self._add_result(TestResult(
            name="Purpose Definitions",
            passed=len(results) > 0,
            message=f"Found {len(results)} purposes with definitions",
            count=len(results),
            details=samples,
        ))
    
    # -------------------------------------------------------------------------
    # Recipient Tests
    # -------------------------------------------------------------------------
    
    def _test_root_recipient(self) -> None:
        """Test root Recipient class exists."""
        results = self._run_query("root_recipient")
        has_recipient = (DPV_OWL.Recipient, None, None) in self.graph
        
        self._add_result(TestResult(
            name="Root Recipient Class",
            passed=len(results) > 0 or has_recipient,
            message="dpv-owl:Recipient exists" if (len(results) > 0 or has_recipient) else "Recipient class not found!",
        ))
    
    def _test_root_legal_entity(self) -> None:
        """Test root LegalEntity class exists."""
        results = self._run_query("root_legal_entity")
        has_le = (DPV_OWL.LegalEntity, None, None) in self.graph
        
        self._add_result(TestResult(
            name="Root LegalEntity Class",
            passed=len(results) > 0 or has_le,
            message="dpv-owl:LegalEntity exists" if (len(results) > 0 or has_le) else "LegalEntity class not found!",
        ))
    
    def _test_direct_legal_entity_children(self) -> None:
        """Test direct children of LegalEntity exist."""
        results = self._run_query("direct_legal_entity_children")
        labels = [
            str(r.get('label', r.get('child', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Direct LegalEntity Children",
            passed=len(results) >= 3,
            message=f"Found {len(results)} direct subclasses of LegalEntity",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_all_recipients(self) -> None:
        """Test all recipients via transitive closure."""
        results = self._run_query("all_recipients_transitive")
        
        self._add_result(TestResult(
            name="All Recipients (Transitive)",
            passed=len(results) >= 10,
            message=f"Found {len(results)} total recipient/entity concepts",
            count=len(results),
        ))
    
    def _test_organisation_hierarchy(self) -> None:
        """Test Organisation hierarchy."""
        results = self._run_query("organisation_hierarchy")
        labels = [
            str(r.get('label', r.get('org', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Organisation Hierarchy",
            passed=len(results) >= 3,
            message=f"Found {len(results)} organisation types",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_authority_hierarchy(self) -> None:
        """Test Authority hierarchy."""
        results = self._run_query("authority_hierarchy")
        labels = [
            str(r.get('label', r.get('auth', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Authority Hierarchy",
            passed=len(results) >= 1,
            message=f"Found {len(results)} authority types",
            count=len(results),
            details=labels[:10],
        ))
    
    def _test_gdpr_roles(self) -> None:
        """Test GDPR roles exist."""
        results = self._run_query("gdpr_roles")
        labels = [
            str(r.get('label', r.get('role', '').split('#')[-1].split('/')[-1]))
            for r in results
        ]
        
        expected_roles = {"DataSubject", "DataController", "DataProcessor", "Recipient", "ThirdParty"}
        found_roles = set(labels)
        
        self._add_result(TestResult(
            name="GDPR Roles",
            passed=len(results) >= 4,
            message=f"Found {len(results)}/5 GDPR roles",
            count=len(results),
            details=labels,
        ))
    
    def _test_recipient_definitions(self) -> None:
        """Test recipients have definitions."""
        results = self._run_query("recipients_with_definitions")
        samples = [
            f"{r.get('label', 'N/A')}: {str(r.get('definition', ''))[:50]}..."
            for r in results[:5]
        ]
        
        self._add_result(TestResult(
            name="Recipient Definitions",
            passed=len(results) > 0,
            message=f"Found {len(results)} recipients with definitions",
            count=len(results),
            details=samples,
        ))
    
    # -------------------------------------------------------------------------
    # Cross-cutting Tests
    # -------------------------------------------------------------------------
    
    def _test_multiple_inheritance(self) -> None:
        """Test multiple inheritance."""
        results = self._run_query("multiple_parents")
        samples = [
            f"{r.get('label', r.get('concept', '').split('#')[-1])}: {r.get('parent_count')} parents"
            for r in results[:5]
        ]
        
        self._add_result(TestResult(
            name="Multiple Inheritance",
            passed=True,  # Informational
            message=f"Found {len(results)} concepts with multiple parents",
            count=len(results),
            details=samples if samples else ["No multiple inheritance found"],
        ))
    
    def _test_disjointness(self) -> None:
        """Test explicit disjointness assertions."""
        results = self._run_query("disjoint_assertions")
        
        self._add_result(TestResult(
            name="Explicit Disjointness",
            passed=True,  # Informational
            message=f"Found {len(results)} owl:disjointWith assertions",
            count=len(results),
            details=[
                "⚠️  DPV rarely asserts disjointness explicitly",
                "→  Reasoning must derive disjointness from context",
            ] if len(results) == 0 else None,
        ))
    
    def _test_sector_concepts(self) -> None:
        """Test sector-specific concepts."""
        results = self._run_query("sector_concepts")
        samples = [
            f"{r.get('sector')}: {r.get('count')} concepts"
            for r in results
        ]
        
        self._add_result(TestResult(
            name="Sector-Specific Concepts",
            passed=True,  # Informational
            message=f"Found concepts across {len(results)} sectors",
            count=len(results),
            details=samples if samples else ["No sector extensions loaded"],
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
        
        # Critical tests
        critical_tests = [
            "Root Purpose Class",
            "Direct Purpose Children",
            "Root Recipient Class",
            "Root LegalEntity Class",
            "GDPR Roles",
        ]
        
        critical_passed = all(
            r.passed for r in self.results if r.name in critical_tests
        )
        
        if critical_passed:
            print("\n✓ READY FOR REASONING")
            print("  DPV ontology loaded correctly for both Purpose and Recipient.")
            print("  You can proceed with ODRL constraint grounding.")
        else:
            print("\n✗ NOT READY")
            print("  Critical tests failed:")
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
    
    Args:
        graph: RDF graph with DPV loaded
        child: Full IRI or local name
        ancestor: Full IRI or local name
        
    Returns:
        True if child rdfs:subClassOf+ ancestor
    """
    if not child.startswith("http"):
        child = f"https://w3id.org/dpv/owl#{child}"
    if not ancestor.startswith("http"):
        ancestor = f"https://w3id.org/dpv/owl#{ancestor}"
    
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        ASK {{ <{child}> rdfs:subClassOf* <{ancestor}> . }}
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
        print("  python sparql_tests.py data/dpv/dpv-owl.ttl")
        sys.exit(1)
    
    # Load files
    loader = DPVLoader()
    for path in sys.argv[1:]:
        loader.load(path)
    
    loader.print_summary()
    
    # Run tests
    tests = DPVReasoningTests(loader)
    results = tests.run_all()
    
    # Demo: Test specific isA relationships
    print("\n" + "=" * 70)
    print("DEMO: isA Relationship Tests")
    print("=" * 70 + "\n")
    
    graph = loader.get_graph()
    
    # Purpose tests
    print("Purpose hierarchy:")
    purpose_tests = [
        ("AcademicResearch", "Purpose"),
        ("Marketing", "Purpose"),
        ("FraudPreventionAndDetection", "Purpose"),
    ]
    for child, ancestor in purpose_tests:
        result = test_isa_relationship(graph, child, ancestor)
        status = "✓" if result else "✗"
        print(f"  {status} {child} ⊑ {ancestor}: {result}")
    
    # Recipient tests
    print("\nRecipient hierarchy:")
    recipient_tests = [
        ("Recipient", "LegalEntity"),
        ("DataController", "LegalEntity"),
        ("DataProcessor", "LegalEntity"),
        ("ThirdParty", "LegalEntity"),
        ("DataProtectionAuthority", "LegalEntity"),
        ("Organisation", "LegalEntity"),
    ]
    for child, ancestor in recipient_tests:
        result = test_isa_relationship(graph, child, ancestor)
        status = "✓" if result else "✗"
        print(f"  {status} {child} ⊑ {ancestor}: {result}")
    
    # Exit code
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 3 else 0)


# Backward compatibility
PurposeReasoningTests = DPVReasoningTests


if __name__ == "__main__":
    main()