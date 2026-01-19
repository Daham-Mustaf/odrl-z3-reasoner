# src/semantics/units.py
"""
Complete unit system with conversion graphs and validation.
Handles all ODRL dimensions with semantic correctness.
"""

from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
import re
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Import debug utilities
try:
    from .constraint_types import debug_print, is_debug_mode
except ImportError:
    def debug_print(category: str, message: str, data: Any = None):
        pass
    def is_debug_mode() -> bool:
        return False


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
                           'http://www.w3.org/2006/time#seconds',
                           'http://dbpedia.org/resource/Second'], 
                          is_base=True),
            
            UnitDefinition('minutes', 'Time', 60.0,
                          ['m', 'min', 'minute', 'minutes',
                           'http://www.w3.org/2006/time#minutes',
                           'http://dbpedia.org/resource/Minute']),
            
            UnitDefinition('hours', 'Time', 3600.0,
                          ['h', 'hr', 'hour', 'hours',
                           'http://www.w3.org/2006/time#hours',
                           'http://dbpedia.org/resource/Hour']),
            
            UnitDefinition('days', 'Time', 86400.0,
                          ['d', 'day', 'days',
                           'http://www.w3.org/2006/time#days',
                           'http://dbpedia.org/resource/Day']),
            
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
                          ['KiB', 'kibibyte', 'kibibytes']),
            
            UnitDefinition('mebibytes', 'Information', 1024**2,
                          ['MiB', 'mebibyte', 'mebibytes']),
            
            UnitDefinition('gibibytes', 'Information', 1024**3,
                          ['GiB', 'gibibyte', 'gibibytes']),
            
            UnitDefinition('tebibytes', 'Information', 1024**4,
                          ['TiB', 'tebibyte', 'tebibytes']),
            
            # Decimal (SI) - Common but less accurate
            UnitDefinition('kilobytes', 'Information', 1000.0,
                          ['kB', 'KB', 'kilobyte', 'kilobytes']),
            
            UnitDefinition('megabytes', 'Information', 1000**2,
                          ['MB', 'megabyte', 'megabytes']),
            
            UnitDefinition('gigabytes', 'Information', 1000**3,
                          ['GB', 'gigabyte', 'gigabytes']),
            
            UnitDefinition('terabytes', 'Information', 1000**4,
                          ['TB', 'terabyte', 'terabytes']),
        ])
        
        # ======================================================================
        # SPATIAL UNITS
        # ======================================================================
        self._register_dimension_units('Length', [
            UnitDefinition('meters', 'Length', 1.0,
                          ['m', 'meter', 'meters',
                           'http://www.w3.org/2003/01/geo/wgs84_pos#meters'],
                          is_base=True),
            
            UnitDefinition('kilometers', 'Length', 1000.0,
                          ['km', 'kilometer', 'kilometers']),
            
            UnitDefinition('miles', 'Length', 1609.34,
                          ['mi', 'mile', 'miles']),
            
            UnitDefinition('feet', 'Length', 0.3048,
                          ['ft', 'foot', 'feet']),
            
            UnitDefinition('inches', 'Length', 0.0254,
                          ['in', 'inch', 'inches']),
        ])
        
        # ======================================================================
        # RESOLUTION UNITS
        # ======================================================================
        self._register_dimension_units('Resolution', [
            UnitDefinition('pixels', 'Resolution', 1.0,
                          ['px', 'pixel', 'pixels'],
                          is_base=True),
            
            UnitDefinition('dpi', 'Resolution', 1.0,
                          ['dpi', 'DPI']),
        ])
        
        # ======================================================================
        # CURRENCY UNITS (Special case - no direct conversion)
        # ======================================================================
        self._register_dimension_units('Currency', [
            UnitDefinition('USD', 'Currency', 1.0,
                          ['USD', '$', 'dollar', 'dollars'],
                          is_base=True),
            
            UnitDefinition('EUR', 'Currency', 1.0,
                          ['EUR', '€', 'euro', 'euros']),
            
            UnitDefinition('GBP', 'Currency', 1.0,
                          ['GBP', '£', 'pound', 'pounds']),
            
            UnitDefinition('JPY', 'Currency', 1.0,
                          ['JPY', '¥', 'yen']),
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
    
    def _debug(self, message: str, data: Any = None):
        """Debug output helper"""
        if self.debug:
            debug_print("UNITS", message, data)
            logger.debug(f"[UNITS] {message}")
    
    def normalize(self, 
                  value: Any,
                  operand: str,
                  unit: Optional[str] = None,
                  semantics: Any = None,
                  odrl_metadata: Any = None) -> Tuple[Any, str, Dict]:
        """
        Main normalization entry point.
        
        Args:
            value: Raw value from RDF
            operand: ODRL operand name
            unit: Optional unit string
            semantics: SemanticInfo object
            odrl_metadata: ODRLMetadata object
        
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
            'is_approximate': False,
            'domain': domain.value,
        }
        
        # Handle ODRL metadata
        if odrl_metadata:
            if hasattr(odrl_metadata, 'unit_of_count') and odrl_metadata.unit_of_count:
                metadata['unit_of_count'] = odrl_metadata.unit_of_count
                metadata['is_per_entity'] = True
            
            if hasattr(odrl_metadata, 'status') and odrl_metadata.status is not None:
                metadata['status'] = odrl_metadata.status
                metadata['has_baseline'] = True
            
            if not unit and hasattr(odrl_metadata, 'unit') and odrl_metadata.unit:
                unit = odrl_metadata.unit
        
        self._debug(f"Normalizing: {operand} = {value} [{unit}]", {
            'domain': domain.value,
            'base_unit': semantics.base_unit
        })
        
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
        
        elif domain == ValueDomain.POSITIONAL:
            return self._normalize_positional(value, unit, semantics, metadata)
        
        elif domain == ValueDomain.CATEGORICAL:
            return self._normalize_categorical(value, operand, metadata)
        
        elif domain == ValueDomain.REFERENCE:
            return self._normalize_reference(value, operand, metadata)
        
        elif domain == ValueDomain.VERSION:
            return self._normalize_version(value, metadata)
        
        else:
            # No normalization needed
            self._debug(f"No normalization for domain: {domain.value}")
            return value, 'none', metadata
    
    # -------------------------------------------------------------------------
    # NUMERIC NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_numeric(self, value, unit, semantics, metadata):
        """Normalize numeric values"""
        # Parse numeric value
        numeric_val = self._parse_numeric(value)
        
        self._debug(f"Numeric normalization: {value} -> {numeric_val}")
        
        # Handle percentage special case
        if semantics.base_unit == 'percent':
            if isinstance(value, str) and '%' in value:
                numeric_val = float(value.replace('%', '').strip())
            return numeric_val, 'percent', metadata
        
        # Apply unit conversion if present
        if unit:
            # Get dimension name
            if hasattr(semantics.dimension, 'value'):
                dimension_name = semantics.dimension.value
            else:
                dimension_name = str(semantics.dimension)
            
            self._debug(f"Looking up base unit for dimension: {dimension_name}")
            
            base_unit = self.registry.get_base_unit(dimension_name)
            
            if base_unit and unit != base_unit:
                try:
                    converted_val, is_approx = self.registry.convert(
                        numeric_val, unit, base_unit
                    )
                    metadata['conversion_applied'] = True
                    metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                    metadata['is_approximate'] = is_approx
                    
                    self._debug(f"Converted: {numeric_val} {unit} -> {converted_val} {base_unit}")
                    
                    return converted_val, base_unit, metadata
                    
                except ValueError as e:
                    self._debug(f"Unit conversion failed: {e}")
                    logger.warning(f"Unit conversion failed: {e}")
            
            elif unit == base_unit:
                self._debug(f"Already in base unit: {unit}")
                return numeric_val, base_unit, metadata
        
        self._debug(f"No conversion applied, using base_unit: {semantics.base_unit}")
        return numeric_val, semantics.base_unit, metadata
    
    def _parse_numeric(self, value: Any) -> float:
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
        
        # Try to convert to float
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Cannot parse numeric value: {value}")
    
    # -------------------------------------------------------------------------
    # TEMPORAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_temporal(self, value, unit, metadata):
        """Normalize temporal point to Unix timestamp"""
        if isinstance(value, (int, float)):
            timestamp = int(value)
        elif isinstance(value, str):
            timestamp = self._parse_datetime(value)
        else:
            raise ValueError(f"Cannot parse temporal value: {value}")
        
        try:
            metadata['iso8601'] = datetime.fromtimestamp(timestamp).isoformat()
        except:
            pass
        
        return timestamp, 'unix_timestamp', metadata
    
    def _normalize_temporal_interval(self, value, unit, metadata):
        """Normalize temporal interval to seconds"""
        if isinstance(value, (int, float)):
            numeric_val = float(value)
            
            if unit:
                try:
                    converted_val, is_approx = self.registry.convert(
                        numeric_val, unit, 'seconds'
                    )
                    metadata['conversion_applied'] = True
                    metadata['is_approximate'] = is_approx
                    metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                    metadata['human_readable'] = self._seconds_to_human(converted_val)
                    
                    return int(converted_val), 'seconds', metadata
                except ValueError:
                    pass
            
            metadata['human_readable'] = self._seconds_to_human(numeric_val)
            return int(numeric_val), 'seconds', metadata
        
        elif isinstance(value, str):
            if value.startswith('P'):
                seconds = self._parse_iso8601_duration(value)
                metadata['human_readable'] = self._seconds_to_human(seconds)
                return int(seconds), 'seconds', metadata
            
            try:
                numeric_val, parsed_unit = self._parse_duration_string(value)
                converted_val, is_approx = self.registry.convert(
                    numeric_val, parsed_unit, 'seconds'
                )
                metadata['conversion_applied'] = True
                metadata['is_approximate'] = is_approx
                metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                metadata['human_readable'] = self._seconds_to_human(converted_val)
                
                return int(converted_val), 'seconds', metadata
            except:
                pass
        
        # Fallback
        return value, 'unknown', metadata
    
    def _parse_datetime(self, value: str) -> int:
        """Parse datetime string to Unix timestamp"""
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except:
            try:
                dt = datetime.fromisoformat(value)
                return int(dt.timestamp())
            except:
                try:
                    from dateutil import parser
                    dt = parser.parse(value)
                    return int(dt.timestamp())
                except ImportError:
                    raise ValueError(f"Cannot parse datetime: {value}")
    
    def _parse_iso8601_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        pattern = r'P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?'
        match = re.match(pattern, duration)
        
        if not match:
            raise ValueError(f"Invalid ISO 8601 duration: {duration}")
        
        years, months, days, hours, minutes, seconds = match.groups()
        
        total_seconds = 0
        if years:
            total_seconds += int(years) * 31536000
        if months:
            total_seconds += int(months) * 2592000
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
        """Parse '3 hours' format to (3, 'hours')"""
        parts = value.strip().split()
        
        if len(parts) == 2:
            return float(parts[0]), parts[1].lower()
        elif len(parts) == 1:
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
        
        currency = 'USD'
        if unit:
            unit_def = self.registry.get_unit(unit)
            if unit_def and unit_def.dimension == 'Currency':
                currency = unit_def.canonical_name
        
        metadata['currency'] = currency
        
        if currency in ['USD', 'EUR', 'GBP', 'CAD', 'AUD']:
            canonical_val = Decimal(str(numeric_val)) * 100
            canonical_unit = f'{currency}_cents'
            metadata['minor_unit_conversion'] = True
        elif currency == 'JPY':
            canonical_val = Decimal(str(numeric_val))
            canonical_unit = currency
        else:
            canonical_val = Decimal(str(numeric_val))
            canonical_unit = currency
        
        return int(canonical_val), canonical_unit, metadata
    
    # -------------------------------------------------------------------------
    # SPATIAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_spatial(self, value, unit, metadata):
        """Normalize spatial value to meters"""
        numeric_val = self._parse_numeric(value)
        
        if unit:
            try:
                converted_val, is_approx = self.registry.convert(
                    numeric_val, unit, 'meters'
                )
                metadata['conversion_applied'] = True
                metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                metadata['is_approximate'] = is_approx
                
                return converted_val, 'meters', metadata
            except ValueError:
                pass
        
        return numeric_val, 'meters', metadata
    
    # -------------------------------------------------------------------------
    # POSITIONAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_positional(self, value, unit, semantics, metadata):
        """Normalize positional values"""
        numeric_val = self._parse_numeric(value)
        
        if semantics.base_unit == 'bytes':
            if unit:
                try:
                    converted_val, is_approx = self.registry.convert(
                        numeric_val, unit, 'bytes'
                    )
                    metadata['conversion_applied'] = True
                    metadata['conversion_factor'] = converted_val / numeric_val if numeric_val != 0 else 0
                    metadata['is_approximate'] = is_approx
                    return int(converted_val), 'bytes', metadata
                except ValueError:
                    pass
            return int(numeric_val), 'bytes', metadata
        
        elif semantics.base_unit == 'percent':
            if isinstance(value, str) and '%' in value:
                numeric_val = float(value.replace('%', '').strip())
            return numeric_val, 'percent', metadata
        
        elif semantics.base_unit == 'pixels':
            return int(numeric_val), 'pixels', metadata
        
        else:
            return numeric_val, semantics.base_unit, metadata
    
    # -------------------------------------------------------------------------
    # CATEGORICAL NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_categorical(self, value, operand, metadata):
        """Normalize categorical values"""
        if operand == 'language':
            canonical = self._normalize_language_code(value)
            return canonical, 'iso639-1', metadata
        
        elif operand in ['media', 'fileFormat']:
            canonical = self._normalize_mime_type(value)
            return canonical, 'mime_type', metadata
        
        else:
            canonical = str(value).lower().strip()
            return canonical, 'string', metadata
    
    def _normalize_language_code(self, value: str) -> str:
        """Normalize language to ISO 639-1 code"""
        lang_map = {
            'english': 'en', 'eng': 'en',
            'french': 'fr', 'fra': 'fr',
            'german': 'de', 'deu': 'de',
            'spanish': 'es', 'spa': 'es',
            'chinese': 'zh', 'zho': 'zh',
            'japanese': 'ja', 'jpn': 'ja',
            'arabic': 'ar', 'ara': 'ar',
        }
        
        lower_val = str(value).lower().strip()
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
        
        lower_val = str(value).lower().strip()
        
        if '/' in lower_val:
            return lower_val
        
        return mime_map.get(lower_val, value)
    
    # -------------------------------------------------------------------------
    # REFERENCE NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_reference(self, value, operand, metadata):
        """Normalize reference values"""
        if isinstance(value, str):
            canonical = value.strip()
            
            if canonical.startswith('http://') or canonical.startswith('https://'):
                metadata['is_uri'] = True
                return canonical, 'uri', metadata
            
            canonical = canonical.lower()
            metadata['is_local_name'] = True
            return canonical, 'identifier', metadata
        
        if isinstance(value, list):
            canonical = [str(v).strip() for v in value]
            metadata['is_multi_valued'] = True
            return canonical, 'uri_list', metadata
        
        return str(value), 'identifier', metadata
    
    # -------------------------------------------------------------------------
    # VERSION NORMALIZATION
    # -------------------------------------------------------------------------
    
    def _normalize_version(self, value, metadata):
        """Normalize version to comparable format"""
        parts = self._parse_version(value)
        
        canonical_val = sum(
            part * (1000 ** (len(parts) - i - 1))
            for i, part in enumerate(parts)
        )
        
        metadata['version_parts'] = parts
        metadata['version_string'] = '.'.join(map(str, parts))
        
        return canonical_val, 'semantic_version', metadata
    
    def _parse_version(self, value: Any) -> List[int]:
        """Parse version string to list of integers"""
        if isinstance(value, (int, float)):
            return [int(value)]
        
        value_str = str(value).strip()
        parts = value_str.split('.')
        
        numeric_parts = []
        for part in parts:
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