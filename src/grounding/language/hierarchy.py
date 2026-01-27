#!/usr/bin/env python3
"""
ODRL-SA Language Ontology Builder - Step 2: BCP47 Hierarchy Builder

Builds the subsumption hierarchy from BCP47 composition rules (RFC 5646 §2.2):

    en-US       ⊑  en           (region specializes language)
    zh-Hans     ⊑  zh           (script specializes language)
    zh-Hans-CN  ⊑  zh-Hans      (region specializes script variant)
    sr-Latn-RS  ⊑  sr-Latn      (region specializes script variant)

This is Step 2 of the ontology building pipeline.

Depends on: Step 1 (IANA Registry Parser)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


# =============================================================================
# BCP47 TAG STRUCTURE
# =============================================================================

@dataclass
class BCP47Tag:
    """
    Parsed BCP47 language tag.
    
    Structure: language [-script] [-region] [-variant]* [-extension]*
    
    Examples:
        en          → language only
        en-US       → language + region
        zh-Hans     → language + script
        zh-Hans-CN  → language + script + region
        sr-Latn-RS  → language + script + region
    """
    raw: str
    language: str
    script: Optional[str] = None
    region: Optional[str] = None
    variants: List[str] = field(default_factory=list)
    extensions: List[str] = field(default_factory=list)
    private_use: Optional[str] = None
    
    def get_parent(self) -> Optional['BCP47Tag']:
        """
        Get the parent tag in the hierarchy.
        
        Hierarchy rules (RFC 5646 §2.2):
        1. If has region, parent removes region
        2. If has script (and no region), parent removes script
        3. If has variant, parent removes last variant
        4. Base language has no parent
        
        Examples:
            zh-Hans-CN → zh-Hans
            zh-Hans    → zh
            en-US      → en
            en         → None (root)
        """
        # Has region? Remove it
        if self.region:
            return BCP47Tag(
                raw=self._build_tag(self.language, self.script, None, self.variants),
                language=self.language,
                script=self.script,
                region=None,
                variants=self.variants.copy(),
            )
        
        # Has variants? Remove last one
        if self.variants:
            new_variants = self.variants[:-1]
            return BCP47Tag(
                raw=self._build_tag(self.language, self.script, None, new_variants),
                language=self.language,
                script=self.script,
                region=None,
                variants=new_variants,
            )
        
        # Has script? Remove it
        if self.script:
            return BCP47Tag(
                raw=self.language,
                language=self.language,
                script=None,
                region=None,
                variants=[],
            )
        
        # Base language - no parent
        return None
    
    def get_ancestors(self) -> List['BCP47Tag']:
        """Get all ancestors (parents up to root)."""
        ancestors = []
        current = self.get_parent()
        while current:
            ancestors.append(current)
            current = current.get_parent()
        return ancestors
    
    def _build_tag(self, lang: str, script: Optional[str], 
                   region: Optional[str], variants: List[str]) -> str:
        """Build tag string from components."""
        parts = [lang]
        if script:
            parts.append(script)
        if region:
            parts.append(region)
        parts.extend(variants)
        return '-'.join(parts)
    
    def is_base_language(self) -> bool:
        """Check if this is a base language (no script, region, variant)."""
        return (self.script is None and 
                self.region is None and 
                len(self.variants) == 0)
    
    def __str__(self) -> str:
        return self.raw
    
    def __hash__(self):
        return hash(self.raw.lower())
    
    def __eq__(self, other):
        if isinstance(other, BCP47Tag):
            return self.raw.lower() == other.raw.lower()
        return False


# =============================================================================
# BCP47 PARSER
# =============================================================================

class BCP47Parser:
    """
    Parser for BCP47 language tags.
    
    Based on RFC 5646 grammar:
        langtag = language ["-" script] ["-" region] *("-" variant)
                  *("-" extension) ["-" privateuse]
    """
    
    # Regex patterns based on RFC 5646
    LANGUAGE_PATTERN = r'^([a-zA-Z]{2,3}|[a-zA-Z]{4}|[a-zA-Z]{5,8})$'
    SCRIPT_PATTERN = r'^[a-zA-Z]{4}$'
    REGION_PATTERN = r'^([a-zA-Z]{2}|[0-9]{3})$'
    VARIANT_PATTERN = r'^([a-zA-Z0-9]{5,8}|[0-9][a-zA-Z0-9]{3})$'
    
    def parse(self, tag: str) -> Optional[BCP47Tag]:
        """
        Parse a BCP47 tag into components.
        
        Args:
            tag: BCP47 language tag string
            
        Returns:
            BCP47Tag or None if invalid
        """
        if not tag:
            return None
        
        # Handle private use tags
        if tag.lower().startswith('x-'):
            return BCP47Tag(
                raw=tag,
                language='x',
                private_use=tag[2:]
            )
        
        parts = tag.split('-')
        
        # First part must be language
        if not re.match(self.LANGUAGE_PATTERN, parts[0]):
            return None
        
        language = parts[0].lower()
        script = None
        region = None
        variants = []
        extensions = []
        private_use = None
        
        i = 1
        
        # Check for script (4 letters)
        if i < len(parts) and re.match(self.SCRIPT_PATTERN, parts[i]):
            script = parts[i].title()  # Capitalize first letter
            i += 1
        
        # Check for region (2 letters or 3 digits)
        if i < len(parts) and re.match(self.REGION_PATTERN, parts[i]):
            region = parts[i].upper()
            i += 1
        
        # Check for variants
        while i < len(parts) and re.match(self.VARIANT_PATTERN, parts[i]):
            variants.append(parts[i].lower())
            i += 1
        
        # Handle extensions and private use (simplified)
        while i < len(parts):
            if parts[i].lower() == 'x':
                private_use = '-'.join(parts[i+1:])
                break
            else:
                extensions.append(parts[i])
            i += 1
        
        # Build normalized raw tag
        raw_parts = [language]
        if script:
            raw_parts.append(script)
        if region:
            raw_parts.append(region)
        raw_parts.extend(variants)
        if extensions:
            raw_parts.extend(extensions)
        if private_use:
            raw_parts.extend(['x', private_use])
        
        return BCP47Tag(
            raw='-'.join(raw_parts),
            language=language,
            script=script,
            region=region,
            variants=variants,
            extensions=extensions,
            private_use=private_use,
        )


# =============================================================================
# HIERARCHY BUILDER
# =============================================================================

@dataclass
class HierarchyEdge:
    """Represents a parent-child relationship in the hierarchy."""
    child: str      # More specific tag (e.g., "en-US")
    parent: str     # More general tag (e.g., "en")
    
    def __str__(self) -> str:
        return f"{self.child} ⊑ {self.parent}"


@dataclass 
class LanguageHierarchy:
    """
    Complete language tag hierarchy.
    """
    tags: Dict[str, BCP47Tag] = field(default_factory=dict)
    edges: List[HierarchyEdge] = field(default_factory=list)
    base_languages: Set[str] = field(default_factory=set)
    
    def add_tag(self, tag: BCP47Tag):
        """Add a tag and compute its hierarchy edges."""
        key = tag.raw.lower()
        
        if key in self.tags:
            return
        
        self.tags[key] = tag
        
        # Track base languages
        if tag.is_base_language():
            self.base_languages.add(key)
        
        # Compute hierarchy edge
        parent = tag.get_parent()
        if parent:
            self.edges.append(HierarchyEdge(
                child=tag.raw,
                parent=parent.raw
            ))
            # Recursively add parent if not present
            if parent.raw.lower() not in self.tags:
                self.add_tag(parent)
    
    def get_ancestors(self, tag: str) -> List[str]:
        """Get all ancestors of a tag."""
        tag_lower = tag.lower()
        if tag_lower not in self.tags:
            return []
        
        return [t.raw for t in self.tags[tag_lower].get_ancestors()]
    
    def get_children(self, tag: str) -> List[str]:
        """Get direct children of a tag."""
        tag_lower = tag.lower()
        return [e.child for e in self.edges if e.parent.lower() == tag_lower]
    
    def get_statistics(self) -> Dict[str, int]:
        """Return hierarchy statistics."""
        return {
            "total_tags": len(self.tags),
            "base_languages": len(self.base_languages),
            "hierarchy_edges": len(self.edges),
            "tags_with_script": sum(1 for t in self.tags.values() if t.script),
            "tags_with_region": sum(1 for t in self.tags.values() if t.region),
        }


class HierarchyBuilder:
    """
    Builds language hierarchy from a set of BCP47 tags.
    """
    
    def __init__(self):
        self.parser = BCP47Parser()
        self.hierarchy = LanguageHierarchy()
    
    def add_tag(self, tag: str) -> Optional[BCP47Tag]:
        """Parse and add a single tag."""
        parsed = self.parser.parse(tag)
        if parsed:
            self.hierarchy.add_tag(parsed)
        return parsed
    
    def add_tags(self, tags: List[str]) -> int:
        """Add multiple tags. Returns count of successfully added."""
        count = 0
        for tag in tags:
            if self.add_tag(tag):
                count += 1
        return count
    
    def build_from_registry(self, registry) -> LanguageHierarchy:
        """
        Build hierarchy from IANA registry + common composite tags.
        
        Args:
            registry: IANARegistry from step1
        """
        # Add base languages
        for lang in registry.languages.values():
            if not lang.is_deprecated():
                self.add_tag(lang.subtag)
        
        # Generate common composite tags
        common_regions = ['US', 'GB', 'CA', 'AU', 'DE', 'AT', 'CH', 
                         'FR', 'BE', 'ES', 'MX', 'AR', 'CO',
                         'BR', 'PT', 'CN', 'TW', 'HK', 'SG',
                         'JP', 'KR', 'IN', 'RU', 'SA', 'AE', 'EG']
        
        common_scripts = ['Hans', 'Hant', 'Latn', 'Cyrl', 'Arab']
        
        # Languages that commonly have regional variants
        regional_languages = ['en', 'es', 'fr', 'de', 'pt', 'ar', 'zh']
        
        for lang in regional_languages:
            if lang in registry.languages:
                for region in common_regions:
                    if region.lower() in registry.regions:
                        self.add_tag(f"{lang}-{region}")
        
        # Chinese script variants
        self.add_tag("zh-Hans")
        self.add_tag("zh-Hant")
        self.add_tag("zh-Hans-CN")
        self.add_tag("zh-Hans-SG")
        self.add_tag("zh-Hant-TW")
        self.add_tag("zh-Hant-HK")
        
        # Serbian script variants
        self.add_tag("sr-Latn")
        self.add_tag("sr-Cyrl")
        
        return self.hierarchy
    
    def get_hierarchy(self) -> LanguageHierarchy:
        return self.hierarchy


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Test the hierarchy builder."""
    
    # Test parser
    print("="*60)
    print("BCP47 Parser Tests")
    print("="*60)
    
    parser = BCP47Parser()
    test_tags = [
        "en",
        "en-US",
        "en-GB",
        "zh",
        "zh-Hans",
        "zh-Hant",
        "zh-Hans-CN",
        "zh-Hant-TW",
        "sr-Latn",
        "sr-Cyrl",
        "de-AT",
        "pt-BR",
    ]
    
    for tag in test_tags:
        parsed = parser.parse(tag)
        if parsed:
            parent = parsed.get_parent()
            parent_str = parent.raw if parent else "None (root)"
            print(f"  {tag:15} → parent: {parent_str}")
    
    # Test hierarchy
    print("\n" + "="*60)
    print("Hierarchy Builder Tests")
    print("="*60)
    
    builder = HierarchyBuilder()
    builder.add_tags(test_tags)
    
    hierarchy = builder.get_hierarchy()
    
    print("\nHierarchy Edges (⊑ = subsumes):")
    for edge in hierarchy.edges:
        print(f"  {edge}")
    
    print("\nBase Languages:")
    print(f"  {', '.join(sorted(hierarchy.base_languages))}")
    
    print("\nStatistics:")
    for key, value in hierarchy.get_statistics().items():
        print(f"  {key}: {value}")
    
    # Test ancestry
    print("\n" + "-"*60)
    print("Ancestry Tests:")
    print("-"*60)
    
    for tag in ["zh-Hans-CN", "en-US", "sr-Latn"]:
        ancestors = hierarchy.get_ancestors(tag)
        print(f"  {tag} → {' → '.join(ancestors) if ancestors else '(root)'}")
    
    return hierarchy


if __name__ == "__main__":
    hierarchy = main()
