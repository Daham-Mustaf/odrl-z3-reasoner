#!/usr/bin/env python3
"""
IANA Media Types Download and RDF Conversion Script

Downloads the official IANA media types XML registry and converts it to RDF/OWL.

Usage:
    python download_iana.py [output_dir]
    
    # Default: downloads to data/iana-media-types/
    python download_iana.py
    
    # Custom directory
    python download_iana.py /path/to/output

This script:
    1. Downloads media-types.xml from IANA
    2. Parses all registered media types
    3. Generates RDF/OWL ontology using W3C namespace
    4. Saves as Turtle file

W3C Namespace Convention:
    https://www.w3.org/ns/iana/media-types/{type}/{subtype}#Resource
    
    Example: https://www.w3.org/ns/iana/media-types/image/png#Resource
"""

import sys
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# RDF Libraries
try:
    from rdflib import Graph, Namespace, URIRef, Literal, BNode
    from rdflib.namespace import RDF, RDFS, OWL, SKOS, XSD, DCTERMS
except ImportError:
    logger.error("rdflib not installed. Run: pip install rdflib")
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

IANA_XML_URL = "https://www.iana.org/assignments/media-types/media-types.xml"

# W3C official namespace for IANA media types
W3C_MT = Namespace("https://www.w3.org/ns/iana/media-types/")

# Our ontology namespace (for classes like MediaType, Application, etc.)
MT_ONT = Namespace("https://www.w3.org/ns/iana/media-types/ontology#")

# IANA namespace for references
IANA = Namespace("https://www.iana.org/assignments/media-types/")

# XML namespace used in IANA registry
IANA_XML_NS = "{http://www.iana.org/assignments}"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MediaTypeRecord:
    """A single media type record from IANA."""
    name: str              # Full name like "image/png"
    type: str              # Top-level type like "image"
    subtype: str           # Subtype like "png"
    template: Optional[str] = None
    references: List[str] = field(default_factory=list)
    deprecated: bool = False
    obsolete: bool = False
    
    @property
    def w3c_uri(self) -> str:
        """Get the W3C namespace URI for this media type."""
        return f"https://www.w3.org/ns/iana/media-types/{self.name}#Resource"
    
    @property
    def has_suffix(self) -> Optional[str]:
        """Extract structured syntax suffix if present."""
        suffixes = ['+xml', '+json', '+zip', '+cbor', '+yaml', '+gzip', 
                    '+ber', '+der', '+jwt', '+sqlite3']
        for suffix in suffixes:
            if self.name.endswith(suffix):
                return suffix
        return None


@dataclass  
class IANARegistry:
    """Parsed IANA media types registry."""
    records: List[MediaTypeRecord] = field(default_factory=list)
    top_level_types: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    
    def add_record(self, record: MediaTypeRecord) -> None:
        self.records.append(record)
        if record.type not in self.top_level_types:
            self.top_level_types.append(record.type)
    
    def get_by_type(self, type_name: str) -> List[MediaTypeRecord]:
        return [r for r in self.records if r.type == type_name]
    
    def __len__(self) -> int:
        return len(self.records)


# =============================================================================
# XML Parser
# =============================================================================

def download_iana_xml(output_path: Path) -> Path:
    """Download IANA media-types.xml."""
    logger.info(f"Downloading {IANA_XML_URL}")
    
    xml_file = output_path / "media-types.xml"
    
    try:
        urllib.request.urlretrieve(IANA_XML_URL, xml_file)
        logger.info(f"Saved to {xml_file}")
        return xml_file
    except Exception as e:
        logger.error(f"Failed to download: {e}")
        raise


def parse_iana_xml(xml_path: Path) -> IANARegistry:
    """Parse IANA media-types.xml into structured data."""
    logger.info(f"Parsing {xml_path}")
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    registry = IANARegistry()
    
    # Get last updated date
    updated = root.find(f"{IANA_XML_NS}updated")
    if updated is not None:
        registry.last_updated = updated.text
    
    # Find all registry sections (one per top-level type)
    for reg in root.findall(f".//{IANA_XML_NS}registry"):
        reg_id = reg.get("id", "")
        
        # Skip non-media-type registries
        if not reg_id or reg_id in ["media-types", "top-level-media-types"]:
            continue
        
        top_type = reg_id  # e.g., "application", "image", etc.
        
        # Find all records in this registry
        for record in reg.findall(f"{IANA_XML_NS}record"):
            name_elem = record.find(f"{IANA_XML_NS}name")
            if name_elem is None or not name_elem.text:
                continue
            
            subtype = name_elem.text.strip()
            full_name = f"{top_type}/{subtype}"
            
            # Get references (RFCs, etc.)
            refs = []
            for xref in record.findall(f"{IANA_XML_NS}xref"):
                ref_type = xref.get("type", "")
                ref_data = xref.get("data", "")
                if ref_type == "rfc" and ref_data:
                    refs.append(f"RFC{ref_data}")
                elif ref_type == "uri" and ref_data:
                    refs.append(ref_data)
            
            # Check for deprecation/obsolete status
            deprecated = False
            obsolete = False
            file_elem = record.find(f"{IANA_XML_NS}file")
            if file_elem is not None:
                file_type = file_elem.get("type", "")
                if "OBSOLETE" in file_type.upper():
                    obsolete = True
                if "DEPRECATED" in file_type.upper():
                    deprecated = True
            
            mt_record = MediaTypeRecord(
                name=full_name,
                type=top_type,
                subtype=subtype,
                references=refs,
                deprecated=deprecated,
                obsolete=obsolete,
            )
            
            registry.add_record(mt_record)
    
    logger.info(f"Parsed {len(registry)} media types in {len(registry.top_level_types)} categories")
    return registry


# =============================================================================
# RDF Generator
# =============================================================================

def generate_rdf(registry: IANARegistry) -> Graph:
    """Generate RDF/OWL ontology from IANA registry."""
    logger.info("Generating RDF ontology")
    
    g = Graph()
    
    # Bind prefixes
    g.bind("mt", W3C_MT)
    g.bind("mt-ont", MT_ONT)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    
    # Create ontology metadata
    ont = MT_ONT[""]
    g.add((ont, RDF.type, OWL.Ontology))
    g.add((ont, RDFS.label, Literal("IANA Media Types Ontology")))
    g.add((ont, DCTERMS.description, Literal(
        "OWL ontology for IANA Media Types (MIME types). "
        "Generated from the official IANA registry."
    )))
    g.add((ont, DCTERMS.source, URIRef(IANA_XML_URL)))
    if registry.last_updated:
        g.add((ont, DCTERMS.modified, Literal(registry.last_updated, datatype=XSD.date)))
    g.add((ont, DCTERMS.created, Literal(datetime.now().strftime("%Y-%m-%d"), datatype=XSD.date)))
    
    # Create root MediaType class
    mt_class = MT_ONT.MediaType
    g.add((mt_class, RDF.type, OWL.Class))
    g.add((mt_class, RDFS.label, Literal("Media Type")))
    g.add((mt_class, SKOS.definition, Literal(
        "A media type (MIME type) identifier for file formats on the Internet, "
        "as registered with IANA."
    )))
    
    # Create top-level type classes
    for top_type in registry.top_level_types:
        type_class = MT_ONT[top_type.capitalize()]
        g.add((type_class, RDF.type, OWL.Class))
        g.add((type_class, RDFS.subClassOf, mt_class))
        g.add((type_class, RDFS.label, Literal(f"{top_type} media type")))
        g.add((type_class, SKOS.notation, Literal(top_type)))
    
    # Create structured syntax suffix classes
    suffix_class = MT_ONT.StructuredSyntax
    g.add((suffix_class, RDF.type, OWL.Class))
    g.add((suffix_class, RDFS.label, Literal("Structured Syntax")))
    
    suffixes_seen = set()
    for record in registry.records:
        if record.has_suffix:
            suffixes_seen.add(record.has_suffix)
    
    for suffix in sorted(suffixes_seen):
        suffix_name = suffix.replace("+", "").upper() + "Based"
        sc = MT_ONT[suffix_name]
        g.add((sc, RDF.type, OWL.Class))
        g.add((sc, RDFS.subClassOf, suffix_class))
        g.add((sc, RDFS.label, Literal(f"{suffix} structured syntax")))
        g.add((sc, SKOS.notation, Literal(suffix)))
    
    # Create individual media type classes using W3C namespace
    for record in registry.records:
        # W3C namespace URI
        mt_uri = URIRef(record.w3c_uri)
        
        g.add((mt_uri, RDF.type, OWL.Class))
        
        # SubClassOf top-level type
        type_class = MT_ONT[record.type.capitalize()]
        g.add((mt_uri, RDFS.subClassOf, type_class))
        
        # SubClassOf structured suffix if applicable
        if record.has_suffix:
            suffix_name = record.has_suffix.replace("+", "").upper() + "Based"
            g.add((mt_uri, RDFS.subClassOf, MT_ONT[suffix_name]))
        
        # Labels and notation
        g.add((mt_uri, RDFS.label, Literal(record.name)))
        g.add((mt_uri, SKOS.notation, Literal(record.name)))
        g.add((mt_uri, SKOS.prefLabel, Literal(record.name)))
        
        # References
        for ref in record.references:
            if ref.startswith("RFC"):
                g.add((mt_uri, DCTERMS.references, URIRef(f"https://tools.ietf.org/html/{ref.lower()}")))
            elif ref.startswith("http"):
                g.add((mt_uri, DCTERMS.references, URIRef(ref)))
        
        # Deprecation status
        if record.deprecated or record.obsolete:
            g.add((mt_uri, OWL.deprecated, Literal(True)))
    
    logger.info(f"Generated {len(g)} triples")
    return g


# =============================================================================
# Common Aliases (these ARE hardcoded but they're not in IANA)
# =============================================================================

def add_common_aliases(g: Graph) -> None:
    """Add common unofficial aliases as owl:equivalentClass."""
    
    # These are NOT in IANA but widely used
    aliases = [
        ("image/jpg", "image/jpeg"),
        ("image/pjpeg", "image/jpeg"),
        ("audio/mp3", "audio/mpeg"),
    ]
    
    for alias, canonical in aliases:
        alias_uri = URIRef(f"https://www.w3.org/ns/iana/media-types/{alias}#Resource")
        canonical_uri = URIRef(f"https://www.w3.org/ns/iana/media-types/{canonical}#Resource")
        
        # Only add if canonical exists
        if (canonical_uri, RDF.type, OWL.Class) in g:
            g.add((alias_uri, RDF.type, OWL.Class))
            g.add((alias_uri, OWL.equivalentClass, canonical_uri))
            g.add((alias_uri, RDFS.label, Literal(alias)))
            g.add((alias_uri, SKOS.notation, Literal(alias)))
            g.add((alias_uri, SKOS.altLabel, Literal(f"Alias for {canonical}")))


# =============================================================================
# Main
# =============================================================================

def main(output_dir: str = "data/iana-media-types") -> None:
    """Download IANA registry and generate RDF ontology."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("IANA Media Types → RDF/OWL Converter")
    print("=" * 60)
    print(f"Output directory: {output_path.absolute()}")
    print()
    
    # Step 1: Download XML
    xml_file = download_iana_xml(output_path)
    
    # Step 2: Parse XML
    registry = parse_iana_xml(xml_file)
    
    # Step 3: Generate RDF
    g = generate_rdf(registry)
    
    # Step 4: Add common aliases
    add_common_aliases(g)
    
    # Step 5: Save
    ttl_file = output_path / "media-types.ttl"
    g.serialize(destination=str(ttl_file), format="turtle")
    logger.info(f"Saved ontology to {ttl_file}")
    
    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Media types:     {len(registry)}")
    print(f"  Top-level types: {len(registry.top_level_types)}")
    print(f"  Total triples:   {len(g)}")
    print(f"  Last updated:    {registry.last_updated}")
    print()
    print("Top-level types:")
    for t in sorted(registry.top_level_types):
        count = len(registry.get_by_type(t))
        print(f"  {t}: {count}")
    print()
    print("=" * 60)
    print(f"Files created:")
    print(f"  {xml_file}")
    print(f"  {ttl_file}")
    print("=" * 60)


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "data/iana-media-types"
    main(output)
