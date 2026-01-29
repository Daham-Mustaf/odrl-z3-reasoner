#!/usr/bin/env python3
# src/grounding/unit/download_qudt.py
"""
Download QUDT Unit Vocabulary

Downloads the official QUDT unit vocabulary and extracts relevant units
for ODRL-SA static analysis.

Usage:
    python download_qudt.py
    
Output:
    data/qudt-unit.ttl      - Full QUDT vocabulary
    data/qudt-extracted.py  - Python dict of extracted units
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError

# QUDT URLs
QUDT_UNIT_URL = "https://qudt.org/3.1.10/vocab/unit.ttl"
QUDT_UNIT_URL_FALLBACK = "https://raw.githubusercontent.com/qudt/qudt-public-repo/main/vocab/unit/VOCAB_QUDT-UNITS-ALL-v2.1.ttl"

# Output directory
DATA_DIR = Path(__file__).parent / "data"


def download_file(url: str, output_path: Path) -> bool:
    """Download a file from URL."""
    print(f"Downloading {url}...")
    try:
        with urlopen(url, timeout=30) as response:
            content = response.read()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)
            print(f"  Saved to {output_path} ({len(content)} bytes)")
            return True
    except URLError as e:
        print(f"  Error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def parse_qudt_ttl(ttl_path: Path) -> Dict[str, dict]:
    """
    Parse QUDT TTL file and extract unit information.
    
    Returns dict of:
        code -> {uri, label, symbol, category}
    """
    try:
        from rdflib import Graph, Namespace, RDF, RDFS
        from rdflib.namespace import SKOS
    except ImportError:
        print("Error: rdflib required. Install with: pip install rdflib")
        return {}
    
    QUDT = Namespace("http://qudt.org/schema/qudt/")
    UNIT = Namespace("http://qudt.org/vocab/unit/")
    
    print(f"Parsing {ttl_path}...")
    g = Graph()
    g.parse(ttl_path, format="turtle")
    
    units = {}
    
    # Query for units
    for unit_uri in g.subjects(RDF.type, QUDT.Unit):
        uri_str = str(unit_uri)
        
        # Extract code from URI
        if "/unit/" in uri_str:
            code = uri_str.split("/unit/")[-1]
        else:
            continue
        
        # Skip complex codes (e.g., "M-PER-SEC2")
        if "-" in code and code not in ["KiloBYTE", "MegaBYTE", "GigaBYTE"]:
            continue
        
        # Get label
        label = None
        for lbl in g.objects(unit_uri, RDFS.label):
            if lbl.language == "en" or lbl.language is None:
                label = str(lbl)
                break
        
        # Get symbol
        symbol = None
        for sym in g.objects(unit_uri, QUDT.symbol):
            symbol = str(sym)
            break
        
        # Determine category based on quantity kind
        category = "unknown"
        for qk in g.objects(unit_uri, QUDT.hasQuantityKind):
            qk_str = str(qk).lower()
            if "currency" in qk_str or "money" in qk_str:
                category = "currency"
            elif "length" in qk_str or "distance" in qk_str:
                category = "size_physical"
            elif "time" in qk_str or "duration" in qk_str:
                category = "time"
            elif "information" in qk_str or "data" in qk_str:
                category = "size_data"
            elif "resolution" in qk_str or "frequency" in qk_str:
                category = "resolution"
            break
        
        units[code] = {
            "uri": uri_str,
            "label": label or code,
            "symbol": symbol,
            "category": category,
        }
    
    print(f"  Extracted {len(units)} units")
    return units


def generate_python_dict(units: Dict[str, dict], output_path: Path):
    """Generate Python file with unit dictionary."""
    
    # Filter to relevant units
    relevant_categories = {"currency", "resolution", "size_data", "size_physical", "time"}
    filtered = {k: v for k, v in units.items() if v["category"] in relevant_categories}
    
    content = '''# Auto-generated from QUDT vocabulary
# Source: https://qudt.org/vocab/unit
# Do not edit manually

QUDT_UNITS = {
'''
    
    for code, info in sorted(filtered.items()):
        symbol_str = f'"{info["symbol"]}"' if info["symbol"] else "None"
        content += f'''    "{code}": {{
        "uri": "{info['uri']}",
        "label": "{info['label']}",
        "symbol": {symbol_str},
        "category": "{info['category']}",
    }},
'''
    
    content += "}\n"
    
    output_path.write_text(content)
    print(f"Generated {output_path} ({len(filtered)} units)")


def main():
    """Main entry point."""
    print("=" * 60)
    print("QUDT Unit Vocabulary Downloader")
    print("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download TTL
    ttl_path = DATA_DIR / "qudt-unit.ttl"
    
    if not download_file(QUDT_UNIT_URL, ttl_path):
        print("Trying fallback URL...")
        if not download_file(QUDT_UNIT_URL_FALLBACK, ttl_path):
            print("Failed to download QUDT vocabulary")
            sys.exit(1)
    
    # Parse and extract
    units = parse_qudt_ttl(ttl_path)
    
    if units:
        # Generate Python dict
        py_path = DATA_DIR / "qudt_extracted.py"
        generate_python_dict(units, py_path)
    
    print("\n" + "=" * 60)
    print("Download complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
