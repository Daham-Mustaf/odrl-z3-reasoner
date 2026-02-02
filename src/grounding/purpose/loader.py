"""
DPV Ontology Loader (OWL Only)
Loads W3C Data Privacy Vocabulary (DPV) OWL ontologies for grounding.
Supports: Purpose, Recipient, LegalEntity hierarchies.
Uses rdfs:subClassOf for hierarchy.

Usage:
    loader = DPVLoader()
    loader.load("data/dpv/dpv-owl.ttl")
    
    # Get purposes
    purposes = loader.get_purpose_iris()
    
    # Get recipients
    recipients = loader.get_recipient_iris()
    
    # Check hierarchy
    loader.is_subclass_of(dpv:AcademicResearch, dpv:NonCommercial)  # True
    loader.is_subclass_of(dpv:PublicAuthority, dpv:ThirdParty)      # True

Download DPV files:
    curl -L -o data/dpv/dpv-owl.ttl https://w3id.org/dpv/2.2/dpv-owl.ttl
"""

from pathlib import Path
from typing import Set, List, Dict, Union, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Concept Types
# =============================================================================

class DPVConceptType(Enum):
    """Types of DPV concepts we support."""
    PURPOSE = "Purpose"
    RECIPIENT = "Recipient"
    LEGAL_ENTITY = "LegalEntity"
    ORGANISATION = "Organisation"
    ENTITY = "Entity"


# =============================================================================
# Namespaces
# =============================================================================

class DPVNamespaces:
    """DPV namespace registry."""
    
    # Core
    DPV_OWL = Namespace("https://w3id.org/dpv/owl#")
    
    # Sectors
    SECTOR_LAW = Namespace("https://w3id.org/dpv/sector/law/owl#")
    SECTOR_INFRA = Namespace("https://w3id.org/dpv/sector/infra/owl#")
    SECTOR_HEALTH = Namespace("https://w3id.org/dpv/sector/health/owl#")
    SECTOR_FINANCE = Namespace("https://w3id.org/dpv/sector/finance/owl#")
    SECTOR_EDUCATION = Namespace("https://w3id.org/dpv/sector/education/owl#")
    SECTOR_PUBLICSERVICES = Namespace("https://w3id.org/dpv/sector/publicservices/owl#")
    
    @classmethod
    def all(cls) -> List[Namespace]:
        """All DPV-related namespaces."""
        return [
            cls.DPV_OWL,
            cls.SECTOR_LAW, cls.SECTOR_INFRA, cls.SECTOR_HEALTH,
            cls.SECTOR_FINANCE, cls.SECTOR_EDUCATION, cls.SECTOR_PUBLICSERVICES,
        ]
    
    @classmethod
    def prefix_map(cls) -> Dict[str, Namespace]:
        """Prefix to namespace mapping."""
        return {
            "dpv-owl": cls.DPV_OWL,
            "sector-law": cls.SECTOR_LAW,
            "sector-infra": cls.SECTOR_INFRA,
            "sector-health": cls.SECTOR_HEALTH,
            "sector-finance": cls.SECTOR_FINANCE,
            "sector-education": cls.SECTOR_EDUCATION,
            "sector-publicservices": cls.SECTOR_PUBLICSERVICES,
        }


# =============================================================================
# DPV Download URLs
# =============================================================================

DPV_SOURCES = {
    "dpv-owl": "https://w3id.org/dpv/2.2/dpv-owl.ttl",
    "purposes-owl": "https://w3id.org/dpv/2.2/purposes/purposes-owl.ttl",
    "entities-owl": "https://w3id.org/dpv/2.2/entities/entities-owl.ttl",
    "sector-law": "https://w3id.org/dpv/2.2/sector/law/sector-law-owl.ttl",
    "sector-infra": "https://w3id.org/dpv/2.2/sector/infra/sector-infra-owl.ttl",
    "sector-health": "https://w3id.org/dpv/2.2/sector/health/sector-health-owl.ttl",
    "sector-finance": "https://w3id.org/dpv/2.2/sector/finance/sector-finance-owl.ttl",
    "sector-education": "https://w3id.org/dpv/2.2/sector/education/sector-education-owl.ttl",
}


# =============================================================================
# Statistics
# =============================================================================

@dataclass
class LoadStats:
    """Statistics about loaded ontology."""
    total_triples: int = 0
    purpose_concepts: int = 0
    recipient_concepts: int = 0
    legal_entity_concepts: int = 0
    organisation_concepts: int = 0
    subclass_edges: int = 0
    sources: List[str] = field(default_factory=list)


# =============================================================================
# Loader
# =============================================================================

class DPVLoader:
    """
    Loader for DPV ontologies (OWL format).
    
    Supports:
    - Purpose hierarchy (for odrl:purpose)
    - Recipient/LegalEntity hierarchy (for odrl:recipient)
    
    Uses rdfs:subClassOf for hierarchy traversal.
    """
    
    HIERARCHY_PREDICATE = RDFS.subClassOf
    
    def __init__(self):
        self._graph = Graph()
        self._sources: List[str] = []
        self._hierarchy_cache: Dict[tuple, bool] = {}
        self._bind_prefixes()
    
    def _bind_prefixes(self) -> None:
        """Bind common prefixes."""
        for prefix, ns in DPVNamespaces.prefix_map().items():
            self._graph.bind(prefix, ns)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("owl", OWL)
        self._graph.bind("skos", SKOS)
    
    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------
    
    def load(self, path: Union[str, Path]) -> int:
        """
        Load a DPV-OWL TTL file.
        
        Returns:
            Number of triples loaded
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        before = len(self._graph)
        self._graph.parse(str(path), format="turtle")
        loaded = len(self._graph) - before
        
        self._sources.append(str(path))
        self._hierarchy_cache.clear()  # Clear cache on new load
        
        logger.info(f"Loaded {loaded} triples from {path.name}")
        return loaded
    
    def load_multiple(self, paths: List[Union[str, Path]]) -> int:
        """Load multiple TTL files."""
        return sum(self.load(p) for p in paths)
    
    def get_graph(self) -> Graph:
        """Get the loaded RDF graph."""
        return self._graph
    
    # -------------------------------------------------------------------------
    # Concept Extraction
    # -------------------------------------------------------------------------
    
    def _get_concepts_by_type(self, type_uri: URIRef) -> Set[URIRef]:
        """Get all concepts of a given type."""
        concepts = set()
        
        # Direct type
        for s, _, _ in self._graph.triples((None, RDF.type, type_uri)):
            if isinstance(s, URIRef):
                concepts.add(s)
        
        # Subclasses (transitive)
        for s in self._get_all_subclasses(type_uri):
            concepts.add(s)
        
        return concepts
    
    def _get_all_subclasses(self, parent: URIRef) -> Set[URIRef]:
        """Get all subclasses (transitive) of a class."""
        subclasses = set()
        to_process = [parent]
        
        while to_process:
            current = to_process.pop()
            for s, _, _ in self._graph.triples((None, RDFS.subClassOf, current)):
                if isinstance(s, URIRef) and s not in subclasses:
                    subclasses.add(s)
                    to_process.append(s)
        
        return subclasses
    
    def get_purpose_iris(self) -> Set[URIRef]:
        """Get all Purpose concept IRIs."""
        return self._get_concepts_by_type(DPVNamespaces.DPV_OWL.Purpose)
    
    def get_recipient_iris(self) -> Set[URIRef]:
        """
        Get all Recipient-related concept IRIs.
        
        Includes: Recipient, DataSubject, DataController, DataProcessor,
                  ThirdParty, Organisation subtypes, etc.
        """
        concepts = set()
        
        # Core recipient types
        core_types = [
            DPVNamespaces.DPV_OWL.Recipient,
            DPVNamespaces.DPV_OWL.LegalEntity,
            DPVNamespaces.DPV_OWL.Entity,
        ]
        
        for type_uri in core_types:
            concepts.update(self._get_concepts_by_type(type_uri))
        
        return concepts
    
    def get_legal_entity_iris(self) -> Set[URIRef]:
        """Get all LegalEntity concept IRIs."""
        return self._get_concepts_by_type(DPVNamespaces.DPV_OWL.LegalEntity)
    
    def get_organisation_iris(self) -> Set[URIRef]:
        """Get all Organisation concept IRIs."""
        return self._get_concepts_by_type(DPVNamespaces.DPV_OWL.Organisation)
    
    # -------------------------------------------------------------------------
    # Hierarchy Reasoning
    # -------------------------------------------------------------------------
    
    def is_subclass_of(self, child: URIRef, parent: URIRef) -> bool:
        """
        Check if child is subclass of parent (transitive).
        
        Args:
            child: The potential subclass
            parent: The potential superclass
            
        Returns:
            True if child rdfs:subClassOf+ parent
        """
        # Same class
        if child == parent:
            return True
        
        # Check cache
        cache_key = (child, parent)
        if cache_key in self._hierarchy_cache:
            return self._hierarchy_cache[cache_key]
        
        # BFS traversal
        visited = set()
        to_process = [child]
        
        while to_process:
            current = to_process.pop(0)
            if current == parent:
                self._hierarchy_cache[cache_key] = True
                return True
            
            if current in visited:
                continue
            visited.add(current)
            
            # Get direct superclasses
            for _, _, superclass in self._graph.triples((current, RDFS.subClassOf, None)):
                if isinstance(superclass, URIRef):
                    to_process.append(superclass)
        
        self._hierarchy_cache[cache_key] = False
        return False
    
    def get_superclasses(self, concept: URIRef, transitive: bool = True) -> Set[URIRef]:
        """Get all superclasses of a concept."""
        superclasses = set()
        
        if transitive:
            to_process = [concept]
            while to_process:
                current = to_process.pop()
                for _, _, parent in self._graph.triples((current, RDFS.subClassOf, None)):
                    if isinstance(parent, URIRef) and parent not in superclasses:
                        superclasses.add(parent)
                        to_process.append(parent)
        else:
            for _, _, parent in self._graph.triples((concept, RDFS.subClassOf, None)):
                if isinstance(parent, URIRef):
                    superclasses.add(parent)
        
        return superclasses
    
    def get_subclasses(self, concept: URIRef, transitive: bool = True) -> Set[URIRef]:
        """Get all subclasses of a concept."""
        if transitive:
            return self._get_all_subclasses(concept)
        else:
            subclasses = set()
            for s, _, _ in self._graph.triples((None, RDFS.subClassOf, concept)):
                if isinstance(s, URIRef):
                    subclasses.add(s)
            return subclasses
    
    def have_common_subclass(self, concept1: URIRef, concept2: URIRef) -> bool:
        """Check if two concepts have a common subclass (compatible)."""
        # Same concept
        if concept1 == concept2:
            return True
        
        # One is subclass of other
        if self.is_subclass_of(concept1, concept2):
            return True
        if self.is_subclass_of(concept2, concept1):
            return True
        
        # Check for common descendants
        subs1 = self.get_subclasses(concept1)
        subs2 = self.get_subclasses(concept2)
        
        return bool(subs1 & subs2)
    
    # -------------------------------------------------------------------------
    # Labels
    # -------------------------------------------------------------------------
    
    def get_label(self, iri: URIRef) -> str:
        """Get label for a concept."""
        # Try skos:prefLabel
        for _, _, label in self._graph.triples((iri, SKOS.prefLabel, None)):
            if isinstance(label, Literal):
                return str(label)
        
        # Try rdfs:label
        for _, _, label in self._graph.triples((iri, RDFS.label, None)):
            if isinstance(label, Literal):
                return str(label)
        
        # Fallback to local name
        return str(iri).split("#")[-1].split("/")[-1]
    
    def get_labels(self, iris: Set[URIRef]) -> Dict[URIRef, str]:
        """Get labels for multiple concepts."""
        return {iri: self.get_label(iri) for iri in iris}
    
    def get_all_labels(self) -> Dict[URIRef, str]:
        """Get labels for all purposes and recipients."""
        all_iris = self.get_purpose_iris() | self.get_recipient_iris()
        return self.get_labels(all_iris)
    
    # -------------------------------------------------------------------------
    # IRI Resolution
    # -------------------------------------------------------------------------
    
    def resolve_iri(self, value: str) -> Optional[URIRef]:
        """
        Resolve a string value to a DPV IRI.
        
        Handles:
        - Full IRIs: "https://w3id.org/dpv/owl#Purpose"
        - Prefixed: "dpv:Purpose", "dpv-owl:Purpose"
        - Local names: "Purpose", "AcademicResearch"
        """
        # Already a full IRI
        if value.startswith("http://") or value.startswith("https://"):
            return URIRef(value)
        
        # Prefixed form
        if ":" in value:
            prefix, local = value.split(":", 1)
            prefix_map = {
                "dpv": DPVNamespaces.DPV_OWL,
                "dpv-owl": DPVNamespaces.DPV_OWL,
            }
            if prefix in prefix_map:
                return prefix_map[prefix][local]
        
        # Local name - search in DPV namespace
        candidate = DPVNamespaces.DPV_OWL[value]
        
        # Verify it exists in graph
        if (candidate, None, None) in self._graph or (None, None, candidate) in self._graph:
            return candidate
        
        # Try case-insensitive match
        all_iris = self.get_purpose_iris() | self.get_recipient_iris()
        for iri in all_iris:
            local_name = str(iri).split("#")[-1].split("/")[-1]
            if local_name.lower() == value.lower():
                return iri
        
        return None
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> LoadStats:
        """Get loading statistics."""
        return LoadStats(
            total_triples=len(self._graph),
            purpose_concepts=len(self.get_purpose_iris()),
            recipient_concepts=len(self.get_recipient_iris()),
            legal_entity_concepts=len(self.get_legal_entity_iris()),
            organisation_concepts=len(self.get_organisation_iris()),
            subclass_edges=len(list(self._graph.triples((None, RDFS.subClassOf, None)))),
            sources=self._sources.copy(),
        )
    
    def print_summary(self) -> None:
        """Print summary of loaded data."""
        stats = self.get_stats()
        print("=" * 60)
        print("DPV Ontology Loader (Purpose + Recipient)")
        print("=" * 60)
        print(f"Total triples:        {stats.total_triples}")
        print(f"Purpose concepts:     {stats.purpose_concepts}")
        print(f"Recipient concepts:   {stats.recipient_concepts}")
        print(f"LegalEntity concepts: {stats.legal_entity_concepts}")
        print(f"Organisation concepts:{stats.organisation_concepts}")
        print(f"Hierarchy edges:      {stats.subclass_edges}")
        print(f"Sources loaded:       {len(stats.sources)}")
        for src in stats.sources:
            print(f"  - {Path(src).name}")
        print("=" * 60)
    
    def print_recipient_hierarchy(self) -> None:
        """Print the recipient hierarchy."""
        print("\nRecipient Hierarchy:")
        print("-" * 40)
        
        root = DPVNamespaces.DPV_OWL.Entity
        self._print_hierarchy_tree(root, indent=0, visited=set())
    
    def _print_hierarchy_tree(self, node: URIRef, indent: int, visited: Set[URIRef]) -> None:
        """Recursively print hierarchy tree."""
        if node in visited:
            return
        visited.add(node)
        
        label = self.get_label(node)
        print("  " * indent + f"├── {label}")
        
        for child in self.get_subclasses(node, transitive=False):
            self._print_hierarchy_tree(child, indent + 1, visited)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_loader(*paths: Union[str, Path]) -> DPVLoader:
    """Create and populate a loader."""
    loader = DPVLoader()
    for path in paths:
        loader.load(path)
    return loader


def get_download_commands() -> str:
    """Get curl commands for downloading DPV."""
    lines = ["# Download DPV-OWL files:", "mkdir -p data/dpv", ""]
    for name, url in DPV_SOURCES.items():
        lines.append(f"curl -L -o data/dpv/{name}.ttl {url}")
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python loader.py <ttl_file> [...]")
        print()
        print(get_download_commands())
        sys.exit(1)
    
    loader = DPVLoader()
    for path in sys.argv[1:]:
        loader.load(path)
    
    loader.print_summary()
    
    # Show sample purposes
    print("\nSample Purposes:")
    purposes = loader.get_purpose_iris()
    for iri in sorted(purposes, key=lambda x: loader.get_label(x))[:10]:
        print(f"  - {loader.get_label(iri)}")
    
    # Show sample recipients
    print("\nSample Recipients:")
    recipients = loader.get_recipient_iris()
    for iri in sorted(recipients, key=lambda x: loader.get_label(x))[:10]:
        print(f"  - {loader.get_label(iri)}")
    
    # Test hierarchy
    print("\nHierarchy Tests:")
    dpv = DPVNamespaces.DPV_OWL
    
    # Purpose test
    if loader.resolve_iri("AcademicResearch") and loader.resolve_iri("NonCommercial"):
        ar = loader.resolve_iri("AcademicResearch")
        nc = loader.resolve_iri("NonCommercial")
        print(f"  AcademicResearch ⊑ NonCommercial: {loader.is_subclass_of(ar, nc)}")
    
    # Recipient test
    if loader.resolve_iri("PublicAuthority") and loader.resolve_iri("ThirdParty"):
        pa = loader.resolve_iri("PublicAuthority")
        tp = loader.resolve_iri("ThirdParty")
        print(f"  PublicAuthority ⊑ ThirdParty: {loader.is_subclass_of(pa, tp)}")
    
    if loader.resolve_iri("AcademicInstitution") and loader.resolve_iri("Organisation"):
        ai = loader.resolve_iri("AcademicInstitution")
        org = loader.resolve_iri("Organisation")
        print(f"  AcademicInstitution ⊑ Organisation: {loader.is_subclass_of(ai, org)}")