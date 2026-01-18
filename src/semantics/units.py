# src/semantics/units.py
"""
Complete unit system with conversion graphs and validation.
Handles all ODRL dimensions with semantic correctness.
"""

from typing import Dict, Optional, Tuple, List, Set
from enum import Enum
from dataclasses import dataclass
import re
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# UNIT DEFINITIONS
# ==============================================================================

@dataclass
class UnitDefinition:
    """Definition of a unit with conversion information"""
    canonical_name: str
    dimension: str
    conversion_factor: float  # Multiplier to base unit
    aliases: List[str]
    is_base: bool = False

class UnitRegistry:
    """
    Central registry of all units with conversion capabilities.
    
    Design:
    - Each dimension has ONE base unit
    - All conversions go through base unit (no direct cross-conversions)
    - Maintains conversion graph for validation
    """
    
    def __init__(self):
        self.units: Dict[str, UnitDefinition] = {}
        self.dimension_base_units: Dict[str, str] = {}
        self._build_registry()
    
    def _build_registry(self):
        """Build complete unit registry"""
        
        # ======================================================================
        # TEMPORAL UNITS
        # ======================================================================
        self._register_dimension_units('Time', [
            UnitDefinition('seconds', 'Time', 1.0, 
                          ['s', 'sec', 'second', 'seconds',
                           'http://www.w3.org/2006/time#seconds'], 
                          is_base=True),
            
            UnitDefinition('minutes', 'Time', 60.0,
                          ['m', 'min', 'minute', 'minutes',
                           'http://www.w3.org/2006/time#minutes']),
            
            UnitDefinition('hours', 'Time', 3600.0,
                          ['h', 'hr', 'hour', 'hours',
                           'http://www.w3.org/2006/time#hours']),
            
            UnitDefinition('days', 'Time', 86400.0,
                          ['d', 'day', 'days',
                           'http://www.w3.org/2006/time#days']),
            
            UnitDefinition('weeks', 'Time', 604800.0,
                          ['w', 'wk', 'week', 'weeks',
                           'http://www.w3.org/2006/time#weeks']),
            
            UnitDefinition('months', 'Time', 2592000.0,  # 30 days
                          ['M', 'month', 'months',
                           'http://www.w3.org/2006/time#months']),
            
            UnitDefinition('years', 'Time', 31536000.0,  # 365 days
                          ['y', 'yr', 'year', 'years',
                           'http://www.w3.org/2006/time#years']),
        ])
        
        # ======================================================================
        # INFORMATION UNITS (Binary - IEC Standard)
        # ======================================================================
        self._register_dimension_units('Information', [
            UnitDefinition('bytes', 'Information', 1.0,
                          ['B', 'byte', 'bytes',
                           'http://www.w3.org/2000/01/rdf-schema#byte'],
                          is_base=True),
            
            # Binary (IEC) - Preferred for accuracy
            UnitDefinition('kibibytes', 'Information', 1024.0,
                          ['KiB', 'kibibyte', 'kibibytes',
                           'http://www.w3.org/2000/01/rdf-schema#kibibyte']),
            
            UnitDefinition('mebibytes', 'Information', 1024**2,
                          ['MiB', 'mebibyte', 'mebibytes',
                           'http://www.w3.org/2000/01/rdf-schema#mebibyte']),
            
            UnitDefinition('gibibytes', 'Information', 1024**3,
                          ['GiB', 'gibibyte', 'gibibytes',
                           'http://www.w3.org/2000/01/rdf-schema#gibibyte']),
            
            UnitDefinition('tebibytes', 'Information', 1024**4,
                          ['TiB', 'tebibyte', 'tebibytes',
                           'http://www.w3.org/2000/01/rdf-schema#tebibyte']),
            
            # Decimal (SI) - Common but less accurate
            UnitDefinition('kilobytes', 'Information', 1000.0,
                          ['kB', 'kilobyte', 'kilobytes',
                           'http://www.w3.org/2000/01/rdf-schema#kilobyte']),
            
            UnitDefinition('megabytes', 'Information', 1000**2,
                          ['MB', 'megabyte', 'megabytes',
                           'http://www.w3.org/2000/01/rdf-schema#megabyte']),
            
            UnitDefinition('gigabytes', 'Information', 1000**3,
                          ['GB', 'gigabyte', 'gigabytes',
                           'http://www.w3.org/2000/01/rdf-schema#gigabyte']),
            
            UnitDefinition('terabytes', 'Information', 1000**4,
                          ['TB', 'terabyte', 'terabytes',
                           'http://www.w3.org/2000/01/rdf-schema#terabyte']),
        ])
        
        # Special handling for ambiguous "KB" - default to SI with warning
        kb_unit = self.units.get('kilobytes')
        if kb_unit:
            kb_unit.aliases.extend(['KB', 'Kb', 'kb'])
        
        # ======================================================================
        # SPATIAL UNITS
        # ======================================================================
        self._register_dimension_units('Length', [
            UnitDefinition('meters', 'Length', 1.0,
                          ['m', 'meter', 'meters',
                           'http://www.w3.org/2003/01/geo/wgs84_pos#meters'],
                          is_base=True),
            
            UnitDefinition('kilometers', 'Length', 1000.0,
                          ['km', 'kilometer', 'kilometers',
                           'http://www.w3.org/2003/01/geo/wgs84_pos#kilometers']),
            
            UnitDefinition('miles', 'Length', 1609.34,
                          ['mi', 'mile', 'miles',
                           'http://www.w3.org/2003/01/geo/wgs84_pos#miles']),
            
            UnitDefinition('feet', 'Length', 0.3048,
                          ['ft', 'foot', 'feet',
                           'http://www.w3.org/2003/01/geo/wgs84_pos#feet']),
            
            UnitDefinition('inches', 'Length', 0.0254,
                          ['in', 'inch', 'inches']),
        ])
        
        # ======================================================================
        # RESOLUTION UNITS (Dimensionless but with context)
        # ======================================================================
        self._register_dimension_units('Resolution', [
            UnitDefinition('pixels', 'Resolution', 1.0,
                          ['px', 'pixel', 'pixels',
                           'http://www.w3.org/ns/odrl/2/pixels'],
                          is_base=True),
            
            UnitDefinition('dpi', 'Resolution', 1.0,  # Context-dependent
                          ['dpi', 'DPI',
                           'http://www.w3.org/ns/odrl/2/dpi']),
            
            UnitDefinition('ppi', 'Resolution', 1.0,  # Context-dependent
                          ['ppi', 'PPI',
                           'http://www.w3.org/ns/odrl/2/ppi']),
        ])
        
        # ======================================================================
        # CURRENCY UNITS (Special case - no direct conversion)
        # ======================================================================
        self._register_dimension_units('Currency', [
            UnitDefinition('USD', 'Currency', 1.0,
                          ['USD', '$',
                           'http://www.w3.org/2001/XMLSchema#currency#USD'],
                          is_base=True),
            
            UnitDefinition('EUR', 'Currency', 1.0,
                          ['EUR', '€',
                           'http://www.w3.org/2001/XMLSchema#currency#EUR']),
            
            UnitDefinition('GBP', 'Currency', 1.0,
                          ['GBP', '£',
                           'http://www.w3.org/2001/XMLSchema#currency#GBP']),
            
            UnitDefinition('JPY', 'Currency', 1.0,
                          ['JPY', '¥',
                           'http://www.w3.org/2001/XMLSchema#currency#JPY']),
            
            UnitDefinition('CNY', 'Currency', 1.0,
                          ['CNY', '元',
                           'http://www.w3.org/2001/XMLSchema#currency#CNY']),
        ])
        
        logger.info(f"Unit registry built: {len(self.units)} units across "
                   f"{len(self.dimension_base_units)} dimensions")
    
    def _register_dimension_units(self, dimension: str, units: List[UnitDefinition]):
        """Register units for a dimension"""
        for unit in units:
            # Store primary name
            self.units[unit.canonical_name] = unit
            
            # Store aliases
            for alias in unit.aliases:
                self.units[alias] = unit
            
            # Track base unit
            if unit.is_base:
                self.dimension_base_units[dimension] = unit.canonical_name
    
    def get_unit(self, unit_str: str) -> Optional[UnitDefinition]:
        """Get unit definition by name or alias"""
        return self.units.get(unit_str)
    
    def get_base_unit(self, dimension: str) -> Optional[str]:
        """Get base unit for a dimension"""
        return self.dimension_base_units.get(dimension)
    
    def can_convert(self, from_unit: str, to_unit: str) -> bool:
        """Check if two units can be converted"""
        from_def = self.get_unit(from_unit)
        to_def = self.get_unit(to_unit)
        
        if not from_def or not to_def:
            return False
        
        # Same dimension = convertible
        return from_def.dimension == to_def.dimension
    
    def convert(self, value: float, from_unit: str, to_unit: str) -> Tuple[float, bool]:
        """
        Convert value between units.
        
        Returns:
            (converted_value, is_approximate)
        """
        from_def = self.get_unit(from_unit)
        to_def = self.get_unit(to_unit)
        
        if not from_def or not to_def:
            raise ValueError(f"Unknown unit: {from_unit} or {to_unit}")
        
        if from_def.dimension != to_def.dimension:
            raise ValueError(f"Cannot convert {from_unit} ({from_def.dimension}) "
                           f"to {to_unit} ({to_def.dimension})")
        
        # Convert to base, then to target
        value_in_base = value * from_def.conversion_factor
        converted_value = value_in_base / to_def.conversion_factor
        
        # Check if conversion is approximate
        is_approximate = self._is_approximate_conversion(from_unit, to_unit)
        
        return converted_value, is_approximate
    
    def _is_approximate_conversion(self, from_unit: str, to_unit: str) -> bool:
        """Check if conversion is approximate (e.g., months, years)"""
        approximate_units = {'months', 'years', 'M', 'y', 'yr'}
        
        from_def = self.get_unit(from_unit)
        to_def = self.get_unit(to_unit)
        
        if not from_def or not to_def:
            return False
        
        return (from_def.canonical_name in approximate_units or 
                to_def.canonical_name in approximate_units)

# Global unit registry
UNIT_REGISTRY = UnitRegistry()

# ==============================================================================
# VALUE NORMALIZER
# ==============================================================================

class ValueNormalizer:
    """
    Normalize values to canonical forms for Z3 encoding.
    
    Handles:
    - Unit conversion
    - Type coercion
    - Special formats (ISO 8601, percentages, versions)
    - Currency minor units
    """
    
    def __init__(self, unit_registry: UnitRegistry = None, debug: bool = False):
        self.registry = unit_registry or UNIT_REGISTRY
        self.debug = debug
    
    def normalize(self, 
                  value: any,
                  operand: str,
                  unit: Optional[str] = None,
                  semantics: any = None) -> Tuple[any, str, Dict]:
        """
        Main normalization entry point.
        
        Args:
            value: Raw value from RDF
            operand: ODRL operand name
            unit: Optional unit string
            semantics: SemanticInfo object
        
        Returns:
            (canonical_value, canonical_unit, metadata)
        """
        from .constraint_types import ValueDomain
        
        if not semantics:
            from .constraint_types import get_operand_semantics
            semantics = get_operand_semantics(operand)
        
        domain = semantics.domain
        metadata = {
            'original_value': value,
            'original_unit': unit,
            'conversion_applied': False,
            'is_approximate': False
        }
        
        # Route to appropriate normalizer
        if domain == ValueDomain.NUMERIC:
            return self._normalize_numeric(value, unit, semantics, metadata)
        
        elif domain == ValueDomain.TEMPORAL:
            return self._normalize_temporal(value, unit, metadata)
        
        elif domain == ValueDomain.TEMPORAL_INTERVAL:
            return self._normalize_temporal_interval(value, unit, metadata)
        
        elif domain == ValueDomain.MONETARY:
            return self._normalize_monetary(value, unit, metadata)
        
        elif domain == ValueDomain.SPATIAL:
            return self._normalize_spatial(value, unit, metadata)
        
        elif domain == ValueDomain.CATEGORICAL:
            return self._normalize_categorical(value, operand, metadata)
        
        elif domain == ValueDomain.VERSION:
            return self._normalize_version(value, metadata)
        
        else:
            # No normalization needed
            return value, 'none', metadata
    
    # -------------------------------------------------------------------------
    # NUMERIC NORMALIZATION
    # -------------------------------------------------------------------------
    def _normalize_numeric(self, value, unit, semantics, metadata):
        """Normalize numeric values"""
        # Parse numeric value
        numeric_val = self._parse_numeric(value)
        
        if self.debug:
            logger.debug(f"  _normalize_numeric called:")
            logger.debug(f"    value={value}, unit={unit}")
            logger.debug(f"    parsed numeric_val={numeric_val}")
        
        # Handle percentage special case
        if semantics.base_unit == 'percent':
            if isinstance(value, str) and '%' in value:
                numeric_val = float(value.replace('%', '').strip())
            return numeric_val, 'percent', metadata
        
        # Apply unit conversion if present
        if unit:
            # Get dimension name (handle both enum and string)
            if hasattr(semantics.dimension, 'value'):
                dimension_name = semantics.dimension.value  # Enum
            else:
                dimension_name = str(semantics.dimension)
            
            if self.debug:
                logger.debug(f"    dimension_name={dimension_name}")
            
            base_unit = self.registry.get_base_unit(dimension_name)
            
            if self.debug:
                logger.debug(f"    base_unit for {dimension_name}={base_unit}")
            
            if base_unit and unit != base_unit:
                try:
                    converted_val, is_approx = self.registry.convert(
                        numeric_val, unit, base_unit
                    )
                    metadata['conversion_applied'] = True
                    metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                    metadata['is_approximate'] = is_approx
                    
                    if self.debug:
                        logger.debug(f"    Converted: {numeric_val} {unit} -> {converted_val} {base_unit}")
                    
                    return converted_val, base_unit, metadata
                    
                except ValueError as e:
                    logger.warning(f"Unit conversion failed: {e}")
                    # Fall through to no conversion
            
            elif unit == base_unit:
                # Already in base unit
                if self.debug:
                    logger.debug(f"    Already in base unit: {unit}")
                return numeric_val, base_unit, metadata
        
        # No conversion needed
        if self.debug:
            logger.debug(f"    No conversion applied")
        
        return numeric_val, semantics.base_unit, metadata
        
    def _parse_numeric(self, value: any) -> float:
        """Parse numeric value with K/M/B suffixes"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip().replace(',', '').replace('_', '')
            
            # Handle K/M/B suffixes
            multipliers = {
                'k': 1_000, 'K': 1_000,
                'm': 1_000_000, 'M': 1_000_000,
                'b': 1_000_000_000, 'B': 1_000_000_000
            }
            
            if value and value[-1] in multipliers:
                return float(value[:-1]) * multipliers[value[-1]]
            
            return float(value)
        
        raise ValueError(f"Cannot parse numeric value: {value}")
    
    # -------------------------------------------------------------------------
    # TEMPORAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_temporal(self, value, unit, metadata):
        """Normalize temporal point to Unix timestamp"""
        if isinstance(value, (int, float)):
            # Already a timestamp
            timestamp = int(value)
        elif isinstance(value, str):
            # Parse ISO 8601 or other formats
            timestamp = self._parse_datetime(value)
        else:
            raise ValueError(f"Cannot parse temporal value: {value}")
        
        metadata['iso8601'] = datetime.fromtimestamp(timestamp).isoformat()
        return timestamp, 'unix_timestamp', metadata
        
    def _normalize_temporal_interval(self, value, unit, metadata):
        """Normalize temporal interval to seconds"""
        if isinstance(value, (int, float)):
            numeric_val = float(value)
            
            # Apply unit conversion
            if unit:
                converted_val, is_approx = self.registry.convert(
                    numeric_val, unit, 'seconds'
                )
                metadata['conversion_applied'] = True
                metadata['is_approximate'] = is_approx
                metadata['human_readable'] = self._seconds_to_human(converted_val)
                # FIX: Add conversion_factor
                metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                
                return int(converted_val), 'seconds', metadata
            else:
                # Assume seconds
                metadata['human_readable'] = self._seconds_to_human(numeric_val)
                return int(numeric_val), 'seconds', metadata
        
        elif isinstance(value, str):
            # Check for ISO 8601 duration
            if value.startswith('P'):
                seconds = self._parse_iso8601_duration(value)
                metadata['human_readable'] = self._seconds_to_human(seconds)
                # No conversion_factor for ISO 8601 (direct parsing)
                return int(seconds), 'seconds', metadata
            
            # Try parsing "3 hours" format
            numeric_val, parsed_unit = self._parse_duration_string(value)
            converted_val, is_approx = self.registry.convert(
                numeric_val, parsed_unit, 'seconds'
            )
            metadata['conversion_applied'] = True
            metadata['is_approximate'] = is_approx
            metadata['human_readable'] = self._seconds_to_human(converted_val)
            # FIX: Add conversion_factor
            metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
            
            return int(converted_val), 'seconds', metadata
        
        raise ValueError(f"Cannot parse temporal interval: {value}")
        
    def _parse_datetime(self, value: str) -> int:
        """Parse datetime string to Unix timestamp"""
        try:
            # ISO 8601 with timezone
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except:
            try:
                # Try without timezone (assume UTC)
                dt = datetime.fromisoformat(value)
                return int(dt.timestamp())
            except:
                # Fallback: use dateutil parser
                try:
                    from dateutil import parser
                    dt = parser.parse(value)
                    return int(dt.timestamp())
                except ImportError:
                    raise ValueError(f"Cannot parse datetime: {value}. Install python-dateutil for advanced parsing.")
    
    def _parse_iso8601_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        # Regex: P[nY][nM][nD]T[nH][nM][nS]
        pattern = r'P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?'
        match = re.match(pattern, duration)
        
        if not match:
            raise ValueError(f"Invalid ISO 8601 duration: {duration}")
        
        years, months, days, hours, minutes, seconds = match.groups()
        
        total_seconds = 0
        if years:
            total_seconds += int(years) * 31536000  # 365 days
        if months:
            total_seconds += int(months) * 2592000  # 30 days
        if days:
            total_seconds += int(days) * 86400
        if hours:
            total_seconds += int(hours) * 3600
        if minutes:
            total_seconds += int(minutes) * 60
        if seconds:
            total_seconds += float(seconds)
        
        return int(total_seconds)
    
    def _parse_duration_string(self, value: str) -> Tuple[float, str]:
        """Parse "3 hours" format to (3, 'hours')"""
        parts = value.strip().split()
        
        if len(parts) == 2:
            return float(parts[0]), parts[1].lower()
        elif len(parts) == 1:
            # Try regex: "3hours" or "3h"
            match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', value)
            if match:
                return float(match.group(1)), match.group(2).lower()
        
        raise ValueError(f"Cannot parse duration string: {value}")
    
    def _seconds_to_human(self, seconds: float) -> str:
        """Convert seconds to human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    # -------------------------------------------------------------------------
    # MONETARY NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_monetary(self, value, unit, metadata):
        """Normalize monetary value to minor units (cents)"""
        numeric_val = self._parse_numeric(value)
        
        # Determine currency
        currency = 'USD'  # Default
        if unit:
            unit_def = self.registry.get_unit(unit)
            if unit_def and unit_def.dimension == 'Currency':
                currency = unit_def.canonical_name
        
        # Convert to minor units (cents for most currencies)
        if currency in ['USD', 'EUR', 'GBP', 'CAD', 'AUD']:
            # Has cents
            canonical_val = Decimal(str(numeric_val)) * 100
            canonical_unit = f'{currency}_cents'
        elif currency == 'JPY':
            # No subunit
            canonical_val = Decimal(str(numeric_val))
            canonical_unit = currency
        else:
            canonical_val = Decimal(str(numeric_val))
            canonical_unit = currency
        
        metadata['currency'] = currency
        metadata['minor_unit_conversion'] = True
        
        return int(canonical_val), canonical_unit, metadata
    
    # -------------------------------------------------------------------------
    # SPATIAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_spatial(self, value, unit, metadata):
        """Normalize spatial value to meters"""
        numeric_val = self._parse_numeric(value)
        
        if unit:
            converted_val, is_approx = self.registry.convert(
                numeric_val, unit, 'meters'
            )
            metadata['conversion_applied'] = True
            metadata['is_approximate'] = is_approx
            # FIX: Add conversion_factor
            metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
            
            return converted_val, 'meters', metadata
        
        return numeric_val, 'meters', metadata
    
    # -------------------------------------------------------------------------
    # CATEGORICAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_categorical(self, value, operand, metadata):
        """Normalize categorical values"""
        if operand == 'language':
            # Normalize to ISO 639-1
            canonical = self._normalize_language_code(value)
            return canonical, 'iso639-1', metadata
        
        elif operand in ['media', 'fileFormat']:
            # Normalize to MIME type
            canonical = self._normalize_mime_type(value)
            return canonical, 'mime_type', metadata
        
        else:
            # Generic: lowercase and trim
            canonical = str(value).lower().strip()
            return canonical, 'string', metadata
    
    def _normalize_language_code(self, value: str) -> str:
        """Normalize language to ISO 639-1 code"""
        # Simple mapping (expand as needed)
        lang_map = {
            'english': 'en', 'eng': 'en',
            'french': 'fr', 'fra': 'fr',
            'german': 'de', 'deu': 'de',
            'spanish': 'es', 'spa': 'es',
            'chinese': 'zh', 'zho': 'zh',
            'japanese': 'ja', 'jpn': 'ja',
            'arabic': 'ar', 'ara': 'ar',
        }
        
        lower_val = value.lower().strip()
        return lang_map.get(lower_val, lower_val)
    
    def _normalize_mime_type(self, value: str) -> str:
        """Normalize to IANA MIME type"""
        mime_map = {
            'pdf': 'application/pdf',
            'json': 'application/json',
            'xml': 'application/xml',
            'html': 'text/html',
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'mp4': 'video/mp4',
            'mp3': 'audio/mpeg',
        }
        
        lower_val = value.lower().strip()
        
        # If already MIME type format
        if '/' in lower_val:
            return lower_val
        
        return mime_map.get(lower_val, value)
    
    # -------------------------------------------------------------------------
    # VERSION NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_version(self, value, metadata):
        """Normalize version to comparable format"""
        parts = self._parse_version(value)
        
        # Convert to integer for comparison
        # e.g., "2.3.1" → 2003001 (pad each part to 3 digits)
        canonical_val = sum(
            part * (1000 ** (len(parts) - i - 1))
            for i, part in enumerate(parts)
        )
        
        metadata['version_parts'] = parts
        metadata['version_string'] = '.'.join(map(str, parts))
        
        return canonical_val, 'semantic_version', metadata
    
    def _parse_version(self, value: any) -> List[int]:
        """Parse version string to list of integers"""
        if isinstance(value, (int, float)):
            return [int(value)]
        
        # Split on dots
        value_str = str(value).strip()
        parts = value_str.split('.')
        
        # Extract numeric parts
        numeric_parts = []
        for part in parts:
            # Extract leading digits
            match = re.match(r'(\d+)', part)
            if match:
                numeric_parts.append(int(match.group(1)))
        
        return numeric_parts if numeric_parts else [0]

# Global normalizer instance
VALUE_NORMALIZER = ValueNormalizer(debug=False)

def get_value_normalizer(debug: bool = False) -> ValueNormalizer:
    """Get value normalizer instance with debug setting"""
    if debug:
        return ValueNormalizer(debug=True)
    return VALUE_NORMALIZER