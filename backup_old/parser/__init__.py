# src/parser/__init__.py
"""
ODRL-SA Parser Module

Parses ODRL Turtle (TTL) files and extracts:
- Policy structure (permissions, prohibitions, duties)
- Constraints (atomic and composite)
- Full ODRL metadata
- Inheritance relationships

Main Components:
    - ODRLParser: Main parser class
    - ParseResult: Container for parsed data
    - Policy: Policy structure
    - Rule: Rule structure (permission/prohibition/duty)
    - RuleType: Enum for rule types

Convenience Functions:
    - parse_ttl_file(filepath): Parse a TTL file
    - parse_ttl_string(ttl_string): Parse TTL from string
"""

from .ttl_parser import (
    # Parser
    ODRLParser,
    
    # Results
    ParseResult,
    
    # Policy structure
    Policy,
    Rule,
    RuleType,
    
    # Convenience
    parse_ttl_file,
    parse_ttl_string,
)

__all__ = [
    "ODRLParser",
    "ParseResult",
    "Policy",
    "Rule",
    "RuleType",
    "parse_ttl_file",
    "parse_ttl_string",
]