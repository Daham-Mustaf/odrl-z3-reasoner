"""
Media Type Oracle

Provides semantic reasoning operations for ODRL fileFormat constraints.

Reasoning Operations:
    - isA(child, parent): Check if child is a subtype of parent
    - eq(a, b): Check if two media types are equivalent (or aliases)
    - hasSuffix(media_type, suffix): Check if media type has structured suffix
    - getType(media_type): Get the top-level type

Usage:
    from file_format.loader import MediaTypeLoader
    from file_format.oracle import MediaTypeOracle
    
    loader = MediaTypeLoader()
    loader.load("data/iana-media-types/media-types.ttl")
    
    oracle = MediaTypeOracle(loader.get_graph())
    
    # Check relationships
    oracle.is_a("image/png", "image")  # True
    oracle.eq("image/jpg", "image/jpeg")  # True (alias)
"""

from typing import Set, Optional, List
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

# W3C Namespaces
W3C_MT = Namespace("https://www.w3.org/ns/iana/media-types/")
MT_ONT = Namespace("https://www.w3.org/ns/iana/media-types/ontology#")


class MediaTypeOracle:
    """
    Semantic reasoning oracle for IANA Media Types.
    
    Uses W3C official namespace:
        https://www.w3.org/ns/iana/media-types/{type}/{subtype}#Resource
    """
    
    def __init__(self, graph: Graph):
        """
        Initialize oracle with an RDF graph containing the media types ontology.
        
        Args:
            graph: RDFLib graph with media types loaded
        """
        self._graph = graph
        self._cache_mappings()
    
    def _cache_mappings(self) -> None:
        """Cache media type string to URI mappings for performance."""
        self._string_to_uri = {}
        self._uri_to_string = {}
        
        for s, _, o in self._graph.triples((None, SKOS.notation, None)):
            if isinstance(s, URIRef) and isinstance(o, Literal):
                mt_string = str(o)
                self._string_to_uri[mt_string] = s
                self._uri_to_string[s] = mt_string
    
    def _resolve(self, media_type: str) -> Optional[URIRef]:
        """Resolve a media type string to its W3C URI."""
        # Normalize
        media_type = media_type.lower().strip()
        
        # Direct lookup from cache
        if media_type in self._string_to_uri:
            return self._string_to_uri[media_type]
        
        # Try constructing W3C URI directly
        if "/" in media_type:
            uri = URIRef(f"https://www.w3.org/ns/iana/media-types/{media_type}#Resource")
            if (uri, RDF.type, OWL.Class) in self._graph:
                return uri
        
        # For top-level types (e.g., "image"), try ontology namespace
        if "/" not in media_type:
            uri = MT_ONT[media_type.capitalize()]
            if (uri, RDF.type, OWL.Class) in self._graph:
                return uri
        
        return None
    
    # =========================================================================
    # Core Reasoning Operations
    # =========================================================================
    
    def is_a(self, child: str, parent: str) -> bool:
        """
        Check if child is a (transitive) subtype of parent.
        
        This is the core operation for ODRL constraints like:
            fileFormat isA "image"
        
        Args:
            child: Media type string (e.g., "image/png")
            parent: Media type or category (e.g., "image")
            
        Returns:
            True if child rdfs:subClassOf* parent
            
        Examples:
            is_a("image/png", "image") → True
            is_a("application/rdf+xml", "application") → True
            is_a("image/png", "application") → False
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
        Check if two media types are equivalent.
        
        Handles:
            - Exact string match
            - Same URI
            - owl:equivalentClass (aliases like image/jpg ↔ image/jpeg)
            
        Args:
            a: First media type
            b: Second media type
            
        Returns:
            True if a and b are equivalent
        """
        # Normalize
        a = a.lower().strip()
        b = b.lower().strip()
        
        # Exact match
        if a == b:
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
    
    def has_suffix(self, media_type: str, suffix: str) -> bool:
        """
        Check if a media type has a structured syntax suffix.
        
        Args:
            media_type: e.g., "application/rdf+xml"
            suffix: e.g., "+xml"
            
        Returns:
            True if the media type uses the suffix
        """
        # Normalize suffix
        if not suffix.startswith("+"):
            suffix = "+" + suffix
        
        # Simple string check first
        if media_type.lower().endswith(suffix.lower()):
            return True
        
        # Check via ontology (if type is subclass of suffix class)
        mt_uri = self._resolve(media_type)
        if mt_uri is None:
            return False
        
        suffix_name = suffix.replace("+", "").upper() + "Based"
        suffix_class = MT_ONT[suffix_name]
        
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            ASK {{
                <{mt_uri}> rdfs:subClassOf <{suffix_class}> .
            }}
        """
        
        return bool(self._graph.query(query))
    
    def get_type(self, media_type: str) -> Optional[str]:
        """
        Get the top-level type of a media type.
        
        Args:
            media_type: e.g., "image/png"
            
        Returns:
            Top-level type (e.g., "image") or None
        """
        if "/" in media_type:
            return media_type.split("/")[0].lower()
        return None
    
    def get_subtype(self, media_type: str) -> Optional[str]:
        """
        Get the subtype portion of a media type.
        
        Args:
            media_type: e.g., "image/png"
            
        Returns:
            Subtype (e.g., "png") or None
        """
        if "/" in media_type:
            return media_type.split("/", 1)[1]
        return None
    
    def is_deprecated(self, media_type: str) -> bool:
        """Check if a media type is deprecated."""
        mt_uri = self._resolve(media_type)
        if mt_uri is None:
            return False
        
        return (mt_uri, OWL.deprecated, Literal(True)) in self._graph
    
    def exists(self, media_type: str) -> bool:
        """Check if a media type exists in the ontology."""
        return self._resolve(media_type) is not None
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def get_all_of_type(self, top_type: str) -> Set[str]:
        """
        Get all media types of a given top-level type.
        
        Args:
            top_type: e.g., "image"
            
        Returns:
            Set of media type strings
        """
        top_uri = self._resolve(top_type)
        if top_uri is None:
            return set()
        
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            
            SELECT ?notation WHERE {{
                ?mt rdfs:subClassOf* <{top_uri}> .
                ?mt skos:notation ?notation .
                FILTER(CONTAINS(STR(?notation), "/"))
            }}
        """
        
        results = set()
        for row in self._graph.query(query):
            results.add(str(row.notation))
        
        return results
    
    def get_all_with_suffix(self, suffix: str) -> Set[str]:
        """
        Get all media types with a given structured suffix.
        
        Args:
            suffix: e.g., "+xml"
            
        Returns:
            Set of media type strings
        """
        if not suffix.startswith("+"):
            suffix = "+" + suffix
        
        suffix_name = suffix.replace("+", "").upper() + "Based"
        suffix_class = MT_ONT[suffix_name]
        
        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            
            SELECT ?notation WHERE {{
                ?mt rdfs:subClassOf <{suffix_class}> .
                ?mt skos:notation ?notation .
            }}
        """
        
        results = set()
        for row in self._graph.query(query):
            results.add(str(row.notation))
        
        return results
    
    def get_aliases(self, media_type: str) -> Set[str]:
        """Get all aliases for a media type."""
        mt_uri = self._resolve(media_type)
        if mt_uri is None:
            return set()
        
        aliases = set()
        
        # Forward equivalences
        for _, _, o in self._graph.triples((mt_uri, OWL.equivalentClass, None)):
            if o in self._uri_to_string:
                aliases.add(self._uri_to_string[o])
        
        # Reverse equivalences  
        for s, _, _ in self._graph.triples((None, OWL.equivalentClass, mt_uri)):
            if s in self._uri_to_string:
                aliases.add(self._uri_to_string[s])
        
        return aliases
    
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
        Evaluate an ODRL constraint on fileFormat.
        
        Args:
            operator: ODRL operator (eq, neq, isA, isPartOf, etc.)
            left_value: The actual file format
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
                return any(self.eq(left_value, rv) for rv in right_value)
            return None
        
        elif op in ("isnoneof", "is_none_of"):
            if isinstance(right_value, (list, set, tuple)):
                return all(not self.eq(left_value, rv) for rv in right_value)
            return None
        
        else:
            return None


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Import loader
    try:
        from loader import MediaTypeLoader
    except ImportError:
        from .loader import MediaTypeLoader
    
    if len(sys.argv) < 2:
        print("Usage: python oracle.py <path-to-media-types.ttl>")
        print()
        print("First run: python download_iana.py data/iana-media-types/")
        print("Then run:  python oracle.py data/iana-media-types/media-types.ttl")
        sys.exit(1)
    
    # Load ontology
    loader = MediaTypeLoader()
    loader.load(sys.argv[1])
    loader.print_summary()
    
    # Create oracle
    oracle = MediaTypeOracle(loader.get_graph())
    
    print()
    print("=" * 60)
    print("ORACLE TESTS")
    print("=" * 60)
    
    # Test isA
    print("\nisA tests:")
    isa_tests = [
        ("image/png", "image", True),
        ("application/json", "application", True),
        ("application/rdf+xml", "application", True),
        ("video/mp4", "video", True),
        ("text/html", "text", True),
        ("image/png", "application", False),
        ("text/html", "video", False),
    ]
    
    for child, parent, expected in isa_tests:
        result = oracle.is_a(child, parent)
        status = "✓" if result == expected else "✗"
        print(f"  {status} isA({child}, {parent}) = {result}")
    
    # Test eq (aliases)
    print("\neq tests:")
    eq_tests = [
        ("image/jpeg", "image/jpeg", True),
        ("image/jpg", "image/jpeg", True),
        ("image/png", "image/jpeg", False),
    ]
    
    for a, b, expected in eq_tests:
        result = oracle.eq(a, b)
        status = "✓" if result == expected else "✗"
        print(f"  {status} eq({a}, {b}) = {result}")
    
    # Test hasSuffix
    print("\nhasSuffix tests:")
    suffix_tests = [
        ("application/rdf+xml", "+xml", True),
        ("application/ld+json", "+json", True),
        ("application/json", "+json", False),
        ("image/svg+xml", "+xml", True),
    ]
    
    for mt, suffix, expected in suffix_tests:
        result = oracle.has_suffix(mt, suffix)
        status = "✓" if result == expected else "✗"
        print(f"  {status} hasSuffix({mt}, {suffix}) = {result}")
    
    # Show sample types
    print("\nSample image/* types:")
    image_types = oracle.get_all_of_type("image")
    for mt in sorted(image_types)[:10]:
        print(f"  {mt}")
    
    print("\nSample +xml types:")
    xml_types = oracle.get_all_with_suffix("+xml")
    for mt in sorted(xml_types)[:10]:
        print(f"  {mt}")