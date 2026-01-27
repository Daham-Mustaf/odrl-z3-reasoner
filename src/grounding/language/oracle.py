"""
Purpose Oracle

Provides semantic reasoning operations for ODRL purpose constraints.

Uses DPV (Data Privacy Vocabulary) OWL ontology for subsumption reasoning.

Reasoning Operations:
    - isA(child, parent): Check if child purpose is a specialization of parent
    - eq(a, b): Check if two purposes are equivalent
    - are_disjoint(a, b): Check if two purposes are disjoint (derived)
    - exists(purpose): Check if purpose is known

Usage:
    from grounding.purpose.loader import DPVPurposeLoader
    from grounding.purpose.oracle import PurposeOracle
    
    loader = DPVPurposeLoader()
    loader.load("data/dpv/dpv-owl.ttl")
    
    oracle = PurposeOracle(loader.get_graph())
    
    # Check relationships
    oracle.is_a("Marketing", "Purpose")  # True
    oracle.is_a("DirectMarketing", "Marketing")  # True
    oracle.is_a("AcademicResearch", "ResearchAndDevelopment")  # True
"""

from typing import Set, Optional, List, Dict
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

# DPV OWL namespace
DPV_OWL = Namespace("https://w3id.org/dpv/owl#")


class PurposeOracle:
    """
    Semantic reasoning oracle for DPV Purpose hierarchy.
    
    Uses OWL/RDFS hierarchy:
        - rdfs:subClassOf for parent relationships
        - skos:prefLabel for labels
        - owl:equivalentClass for equivalences
    
    Note: DPV has NO explicit owl:disjointWith assertions.
    Disjointness must be derived from branch analysis.
    """
    
    ROOT_CLASS = DPV_OWL.Purpose
    
    def __init__(self, graph: Graph, namespace: Namespace = None):
        """
        Initialize oracle with an RDF graph containing the DPV ontology.
        
        Args:
            graph: RDFLib graph with DPV Purpose hierarchy loaded
            namespace: DPV namespace (default: https://w3id.org/dpv/owl#)
        """
        self._graph = graph
        self._ns = namespace or DPV_OWL
        self._cache_mappings()
    
    def _cache_mappings(self) -> None:
        """Cache purpose name to URI mappings for performance."""
        self._name_to_uri: Dict[str, URIRef] = {}
        self._uri_to_name: Dict[URIRef, str] = {}
        
        # Find all purposes (subclasses of dpv-owl:Purpose)
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dpv-owl: <{self._ns}>
            
            SELECT ?purpose ?label WHERE {{
                ?purpose rdfs:subClassOf+ dpv-owl:Purpose .
                OPTIONAL {{ ?purpose skos:prefLabel ?label }}
            }}
        """
        
        for row in self._graph.query(query):
            uri = row.purpose
            if isinstance(uri, URIRef):
                # Extract local name from URI
                local_name = str(uri).split("#")[-1].split("/")[-1]
                self._name_to_uri[local_name.lower()] = uri
                self._uri_to_name[uri] = local_name
                
                # Also cache with label if available
                if row.label:
                    label = str(row.label).lower()
                    self._name_to_uri[label] = uri
    
    def _resolve(self, purpose: str) -> Optional[URIRef]:
        """Resolve a purpose name to its URI."""
        # Normalize: strip, don't lowercase (DPV uses CamelCase)
        purpose_lower = purpose.strip().lower()
        
        # Direct lookup from cache
        if purpose_lower in self._name_to_uri:
            return self._name_to_uri[purpose_lower]
        
        # Try as full URI
        if purpose.startswith("http"):
            uri = URIRef(purpose)
            if (uri, RDF.type, OWL.Class) in self._graph or \
               (uri, RDFS.subClassOf, None) in self._graph:
                return uri
        
        # Try constructing URI directly with DPV namespace
        uri = self._ns[purpose]
        if (uri, RDF.type, OWL.Class) in self._graph or \
           (uri, RDFS.subClassOf, None) in self._graph:
            return uri
        
        return None
    
    # =========================================================================
    # Core Reasoning Operations
    # =========================================================================
    
    def is_a(self, child: str, parent: str) -> bool:
        """
        Check if child purpose is a specialization of parent.
        
        Uses rdfs:subClassOf* for transitive closure.
        
        Args:
            child: Purpose name (e.g., "DirectMarketing")
            parent: Purpose name (e.g., "Marketing")
            
        Returns:
            True if child rdfs:subClassOf* parent
            
        Examples:
            is_a("DirectMarketing", "Marketing") → True
            is_a("Marketing", "Purpose") → True
            is_a("AcademicResearch", "ResearchAndDevelopment") → True
            is_a("Marketing", "ResearchAndDevelopment") → False
        """
        child_uri = self._resolve(child)
        parent_uri = self._resolve(parent)
        
        if child_uri is None or parent_uri is None:
            return False
        
        # Same URI
        if child_uri == parent_uri:
            return True
        
        # Use SPARQL for transitive closure
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            ASK {{
                <{child_uri}> rdfs:subClassOf* <{parent_uri}> .
            }}
        """
        
        return bool(self._graph.query(query))
    
    def eq(self, a: str, b: str) -> bool:
        """
        Check if two purposes are equivalent.
        
        Handles:
            - Same name (case-insensitive)
            - Same URI
            - owl:equivalentClass relationships
            
        Args:
            a: First purpose
            b: Second purpose
            
        Returns:
            True if a and b are equivalent
        """
        # Normalize and compare
        if a.lower().strip() == b.lower().strip():
            return True
        
        a_uri = self._resolve(a)
        b_uri = self._resolve(b)
        
        if a_uri is None or b_uri is None:
            return False
        
        # Same URI
        if a_uri == b_uri:
            return True
        
        # Check owl:equivalentClass (bidirectional)
        if (a_uri, OWL.equivalentClass, b_uri) in self._graph:
            return True
        if (b_uri, OWL.equivalentClass, a_uri) in self._graph:
            return True
        
        return False
    
    def are_disjoint(self, a: str, b: str) -> bool:
        """
        Check if two purposes are disjoint (cannot overlap).
        
        IMPORTANT: DPV has NO explicit owl:disjointWith assertions!
        This method derives disjointness from branch structure.
        
        Two purposes are disjoint if:
            1. Neither is an ancestor of the other
            2. They don't share any common descendants
        
        Args:
            a: First purpose
            b: Second purpose
            
        Returns:
            True if a and b are disjoint
        """
        a_uri = self._resolve(a)
        b_uri = self._resolve(b)
        
        if a_uri is None or b_uri is None:
            return False  # Unknown purposes - can't determine
        
        # If one is ancestor of other, not disjoint
        if self.is_a(a, b) or self.is_a(b, a):
            return False
        
        # Check for common descendants
        a_descendants = self.get_descendants(a)
        b_descendants = self.get_descendants(b)
        
        if a_descendants & b_descendants:
            # Shared descendants means not disjoint
            return False
        
        # Different branches with no common descendants → disjoint
        return True
    
    def exists(self, purpose: str) -> bool:
        """Check if a purpose exists in the ontology."""
        return self._resolve(purpose) is not None
    
    def get_parent(self, purpose: str) -> Optional[str]:
        """Get the direct parent purpose (may have multiple - returns first)."""
        uri = self._resolve(purpose)
        if uri is None:
            return None
        
        for _, _, parent in self._graph.triples((uri, RDFS.subClassOf, None)):
            if isinstance(parent, URIRef) and parent in self._uri_to_name:
                return self._uri_to_name[parent]
        
        return None
    
    def get_parents(self, purpose: str) -> Set[str]:
        """Get all direct parent purposes (DPV has multi-inheritance)."""
        uri = self._resolve(purpose)
        if uri is None:
            return set()
        
        parents = set()
        for _, _, parent in self._graph.triples((uri, RDFS.subClassOf, None)):
            if isinstance(parent, URIRef) and parent in self._uri_to_name:
                parents.add(self._uri_to_name[parent])
        
        return parents
    
    def get_ancestors(self, purpose: str) -> Set[str]:
        """Get all ancestor purposes (transitive)."""
        uri = self._resolve(purpose)
        if uri is None:
            return set()
        
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?ancestor WHERE {{
                <{uri}> rdfs:subClassOf+ ?ancestor .
                FILTER(isIRI(?ancestor))
            }}
        """
        
        ancestors = set()
        for row in self._graph.query(query):
            if row.ancestor in self._uri_to_name:
                ancestors.add(self._uri_to_name[row.ancestor])
        
        return ancestors
    
    def get_children(self, purpose: str) -> Set[str]:
        """Get direct child purposes."""
        uri = self._resolve(purpose)
        if uri is None:
            return set()
        
        children = set()
        for child, _, _ in self._graph.triples((None, RDFS.subClassOf, uri)):
            if isinstance(child, URIRef) and child in self._uri_to_name:
                children.add(self._uri_to_name[child])
        
        return children
    
    def get_descendants(self, purpose: str) -> Set[str]:
        """Get all descendant purposes (transitive)."""
        uri = self._resolve(purpose)
        if uri is None:
            return set()
        
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?descendant WHERE {{
                ?descendant rdfs:subClassOf+ <{uri}> .
                FILTER(isIRI(?descendant))
            }}
        """
        
        descendants = set()
        for row in self._graph.query(query):
            if row.descendant in self._uri_to_name:
                descendants.add(self._uri_to_name[row.descendant])
        
        return descendants
    
    def get_top_level_purposes(self) -> Set[str]:
        """Get direct children of dpv:Purpose (top-level categories)."""
        return self.get_children("Purpose")
    
    # =========================================================================
    # ODRL Operator Support
    # =========================================================================
    
    def evaluate_constraint(
        self, 
        operator: str, 
        left_value: str, 
        right_value: str
    ) -> Optional[bool]:
        """
        Evaluate an ODRL constraint on purpose.
        
        Args:
            operator: ODRL operator (eq, neq, isA, isPartOf, etc.)
            left_value: The actual purpose value
            right_value: The constraint value
            
        Returns:
            True/False if evaluable, None if cannot determine
        """
        op = operator.lower()
        
        if op == "eq":
            return self.eq(left_value, right_value)
        
        elif op == "neq":
            return not self.eq(left_value, right_value)
        
        elif op in ("isa", "is_a"):
            return self.is_a(left_value, right_value)
        
        elif op in ("ispartof", "is_part_of"):
            return self.is_a(left_value, right_value)
        
        elif op in ("isanyof", "is_any_of"):
            if isinstance(right_value, (list, set, tuple)):
                return any(self.eq(left_value, rv) or self.is_a(left_value, rv) 
                          for rv in right_value)
            return None
        
        elif op in ("isnoneof", "is_none_of"):
            if isinstance(right_value, (list, set, tuple)):
                return all(not self.eq(left_value, rv) and not self.is_a(left_value, rv)
                          for rv in right_value)
            return None
        
        else:
            return None


# =============================================================================
# Main - Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Try to import loader
    try:
        from loader import DPVPurposeLoader
    except ImportError:
        try:
            from .loader import DPVPurposeLoader
        except ImportError:
            print("Cannot import DPVPurposeLoader")
            DPVPurposeLoader = None
    
    if len(sys.argv) < 2:
        print("Usage: python oracle.py <path-to-dpv-owl.ttl> [additional-files...]")
        print()
        print("Example: python oracle.py data/dpv/dpv-owl.ttl data/dpv/sector-*.ttl")
        sys.exit(1)
    
    # Load graph
    g = Graph()
    for path in sys.argv[1:]:
        print(f"Loading: {path}")
        g.parse(path, format="turtle")
    print(f"Total triples: {len(g)}")
    
    # Create oracle
    oracle = PurposeOracle(g)
    
    print()
    print("=" * 60)
    print("PURPOSE ORACLE TESTS")
    print("=" * 60)
    
    # Test isA
    print("\nisA tests (child, parent, expected):")
    isa_tests = [
        ("Marketing", "Purpose", True),
        ("DirectMarketing", "Marketing", True),
        ("AcademicResearch", "ResearchAndDevelopment", True),
        ("FraudPreventionAndDetection", "EnforceSecurity", True),
        ("Marketing", "ResearchAndDevelopment", False),
        ("Purpose", "Marketing", False),
    ]
    
    for child, parent, expected in isa_tests:
        result = oracle.is_a(child, parent)
        status = "✓" if result == expected else "✗"
        print(f"  {status} isA({child}, {parent}) = {result}")
    
    # Test eq
    print("\neq tests:")
    eq_tests = [
        ("Marketing", "Marketing", True),
        ("marketing", "Marketing", True),  # Case insensitive
        ("Marketing", "DirectMarketing", False),
    ]
    
    for a, b, expected in eq_tests:
        result = oracle.eq(a, b)
        status = "✓" if result == expected else "✗"
        print(f"  {status} eq({a}, {b}) = {result}")
    
    # Test disjointness (derived)
    print("\nare_disjoint tests (derived from structure):")
    disjoint_tests = [
        ("Marketing", "ResearchAndDevelopment", True),  # Different branches
        ("Marketing", "DirectMarketing", False),  # Parent-child
        ("DirectMarketing", "Marketing", False),  # Child-parent
    ]
    
    for a, b, expected in disjoint_tests:
        result = oracle.are_disjoint(a, b)
        status = "✓" if result == expected else "✗"
        print(f"  {status} are_disjoint({a}, {b}) = {result}")
    
    # Show top-level purposes
    print("\nTop-level purposes (direct children of Purpose):")
    top_level = oracle.get_top_level_purposes()
    for p in sorted(top_level)[:15]:
        print(f"  {p}")
    if len(top_level) > 15:
        print(f"  ... and {len(top_level) - 15} more")
    
    print()
    print("=" * 60)
