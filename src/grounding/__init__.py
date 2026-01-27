# src/grounding/__init__.py
"""
Grounding Module

Provides semantic grounding for ODRL constraints via oracles.

Submodules:
- language: BCP47 language tags (LanguageOracle)
- purpose: W3C DPV purposes (PurposeOracle)
- file_format: IANA media types (MediaTypeOracle)
- spatial: Locations (TODO)

Usage:
    from grounding.language import LanguageOracle
    
    oracle = LanguageOracle()
    oracle.load()
    
    # Check subsumption
    result = oracle.is_a("en-US", "en")  # True
"""

__all__ = ["language", "purpose", "file_format", "spatial"]