"""
DPV Grounding Module (OWL Only)
Loads W3C DPV ontologies for ODRL constraint grounding.
Supports: Purpose, Recipient, LegalEntity hierarchies.
Uses rdfs:subClassOf for hierarchy (not SKOS).

Usage:
    from grounding.dpv import DPVLoader, DPVNamespaces
    
    loader = DPVLoader()
    loader.load("data/dpv/dpv-owl.ttl")
    
    # Purpose grounding
    purposes = loader.get_purpose_iris()
    
    # Recipient grounding
    recipients = loader.get_recipient_iris()
    
    # Hierarchy reasoning
    loader.is_subclass_of(dpv:AcademicResearch, dpv:NonCommercial)  # True
    loader.is_subclass_of(dpv:PublicAuthority, dpv:ThirdParty)      # True

Download:
    curl -L -o data/dpv/dpv-owl.ttl https://w3id.org/dpv/2.2/dpv-owl.ttl
"""

from .loader import (
    DPVLoader,
    DPVNamespaces,
    DPVConceptType,
    DPV_SOURCES,
    LoadStats,
    create_loader,
    get_download_commands,
)

# Backward compatibility aliases
DPVPurposeLoader = DPVLoader  # Old name still works

__all__ = [
    # Main exports
    "DPVLoader",
    "DPVNamespaces",
    "DPVConceptType",
    "DPV_SOURCES",
    "LoadStats",
    "create_loader",
    "get_download_commands",
    # Backward compatibility
    "DPVPurposeLoader",
]

__version__ = "0.3.0"