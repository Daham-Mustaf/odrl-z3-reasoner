# src/grounding/language/__init__.py
"""
Language Grounding Module

Provides semantic grounding for ODRL language constraints using BCP47.

Components:
- builder: Generates BCP47 SKOS hierarchy from IANA registry
- oracle: LanguageKGOracle for policy reasoning

Theory:
- Subsumption: en-US ⊑ en (regional variant of base language)
- Disjointness: en ⊥ de (different base languages)
- Script disjoint: zh-Hans ⊥ zh-Hant (different scripts)

Sources:
- RFC 5646: BCP47 syntax
- ISO 639-1/3: Language codes
- ISO 15924: Script codes
- ISO 3166-1: Region codes
"""

from .oracle import LanguageKGOracle

__all__ = ["LanguageKGOracle"]
