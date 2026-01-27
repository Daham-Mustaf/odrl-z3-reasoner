#!/usr/bin/env python3
"""
ODRL-SA Language Ontology Builder - Step 3: RDF/SKOS Generator

Generates the final SKOS ontology in Turtle format with:
- skos:Concept for each language tag
- skos:broader for hierarchy
- skos:exactMatch for deprecated codes
- skos:notation for tag values
- Links to LCC authoritative URIs

This is Step 3 of the ontology building pipeline.

Depends on: Step 1 (IANA Parser), Step 2 (Hierarchy Builder)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import date


# =============================================================================
# NAMESPACE CONFIGURATION
# =============================================================================

@dataclass
class Namespaces:
    """RDF namespace configuration."""
    
    # Ontology namespace (separate from instance namespace per review)
    ontology_iri: str = "http://w3id.org/odrl/bcp47"
    
    # Instance namespace (concepts live here)
    instance_base: str = "http://w3id.org/odrl/bcp47/lang/"
    
    # Scheme IRI
    scheme_iri: str = "http://w3id.org/odrl/bcp47/lang/scheme"
    
    # Standard namespaces
    skos: str = "http://www.w3.org/2004/02/skos/core#"
    owl: str = "http://www.w3.org/2002/07/owl#"
    rdfs: str = "http://www.w3.org/2000/01/rdf-schema#"
    rdf: str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xsd: str = "http://www.w3.org/2001/XMLSchema#"
    dct: str = "http://purl.org/dc/terms/"
    
    # LCC namespaces (OMG authoritative URIs)
    lcc_639_1: str = "https://www.omg.org/spec/LCC/Languages/ISO639-1-LanguageCodes/"
    lcc_639_2: str = "https://www.omg.org/spec/LCC/Languages/ISO639-2-LanguageCodes/"
    lcc_3166_1: str = "https://www.omg.org/spec/LCC/Countries/ISO3166-1-CountryCodes/"
    lcc_15924: str = "https://www.omg.org/spec/LCC/Languages/ISO15924-CodeSet/"


# =============================================================================
# LCC MAPPINGS
# =============================================================================

# ISO 639-1 code → LCC local name
# Source: https://www.omg.org/spec/LCC/Languages/ISO639-1-LanguageCodes/
LCC_LANGUAGE_MAP = {
    "aa": "Afar", "ab": "Abkhazian", "af": "Afrikaans", "ak": "Akan",
    "am": "Amharic", "ar": "Arabic", "as": "Assamese", "ay": "Aymara",
    "az": "Azerbaijani", "ba": "Bashkir", "be": "Belarusian", "bg": "Bulgarian",
    "bn": "Bengali", "bo": "Tibetan", "br": "Breton", "bs": "Bosnian",
    "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish",
    "de": "German", "dz": "Dzongkha", "el": "ModernGreek", "en": "English",
    "eo": "Esperanto", "es": "Spanish", "et": "Estonian", "eu": "Basque",
    "fa": "Persian", "fi": "Finnish", "fj": "Fijian", "fo": "Faroese",
    "fr": "French", "fy": "WesternFrisian", "ga": "Irish", "gd": "ScottishGaelic",
    "gl": "Galician", "gn": "Guarani", "gu": "Gujarati", "ha": "Hausa",
    "he": "Hebrew", "hi": "Hindi", "hr": "Croatian", "hu": "Hungarian",
    "hy": "Armenian", "id": "Indonesian", "is": "Icelandic", "it": "Italian",
    "ja": "Japanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
    "kn": "Kannada", "ko": "Korean", "ku": "Kurdish", "ky": "Kirghiz",
    "la": "Latin", "lb": "Luxembourgish", "lo": "Lao", "lt": "Lithuanian",
    "lv": "Latvian", "mg": "Malagasy", "mi": "Maori", "mk": "Macedonian",
    "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi", "ms": "Malay",
    "mt": "Maltese", "my": "Burmese", "ne": "Nepali", "nl": "Dutch",
    "no": "Norwegian", "pa": "Panjabi", "pl": "Polish", "ps": "Pushto",
    "pt": "Portuguese", "qu": "Quechua", "ro": "Romanian", "ru": "Russian",
    "rw": "Kinyarwanda", "sa": "Sanskrit", "sd": "Sindhi", "si": "Sinhala",
    "sk": "Slovak", "sl": "Slovenian", "so": "Somali", "sq": "Albanian",
    "sr": "Serbian", "sv": "Swedish", "sw": "Swahili", "ta": "Tamil",
    "te": "Telugu", "tg": "Tajik", "th": "Thai", "ti": "Tigrinya",
    "tk": "Turkmen", "tl": "Tagalog", "tr": "Turkish", "uk": "Ukrainian",
    "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese", "yi": "Yiddish",
    "zh": "Chinese", "zu": "Zulu",
}

# ISO 3166-1 alpha-2 → LCC local name
# Source: https://www.omg.org/spec/LCC/Countries/ISO3166-1-CountryCodes/
LCC_REGION_MAP = {
    "AD": "Andorra", "AE": "UnitedArabEmirates", "AF": "Afghanistan",
    "AR": "Argentina", "AT": "Austria", "AU": "Australia", "BE": "Belgium",
    "BR": "Brazil", "CA": "Canada", "CH": "Switzerland", "CN": "China",
    "CO": "Colombia", "DE": "Germany", "EG": "Egypt", "ES": "Spain",
    "FR": "France", "GB": "UnitedKingdom", "HK": "HongKong", "IN": "India",
    "IT": "Italy", "JP": "Japan", "KR": "SouthKorea", "MX": "Mexico",
    "NL": "Netherlands", "PT": "Portugal", "RU": "Russia", "SA": "SaudiArabia",
    "SG": "Singapore", "TW": "Taiwan", "US": "UnitedStates", "ZA": "SouthAfrica",
}

# ISO 15924 → LCC local name  
# Source: https://www.omg.org/spec/LCC/Languages/ISO15924-CodeSet/
LCC_SCRIPT_MAP = {
    "Arab": "Arab", "Armn": "Armn", "Cyrl": "Cyrl", "Deva": "Deva",
    "Geor": "Geor", "Grek": "Grek", "Hang": "Hang", "Hani": "Hani",
    "Hans": "Hans", "Hant": "Hant", "Hebr": "Hebr", "Jpan": "Jpan",
    "Kore": "Kore", "Latn": "Latn", "Thai": "Thai", "Tibt": "Tibt",
}


# =============================================================================
# TURTLE GENERATOR
# =============================================================================

class TurtleGenerator:
    """
    Generates SKOS Turtle output for the language ontology.
    """
    
    def __init__(self, namespaces: Namespaces = None):
        self.ns = namespaces or Namespaces()
        self.lines: List[str] = []
    
    def generate(self, hierarchy, registry, deprecated_mappings: Dict[str, str]) -> str:
        """
        Generate complete Turtle ontology.
        
        Args:
            hierarchy: LanguageHierarchy from step 2
            registry: IANARegistry from step 1
            deprecated_mappings: Dict of deprecated → preferred codes
        """
        self.lines = []
        
        # Prefixes
        self._add_prefixes()
        
        # Ontology declaration
        self._add_ontology()
        
        # Concept scheme
        self._add_scheme()
        
        # All concepts
        self._add_concepts(hierarchy, registry)
        
        # Deprecated equivalences
        self._add_equivalences(deprecated_mappings)
        
        return '\n'.join(self.lines)
    
    def _add_prefixes(self):
        """Add Turtle prefix declarations."""
        self.lines.append(f"@prefix lang: <{self.ns.instance_base}> .")
        self.lines.append(f"@prefix skos: <{self.ns.skos}> .")
        self.lines.append(f"@prefix owl: <{self.ns.owl}> .")
        self.lines.append(f"@prefix rdfs: <{self.ns.rdfs}> .")
        self.lines.append(f"@prefix rdf: <{self.ns.rdf}> .")
        self.lines.append(f"@prefix xsd: <{self.ns.xsd}> .")
        self.lines.append(f"@prefix dct: <{self.ns.dct}> .")
        self.lines.append(f"@prefix lcc-639-1: <{self.ns.lcc_639_1}> .")
        self.lines.append(f"@prefix lcc-3166-1: <{self.ns.lcc_3166_1}> .")
        self.lines.append(f"@prefix lcc-15924: <{self.ns.lcc_15924}> .")
        self.lines.append("")
    
    def _add_ontology(self):
        """Add ontology declaration."""
        today = date.today().isoformat()
        
        self.lines.append(f"<{self.ns.ontology_iri}> a owl:Ontology ;")
        self.lines.append(f'    dct:title "BCP47 Language Tag Hierarchy for ODRL Policy Reasoning"@en ;')
        self.lines.append(f'    dct:created "{today}"^^xsd:date ;')
        self.lines.append(f'    rdfs:comment "Base language concepts include ISO 639-1 (2-letter) and ISO 639-3 (3-letter) codes as defined by the IANA Language Subtag Registry. Only ISO 639-1 codes have skos:exactMatch links to LCC."@en ;')
        self.lines.append(f'    dct:description """')
        self.lines.append('Semantic grounding for ODRL language constraints (odrl:language)')
        self.lines.append('by mapping BCP47 language tags to SKOS concepts with hierarchical relationships.')
        self.lines.append('')
        self.lines.append('DESIGN PRINCIPLES:')
        self.lines.append('1. Zero new vocabulary - reuses only SKOS, OWL, Dublin Core, LCC')
        self.lines.append('2. Hierarchy via skos:broader (derived from RFC 5646 composition rules)')
        self.lines.append('3. Equivalence via skos:exactMatch (not owl:sameAs)')
        self.lines.append('4. Disjointness is DERIVED, not asserted')
        self.lines.append('')
        self.lines.append('STANDARDS REUSED:')
        self.lines.append('- SKOS (W3C): Taxonomy structure')
        self.lines.append('- OWL (W3C): Ontology declaration')
        self.lines.append('- Dublin Core: Metadata')
        self.lines.append('- LCC (OMG): Authoritative URIs for ISO codes')
        self.lines.append('"""@en ;')
        self.lines.append(f'    dct:source <https://www.rfc-editor.org/rfc/rfc5646> ,')
        self.lines.append(f'               <https://www.iso.org/iso-639-language-codes.html> ,')
        self.lines.append(f'               <https://www.omg.org/spec/LCC/> ;')
        self.lines.append(f'    rdfs:comment "Generated by ODRL-SA Language Ontology Builder"@en ;')
        self.lines.append(f'    owl:versionInfo "1.0" .')
        self.lines.append("")
    
    def _add_scheme(self):
        """Add SKOS ConceptScheme."""
        self.lines.append(f"lang:scheme a skos:ConceptScheme ;")
        self.lines.append(f'    dct:title "BCP47 Language Tags"@en ;')
        self.lines.append(f'    dct:description "Hierarchical organization of BCP47 language tags for ODRL constraint reasoning."@en ;')
        self.lines.append(f'    skos:note "Hierarchy: specific tags (e.g., en-US) have skos:broader links to more general tags (e.g., en). Base languages are skos:topConceptOf this scheme."@en .')
        self.lines.append("")
        
    def _add_concepts(self, hierarchy, registry):
        """Add all language tag concepts."""
        
        # Sort for consistent output
        sorted_tags = sorted(hierarchy.tags.keys())
        
        for tag_key in sorted_tags:
            tag = hierarchy.tags[tag_key]
            self._add_concept(tag, hierarchy, registry)
    
    def _add_concept(self, tag, hierarchy, registry):
        """Add a single concept."""
        tag_id = self._tag_to_id(tag.raw)
        
        self.lines.append(f"lang:{tag_id} a skos:Concept ;")
        
        # Notation (the tag itself)
        self.lines.append(f'    skos:notation "{tag.raw}"^^xsd:language ;')
        
        # PrefLabel (human-readable name)
        label = self._get_label(tag, registry)
        self.lines.append(f'    skos:prefLabel "{label}"@en ;')
        
        # In scheme
        self.lines.append(f'    skos:inScheme lang:scheme ;')
        
        # Hierarchy
        if tag.is_base_language():
            self.lines.append(f'    skos:topConceptOf lang:scheme ;')
            
            # Link to LCC for base languages
            if tag.language in LCC_LANGUAGE_MAP:
                lcc_name = LCC_LANGUAGE_MAP[tag.language]
                self.lines.append(f'    skos:exactMatch lcc-639-1:{lcc_name} ;')
        else:
            # Add skos:broader to parent
            parent = tag.get_parent()
            if parent:
                parent_id = self._tag_to_id(parent.raw)
                self.lines.append(f'    skos:broader lang:{parent_id} ;')
        
        # Component links (for composite tags)
        if tag.script or tag.region:
            # Language component
            if tag.language in LCC_LANGUAGE_MAP:
                lcc_name = LCC_LANGUAGE_MAP[tag.language]
                self.lines.append(f'    dct:language lcc-639-1:{lcc_name} ;')
            
            # Script component
            if tag.script and tag.script in LCC_SCRIPT_MAP:
                lcc_script = LCC_SCRIPT_MAP[tag.script]
                self.lines.append(f'    dct:conformsTo lcc-15924:{lcc_script} ;')
            
            # Region component
            if tag.region and tag.region in LCC_REGION_MAP:
                lcc_region = LCC_REGION_MAP[tag.region]
                self.lines.append(f'    dct:spatial lcc-3166-1:{lcc_region} ;')
        
        # Source reference
        self.lines.append(f'    dct:source <https://www.rfc-editor.org/rfc/rfc5646> .')
        self.lines.append("")
    
    def _add_equivalences(self, deprecated_mappings: Dict[str, str]):
        """Add equivalence mappings for deprecated codes."""
        if not deprecated_mappings:
            return
        
        self.lines.append("# Deprecated code equivalences")
        self.lines.append("# These map old codes to their preferred modern equivalents")
        self.lines.append("")
        
        for old_code, new_code in sorted(deprecated_mappings.items()):
            old_id = self._tag_to_id(old_code)
            new_id = self._tag_to_id(new_code)
            
            self.lines.append(f"lang:{old_id} skos:exactMatch lang:{new_id} .")
        
        self.lines.append("")
    
    def _tag_to_id(self, tag: str) -> str:
        """Convert tag to valid RDF local name."""
        # Replace hyphens with underscores or keep as-is
        # Most systems handle hyphens fine in local names
        return tag
    
    def _get_label(self, tag, registry) -> str:
        """Get human-readable label for a tag."""
        
        # Base language
        if tag.is_base_language():
            if tag.language in registry.languages:
                return registry.languages[tag.language].description[0]
            return tag.language.upper()
        
        # Composite tag - build label from components
        parts = []
        
        # Language name
        if tag.language in registry.languages:
            parts.append(registry.languages[tag.language].description[0])
        else:
            parts.append(tag.language.upper())
        
        # Script name
        if tag.script:
            script_lower = tag.script.lower()
            if script_lower in registry.scripts:
                script_desc = registry.scripts[script_lower].description[0]
                # Simplify "Han (Simplified variant)" → "Simplified"
                if "Simplified" in script_desc:
                    parts.append("Simplified")
                elif "Traditional" in script_desc:
                    parts.append("Traditional")
                elif "Latin" in script_desc:
                    parts.append("Latin")
                elif "Cyrillic" in script_desc:
                    parts.append("Cyrillic")
                else:
                    parts.append(tag.script)
            else:
                parts.append(tag.script)
        
        # Region name
        if tag.region:
            region_lower = tag.region.lower()
            if region_lower in registry.regions:
                region_desc = registry.regions[region_lower].description[0]
                # Simplify long names
                if "United States" in region_desc:
                    parts.append("United States")
                elif "United Kingdom" in region_desc:
                    parts.append("United Kingdom")
                else:
                    parts.append(region_desc.split(',')[0])  # Take first part
            else:
                parts.append(tag.region)
        
        # Format: "Language (Script, Region)" or "Language (Region)"
        if len(parts) == 1:
            return parts[0]
        else:
            return f"{parts[0]} ({', '.join(parts[1:])})"


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Generate the complete ontology."""
    
    # Import step 1 and step 2
    from step1_iana_parser import IANARegistryParser, SAMPLE_REGISTRY
    from step2_hierarchy_builder import HierarchyBuilder
    
    print("="*60)
    print("Step 3: Generate RDF/SKOS Ontology")
    print("="*60)
    
    # Step 1: Parse IANA registry
    print("\n[1/3] Parsing IANA registry...")
    parser = IANARegistryParser()
    try:
        content = parser.fetch_registry()
    except Exception as e:
        print(f"  Could not fetch: {e}")
        print("  Using sample data...")
        content = SAMPLE_REGISTRY
    
    registry = parser.parse(content)
    print(f"  Loaded {len(registry.languages)} languages, "
          f"{len(registry.scripts)} scripts, {len(registry.regions)} regions")
    
    # Step 2: Build hierarchy
    print("\n[2/3] Building hierarchy...")
    builder = HierarchyBuilder()
    hierarchy = builder.build_from_registry(registry)
    
    stats = hierarchy.get_statistics()
    print(f"  Built {stats['total_tags']} tags, {stats['hierarchy_edges']} edges")
    
    # Step 3: Generate Turtle
    print("\n[3/3] Generating Turtle...")
    generator = TurtleGenerator()
    
    deprecated_mappings = registry.get_deprecated_mappings()
    turtle = generator.generate(hierarchy, registry, deprecated_mappings)
    
    # Save to file
    output_path = "bcp47-language-hierarchy-generated.ttl"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(turtle)
    
    print(f"  Written to {output_path}")
    print(f"  Size: {len(turtle)} characters, {turtle.count(chr(10))} lines")
    
    # Show sample
    print("\n" + "-"*60)
    print("Sample output (first 100 lines):")
    print("-"*60)
    for i, line in enumerate(turtle.split('\n')[:100]):
        print(line)
    
    return turtle


if __name__ == "__main__":
    turtle = main()
