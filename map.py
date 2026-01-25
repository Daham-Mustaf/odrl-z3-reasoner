#!/usr/bin/env python3
"""
BCP47 Language Tag Hierarchy for ODRL Policy Reasoning
Complete implementation with semantic annotations - FIXED VERSION

Author: [Your Name]
Date: 2026-01-21
Version: 1.0
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, SKOS, DCTERMS, OWL, XSD
from datetime import date

# ==========================================
# NAMESPACE DEFINITIONS
# ==========================================

# External ontologies
LCC_LR = Namespace("https://www.omg.org/spec/LCC/Languages/LanguageRepresentation/")
LCC_639_1 = Namespace("https://www.omg.org/spec/LCC/Languages/ISO639-1-LanguageCodes/")
LCC_3166_1 = Namespace("https://www.omg.org/spec/LCC/Countries/ISO3166-1-CountryCodes/")
LCC_15924 = Namespace("https://www.omg.org/spec/LCC/Languages/ISO15924-CodeSet/")

# Our ontology
LANG = Namespace("http://w3id.org/odrl/bcp47/")
ONTOLOGY = URIRef("http://w3id.org/odrl/bcp47")

# Standards references
RFC5646 = Namespace("https://www.rfc-editor.org/rfc/rfc5646")
ISO639 = URIRef("https://www.iso.org/standard/4766.html")
ISO3166 = URIRef("https://www.iso.org/standard/63545.html")
ISO15924 = URIRef("https://www.unicode.org/iso15924/")

# ==========================================
# HELPER DATA
# ==========================================

# Base languages from IANA registry
BASE_LANGUAGES = [
    ('en', 'English', 'Germanic'),
    ('zh', 'Chinese', 'Sino-Tibetan'),
    ('es', 'Spanish', 'Romance'),
    ('hi', 'Hindi', 'Indo-Aryan'),
    ('ar', 'Arabic', 'Semitic'),
    ('pt', 'Portuguese', 'Romance'),
    ('bn', 'Bengali', 'Indo-Aryan'),
    ('ru', 'Russian', 'Slavic'),
    ('ja', 'Japanese', 'Japonic'),
    ('de', 'German', 'Germanic'),
    ('fr', 'French', 'Romance'),
    ('ko', 'Korean', 'Koreanic'),
]

# Create helper dictionary for lookups
LANG_TAG_TO_NAME = {tag: name for tag, name, _ in BASE_LANGUAGES}

# Regional variants: (tag, base, region_code, region_name, label)
REGIONAL_VARIANTS = [
    ('en-US', 'en', 'US', 'UnitedStates', 'English (United States)'),
    ('en-GB', 'en', 'GB', 'UnitedKingdom', 'English (United Kingdom)'),
    ('en-AU', 'en', 'AU', 'Australia', 'English (Australia)'),
    ('en-CA', 'en', 'CA', 'Canada', 'English (Canada)'),
    ('en-IN', 'en', 'IN', 'India', 'English (India)'),
    
    ('es-ES', 'es', 'ES', 'Spain', 'Spanish (Spain)'),
    ('es-MX', 'es', 'MX', 'Mexico', 'Spanish (Mexico)'),
    ('es-AR', 'es', 'AR', 'Argentina', 'Spanish (Argentina)'),
    ('es-CO', 'es', 'CO', 'Colombia', 'Spanish (Colombia)'),
    
    ('fr-FR', 'fr', 'FR', 'France', 'French (France)'),
    ('fr-CA', 'fr', 'CA', 'Canada', 'French (Canada)'),
    ('fr-BE', 'fr', 'BE', 'Belgium', 'French (Belgium)'),
    ('fr-CH', 'fr', 'CH', 'Switzerland', 'French (Switzerland)'),
    
    ('de-DE', 'de', 'DE', 'Germany', 'German (Germany)'),
    ('de-AT', 'de', 'AT', 'Austria', 'German (Austria)'),
    ('de-CH', 'de', 'CH', 'Switzerland', 'German (Switzerland)'),
    
    ('pt-PT', 'pt', 'PT', 'Portugal', 'Portuguese (Portugal)'),
    ('pt-BR', 'pt', 'BR', 'Brazil', 'Portuguese (Brazil)'),
    
    ('ar-SA', 'ar', 'SA', 'SaudiArabia', 'Arabic (Saudi Arabia)'),
    ('ar-EG', 'ar', 'EG', 'Egypt', 'Arabic (Egypt)'),
    ('ar-AE', 'ar', 'AE', 'UnitedArabEmirates', 'Arabic (United Arab Emirates)'),
]

# Script variants: (tag, base, script_code, label, script_desc)
SCRIPT_VARIANTS = [
    ('zh-Hans', 'zh', 'Hans', 'Chinese (Simplified)', 'Simplified Han script'),
    ('zh-Hant', 'zh', 'Hant', 'Chinese (Traditional)', 'Traditional Han script'),
    ('sr-Cyrl', 'sr', 'Cyrl', 'Serbian (Cyrillic)', 'Cyrillic script'),
    ('sr-Latn', 'sr', 'Latn', 'Serbian (Latin)', 'Latin script'),
]

# Complex tags: (tag, parent, region_code, region_name, label)
COMPLEX_TAGS = [
    ('zh-Hans-CN', 'zh-Hans', 'CN', 'China', 'Chinese (Simplified, China)'),
    ('zh-Hans-SG', 'zh-Hans', 'SG', 'Singapore', 'Chinese (Simplified, Singapore)'),
    ('zh-Hant-TW', 'zh-Hant', 'TW', 'Taiwan', 'Chinese (Traditional, Taiwan)'),
    ('zh-Hant-HK', 'zh-Hant', 'HK', 'HongKong', 'Chinese (Traditional, Hong Kong)'),
]

# ==========================================
# MAIN ONTOLOGY CREATION
# ==========================================

def create_complete_ontology():
    """
    Create complete BCP47 language hierarchy with full annotations
    """
    
    g = Graph()
    
    # Bind namespaces
    g.bind("lang", LANG)
    g.bind("skos", SKOS)
    g.bind("dct", DCTERMS)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("lcc-lr", LCC_LR)
    g.bind("lcc-639-1", LCC_639_1)
    g.bind("lcc-3166-1", LCC_3166_1)
    g.bind("lcc-15924", LCC_15924)
    
    print("="*70)
    print("Creating BCP47 Language Hierarchy with Semantic Annotations")
    print("="*70)
    
    # ==========================================
    # SECTION 1: ONTOLOGY METADATA
    # ==========================================
    
    print("\n[1/6] Creating ontology metadata...")
    
    g.add((ONTOLOGY, RDF.type, OWL.Ontology))
    
    g.add((ONTOLOGY, DCTERMS.title, 
           Literal("BCP47 Language Tag Hierarchy for ODRL Policy Reasoning", lang="en")))
    
    g.add((ONTOLOGY, DCTERMS.description, Literal("""
This ontology provides semantic grounding for ODRL language constraints (odrl:language) 
by mapping BCP47 language tags to SKOS concepts with hierarchical relationships.

DESIGN PRINCIPLES:
1. Zero new vocabulary: Reuses only existing W3C and OMG standards
2. Standards-based: All mappings grounded in official specifications
3. Hierarchical: Regional and script variants linked via skos:broader
4. Component-linked: Tags decomposed and linked to LCC authoritative URIs
5. SPARQL-queryable: Enables semantic reasoning over language hierarchies

STANDARDS REUSED:
- SKOS (W3C): Taxonomy structure (skos:Concept, skos:broader, skos:notation)
- OWL (W3C): Identity relations (owl:sameAs)
- Dublin Core: Metadata and component links (dct:language, dct:spatial, dct:conformsTo)
- LCC (OMG): Authoritative URIs for languages (ISO 639), regions (ISO 3166), scripts (ISO 15924)
    """, lang="en")))
    
    # Standards references
    g.add((ONTOLOGY, DCTERMS.source, RFC5646['']))
    g.add((ONTOLOGY, DCTERMS.source, URIRef("https://www.omg.org/spec/LCC/")))
    g.add((ONTOLOGY, DCTERMS.source, ISO639))
    g.add((ONTOLOGY, DCTERMS.source, ISO3166))
    
    # Metadata
    g.add((ONTOLOGY, DCTERMS.creator, Literal("Your Name")))
    g.add((ONTOLOGY, DCTERMS.created, Literal(date.today().isoformat(), datatype=XSD.date)))
    g.add((ONTOLOGY, OWL.versionInfo, Literal("1.0")))
    g.add((ONTOLOGY, RDFS.comment, Literal(
        "No custom properties or classes defined. Uses only standard vocabularies: "
        "SKOS, OWL, Dublin Core, LCC.", lang="en")))
    
    print(f"  ✓ Ontology metadata complete")
    
    # ==========================================
    # SECTION 2: CONCEPT SCHEME
    # ==========================================
    
    print("\n[2/6] Creating SKOS Concept Scheme...")
    
    scheme_uri = LANG["scheme"]
    
    g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    g.add((scheme_uri, DCTERMS.title, Literal("BCP47 Language Tags", lang="en")))
    g.add((scheme_uri, DCTERMS.description, Literal(
        "Hierarchical organization of BCP47 language tags for ODRL constraint reasoning.", 
        lang="en")))
    
    print(f"  ✓ Concept scheme created")
    
    # ==========================================
    # SECTION 3: BASE LANGUAGES
    # ==========================================
    
    print("\n[3/6] Creating base language concepts...")
    
    for tag, name, family in BASE_LANGUAGES:
        concept_uri = LANG[tag]
        lcc_uri = LCC_639_1[name]
        
        # Basic properties
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.notation, Literal(tag, datatype=XSD.language)))
        g.add((concept_uri, SKOS.prefLabel, Literal(name, lang="en")))
        g.add((concept_uri, SKOS.inScheme, scheme_uri))
        g.add((concept_uri, SKOS.topConceptOf, scheme_uri))
        
        # Link to LCC
        g.add((concept_uri, OWL.sameAs, lcc_uri))
        g.add((concept_uri, DCTERMS.source, ISO639))
        
        # Annotation for first example
        if tag == 'en':
            g.add((concept_uri, RDFS.comment, Literal(
                f"Base language concept for {name} (ISO 639-1: {tag}). "
                f"Linked to LCC authoritative URI via owl:sameAs. All regional and script "
                f"variants of {name} are represented as narrower concepts (skos:broader).",
                lang="en")))
            g.add((concept_uri, SKOS.note, Literal(
                "This is an example of the base language pattern. All base languages follow "
                "this structure: skos:Concept with notation, prefLabel, owl:sameAs to LCC, "
                "and topConceptOf the scheme.",
                lang="en")))
        
        print(f"  ✓ {tag:3s} → {name:15s} (family: {family})")
    
    print(f"  ✓ Created {len(BASE_LANGUAGES)} base language concepts")
    
    # ==========================================
    # SECTION 4: REGIONAL VARIANTS
    # ==========================================
    
    print("\n[4/6] Creating regional variant concepts...")
    
    first_regional = True
    
    for tag, base, region_code, region_name, label in REGIONAL_VARIANTS:
        concept_uri = LANG[tag]
        base_uri = LANG[base]
        
        # Get language name from lookup dictionary
        lang_name = LANG_TAG_TO_NAME.get(base, base.upper())
        lcc_lang = LCC_639_1[lang_name]
        lcc_region = LCC_3166_1[region_name]
        
        # Basic properties
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.notation, Literal(tag, datatype=XSD.language)))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.inScheme, scheme_uri))
        
        # Hierarchy
        g.add((concept_uri, SKOS.broader, base_uri))
        
        # Components
        g.add((concept_uri, DCTERMS.language, lcc_lang))
        g.add((concept_uri, DCTERMS.spatial, lcc_region))
        g.add((concept_uri, DCTERMS.source, RFC5646['#section-2.2.4']))
        
        # Detailed annotation for first example
        if first_regional:
            g.add((concept_uri, RDFS.comment, Literal(
                f"{label} is a regional variant of {lang_name}. "
                f"Per BCP47 (RFC 5646, Section 2.2.4), regional subtags (ISO 3166-1) "
                f"specialize the primary language by geographic usage. The hierarchy "
                f"'{tag} skos:broader {base}' represents that {region_code} variant "
                f"is a more specific form of the base language.",
                lang="en")))
            g.add((concept_uri, SKOS.note, Literal(
                f"BCP47 tag decomposed into components: language '{base}' (ISO 639-1) "
                f"→ lcc-639-1:{lang_name}, region '{region_code}' "
                f"(ISO 3166-1) → lcc-3166-1:{region_name}. This component pattern applies "
                f"to all [language]-[region] tags in this ontology.",
                lang="en")))
            first_regional = False
        
        print(f"  ✓ {tag:8s} → broader: {base:3s} (region: {region_code})")
    
    print(f"  ✓ Created {len(REGIONAL_VARIANTS)} regional variants")
    
    # ==========================================
    # SECTION 5: SCRIPT VARIANTS
    # ==========================================
    
    print("\n[5/6] Creating script variant concepts...")
    
    # Add Serbian base first (not in BASE_LANGUAGES)
    if 'sr' not in LANG_TAG_TO_NAME:
        sr_uri = LANG['sr']
        g.add((sr_uri, RDF.type, SKOS.Concept))
        g.add((sr_uri, SKOS.notation, Literal('sr', datatype=XSD.language)))
        g.add((sr_uri, SKOS.prefLabel, Literal('Serbian', lang="en")))
        g.add((sr_uri, SKOS.inScheme, scheme_uri))
        g.add((sr_uri, SKOS.topConceptOf, scheme_uri))
        g.add((sr_uri, OWL.sameAs, LCC_639_1['Serbian']))
        LANG_TAG_TO_NAME['sr'] = 'Serbian'  # Add to lookup
        print(f"  ✓ sr  → Serbian (added for script variants)")
    
    first_script = True
    
    for tag, base, script_code, label, script_desc in SCRIPT_VARIANTS:
        concept_uri = LANG[tag]
        base_uri = LANG[base]
        lcc_script = LCC_15924[script_code]
        
        # Basic properties
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.notation, Literal(tag, datatype=XSD.language)))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.inScheme, scheme_uri))
        
        # Hierarchy
        g.add((concept_uri, SKOS.broader, base_uri))
        
        # Components
        lang_name = LANG_TAG_TO_NAME.get(base, base.upper())
        g.add((concept_uri, DCTERMS.language, LCC_639_1[lang_name]))
        g.add((concept_uri, DCTERMS.conformsTo, lcc_script))
        g.add((concept_uri, DCTERMS.source, RFC5646['#section-2.2.3']))
        
        # Annotation for first example
        if first_script:
            g.add((concept_uri, RDFS.comment, Literal(
                f"{label} is a script variant of {base.upper()}. Per BCP47 (RFC 5646, "
                f"Section 2.2.3), script subtags (ISO 15924) specialize a language by "
                f"writing system. The '{script_code}' script ({script_desc}) distinguishes "
                f"this variant from other writing systems of the same language.",
                lang="en")))
            first_script = False
        
        print(f"  ✓ {tag:10s} → broader: {base:3s} (script: {script_code})")
    
    print(f"  ✓ Created {len(SCRIPT_VARIANTS)} script variants")
    
    # ==========================================
    # SECTION 6: COMPLEX TAGS
    # ==========================================
    
    print("\n[6/6] Creating complex (multi-level) tags...")
    
    first_complex = True
    
    for tag, parent, region_code, region_name, label in COMPLEX_TAGS:
        concept_uri = LANG[tag]
        parent_uri = LANG[parent]
        lcc_region = LCC_3166_1[region_name]
        
        # Basic properties
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.notation, Literal(tag, datatype=XSD.language)))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.inScheme, scheme_uri))
        
        # Hierarchy
        g.add((concept_uri, SKOS.broader, parent_uri))
        
        # Components
        g.add((concept_uri, DCTERMS.language, LCC_639_1['Chinese']))
        g.add((concept_uri, DCTERMS.spatial, lcc_region))
        
        # Script from parent
        if 'Hans' in parent:
            g.add((concept_uri, DCTERMS.conformsTo, LCC_15924['Hans']))
        elif 'Hant' in parent:
            g.add((concept_uri, DCTERMS.conformsTo, LCC_15924['Hant']))
        
        g.add((concept_uri, DCTERMS.source, RFC5646['#section-2.1']))
        
        # Annotation for first example
        if first_complex:
            g.add((concept_uri, RDFS.comment, Literal(
                f"{label} is a complex tag combining script and region. "
                f"Multi-level hierarchy: {tag} → {parent} → zh. Per BCP47, complex tags "
                f"are built by adding subtags to existing variants.",
                lang="en")))
            first_complex = False
        
        print(f"  ✓ {tag:12s} → broader: {parent:10s} → zh")
    
    print(f"  ✓ Created {len(COMPLEX_TAGS)} complex tags")
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    total_concepts = len(list(g.subjects(RDF.type, SKOS.Concept)))
    total_hierarchy = len(list(g.triples((None, SKOS.broader, None))))
    total_triples = len(g)
    
    print("\n" + "="*70)
    print("ONTOLOGY STATISTICS")
    print("="*70)
    print(f"Total concepts:        {total_concepts}")
    print(f"Base languages:        {len(BASE_LANGUAGES) + 1}")  # +1 for Serbian
    print(f"Regional variants:     {len(REGIONAL_VARIANTS)}")
    print(f"Script variants:       {len(SCRIPT_VARIANTS)}")
    print(f"Complex tags:          {len(COMPLEX_TAGS)}")
    print(f"Hierarchy relations:   {total_hierarchy}")
    print(f"Total RDF triples:     {total_triples}")
    print("="*70)
    
    return g

# ==========================================
# VALIDATION TESTS
# ==========================================

def run_validation_tests(g):
    """
    Comprehensive validation tests
    """
    
    print("\n" + "="*70)
    print("VALIDATION TESTS")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Resolve BCP47 tag
    print("\n[Test 1] Resolve BCP47 tag to concept")
    query = """
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?concept WHERE {
        ?concept skos:notation "en-US"^^xsd:language .
    }
    """
    results = list(g.query(query))
    if len(results) == 1:
        print(f"  ✓ PASS: Resolved 'en-US' to {results[0].concept}")
        tests_passed += 1
    else:
        print(f"  ✗ FAIL: Expected 1 result, got {len(results)}")
        tests_failed += 1
    
    # Test 2: Direct hierarchy
    print("\n[Test 2] Direct hierarchy: en-US → en")
    query = """
    PREFIX lang: <http://w3id.org/odrl/bcp47/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    ASK { lang:en-US skos:broader lang:en }
    """
    result = bool(g.query(query))
    if result:
        print(f"  ✓ PASS: en-US is directly broader en")
        tests_passed += 1
    else:
        print(f"  ✗ FAIL: Hierarchy not found")
        tests_failed += 1
    
    # Test 3: Transitive hierarchy
    print("\n[Test 3] Transitive hierarchy: zh-Hans-CN → zh")
    query = """
    PREFIX lang: <http://w3id.org/odrl/bcp47/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    ASK { lang:zh-Hans-CN skos:broader+ lang:zh }
    """
    result = bool(g.query(query))
    if result:
        print(f"  ✓ PASS: zh-Hans-CN is transitively broader zh")
        tests_passed += 1
    else:
        print(f"  ✗ FAIL: Transitive hierarchy not found")
        tests_failed += 1
    
    # Test 4: Find English variants
    print("\n[Test 4] Find all English variants")
    query = """
    PREFIX lang: <http://w3id.org/odrl/bcp47/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT ?variant ?label WHERE {
        ?variant skos:broader+ lang:en ;
                 skos:prefLabel ?label .
    }
    ORDER BY ?label
    """
    results = list(g.query(query))
    print(f"  Found {len(results)} English variants:")
    for row in results[:5]:
        print(f"    - {row.label}")
    if len(results) >= 5:
        print(f"  ✓ PASS: Found {len(results)} variants")
        tests_passed += 1
    else:
        print(f"  ✗ FAIL: Expected at least 5, got {len(results)}")
        tests_failed += 1
    
    # Test 5: Conflict detection
    print("\n[Test 5] ODRL Conflict Detection")
    print("  Scenario: PERMIT 'en' + PROHIBIT 'en-US'")
    query = """
    PREFIX lang: <http://w3id.org/odrl/bcp47/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    ASK { lang:en-US skos:broader+ lang:en }
    """
    result = bool(g.query(query))
    if result:
        print(f"  ✓ PASS: Conflict detected")
        tests_passed += 1
    else:
        print(f"  ✗ FAIL: Conflict not detected")
        tests_failed += 1
    
    # Summary
    print("\n" + "="*70)
    print(f"TESTS PASSED: {tests_passed}/{tests_passed + tests_failed}")
    if tests_failed == 0:
        print("✓ ALL TESTS PASSED")
    else:
        print(f"✗ {tests_failed} TEST(S) FAILED")
    print("="*70)
    
    return tests_failed == 0

# ==========================================
# EXPORT
# ==========================================

def export_ontology(g):
    """Export ontology"""
    
    print("\n" + "="*70)
    print("EXPORTING ONTOLOGY")
    print("="*70)
    
    formats = [
        ('bcp47-language-hierarchy.ttl', 'turtle'),
        ('bcp47-language-hierarchy.rdf', 'xml'),
        ('bcp47-language-hierarchy.jsonld', 'json-ld'),
    ]
    
    for filename, fmt in formats:
        g.serialize(filename, format=fmt)
        print(f"  ✓ Exported: {filename}")
    
    print("="*70)

# ==========================================
# MAIN
# ==========================================

def main():
    """Main execution"""
    
    print("\n" + "="*70)
    print("BCP47 LANGUAGE HIERARCHY - COMPLETE IMPLEMENTATION")
    print("="*70)
    
    g = create_complete_ontology()
    all_passed = run_validation_tests(g)
    export_ontology(g)
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ SUCCESS: Ontology created and validated")
        print("✓ Files exported")
        print("✓ Ready for ODRL policy reasoning")
    else:
        print("⚠ WARNING: Some tests failed")
    print("="*70)
    print()

if __name__ == "__main__":
    main()