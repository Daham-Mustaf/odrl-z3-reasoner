"""
Purpose Grounding Module (OWL Only)

Loads W3C DPV purpose ontologies for ODRL constraint grounding.
Uses rdfs:subClassOf for hierarchy (not SKOS).

Usage:
    from grounding.purpose import DPVPurposeLoader, DPVNamespaces
    
    loader = DPVPurposeLoader()
    loader.load("data/dpv-owl.ttl")
    loader.load("data/sector-law-owl.ttl")
    
    graph = loader.get_graph()  # For reasoning stage

Download:
    curl -L -o data/dpv-owl.ttl https://w3id.org/dpv/2.2/dpv-owl.ttl
"""

from .loader import (
    DPVPurposeLoader,
    DPVNamespaces,
    DPV_SOURCES,
    LoadStats,
    create_loader,
    get_download_commands,
)

__all__ = [
    "DPVPurposeLoader",
    "DPVNamespaces", 
    "DPV_SOURCES",
    "LoadStats",
    "create_loader",
    "get_download_commands",
]

__version__ = "0.2.0"