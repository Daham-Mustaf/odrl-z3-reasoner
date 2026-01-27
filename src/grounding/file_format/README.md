# File Format Grounding Module

Semantic grounding for ODRL `fileFormat` constraints using **IANA Media Types**.

## Overview

This module provides semantic reasoning for ODRL file format constraints by:

1. **Downloading** the official IANA media types registry (XML)
2. **Converting** to RDF/OWL using W3C's official namespace
3. **Reasoning** with SPARQL queries for isA, eq, etc.

## W3C Namespace

Uses the **official W3C namespace** for IANA media types:

```
https://www.w3.org/ns/iana/media-types/{type}/{subtype}#Resource
```

Examples:
- `https://www.w3.org/ns/iana/media-types/image/png#Resource`
- `https://www.w3.org/ns/iana/media-types/application/json#Resource`
- `https://www.w3.org/ns/iana/media-types/application/rdf+xml#Resource`

Reference: https://www.w3.org/ns/iana/media-types/

## Setup

### Step 1: Download IANA Registry

```bash
# From your project root
python -m src.grounding.file_format.download_iana data/iana-media-types/

# Or directly
cd src/grounding/file_format
python download_iana.py ../../../data/iana-media-types/
```

This will:
1. Download `media-types.xml` from IANA
2. Parse all registered media types (~2000+)
3. Generate `media-types.ttl` with W3C namespace URIs

### Step 2: Use the Oracle

```python
from src.grounding.file_format import MediaTypeLoader, MediaTypeOracle

# Load
loader = MediaTypeLoader()
loader.load("data/iana-media-types/media-types.ttl")
loader.print_summary()

# Create oracle
oracle = MediaTypeOracle(loader.get_graph())

# Evaluate ODRL constraints
oracle.is_a("image/png", "image")           # True
oracle.is_a("application/json", "application")  # True
oracle.eq("image/jpg", "image/jpeg")        # True (alias)
oracle.has_suffix("application/rdf+xml", "+xml")  # True
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│                                                                     │
│  IANA Registry (Authoritative)                                      │
│  https://www.iana.org/assignments/media-types/media-types.xml       │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              download_iana.py                                │   │
│  │                                                              │   │
│  │  1. Download XML from IANA                                   │   │
│  │  2. Parse all media type registrations                       │   │
│  │  3. Generate RDF/OWL with W3C namespace                      │   │
│  │  4. Save as media-types.ttl                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              media-types.ttl                                 │   │
│  │                                                              │   │
│  │  - ~2000+ media types                                        │   │
│  │  - W3C namespace URIs                                        │   │
│  │  - Hierarchy (type → subtype)                                │   │
│  │  - Structured suffixes (+xml, +json, etc.)                   │   │
│  │  - Common aliases                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              loader.py → oracle.py                           │   │
│  │                                                              │   │
│  │  Reasoning operations:                                       │   │
│  │  - isA(child, parent)                                        │   │
│  │  - eq(a, b)                                                  │   │
│  │  - hasSuffix(mt, suffix)                                     │   │
│  │  - exists(mt)                                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Ontology Structure

```turtle
@prefix mt: <https://www.w3.org/ns/iana/media-types/> .
@prefix mt-ont: <https://www.w3.org/ns/iana/media-types/ontology#> .

# Root class
mt-ont:MediaType a owl:Class ;
    rdfs:label "Media Type" .

# Top-level types
mt-ont:Image a owl:Class ;
    rdfs:subClassOf mt-ont:MediaType ;
    skos:notation "image" .

mt-ont:Application a owl:Class ;
    rdfs:subClassOf mt-ont:MediaType ;
    skos:notation "application" .

# Specific media types (W3C namespace)
mt:image/png#Resource a owl:Class ;
    rdfs:subClassOf mt-ont:Image ;
    rdfs:label "image/png" ;
    skos:notation "image/png" .

mt:application/rdf+xml#Resource a owl:Class ;
    rdfs:subClassOf mt-ont:Application ;
    rdfs:subClassOf mt-ont:XMLBased ;  # Structured suffix
    rdfs:label "application/rdf+xml" ;
    skos:notation "application/rdf+xml" .
```

## Files

| File | Purpose |
|------|---------|
| `download_iana.py` | Downloads IANA XML and generates RDF |
| `loader.py` | Loads the generated ontology |
| `oracle.py` | Reasoning operations for ODRL |
| `__init__.py` | Module exports |
| `README.md` | This file |

## What's NOT Hardcoded

| Aspect | Source |
|--------|--------|
| Media types list | Downloaded from IANA |
| Hierarchy | Parsed from IANA registry structure |
| Namespace | W3C official namespace |
| RFC references | Parsed from IANA XML |
| Deprecation status | Parsed from IANA XML |

## What IS Hardcoded (Minimal)

| Aspect | Reason |
|--------|--------|
| Common aliases (image/jpg) | Not in IANA but widely used |
| Structured suffix list | Based on RFC 6839 |

## Comparison with Other Grounding Modules

| Module | Data Source | Namespace | Download |
|--------|-------------|-----------|----------|
| `language` | BCP47/Lexvo | Lexvo | Yes, external |
| `purpose` | DPV | W3C DPV | Yes, external |
| `file_format` | IANA | W3C official | Yes, from IANA |

## ODRL Constraint Examples

```turtle
# File must be an image
odrl:constraint [
    odrl:leftOperand odrl:fileFormat ;
    odrl:operator odrl:isA ;
    odrl:rightOperand "image" ;
] .

# File must be PDF
odrl:constraint [
    odrl:leftOperand odrl:fileFormat ;
    odrl:operator odrl:eq ;
    odrl:rightOperand "application/pdf" ;
] .

# File must use XML syntax
odrl:constraint [
    odrl:leftOperand odrl:fileFormat ;
    odrl:operator odrl:isA ;
    odrl:rightOperand "+xml" ;  # Structured suffix
] .
```

## References

- IANA Media Types Registry: https://www.iana.org/assignments/media-types/
- W3C IANA Namespace: https://www.w3.org/ns/iana/media-types/
- RFC 6838: Media Type Specifications and Registration Procedures
- RFC 6839: Additional Structured Syntax Suffixes