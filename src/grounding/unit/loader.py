# src/grounding/unit/loader.py
"""
QUDT Unit Vocabulary Loader

Loads unit definitions from QUDT TTL file and builds the oracle registry.

Usage:
    from grounding.unit.loader import load_qudt_units, QUDTLoader
    
    # Load from bundled file
    units = load_qudt_units()
    
    # Or use loader directly
    loader = QUDTLoader()
    loader.load("data/qudt-units-odrl.ttl")
    units = loader.get_units()
"""

from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Default data file location
DEFAULT_TTL_PATH = Path(__file__).parent / "data" / "qudt-unit.ttl"


@dataclass
class QUDTUnit:
    """Unit information from QUDT."""
    code: str
    uri: str
    label: str
    symbol: Optional[str] = None
    category: Optional[str] = None
    conversion_multiplier: Optional[float] = None


class QUDTLoader:
    """
    Loader for QUDT unit vocabulary.
    
    Parses TTL file and extracts unit definitions.
    """
    
    def __init__(self):
        self._units: Dict[str, QUDTUnit] = {}
        self._loaded = False
    
    def load(self, ttl_path: Optional[Path] = None) -> bool:
        """
        Load units from TTL file.
        
        Args:
            ttl_path: Path to TTL file (uses default if None)
            
        Returns:
            True if loaded successfully
        """
        if ttl_path is None:
            ttl_path = DEFAULT_TTL_PATH
        
        ttl_path = Path(ttl_path)
        
        if not ttl_path.exists():
            logger.error(f"TTL file not found: {ttl_path}")
            return False
        
        try:
            from rdflib import Graph, Namespace, RDF, RDFS
            from rdflib.namespace import SKOS
        except ImportError:
            logger.warning("rdflib not installed, using fallback parsing")
            return self._load_fallback(ttl_path)
        
        QUDT = Namespace("http://qudt.org/schema/qudt/")
        UNIT = Namespace("http://qudt.org/vocab/unit/")
        
        logger.info(f"Loading QUDT units from {ttl_path}")
        
        g = Graph()
        g.parse(ttl_path, format="turtle")
        
        # Find all units
        for unit_uri in g.subjects(RDF.type, QUDT.Unit):
            self._parse_unit(g, unit_uri, QUDT, RDFS, SKOS)
        
        # Also check for CurrencyUnit
        for unit_uri in g.subjects(RDF.type, QUDT.CurrencyUnit):
            self._parse_unit(g, unit_uri, QUDT, RDFS, SKOS, category="currency")
        
        self._loaded = True
        logger.info(f"Loaded {len(self._units)} units")
        return True
    
    def _parse_unit(self, g, unit_uri, QUDT, RDFS, SKOS, category: Optional[str] = None):
        """Parse a single unit from the graph."""
        uri_str = str(unit_uri)
        
        # Extract code from notation or URI
        code = None
        for notation in g.objects(unit_uri, SKOS.notation):
            code = str(notation)
            break
        
        if code is None:
            # Extract from URI
            if "/unit/" in uri_str:
                code = uri_str.split("/unit/")[-1]
            else:
                return
        
        # Get label
        label = code
        for lbl in g.objects(unit_uri, RDFS.label):
            if hasattr(lbl, 'language'):
                if lbl.language == "en" or lbl.language is None:
                    label = str(lbl)
                    break
            else:
                label = str(lbl)
                break
        
        # Get symbol
        symbol = None
        for sym in g.objects(unit_uri, QUDT.symbol):
            symbol = str(sym)
            break
        
        # Get conversion multiplier
        multiplier = None
        for mult in g.objects(unit_uri, QUDT.conversionMultiplier):
            try:
                multiplier = float(mult)
            except (ValueError, TypeError):
                pass
            break
        
        # Infer category if not provided
        if category is None:
            category = self._infer_category(code, uri_str)
        
        self._units[code] = QUDTUnit(
            code=code,
            uri=uri_str,
            label=label,
            symbol=symbol,
            category=category,
            conversion_multiplier=multiplier,
        )
    
    def _infer_category(self, code: str, uri: str) -> str:
        """Infer category from code or URI."""
        code_lower = code.lower()
        
        # Currency (3-letter codes)
        if len(code) == 3 and code.isupper():
            if code in {"EUR", "USD", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "BRL"}:
                return "currency"
        
        # Resolution
        if code_lower in {"dpi", "ppi", "dpcm"}:
            return "resolution"
        
        # Data size
        if "byte" in code_lower or "bit" in code_lower:
            return "size_data"
        
        # Physical size
        if code_lower in {"px", "pixel", "m", "cm", "mm", "in", "pt"}:
            return "size_physical"
        
        # Time
        if code_lower in {"sec", "min", "hr", "day", "wk", "mo", "yr"}:
            return "time"
        
        return "unknown"
    
    def _load_fallback(self, ttl_path: Path) -> bool:
        """
        Fallback parsing without rdflib.
        
        Simple regex-based extraction for our known format.
        """
        import re
        
        content = ttl_path.read_text()
        
        # Pattern: unit:CODE a qudt:Unit
        unit_pattern = re.compile(
            r'unit:(\w+)\s+a\s+qudt:(?:Unit|CurrencyUnit)',
            re.MULTILINE
        )
        
        # Pattern: rdfs:label "..."@en
        label_pattern = re.compile(
            r'rdfs:label\s+"([^"]+)"@en'
        )
        
        # Pattern: qudt:symbol "..."
        symbol_pattern = re.compile(
            r'qudt:symbol\s+"([^"]+)"'
        )
        
        # Split by unit definitions
        blocks = content.split('unit:')[1:]  # Skip prefix block
        
        for block in blocks:
            lines = block.split('\n')
            if not lines:
                continue
            
            # Get code from first line
            first_line = lines[0].strip()
            match = re.match(r'^(\w+)', first_line)
            if not match:
                continue
            
            code = match.group(1)
            block_text = '\n'.join(lines)
            
            # Extract label
            label = code
            label_match = label_pattern.search(block_text)
            if label_match:
                label = label_match.group(1)
            
            # Extract symbol
            symbol = None
            symbol_match = symbol_pattern.search(block_text)
            if symbol_match:
                symbol = symbol_match.group(1)
            
            # Infer category
            category = self._infer_category(code, f"http://qudt.org/vocab/unit/{code}")
            
            self._units[code] = QUDTUnit(
                code=code,
                uri=f"http://qudt.org/vocab/unit/{code}",
                label=label,
                symbol=symbol,
                category=category,
            )
        
        self._loaded = True
        logger.info(f"Loaded {len(self._units)} units (fallback parser)")
        return True
    
    def get_units(self) -> Dict[str, QUDTUnit]:
        """Get all loaded units."""
        return self._units.copy()
    
    def get_unit(self, code: str) -> Optional[QUDTUnit]:
        """Get a specific unit by code."""
        return self._units.get(code)
    
    def is_loaded(self) -> bool:
        """Check if units are loaded."""
        return self._loaded


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_loader: Optional[QUDTLoader] = None


def get_loader() -> QUDTLoader:
    """Get the global QUDT loader instance."""
    global _loader
    if _loader is None:
        _loader = QUDTLoader()
        _loader.load()
    return _loader


def load_qudt_units(ttl_path: Optional[Path] = None) -> Dict[str, QUDTUnit]:
    """
    Load QUDT units from TTL file.
    
    Args:
        ttl_path: Path to TTL file (uses default if None)
        
    Returns:
        Dict of code -> QUDTUnit
    """
    loader = QUDTLoader()
    loader.load(ttl_path)
    return loader.get_units()


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("QUDT Loader Test")
    print("=" * 60)
    
    loader = QUDTLoader()
    
    if loader.load():
        units = loader.get_units()
        
        # Group by category
        by_category: Dict[str, List[str]] = {}
        for code, unit in units.items():
            cat = unit.category or "unknown"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(code)
        
        print(f"\nLoaded {len(units)} units:")
        for category, codes in sorted(by_category.items()):
            print(f"\n  {category}:")
            for code in sorted(codes)[:10]:
                unit = units[code]
                symbol = f" ({unit.symbol})" if unit.symbol else ""
                print(f"    {code}: {unit.label}{symbol}")
            if len(codes) > 10:
                print(f"    ... and {len(codes) - 10} more")
    else:
        print("Failed to load units")
    
    print("\n" + "=" * 60)
