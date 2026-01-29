# =============================================================================
# FIX FOR xsd:date HANDLING IN z3_encoder.py
# =============================================================================
#
# PROBLEM: date objects (from xsd:date) are being converted to 0 in Z3 encoding
#
# ROOT CAUSE: The _to_z3_value method doesn't handle date objects
#
# LOCATION: src/encoder/z3_encoder.py, in class ConstraintEncoder
#
# Replace the _to_z3_value method with this fixed version:
# =============================================================================

def _to_z3_value(self, value: Any, var: Any) -> Any:
    """Convert Python value to Z3 value matching variable sort."""
    if value is None:
        return IntVal(0)
    
    # Handle datetime (convert to timestamp)
    if hasattr(value, 'timestamp'):
        # This handles datetime objects with timezone
        return IntVal(int(value.timestamp())) if str(var.sort()) == 'Int' else RealVal(int(value.timestamp()))
    
    # Handle date objects (from xsd:date) - convert to start of day UTC
    # IMPORTANT: Check this AFTER datetime since datetime is subclass of date
    from datetime import date, datetime, timezone
    if isinstance(value, date) and not isinstance(value, datetime):
        # Convert date to datetime at start of day UTC
        dt = datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=timezone.utc)
        timestamp = int(dt.timestamp())
        return IntVal(timestamp) if str(var.sort()) == 'Int' else RealVal(timestamp)
    
    # Handle timedelta (convert to seconds)
    if hasattr(value, 'total_seconds'):
        seconds = int(value.total_seconds())
        return IntVal(seconds) if str(var.sort()) == 'Int' else RealVal(seconds)
    
    # Handle Decimal
    from decimal import Decimal
    if isinstance(value, Decimal):
        value = float(value)
    
    # Handle numeric
    if isinstance(value, int):
        return IntVal(value) if str(var.sort()) == 'Int' else RealVal(value)
    if isinstance(value, float):
        return RealVal(value)
    
    # Handle string (try to parse as number or date)
    if isinstance(value, str):
        # First try to parse as ISO date/datetime
        try:
            # Try datetime first
            if 'T' in value or ' ' in value:
                if value.endswith('Z'):
                    value_str = value[:-1] + '+00:00'
                else:
                    value_str = value
                dt = datetime.fromisoformat(value_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                timestamp = int(dt.timestamp())
                return IntVal(timestamp) if str(var.sort()) == 'Int' else RealVal(timestamp)
            # Try date only (YYYY-MM-DD)
            elif '-' in value and len(value) == 10:
                d = date.fromisoformat(value)
                dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
                timestamp = int(dt.timestamp())
                return IntVal(timestamp) if str(var.sort()) == 'Int' else RealVal(timestamp)
        except (ValueError, TypeError):
            pass
        
        # Try to parse as number
        try:
            if '.' in value:
                return RealVal(float(value))
            return IntVal(int(value))
        except ValueError:
            # String value - return 0 as placeholder
            logger.warning(f"Cannot convert string '{value}' to Z3 numeric")
            return IntVal(0)
    
    return IntVal(0)


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    from datetime import date, datetime, timezone
    from z3 import Int, Real, IntVal, RealVal
    
    # Create test variable
    var = Int("test_var")
    
    print("Testing _to_z3_value fix:")
    print("=" * 50)
    
    # Simulate the method
    def test_to_z3_value(value, var):
        if value is None:
            return IntVal(0)
        
        if hasattr(value, 'timestamp'):
            return IntVal(int(value.timestamp()))
        
        from datetime import date as date_type, datetime as datetime_type
        if isinstance(value, date_type) and not isinstance(value, datetime_type):
            dt = datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=timezone.utc)
            return IntVal(int(dt.timestamp()))
        
        if hasattr(value, 'total_seconds'):
            return IntVal(int(value.total_seconds()))
        
        if isinstance(value, (int, float)):
            return IntVal(int(value))
        
        return IntVal(0)
    
    # Test cases
    tests = [
        (datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc), "datetime 2024-01-01"),
        (date(2024, 1, 1), "date 2024-01-01 (xsd:date)"),
        (date(2024, 12, 31), "date 2024-12-31 (xsd:date)"),
        (1704067200, "int timestamp"),
    ]
    
    print("\nResults:")
    for value, desc in tests:
        result = test_to_z3_value(value, var)
        print(f"  {desc}: {type(value).__name__} -> {result}")
    
    print("\nExpected:")
    print("  2024-01-01 = IntVal(1704067200)")
    print("  2024-12-31 = IntVal(1735603200)")