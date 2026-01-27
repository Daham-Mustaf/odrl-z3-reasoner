#!/usr/bin/env python3
"""
ODRL-SA Language Ontology Builder - Step 1: IANA Registry Parser

Parses the IANA Language Subtag Registry to extract:
- Base languages (ISO 639)
- Scripts (ISO 15924)
- Regions (ISO 3166-1 / UN M.49)
- Deprecated codes and their preferred values

Source: https://www.iana.org/assignments/language-subtag-registry

This is Step 1 of the ontology building pipeline.
"""

import re
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
from pathlib import Path


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class SubtagType(Enum):
    """Types of subtags in BCP47."""
    LANGUAGE = "language"
    SCRIPT = "script"
    REGION = "region"
    VARIANT = "variant"
    GRANDFATHERED = "grandfathered"
    REDUNDANT = "redundant"
    EXTLANG = "extlang"


@dataclass
class Subtag:
    """
    Represents a single subtag from IANA registry.
    
    Examples:
        - language: en, de, zh
        - script: Hans, Hant, Latn
        - region: US, GB, CN
    """
    type: SubtagType
    subtag: str
    description: List[str] = field(default_factory=list)
    added: Optional[str] = None
    deprecated: Optional[str] = None
    preferred_value: Optional[str] = None
    suppress_script: Optional[str] = None
    scope: Optional[str] = None  # macrolanguage, collection, etc.
    macrolanguage: Optional[str] = None
    prefix: List[str] = field(default_factory=list)
    comments: Optional[str] = None
    
    def is_deprecated(self) -> bool:
        return self.deprecated is not None
    
    def has_preferred(self) -> bool:
        return self.preferred_value is not None
    
    def __str__(self) -> str:
        desc = self.description[0] if self.description else "?"
        status = " (DEPRECATED)" if self.is_deprecated() else ""
        return f"{self.subtag}: {desc}{status}"


@dataclass
class IANARegistry:
    """
    Complete IANA Language Subtag Registry.
    """
    file_date: Optional[str] = None
    languages: Dict[str, Subtag] = field(default_factory=dict)
    scripts: Dict[str, Subtag] = field(default_factory=dict)
    regions: Dict[str, Subtag] = field(default_factory=dict)
    variants: Dict[str, Subtag] = field(default_factory=dict)
    grandfathered: Dict[str, Subtag] = field(default_factory=dict)
    redundant: Dict[str, Subtag] = field(default_factory=dict)
    extlangs: Dict[str, Subtag] = field(default_factory=dict)
    
    def add_subtag(self, subtag: Subtag):
        """Add a subtag to the appropriate dictionary."""
        key = subtag.subtag.lower()
        
        if subtag.type == SubtagType.LANGUAGE:
            self.languages[key] = subtag
        elif subtag.type == SubtagType.SCRIPT:
            self.scripts[key] = subtag
        elif subtag.type == SubtagType.REGION:
            self.regions[key] = subtag
        elif subtag.type == SubtagType.VARIANT:
            self.variants[key] = subtag
        elif subtag.type == SubtagType.GRANDFATHERED:
            self.grandfathered[key] = subtag
        elif subtag.type == SubtagType.REDUNDANT:
            self.redundant[key] = subtag
        elif subtag.type == SubtagType.EXTLANG:
            self.extlangs[key] = subtag
    
    def get_statistics(self) -> Dict[str, int]:
        """Return counts of each subtag type."""
        return {
            "languages": len(self.languages),
            "scripts": len(self.scripts),
            "regions": len(self.regions),
            "variants": len(self.variants),
            "grandfathered": len(self.grandfathered),
            "redundant": len(self.redundant),
            "extlangs": len(self.extlangs),
            "deprecated_languages": sum(1 for s in self.languages.values() if s.is_deprecated()),
            "deprecated_with_preferred": sum(1 for s in self.languages.values() if s.has_preferred()),
        }
    
    def get_deprecated_mappings(self) -> Dict[str, str]:
        """Get all deprecated → preferred mappings."""
        mappings = {}
        for subtag in self.languages.values():
            if subtag.has_preferred():
                mappings[subtag.subtag] = subtag.preferred_value
        return mappings


# =============================================================================
# PARSER
# =============================================================================

class IANARegistryParser:
    """
    Parser for IANA Language Subtag Registry.
    
    The registry format is:
        %%
        Type: language
        Subtag: en
        Description: English
        Added: 2005-10-16
        %%
    """
    
    REGISTRY_URL = "https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry"
    
    def __init__(self):
        self.registry = IANARegistry()
    
    def fetch_registry(self) -> str:
        """Fetch the registry from IANA."""
        print(f"Fetching registry from {self.REGISTRY_URL}...")
        with urllib.request.urlopen(self.REGISTRY_URL) as response:
            content = response.read().decode('utf-8')
        print(f"Fetched {len(content)} bytes")
        return content
    
    def load_from_file(self, filepath: str) -> str:
        """Load registry from local file."""
        print(f"Loading registry from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Loaded {len(content)} bytes")
        return content
    
    def parse(self, content: str) -> IANARegistry:
        """Parse the registry content."""
        self.registry = IANARegistry()
        
        # Split into records (separated by %%)
        records = content.split('%%')
        
        for record in records:
            record = record.strip()
            if not record:
                continue
            
            # Check for File-Date header
            if record.startswith('File-Date:'):
                self.registry.file_date = record.split(':')[1].strip()
                continue
            
            # Parse the record
            subtag = self._parse_record(record)
            if subtag:
                self.registry.add_subtag(subtag)
        
        return self.registry
    
    def _parse_record(self, record: str) -> Optional[Subtag]:
        """Parse a single registry record."""
        fields = {}
        current_field = None
        current_value = []
        
        for line in record.split('\n'):
            line = line.rstrip()
            
            # Check for field continuation (starts with whitespace)
            if line.startswith(' ') or line.startswith('\t'):
                if current_field:
                    current_value.append(line.strip())
                continue
            
            # Save previous field
            if current_field:
                value = ' '.join(current_value)
                if current_field in fields:
                    # Handle multiple values (e.g., multiple Description fields)
                    if isinstance(fields[current_field], list):
                        fields[current_field].append(value)
                    else:
                        fields[current_field] = [fields[current_field], value]
                else:
                    fields[current_field] = value
            
            # Parse new field
            if ':' in line:
                parts = line.split(':', 1)
                current_field = parts[0].strip()
                current_value = [parts[1].strip()] if len(parts) > 1 else []
            else:
                current_field = None
                current_value = []
        
        # Save last field
        if current_field:
            value = ' '.join(current_value)
            if current_field in fields:
                if isinstance(fields[current_field], list):
                    fields[current_field].append(value)
                else:
                    fields[current_field] = [fields[current_field], value]
            else:
                fields[current_field] = value
        
        # Create Subtag object
        if 'Type' not in fields:
            return None
        
        try:
            subtag_type = SubtagType(fields['Type'].lower())
        except ValueError:
            return None
        
        # Get subtag or tag
        subtag_value = fields.get('Subtag') or fields.get('Tag')
        if not subtag_value:
            return None
        
        # Handle description (can be string or list)
        description = fields.get('Description', [])
        if isinstance(description, str):
            description = [description]
        
        # Handle prefix (can be string or list)
        prefix = fields.get('Prefix', [])
        if isinstance(prefix, str):
            prefix = [prefix]
        
        return Subtag(
            type=subtag_type,
            subtag=subtag_value,
            description=description,
            added=fields.get('Added'),
            deprecated=fields.get('Deprecated'),
            preferred_value=fields.get('Preferred-Value'),
            suppress_script=fields.get('Suppress-Script'),
            scope=fields.get('Scope'),
            macrolanguage=fields.get('Macrolanguage'),
            prefix=prefix,
            comments=fields.get('Comments'),
        )

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_REGISTRY_PATH = "data/iana/language-subtag-registry.txt"


# =============================================================================
# LOAD FUNCTION
# =============================================================================

def load_registry(path: str = DEFAULT_REGISTRY_PATH) -> IANARegistry:
    """Load and parse registry from local file."""
    parser = IANARegistryParser()
    content = parser.load_from_file(path)
    return parser.parse(content)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for testing the parser."""
    import argparse
    
    arg_parser = argparse.ArgumentParser(
        description="Parse IANA Language Subtag Registry"
    )
    arg_parser.add_argument(
        '--online', 
        action='store_true',
        help='Fetch from IANA instead of local file'
    )
    arg_parser.add_argument(
        '--file', '-f',
        default=DEFAULT_REGISTRY_PATH,
        help=f'Local registry file (default: {DEFAULT_REGISTRY_PATH})'
    )
    
    args = arg_parser.parse_args()
    
    parser = IANARegistryParser()
    
    # Load content
    if args.online:
        print("Mode: ONLINE (fetching from IANA)")
        try:
            content = parser.fetch_registry()
        except Exception as e:
            print(f"ERROR: Could not fetch registry: {e}")
            return None
    else:
        print(f"Mode: LOCAL ({args.file})")
        try:
            content = parser.load_from_file(args.file)
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.file}")
            print(f"")
            print(f"To download the registry:")
            print(f"  mkdir -p data/iana")
            print(f"  curl -o {args.file} \\")
            print(f"    https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry")
            return None
    
    registry = parser.parse(content)
    
    # Print statistics
    print("\n" + "="*60)
    print("IANA Language Subtag Registry Statistics")
    print("="*60)
    print(f"File Date: {registry.file_date}")
    print()
    
    stats = registry.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Print some examples
    print("\n" + "-"*60)
    print("Sample Languages:")
    print("-"*60)
    for code in ['en', 'de', 'zh', 'ar', 'he', 'iw']:
        if code in registry.languages:
            subtag = registry.languages[code]
            print(f"  {subtag}")
            if subtag.has_preferred():
                print(f"    → Preferred: {subtag.preferred_value}")
    
    print("\n" + "-"*60)
    print("Sample Scripts:")
    print("-"*60)
    for code in ['latn', 'hans', 'hant', 'cyrl', 'arab']:
        if code in registry.scripts:
            print(f"  {registry.scripts[code]}")
    
    print("\n" + "-"*60)
    print("Sample Regions:")
    print("-"*60)
    for code in ['us', 'gb', 'de', 'cn', 'tw']:
        if code in registry.regions:
            print(f"  {registry.regions[code]}")
    
    print("\n" + "-"*60)
    print("Deprecated → Preferred Mappings:")
    print("-"*60)
    mappings = registry.get_deprecated_mappings()
    for old, new in list(mappings.items())[:10]:
        print(f"  {old} → {new}")
    if len(mappings) > 10:
        print(f"  ... and {len(mappings) - 10} more")
    
    return registry


if __name__ == "__main__":
    registry = main()