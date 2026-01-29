# src/grounding/unit/tests.py
"""
Unit Oracle Tests

Run with:
    python tests.py
    # OR
    python -m pytest tests.py -v
"""

import unittest
import sys
from pathlib import Path

# Add parent to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent))

from oracle import (
    UnitOracle, 
    UnitCategory, 
    normalize_unit, 
    are_units_compatible
)


class TestUnitOracle(unittest.TestCase):
    """Test cases for UnitOracle."""
    
    def setUp(self):
        self.oracle = UnitOracle()
    
    # -------------------------------------------------------------------------
    # Currency Tests
    # -------------------------------------------------------------------------
    
    def test_currency_canonical(self):
        """Test canonical currency codes."""
        self.assertEqual(self.oracle.normalize("EUR"), "EUR")
        self.assertEqual(self.oracle.normalize("USD"), "USD")
        self.assertEqual(self.oracle.normalize("GBP"), "GBP")
    
    def test_currency_qudt_uri(self):
        """Test QUDT currency URIs."""
        self.assertEqual(
            self.oracle.normalize("http://qudt.org/vocab/unit/EUR"), 
            "EUR"
        )
        self.assertEqual(
            self.oracle.normalize("http://qudt.org/vocab/unit/USD"), 
            "USD"
        )
    
    def test_currency_iso4217(self):
        """Test ISO 4217 URIs."""
        self.assertEqual(
            self.oracle.normalize("http://iso.org/4217/EUR"), 
            "EUR"
        )
        self.assertEqual(
            self.oracle.normalize("http://iso.org/4217/USD"), 
            "USD"
        )
    
    def test_currency_dbpedia(self):
        """Test DBpedia URIs."""
        self.assertEqual(
            self.oracle.normalize("http://dbpedia.org/resource/Euro"), 
            "EUR"
        )
        self.assertEqual(
            self.oracle.normalize("http://dbpedia.org/resource/United_States_dollar"), 
            "USD"
        )
    
    def test_currency_common_names(self):
        """Test common currency names."""
        self.assertEqual(self.oracle.normalize("euro"), "EUR")
        self.assertEqual(self.oracle.normalize("euros"), "EUR")
        self.assertEqual(self.oracle.normalize("dollar"), "USD")
        self.assertEqual(self.oracle.normalize("dollars"), "USD")
    
    # -------------------------------------------------------------------------
    # Resolution Tests
    # -------------------------------------------------------------------------
    
    def test_resolution_canonical(self):
        """Test canonical resolution codes."""
        self.assertEqual(self.oracle.normalize("DPI"), "DPI")
        self.assertEqual(self.oracle.normalize("PPI"), "PPI")
    
    def test_resolution_lowercase(self):
        """Test lowercase resolution names."""
        self.assertEqual(self.oracle.normalize("dpi"), "DPI")
        self.assertEqual(self.oracle.normalize("ppi"), "PPI")
    
    def test_resolution_phrases(self):
        """Test resolution phrases."""
        self.assertEqual(self.oracle.normalize("dots per inch"), "DPI")
        self.assertEqual(self.oracle.normalize("pixels per inch"), "PPI")
    
    # -------------------------------------------------------------------------
    # Data Size Tests
    # -------------------------------------------------------------------------
    
    def test_size_canonical(self):
        """Test canonical size codes."""
        self.assertEqual(self.oracle.normalize("BYTE"), "BYTE")
        self.assertEqual(self.oracle.normalize("KiloBYTE"), "KiloBYTE")
        self.assertEqual(self.oracle.normalize("MegaBYTE"), "MegaBYTE")
    
    def test_size_common_abbrev(self):
        """Test common size abbreviations."""
        self.assertEqual(self.oracle.normalize("kb"), "KiloBYTE")
        self.assertEqual(self.oracle.normalize("mb"), "MegaBYTE")
        self.assertEqual(self.oracle.normalize("gb"), "GigaBYTE")
    
    def test_size_names(self):
        """Test size names."""
        self.assertEqual(self.oracle.normalize("bytes"), "BYTE")
        self.assertEqual(self.oracle.normalize("kilobyte"), "KiloBYTE")
        self.assertEqual(self.oracle.normalize("megabytes"), "MegaBYTE")
    
    # -------------------------------------------------------------------------
    # Time Tests
    # -------------------------------------------------------------------------
    
    def test_time_canonical(self):
        """Test canonical time codes."""
        self.assertEqual(self.oracle.normalize("SEC"), "SEC")
        self.assertEqual(self.oracle.normalize("MIN"), "MIN")
        self.assertEqual(self.oracle.normalize("HR"), "HR")
    
    def test_time_common(self):
        """Test common time names."""
        self.assertEqual(self.oracle.normalize("seconds"), "SEC")
        self.assertEqual(self.oracle.normalize("minutes"), "MIN")
        self.assertEqual(self.oracle.normalize("hours"), "HR")
    
    def test_time_abbrev(self):
        """Test time abbreviations."""
        self.assertEqual(self.oracle.normalize("s"), "SEC")
        self.assertEqual(self.oracle.normalize("h"), "HR")
    
    # -------------------------------------------------------------------------
    # Compatibility Tests
    # -------------------------------------------------------------------------
    
    def test_same_unit_compatible(self):
        """Same units should be compatible."""
        self.assertTrue(self.oracle.are_compatible("EUR", "EUR"))
        self.assertTrue(self.oracle.are_compatible("DPI", "DPI"))
        self.assertTrue(self.oracle.are_compatible("BYTE", "BYTE"))
    
    def test_alias_compatible(self):
        """Aliased units should be compatible."""
        self.assertTrue(self.oracle.are_compatible("EUR", "euro"))
        self.assertTrue(self.oracle.are_compatible("http://qudt.org/vocab/unit/EUR", "euro"))
        self.assertTrue(self.oracle.are_compatible("kb", "kilobyte"))
        self.assertTrue(self.oracle.are_compatible("seconds", "SEC"))
    
    def test_different_units_incompatible(self):
        """Different units should be incompatible."""
        self.assertFalse(self.oracle.are_compatible("EUR", "USD"))
        self.assertFalse(self.oracle.are_compatible("DPI", "PPI"))
        self.assertFalse(self.oracle.are_compatible("KB", "MB"))
        self.assertFalse(self.oracle.are_compatible("SEC", "MIN"))
    
    def test_none_incompatible(self):
        """None should be incompatible with anything."""
        self.assertFalse(self.oracle.are_compatible(None, "EUR"))
        self.assertFalse(self.oracle.are_compatible("EUR", None))
        self.assertFalse(self.oracle.are_compatible(None, None))
    
    # -------------------------------------------------------------------------
    # Category Tests
    # -------------------------------------------------------------------------
    
    def test_currency_category(self):
        """Test currency category."""
        self.assertEqual(self.oracle.get_category("EUR"), UnitCategory.CURRENCY)
        self.assertEqual(self.oracle.get_category("USD"), UnitCategory.CURRENCY)
    
    def test_resolution_category(self):
        """Test resolution category."""
        self.assertEqual(self.oracle.get_category("DPI"), UnitCategory.RESOLUTION)
        self.assertEqual(self.oracle.get_category("PPI"), UnitCategory.RESOLUTION)
    
    def test_size_category(self):
        """Test size category."""
        self.assertEqual(self.oracle.get_category("BYTE"), UnitCategory.SIZE_DATA)
        self.assertEqual(self.oracle.get_category("PIXEL"), UnitCategory.SIZE_PHYSICAL)
    
    def test_time_category(self):
        """Test time category."""
        self.assertEqual(self.oracle.get_category("SEC"), UnitCategory.TIME)
        self.assertEqual(self.oracle.get_category("HR"), UnitCategory.TIME)
    
    def test_unknown_category(self):
        """Test unknown category."""
        self.assertEqual(self.oracle.get_category("UNKNOWN_UNIT"), UnitCategory.UNKNOWN)
    
    # -------------------------------------------------------------------------
    # Same Category Tests
    # -------------------------------------------------------------------------
    
    def test_same_category_currency(self):
        """Currencies are same category."""
        self.assertTrue(self.oracle.are_same_category("EUR", "USD"))
        self.assertTrue(self.oracle.are_same_category("GBP", "JPY"))
    
    def test_same_category_size(self):
        """Sizes are same category."""
        self.assertTrue(self.oracle.are_same_category("KB", "MB"))
        self.assertTrue(self.oracle.are_same_category("BYTE", "GigaBYTE"))
    
    def test_different_category(self):
        """Different categories should return False."""
        self.assertFalse(self.oracle.are_same_category("EUR", "BYTE"))
        self.assertFalse(self.oracle.are_same_category("DPI", "SEC"))
    
    # -------------------------------------------------------------------------
    # Info Tests
    # -------------------------------------------------------------------------
    
    def test_get_info(self):
        """Test get_info method."""
        info = self.oracle.get_info("EUR")
        self.assertIsNotNone(info)
        self.assertEqual(info.canonical, "EUR")
        self.assertEqual(info.symbol, "€")
        self.assertEqual(info.category, UnitCategory.CURRENCY)
    
    def test_get_uri(self):
        """Test get_uri method."""
        uri = self.oracle.get_uri("EUR")
        self.assertEqual(uri, "http://qudt.org/vocab/unit/EUR")
    
    # -------------------------------------------------------------------------
    # Convenience Function Tests
    # -------------------------------------------------------------------------
    
    def test_convenience_normalize(self):
        """Test convenience normalize_unit function."""
        self.assertEqual(normalize_unit("euro"), "EUR")
        self.assertEqual(normalize_unit("dpi"), "DPI")
    
    def test_convenience_compatible(self):
        """Test convenience are_units_compatible function."""
        self.assertTrue(are_units_compatible("EUR", "euro"))
        self.assertFalse(are_units_compatible("EUR", "USD"))


if __name__ == "__main__":
    unittest.main()