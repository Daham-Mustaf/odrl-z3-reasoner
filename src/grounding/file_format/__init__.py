"""
File Format Grounding Module

Provides semantic grounding for ODRL fileFormat constraints using IANA Media Types.

Usage:
    from grounding.file_format import MediaTypeLoader, MediaTypeOracle
    
    # Load the ontology
    loader = MediaTypeLoader()
    loader.load_builtin()  # Uses built-in common types
    # or: loader.load("path/to/media-types.ttl")
    
    # Create oracle for reasoning
    oracle = MediaTypeOracle(loader.get_graph())
    
    # Evaluate constraints
    oracle.is_a("image/png", "image")  # True
    oracle.eq("image/jpg", "image/jpeg")  # True
    oracle.has_suffix("application/rdf+xml", "+xml")  # True
"""

from .loader import (
    MediaTypeLoader,
    MediaTypeNamespaces,
    LoadStats,
    create_loader,
)

from .oracle import (
    MediaTypeOracle,
)

from .ontology_builder import (
    MediaTypeOntologyBuilder,
    MediaTypeInfo,
    build_default_ontology,
    get_iri_for_media_type,
    TOP_LEVEL_TYPES,
    STRUCTURED_SUFFIXES,
    ALIASES,
    COMMON_MEDIA_TYPES,
)

__all__ = [
    # Loader
    "MediaTypeLoader",
    "MediaTypeNamespaces", 
    "LoadStats",
    "create_loader",
    # Oracle
    "MediaTypeOracle",
    # Builder
    "MediaTypeOntologyBuilder",
    "MediaTypeInfo",
    "build_default_ontology",
    "get_iri_for_media_type",
    # Data
    "TOP_LEVEL_TYPES",
    "STRUCTURED_SUFFIXES",
    "ALIASES",
    "COMMON_MEDIA_TYPES",
]
