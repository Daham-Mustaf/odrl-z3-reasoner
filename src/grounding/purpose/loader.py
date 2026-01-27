"""
DPV Purpose Ontology Loader (OWL Only)

Loads W3C Data Privacy Vocabulary (DPV) OWL ontologies for purpose grounding.
Uses rdfs:subClassOf for hierarchy.

Usage:
    loader = DPVPurposeLoader()
    loader.load("data/dpv/dpv-owl.ttl")
    loader.load("data/dpv/sector-law-owl.ttl")
    graph = loader.get_graph()

Download DPV files:
    curl -L -o data/dpv/dpv-owl.ttl https://w3id.org/dpv/2.2/dpv-owl.ttl
    curl -L -o data/dpv/sector-law-owl.ttl https://w3id.org/dpv/2.2/sector/law/sector-law-owl.ttl
"""

from pathlib import Path
from typing import Set, List, Dict, Union
from dataclasses import dataclass, field
import logging

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    # SPECIAL (for cross-references via skos:related)
    SVPU = Namespace("https://specialprivacy.ercim.eu/vocabs/purposes#")
    
    @classmethod
    def all(cls) -> List[Namespace]:
        """All purpose-related namespaces."""
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
            "svpu": cls.SVPU,
        }


# =============================================================================
# DPV Download URLs (corrected)
# =============================================================================

DPV_SOURCES = {
    "dpv-owl": "https://w3id.org/dpv/2.2/dpv-owl.ttl",
    "purposes-owl": "https://w3id.org/dpv/2.2/purposes/purposes-owl.ttl",
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
    subclass_edges: int = 0
    sources: List[str] = field(default_factory=list)


# =============================================================================
# Loader
# =============================================================================

class DPVPurposeLoader:
    """
    Loader for DPV Purpose ontologies (OWL format).
    
    Uses rdfs:subClassOf for hierarchy traversal.
    """
    
    # The hierarchy predicate (OWL only)
    HIERARCHY_PREDICATE = RDFS.subClassOf
    
    def __init__(self):
        self._graph = Graph()
        self._sources: List[str] = []
        self._bind_prefixes()
    
    def _bind_prefixes(self) -> None:
        """Bind common prefixes."""
        for prefix, ns in DPVNamespaces.prefix_map().items():
            self._graph.bind(prefix, ns)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("owl", OWL)
        self._graph.bind("skos", SKOS)
    
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
        logger.info(f"Loaded {loaded} triples from {path.name}")
        
        return loaded
    
    def load_multiple(self, paths: List[Union[str, Path]]) -> int:
        """Load multiple TTL files."""
        return sum(self.load(p) for p in paths)
    
    def get_graph(self) -> Graph:
        """Get the loaded RDF graph."""
        return self._graph
    
    def get_stats(self) -> LoadStats:
        """Get loading statistics."""
        return LoadStats(
            total_triples=len(self._graph),
            purpose_concepts=len(self.get_purpose_iris()),
            subclass_edges=len(list(self._graph.triples((None, RDFS.subClassOf, None)))),
            sources=self._sources.copy(),
        )
    
    def get_purpose_iris(self) -> Set[URIRef]:
        """Get all purpose concept IRIs."""
        purposes = set()
        
        # By rdf:type dpv-owl:Purpose
        for s, _, _ in self._graph.triples((None, RDF.type, DPVNamespaces.DPV_OWL.Purpose)):
            if isinstance(s, URIRef):
                purposes.add(s)
        
        # By namespace + subClassOf pattern
        for ns in DPVNamespaces.all():
            for s in self._graph.subjects(RDFS.subClassOf, None):
                if isinstance(s, URIRef) and str(s).startswith(str(ns)):
                    purposes.add(s)
        
        return purposes
    
    def get_labels(self) -> Dict[URIRef, str]:
        """Get labels for all purposes."""
        labels = {}
        for iri in self.get_purpose_iris():
            # Try skos:prefLabel (DPV uses this)
            for _, _, label in self._graph.triples((iri, SKOS.prefLabel, None)):
                if isinstance(label, Literal):
                    labels[iri] = str(label)
                    break
            # Fallback to rdfs:label
            if iri not in labels:
                for _, _, label in self._graph.triples((iri, RDFS.label, None)):
                    if isinstance(label, Literal):
                        labels[iri] = str(label)
                        break
            # Fallback to local name
            if iri not in labels:
                labels[iri] = str(iri).split("#")[-1].split("/")[-1]
        return labels
    
    def print_summary(self) -> None:
        """Print summary of loaded data."""
        stats = self.get_stats()
        print("=" * 50)
        print("DPV Purpose Ontology (OWL)")
        print("=" * 50)
        print(f"Total triples:     {stats.total_triples}")
        print(f"Purpose concepts:  {stats.purpose_concepts}")
        print(f"Hierarchy edges:   {stats.subclass_edges}")
        print(f"Sources loaded:    {len(stats.sources)}")
        for src in stats.sources:
            print(f"  - {Path(src).name}")
        print("=" * 50)


# =============================================================================
# Convenience
# =============================================================================

def create_loader(*paths: Union[str, Path]) -> DPVPurposeLoader:
    """Create and populate a loader."""
    loader = DPVPurposeLoader()
    for path in paths:
        loader.load(path)
    return loader


def get_download_commands() -> str:
    """Get curl commands for downloading DPV."""
    lines = ["# Download DPV-OWL files:", "mkdir -p data", ""]
    for name, url in DPV_SOURCES.items():
        lines.append(f"curl -L -o data/{name}.ttl {url}")
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
    
    loader = DPVPurposeLoader()
    for path in sys.argv[1:]:
        loader.load(path)
    
    loader.print_summary()
    
    print("\nSample purposes:")
    for iri, label in sorted(loader.get_labels().items(), key=lambda x: x[1])[:10]:
        print(f"  {label}")