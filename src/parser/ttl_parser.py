# src/parser/ttl_parser.py
"""
Parse ODRL policies from TTL/RDF and JSON-LD files.
Uses RDFLib for robust RDF handling.

Implementation Plan Alignment:
- Complete ODRL constraint parsing
- Supports: TTL (Turtle) and JSON-LD formats
- Extracts: All metadata (unit, unitOfCount, status, dataType)
"""

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
import json
import os

# Import debug utilities from types
try:
    from src.semantics.constraint_types import debug_print, is_debug_mode, ODRLMetadata
except ImportError:
    # Fallback if running standalone
    def debug_print(category: str, message: str, data: Any = None):
        pass
    def is_debug_mode() -> bool:
        return False
    ODRLMetadata = None

logger = logging.getLogger(__name__)


# ==============================================================================
# NAMESPACES
# ==============================================================================

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


# ==============================================================================
# TTL PARSER
# ==============================================================================

class TTLParser:
    """
    Parse ODRL policies from TTL and JSON-LD files.
    
    Features:
    - Robust RDF parsing via RDFLib
    - Support for TTL (Turtle) and JSON-LD formats
    - Full metadata extraction (unit, unitOfCount, status, dataType)
    - Namespace handling
    - Debug mode with detailed output
    
    Implementation Plan Alignment:
    - Phase 1: Complete ODRL constraint parser
    - Extracts all metadata per §2.3
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize parser.
        
        Args:
            debug: Enable debug output (--dev mode)
        """
        self.debug = debug
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        """Bind common namespaces"""
        self.graph.bind("odrl", ODRL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("skos", SKOS)
    
    def reset(self):
        """Reset the graph for parsing new content"""
        self.graph = Graph()
        self._bind_namespaces()
    
    # ==========================================================================
    # FILE PARSING
    # ==========================================================================
    
    def parse_file(self, filepath: str) -> Graph:
        """
        Parse TTL or JSON-LD file into RDF graph.
        
        Args:
            filepath: Path to .ttl or .jsonld file
            
        Returns:
            RDFLib Graph object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is malformed
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Determine format from extension
        ext = os.path.splitext(filepath)[1].lower()
        format_map = {
            '.ttl': 'turtle',
            '.turtle': 'turtle',
            '.jsonld': 'json-ld',
            '.json': 'json-ld',
            '.rdf': 'xml',
            '.xml': 'xml',
            '.n3': 'n3',
            '.nt': 'nt',
        }
        
        rdf_format = format_map.get(ext, 'turtle')
        
        try:
            self._debug(f"Parsing file: {filepath} (format: {rdf_format})")
            self.graph.parse(filepath, format=rdf_format)
            
            self._debug(f"Parsed {len(self.graph)} triples")
            if self.debug:
                self._debug_print_triples()
            
            return self.graph
            
        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}")
            raise ValueError(f"Malformed {rdf_format.upper()} file: {e}")
    
    def parse_string(self, content: str, format: str = 'turtle') -> Graph:
        """
        Parse RDF from string.
        
        Args:
            content: RDF content as string
            format: 'turtle', 'json-ld', 'xml', 'n3', 'nt'
            
        Returns:
            RDFLib Graph object
        """
        try:
            self._debug(f"Parsing string content (format: {format})")
            self.graph.parse(data=content, format=format)
            
            self._debug(f"Parsed {len(self.graph)} triples")
            
            return self.graph
            
        except Exception as e:
            logger.error(f"Failed to parse string: {e}")
            raise ValueError(f"Malformed {format.upper()} content: {e}")
    
    def parse_jsonld(self, jsonld_content: Union[str, dict]) -> Graph:
        """
        Parse JSON-LD content.
        
        Args:
            jsonld_content: JSON-LD as string or dict
            
        Returns:
            RDFLib Graph object
        """
        if isinstance(jsonld_content, dict):
            jsonld_content = json.dumps(jsonld_content)
        
        return self.parse_string(jsonld_content, format='json-ld')
    
    # ==========================================================================
    # POLICY EXTRACTION
    # ==========================================================================
    
    def get_policies(self) -> List[URIRef]:
        """Get all policy URIs in the graph"""
        policies = []
        
        # ODRL Policy types
        policy_types = [
            ODRL.Policy,
            ODRL.Set,
            ODRL.Offer,
            ODRL.Agreement,
            ODRL.Request,
            ODRL.Privacy,
        ]
        
        for policy_type in policy_types:
            policies.extend(self.graph.subjects(RDF.type, policy_type))
        
        # Also check for policies without explicit type but with rules
        for subj in self.graph.subjects(ODRL.permission, None):
            if subj not in policies:
                policies.append(subj)
        for subj in self.graph.subjects(ODRL.prohibition, None):
            if subj not in policies:
                policies.append(subj)
        
        self._debug(f"Found {len(policies)} policies")
        return list(set(policies))  # Deduplicate
    
    def get_policy_metadata(self, policy_uri: URIRef) -> Dict[str, Any]:
        """
        Get policy-level metadata.
        
        Returns:
            Dict with policy metadata including inheritFrom
        """
        metadata = {
            'id': str(policy_uri),
            'type': None,
            'profile': None,
            'inheritFrom': None,
            'conflict': None,
        }
        
        # Get policy type
        for policy_type in self.graph.objects(policy_uri, RDF.type):
            if str(policy_type).startswith(str(ODRL)):
                metadata['type'] = self._local_name(policy_type)
                break
        
        # Get profile
        for profile in self.graph.objects(policy_uri, ODRL.profile):
            metadata['profile'] = str(profile)
            break
        
        # Get inheritFrom (important for inheritance checking)
        for parent in self.graph.objects(policy_uri, ODRL.inheritFrom):
            metadata['inheritFrom'] = str(parent)
            break
        
        # Get conflict resolution strategy
        for conflict in self.graph.objects(policy_uri, ODRL.conflict):
            metadata['conflict'] = self._local_name(conflict)
            break
        
        self._debug(f"Policy metadata for {policy_uri}", metadata)
        return metadata
    
    # ==========================================================================
    # RULE EXTRACTION
    # ==========================================================================
    
    def get_rules(self, policy_uri: URIRef) -> Dict[str, List[URIRef]]:
        """
        Get all rules for a policy.
        
        Returns:
            Dict with 'permissions', 'prohibitions', 'duties', 'obligations'
        """
        rules = {
            'permissions': list(self.graph.objects(policy_uri, ODRL.permission)),
            'prohibitions': list(self.graph.objects(policy_uri, ODRL.prohibition)),
            'duties': list(self.graph.objects(policy_uri, ODRL.duty)),
            'obligations': list(self.graph.objects(policy_uri, ODRL.obligation)),
        }
        
        self._debug(f"Rules for {policy_uri}: "
                   f"{len(rules['permissions'])} permissions, "
                   f"{len(rules['prohibitions'])} prohibitions, "
                   f"{len(rules['duties'])} duties")
        
        return rules
    
    def get_rule_details(self, rule_uri: URIRef) -> Dict[str, Any]:
        """
        Get full details for a rule.
        
        Returns:
            Dict with action, target, constraint, assigner, assignee, etc.
        """
        details = {
            'id': str(rule_uri),
            'action': None,
            'target': None,
            'assigner': None,
            'assignee': None,
            'constraint': None,
            'duty': [],  # Duties attached to permissions
            'remedy': [],  # Remedies for prohibitions
            'consequence': [],  # Consequences for duties
        }
        
        # Get action
        for action in self.graph.objects(rule_uri, ODRL.action):
            details['action'] = str(action)
            break
        
        # Get target (asset)
        for target in self.graph.objects(rule_uri, ODRL.target):
            details['target'] = str(target)
            break
        
        # Get assigner
        for assigner in self.graph.objects(rule_uri, ODRL.assigner):
            details['assigner'] = str(assigner)
            break
        
        # Get assignee
        for assignee in self.graph.objects(rule_uri, ODRL.assignee):
            details['assignee'] = str(assignee)
            break
        
        # Get constraint
        for constraint in self.graph.objects(rule_uri, ODRL.constraint):
            details['constraint'] = constraint  # Keep as URIRef/BNode
            break
        
        # Get duties (for permissions)
        details['duty'] = list(self.graph.objects(rule_uri, ODRL.duty))
        
        # Get remedies (for prohibitions)
        details['remedy'] = list(self.graph.objects(rule_uri, ODRL.remedy))
        
        # Get consequences (for duties)
        details['consequence'] = list(self.graph.objects(rule_uri, ODRL.consequence))
        
        self._debug(f"Rule details for {rule_uri}", {
            'action': details['action'],
            'constraint': str(details['constraint']) if details['constraint'] else None
        })
        
        return details
    
    # ==========================================================================
    # CONSTRAINT EXTRACTION (Full metadata support)
    # ==========================================================================
    
    def get_constraints(self, rule_uri: URIRef) -> List[URIRef]:
        """Get all constraint URIs for a rule"""
        return list(self.graph.objects(rule_uri, ODRL.constraint))
    
    def get_constraint_details(self, constraint_uri: Union[URIRef, BNode]) -> Dict[str, Any]:
        """
        Get full details for a constraint including all metadata.
        
        Implementation Plan §2.3 Metadata:
        - unit: Measurement unit
        - unitOfCount: Multiplier entity
        - status: Reference value
        - dataType: Type annotation
        
        Returns:
            Dict with all constraint properties
        """
        details = {
            'id': str(constraint_uri),
            'type': 'atomic',  # 'atomic', 'and', 'or', 'xone', 'andSequence'
            
            # Core constraint properties
            'leftOperand': None,
            'operator': None,
            'rightOperand': None,
            'rightOperandReference': None,
            
            # ODRL Metadata (Plan §2.3)
            'unit': None,
            'unitOfCount': None,
            'status': None,
            'dataType': None,
            
            # Logical constraint children
            'and': [],
            'or': [],
            'xone': [],
            'andSequence': [],
            
            # Additional metadata
            'metadata': {}
        }
        
        # Check if logical constraint
        is_logical = False
        for logical_op in ['and', 'or', 'xone', 'andSequence']:
            children = list(self.graph.objects(constraint_uri, ODRL[logical_op]))
            if children:
                details['type'] = logical_op
                details[logical_op] = [self._resolve_node(c) for c in children]
                is_logical = True
                break
        
        # Get atomic constraint properties
        if not is_logical:
            # leftOperand
            for lo in self.graph.objects(constraint_uri, ODRL.leftOperand):
                details['leftOperand'] = self._resolve_operand(lo)
                break
            
            # operator
            for op in self.graph.objects(constraint_uri, ODRL.operator):
                details['operator'] = self._local_name(op)
                break
            
            # rightOperand (can be literal or URI)
            for ro in self.graph.objects(constraint_uri, ODRL.rightOperand):
                details['rightOperand'] = self._resolve_value(ro)
                # Also capture datatype from literal
                if isinstance(ro, Literal) and ro.datatype:
                    details['dataType'] = str(ro.datatype)
                break
            
            # rightOperandReference
            for ror in self.graph.objects(constraint_uri, ODRL.rightOperandReference):
                details['rightOperandReference'] = str(ror)
                break
            
            # ══════════════════════════════════════════════════════════════════
            # ODRL METADATA EXTRACTION (Plan §2.3)
            # ══════════════════════════════════════════════════════════════════
            
            # unit - Measurement unit (URI or literal)
            for unit in self.graph.objects(constraint_uri, ODRL.unit):
                details['unit'] = str(unit)
                break
            
            # unitOfCount - Multiplier entity
            for uoc in self.graph.objects(constraint_uri, ODRL.unitOfCount):
                details['unitOfCount'] = self._resolve_operand(uoc)
                break
            
            # status - Reference value
            for status in self.graph.objects(constraint_uri, ODRL.status):
                details['status'] = self._resolve_value(status)
                break
            
            # dataType - explicit datatype annotation (if not from literal)
            if not details['dataType']:
                for dt in self.graph.objects(constraint_uri, ODRL.dataType):
                    details['dataType'] = str(dt)
                    break
        
        self._debug(f"Constraint details for {constraint_uri}", {
            'type': details['type'],
            'leftOperand': details['leftOperand'],
            'operator': details['operator'],
            'rightOperand': details['rightOperand'],
            'unit': details['unit'],
            'unitOfCount': details['unitOfCount'],
            'status': details['status'],
            'dataType': details['dataType'],
        })
        
        return details
    
    def extract_odrl_metadata(self, constraint_uri: Union[URIRef, BNode]) -> Dict[str, Any]:
        """
        Extract ODRL metadata into ODRLMetadata object or dict.
        
        Returns:
            ODRLMetadata object or dict with unit, unitOfCount, status, datatype
        """
        details = self.get_constraint_details(constraint_uri)
        
        result = {
            'unit': details.get('unit'),
            'unitOfCount': details.get('unitOfCount'),
            'status': details.get('status'),
            'datatype': details.get('dataType'),
            'rightOperandReference': details.get('rightOperandReference'),
        }
        
        # Try to return ODRLMetadata if available
        try:
            from src.semantics.constraint_types import ODRLMetadata
            return ODRLMetadata(
                unit=result['unit'],
                unit_of_count=result['unitOfCount'],
                status=result['status'],
                datatype=result['datatype'],
                operator_reference=result['rightOperandReference'],
            )
        except ImportError:
            return result
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def _resolve_node(self, node: Union[URIRef, BNode, Literal]) -> Any:
        """Resolve an RDF node to a usable value"""
        if isinstance(node, Literal):
            return self._resolve_value(node)
        elif isinstance(node, (URIRef, BNode)):
            return node  # Return as-is for further processing
        return str(node)
    
    def _resolve_value(self, value: Union[URIRef, Literal, BNode]) -> Any:
        """
        Resolve an RDF value to Python type.
        
        Handles:
        - Literals with datatypes (int, float, datetime, etc.)
        - URIs (as strings)
        - Lists (RDF collections)
        """
        if isinstance(value, Literal):
            # Get the Python value
            try:
                # Check datatype
                if value.datatype:
                    dt = str(value.datatype)
                    if 'integer' in dt.lower() or 'int' in dt.lower():
                        return int(value)
                    elif 'decimal' in dt.lower() or 'float' in dt.lower() or 'double' in dt.lower():
                        return float(value)
                    elif 'boolean' in dt.lower():
                        return value.toPython()
                    elif 'date' in dt.lower():
                        return str(value)  # Keep as ISO string for now
                
                # Try to infer type
                val_str = str(value)
                if val_str.isdigit():
                    return int(val_str)
                try:
                    return float(val_str)
                except ValueError:
                    pass
                
                return val_str
                
            except (ValueError, TypeError):
                return str(value)
        
        elif isinstance(value, URIRef):
            return str(value)
        
        elif isinstance(value, BNode):
            # Check if it's an RDF list
            items = self._extract_rdf_list(value)
            if items:
                return items
            return str(value)
        
        return str(value)
    
    def _resolve_operand(self, operand: Union[URIRef, Literal]) -> str:
        """Resolve a leftOperand to its local name"""
        if isinstance(operand, URIRef):
            return self._local_name(operand)
        return str(operand)
    
    def _local_name(self, uri: URIRef) -> str:
        """Extract local name from URI"""
        uri_str = str(uri)
        
        # Try fragment
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        
        # Try last path segment
        if '/' in uri_str:
            return uri_str.split('/')[-1]
        
        return uri_str
    
    def _extract_rdf_list(self, node: BNode) -> Optional[List]:
        """Extract items from an RDF list (rdf:first/rdf:rest)"""
        items = []
        current = node
        
        while current and current != RDF.nil:
            # Get first element
            first = None
            for f in self.graph.objects(current, RDF.first):
                first = self._resolve_value(f)
                break
            
            if first is not None:
                items.append(first)
            
            # Get rest
            rest = None
            for r in self.graph.objects(current, RDF.rest):
                rest = r
                break
            
            if rest is None or rest == RDF.nil:
                break
            
            current = rest
        
        return items if items else None
    
    # ==========================================================================
    # DEBUG METHODS
    # ==========================================================================
    
    def _debug(self, message: str, data: Any = None):
        """Print debug message if debug mode enabled"""
        if self.debug:
            debug_print("PARSER", message, data)
            logger.debug(f"[PARSER] {message}")
            if data:
                logger.debug(f"         {data}")
    
    def _debug_print_triples(self):
        """Print all triples for debugging"""
        if not self.debug:
            return
        
        print("\n" + "=" * 70)
        print("📄 RDF TRIPLES")
        print("=" * 70)
        
        for i, (s, p, o) in enumerate(self.graph, 1):
            s_str = self._local_name(s) if isinstance(s, URIRef) else str(s)[:30]
            p_str = self._local_name(p) if isinstance(p, URIRef) else str(p)
            o_str = self._local_name(o) if isinstance(o, URIRef) else str(o)[:40]
            print(f"  {i:3d}. {s_str:30} {p_str:20} {o_str}")
        
        print("=" * 70 + "\n")
    
    def print_policy_summary(self, policy_uri: URIRef = None):
        """Print a summary of the policy for debugging"""
        if not self.debug:
            return
        
        policies = [policy_uri] if policy_uri else self.get_policies()
        
        for policy in policies:
            print(f"\n📋 Policy: {self._local_name(policy)}")
            print("-" * 50)
            
            metadata = self.get_policy_metadata(policy)
            if metadata.get('inheritFrom'):
                print(f"   Inherits from: {metadata['inheritFrom']}")
            
            rules = self.get_rules(policy)
            
            for rule_type, rule_list in rules.items():
                if rule_list:
                    print(f"\n   {rule_type.upper()} ({len(rule_list)}):")
                    for rule in rule_list:
                        details = self.get_rule_details(rule)
                        print(f"      - Action: {details['action']}")
                        if details['constraint']:
                            c_details = self.get_constraint_details(details['constraint'])
                            if c_details['type'] == 'atomic':
                                print(f"        Constraint: {c_details['leftOperand']} "
                                      f"{c_details['operator']} {c_details['rightOperand']}")
                                if c_details['unit']:
                                    print(f"        Unit: {c_details['unit']}")
                            else:
                                print(f"        Constraint: {c_details['type'].upper()} "
                                      f"({len(c_details.get(c_details['type'], []))} children)")


# ==============================================================================
# JSON-LD PARSER (Convenience wrapper)
# ==============================================================================

class JSONLDParser(TTLParser):
    """
    Parse ODRL policies from JSON-LD files.
    
    Inherits from TTLParser, adds JSON-LD specific conveniences.
    """
    
    def parse_file(self, filepath: str) -> Graph:
        """Parse JSON-LD file"""
        self._debug(f"Parsing JSON-LD file: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_string(content, format='json-ld')
    
    def parse_dict(self, jsonld_dict: dict) -> Graph:
        """Parse JSON-LD from dictionary"""
        return self.parse_jsonld(jsonld_dict)


# ==============================================================================
# FACTORY FUNCTION
# ==============================================================================

def create_parser(filepath: str = None, debug: bool = False) -> TTLParser:
    """
    Create appropriate parser based on file extension.
    
    Args:
        filepath: Optional file path to determine format
        debug: Enable debug mode
        
    Returns:
        TTLParser or JSONLDParser instance
    """
    if filepath:
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ('.json', '.jsonld'):
            return JSONLDParser(debug=debug)
    
    return TTLParser(debug=debug)