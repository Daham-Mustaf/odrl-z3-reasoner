# src/parser/ttl_parser.py
"""
ODRL-SA TTL Parser (Complete Implementation)

Parses ODRL policies from Turtle (TTL) files and extracts:
- Policy structure (permissions, prohibitions, duties)
- Constraints (atomic and composite)
- Full ODRL metadata (unit, unitOfCount, status, dataType)
- Inheritance relationships (odrl:inheritFrom)
- Logical constraints (AND, OR, XONE, andSequence)

Based on the formal specification constraint tuple:
    c = (ℓ, ⋈, v, u?, d?, r?, s?)

This parser converts RDF to the core types defined in src/core/types.py.
"""

from typing import List, Dict, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import logging
import os
import warnings

from rdflib import Graph, URIRef, Literal, BNode, Namespace, RDF
from rdflib.collection import Collection
from rdflib.namespace import RDFS, XSD

# Import core types
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.types import (
    AtomicConstraint,
    CompositeConstraint,
    OperatorType,
    LogicalOperator,
    RightOperand,
    ConstraintMetadata,
    Constraint,
)

logger = logging.getLogger(__name__)


# =============================================================================
# NAMESPACES
# =============================================================================

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
DCTERMS = Namespace("http://purl.org/dc/terms/")


# =============================================================================
# RULE TYPE (Policy-Level)
# =============================================================================

class RuleType(Enum):
    """Type of ODRL rule."""
    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    DUTY = "duty"
    OBLIGATION = "obligation"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Rule:
    """
    An ODRL Rule (Permission, Prohibition, or Duty).
    
    Contains:
    - Action being permitted/prohibited
    - Target asset
    - Associated constraints
    """
    uid: str
    rule_type: RuleType
    action: Optional[str] = None
    target: Optional[str] = None
    assigner: Optional[str] = None
    assignee: Optional[str] = None
    constraint_ids: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        return f"{self.rule_type.value}({self.action})"


@dataclass
class Policy:
    """
    An ODRL Policy.
    
    Contains:
    - Policy URI and type
    - Rules (permissions, prohibitions, duties)
    - Inheritance relationship
    """
    uid: str
    policy_type: Optional[str] = None
    rules: List[Rule] = field(default_factory=list)
    inherits_from: Optional[str] = None
    profile: Optional[str] = None
    conflict_strategy: Optional[str] = None
    
    @property
    def permissions(self) -> List[Rule]:
        return [r for r in self.rules if r.rule_type == RuleType.PERMISSION]
    
    @property
    def prohibitions(self) -> List[Rule]:
        return [r for r in self.rules if r.rule_type == RuleType.PROHIBITION]
    
    @property
    def duties(self) -> List[Rule]:
        return [r for r in self.rules if r.rule_type in {RuleType.DUTY, RuleType.OBLIGATION}]
    
    def is_empty(self) -> bool:
        """Check if policy has no rules."""
        return len(self.rules) == 0


@dataclass
class ParseResult:
    """Complete result of parsing an ODRL TTL file."""
    
    # Policies
    policies: List[Policy] = field(default_factory=list)
    
    # All constraints (keyed by UID)
    constraints: Dict[str, Constraint] = field(default_factory=dict)
    
    # Parsing errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Statistics
    stats: Dict[str, int] = field(default_factory=dict)
    
    def get_atomic_constraints(self) -> List[AtomicConstraint]:
        """Get all atomic constraints."""
        return [c for c in self.constraints.values() if isinstance(c, AtomicConstraint)]
    
    def get_composite_constraints(self) -> List[CompositeConstraint]:
        """Get all composite constraints."""
        return [c for c in self.constraints.values() if isinstance(c, CompositeConstraint)]
    
    def get_constraints_for_policy(self, policy_uid: str) -> List[Constraint]:
        """Get all constraints associated with a policy."""
        policy = next((p for p in self.policies if p.uid == policy_uid), None)
        if not policy:
            return []
        
        constraint_ids = set()
        for rule in policy.rules:
            constraint_ids.update(rule.constraint_ids)
        
        return [self.constraints[uid] for uid in constraint_ids if uid in self.constraints]
    
    def get_constraint(self, uid: str) -> Optional[Constraint]:
        """Get a constraint by UID."""
        return self.constraints.get(uid)
    
    def has_errors(self) -> bool:
        """Check if parsing had errors."""
        return len(self.errors) > 0
    
    def has_policies(self) -> bool:
        """Check if any policies were found."""
        return len(self.policies) > 0
    
    def summary(self) -> str:
        """Get a summary string."""
        return (
            f"ParseResult: {len(self.policies)} policies, "
            f"{len(self.get_atomic_constraints())} atomic constraints, "
            f"{len(self.get_composite_constraints())} composite constraints, "
            f"{len(self.errors)} errors"
        )


# =============================================================================
# ODRL PARSER
# =============================================================================

class ODRLParser:
    """
    Parser for ODRL Turtle files.
    
    Features:
    - Full policy structure extraction
    - Atomic and composite constraints (AND, OR, XONE)
    - Complete ODRL metadata
    - Inheritance relationships
    - RDF Collection handling for logical constraints
    - Robust error handling
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize parser.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug
        self.graph: Optional[Graph] = None
        self._constraint_counter = 0
        self._rule_counter = 0
        self._processed_nodes: Set = set()
        self._node_to_uid: Dict[Any, str] = {}
    
    def parse_file(self, filepath: str) -> ParseResult:
        """
        Parse an ODRL TTL file.
        
        Args:
            filepath: Path to .ttl file
            
        Returns:
            ParseResult with policies and constraints
        """
        result = ParseResult()
        
        # Check file exists
        if not os.path.exists(filepath):
            result.errors.append(f"File not found: {filepath}")
            return result
        
        # Determine format
        ext = os.path.splitext(filepath)[1].lower()
        format_map = {
            '.ttl': 'turtle',
            '.turtle': 'turtle',
            '.rdf': 'xml',
            '.xml': 'xml',
            '.n3': 'n3',
            '.jsonld': 'json-ld',
            '.json': 'json-ld',
        }
        rdf_format = format_map.get(ext, 'turtle')
        
        self._debug(f"Parsing file: {filepath} (format: {rdf_format})")
        
        # Parse with error handling
        try:
            self.graph = Graph()
            # Suppress rdflib warnings about invalid URIs
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.graph.parse(filepath, format=rdf_format)
        except Exception as e:
            result.errors.append(f"Failed to parse RDF: {e}")
            return result
        
        self._debug(f"Loaded {len(self.graph)} triples")
        result.stats['triples'] = len(self.graph)
        
        return self._extract_all(result)
    
    def parse_string(self, ttl_string: str, format: str = 'turtle') -> ParseResult:
        """
        Parse ODRL from a string.
        
        Args:
            ttl_string: TTL content
            format: RDF format ('turtle', 'xml', 'json-ld')
            
        Returns:
            ParseResult with policies and constraints
        """
        result = ParseResult()
        
        # Handle empty string
        if not ttl_string or not ttl_string.strip():
            result.warnings.append("Empty TTL string provided")
            return result
        
        # Parse with error handling
        try:
            self.graph = Graph()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.graph.parse(data=ttl_string, format=format)
        except Exception as e:
            result.errors.append(f"Failed to parse RDF: {e}")
            return result
        
        self._debug(f"Parsed {len(self.graph)} triples from string")
        result.stats['triples'] = len(self.graph)
        
        return self._extract_all(result)
    
    # =========================================================================
    # MAIN EXTRACTION
    # =========================================================================
    
    def _extract_all(self, result: ParseResult) -> ParseResult:
        """Extract all ODRL structures from the graph."""
        self._constraint_counter = 0
        self._rule_counter = 0
        self._processed_nodes = set()
        self._node_to_uid = {}
        
        # Find all policies
        policy_uris = self._find_policies()
        self._debug(f"Found {len(policy_uris)} policies")
        result.stats['policies_found'] = len(policy_uris)
        
        if not policy_uris:
            result.warnings.append("No ODRL policies found in the input")
            return result
        
        # Extract each policy
        for policy_uri in policy_uris:
            try:
                policy = self._extract_policy(policy_uri, result)
                if policy:
                    result.policies.append(policy)
            except Exception as e:
                error_msg = f"Failed to extract policy {policy_uri}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        # Update statistics
        result.stats['policies'] = len(result.policies)
        result.stats['atomic_constraints'] = len(result.get_atomic_constraints())
        result.stats['composite_constraints'] = len(result.get_composite_constraints())
        
        return result
    
    def _find_policies(self) -> List[URIRef]:
        """Find all policy URIs in the graph."""
        policies = set()
        
        # ODRL policy types
        policy_types = [
            ODRL.Policy, ODRL.Set, ODRL.Offer, 
            ODRL.Agreement, ODRL.Request, ODRL.Privacy,
            ODRL.Ticket, ODRL.Assertion
        ]
        
        for ptype in policy_types:
            for s in self.graph.subjects(RDF.type, ptype):
                if isinstance(s, (URIRef, BNode)):
                    policies.add(s)
        
        # Also check for subjects with rules (implicit policies)
        for pred in [ODRL.permission, ODRL.prohibition, ODRL.duty, ODRL.obligation]:
            for s in self.graph.subjects(pred, None):
                if isinstance(s, URIRef):
                    policies.add(s)
        
        return list(policies)
    
    # =========================================================================
    # POLICY EXTRACTION
    # =========================================================================
    
    def _extract_policy(self, policy_uri: Any, result: ParseResult) -> Optional[Policy]:
        """Extract a single policy."""
        self._debug(f"Extracting policy: {policy_uri}")
        
        # Get policy type
        policy_type = None
        for ptype in self.graph.objects(policy_uri, RDF.type):
            ptype_str = str(ptype)
            if ptype_str.startswith(str(ODRL)):
                policy_type = self._local_name(ptype)
                break
        
        # Get inheritance
        inherits_from = None
        for parent in self.graph.objects(policy_uri, ODRL.inheritFrom):
            inherits_from = str(parent)
            break
        
        # Get profile
        profile = None
        for p in self.graph.objects(policy_uri, ODRL.profile):
            profile = str(p)
            break
        
        # Get conflict strategy
        conflict = None
        for c in self.graph.objects(policy_uri, ODRL.conflict):
            conflict = self._local_name(c)
            break
        
        # Create policy
        policy = Policy(
            uid=str(policy_uri),
            policy_type=policy_type,
            inherits_from=inherits_from,
            profile=profile,
            conflict_strategy=conflict
        )
        
        # Extract rules
        rule_mappings = [
            (ODRL.permission, RuleType.PERMISSION),
            (ODRL.prohibition, RuleType.PROHIBITION),
            (ODRL.duty, RuleType.DUTY),
            (ODRL.obligation, RuleType.OBLIGATION),
        ]
        
        for predicate, rule_type in rule_mappings:
            for rule_node in self.graph.objects(policy_uri, predicate):
                try:
                    rule = self._extract_rule(rule_node, rule_type, result)
                    if rule:
                        policy.rules.append(rule)
                except Exception as e:
                    result.warnings.append(f"Failed to extract rule: {e}")
        
        self._debug(f"Extracted policy with {len(policy.rules)} rules")
        
        # Warn if policy is empty
        if policy.is_empty():
            result.warnings.append(f"Policy {policy.uid} has no rules")
        
        return policy
    
    # =========================================================================
    # RULE EXTRACTION
    # =========================================================================
    
    def _extract_rule(
        self, 
        rule_node: Any, 
        rule_type: RuleType, 
        result: ParseResult
    ) -> Optional[Rule]:
        """Extract a single rule."""
        rule_uid = self._make_uid(rule_node, 'rule')
        
        # Get action
        action = None
        for a in self.graph.objects(rule_node, ODRL.action):
            action = self._local_name(a)
            break
        
        # Get target
        target = None
        for t in self.graph.objects(rule_node, ODRL.target):
            target = str(t)
            break
        
        # Get assigner/assignee
        assigner = None
        assignee = None
        for a in self.graph.objects(rule_node, ODRL.assigner):
            assigner = str(a)
            break
        for a in self.graph.objects(rule_node, ODRL.assignee):
            assignee = str(a)
            break
        
        rule = Rule(
            uid=rule_uid,
            rule_type=rule_type,
            action=action,
            target=target,
            assigner=assigner,
            assignee=assignee
        )
        
        # Extract constraints from odrl:constraint
        for constraint_node in self.graph.objects(rule_node, ODRL.constraint):
            try:
                constraint_uid = self._extract_constraint(constraint_node, result)
                if constraint_uid:
                    rule.constraint_ids.append(constraint_uid)
            except Exception as e:
                result.warnings.append(f"Failed to extract constraint: {e}")
        
        # Extract refinements
        for constraint_node in self.graph.objects(rule_node, ODRL.refinement):
            try:
                constraint_uid = self._extract_constraint(constraint_node, result)
                if constraint_uid:
                    rule.constraint_ids.append(constraint_uid)
            except Exception as e:
                result.warnings.append(f"Failed to extract refinement: {e}")
        
        self._debug(f"Extracted {rule_type.value} with {len(rule.constraint_ids)} constraints")
        
        return rule
    
    # =========================================================================
    # CONSTRAINT EXTRACTION
    # =========================================================================
    
    def _extract_constraint(
        self, 
        node: Any, 
        result: ParseResult
    ) -> Optional[str]:
        """
        Extract a constraint (atomic or composite).
        
        Returns the constraint UID.
        """
        # Check if already processed
        if node in self._node_to_uid:
            return self._node_to_uid[node]
        
        # Check for logical operators (composite) - MUST check these first
        # ODRL uses odrl:and, odrl:or, odrl:xone for logical constraints
        logical_predicates = [
            (ODRL['and'], LogicalOperator.AND),
            (ODRL['or'], LogicalOperator.OR),
            (ODRL.xone, LogicalOperator.XONE),
            (ODRL.andSequence, LogicalOperator.AND_SEQUENCE),
        ]
        
        for pred, operator in logical_predicates:
            # Check if this node has the logical predicate
            logical_obj = self.graph.value(node, pred)
            if logical_obj is not None:
                self._debug(f"Found {operator.value} constraint at {node}")
                return self._extract_composite(node, operator, logical_obj, result)
        
        # Check if this is a LogicalConstraint type
        for rdf_type in self.graph.objects(node, RDF.type):
            if rdf_type == ODRL.LogicalConstraint:
                # It's a LogicalConstraint but we need to find which operator
                for pred, operator in logical_predicates:
                    logical_obj = self.graph.value(node, pred)
                    if logical_obj is not None:
                        return self._extract_composite(node, operator, logical_obj, result)
        
        # Otherwise it's an atomic constraint
        return self._extract_atomic(node, result)
    
    def _extract_composite(
        self, 
        node: Any, 
        operator: LogicalOperator,
        list_node: Any,
        result: ParseResult
    ) -> Optional[str]:
        """
        Extract a composite constraint (AND, OR, XONE, andSequence).
        
        The list_node is typically an RDF Collection (list) of child constraints.
        """
        uid = self._make_uid(node, f'{operator.value}')
        self._node_to_uid[node] = uid
        
        self._debug(f"Extracting {operator.value} composite: {uid}")
        
        # Parse the RDF Collection to get child nodes
        child_nodes = self._parse_rdf_collection(list_node)
        
        if not child_nodes:
            # Maybe it's not a collection, try direct children
            child_nodes = [list_node]
        
        self._debug(f"  Found {len(child_nodes)} children in {operator.value}")
        
        # Extract each child constraint
        child_uids = []
        for child_node in child_nodes:
            try:
                child_uid = self._extract_constraint(child_node, result)
                if child_uid:
                    child_uids.append(child_uid)
                    self._debug(f"    Child: {child_uid}")
            except Exception as e:
                result.warnings.append(f"Failed to extract child constraint: {e}")
        
        if not child_uids:
            result.warnings.append(f"Composite constraint {uid} has no valid children")
            return None
        
        # Create composite constraint
        composite = CompositeConstraint(
            uid=uid,
            operator=operator,
            operands=tuple(child_uids)
        )
        
        result.constraints[uid] = composite
        self._debug(f"Created {operator.value} composite with {len(child_uids)} children: {child_uids}")
        
        return uid
    
    def _parse_rdf_collection(self, node: Any) -> List[Any]:
        """
        Parse an RDF Collection (list) to get all items.
        
        RDF Collections use rdf:first/rdf:rest pattern.
        """
        if node is None:
            return []
        
        # Try using rdflib's Collection helper
        try:
            items = list(Collection(self.graph, node))
            if items:
                return items
        except Exception:
            pass
        
        # Manual parsing as fallback
        items = []
        current = node
        visited = set()
        max_iterations = 100
        
        for _ in range(max_iterations):
            if current is None:
                break
            if current == RDF.nil:
                break
            if current in visited:
                break  # Avoid infinite loops
            visited.add(current)
            
            # Get rdf:first
            first = self.graph.value(current, RDF.first)
            if first is not None:
                items.append(first)
            
            # Move to rdf:rest
            current = self.graph.value(current, RDF.rest)
        
        return items
    
    def _extract_atomic(self, node: Any, result: ParseResult) -> Optional[str]:
        """Extract an atomic constraint."""
        uid = self._make_uid(node, 'constraint')
        self._node_to_uid[node] = uid
        
        # leftOperand (REQUIRED)
        left_op = self.graph.value(node, ODRL.leftOperand)
        if left_op is None:
            self._debug(f"Constraint {node} missing leftOperand")
            result.warnings.append(f"Constraint missing leftOperand: {node}")
            return None
        
        # operator (REQUIRED)
        op_uri = self.graph.value(node, ODRL.operator)
        if op_uri is None:
            self._debug(f"Constraint {node} missing operator")
            result.warnings.append(f"Constraint missing operator: {node}")
            return None
        
        # Parse operator
        try:
            operator = OperatorType.from_string(str(op_uri))
        except ValueError as e:
            self._debug(f"Unknown operator: {op_uri}")
            result.warnings.append(f"Unknown operator: {op_uri}")
            return None
        
        # rightOperand or rightOperandReference
        right_op = self.graph.value(node, ODRL.rightOperand)
        right_op_ref = self.graph.value(node, ODRL.rightOperandReference)
        
        if right_op is None and right_op_ref is None:
            # Check for special values
            # Check if rightOperand is policyUsage
            for _, _, o in self.graph.triples((node, ODRL.rightOperand, None)):
                if o == ODRL.policyUsage:
                    right_operand = RightOperand.policy_usage()
                    break
            else:
                self._debug(f"Constraint {node} missing rightOperand")
                result.warnings.append(f"Constraint missing rightOperand: {node}")
                return None
        elif right_op_ref is not None:
            right_operand = RightOperand.iri(str(right_op_ref))
        else:
            right_operand = self._parse_right_operand(right_op)
        
        # Extract metadata
        metadata = self._extract_metadata(node)
        
        # Create constraint
        constraint = AtomicConstraint(
            uid=uid,
            left_operand=self._local_name(left_op),
            operator=operator,
            right_operand=right_operand,
            metadata=metadata
        )
        
        result.constraints[uid] = constraint
        self._debug(f"Extracted atomic: {constraint}")
        
        return uid
    
    def _extract_metadata(self, node: Any) -> ConstraintMetadata:
        """Extract ODRL metadata from constraint node."""
        # unit
        unit = self.graph.value(node, ODRL.unit)
        
        # dataType
        datatype = self.graph.value(node, ODRL.dataType)
        
        # rightOperandReference
        right_op_ref = self.graph.value(node, ODRL.rightOperandReference)
        
        # unitOfCount
        unit_of_count = self.graph.value(node, ODRL.unitOfCount)
        
        # status
        status = self.graph.value(node, ODRL.status)
        
        return ConstraintMetadata(
            unit=str(unit) if unit else None,
            datatype=str(datatype) if datatype else None,
            right_operand_reference=str(right_op_ref) if right_op_ref else None,
            unit_of_count=str(unit_of_count) if unit_of_count else None,
        )
    
    def _parse_right_operand(self, value: Any) -> RightOperand:
        """Parse a rightOperand value."""
        if isinstance(value, Literal):
            datatype = str(value.datatype) if value.datatype else None
            py_value = value.toPython()
            return RightOperand.literal(py_value, datatype)
        
        elif isinstance(value, URIRef):
            return RightOperand.iri(str(value))
        
        elif isinstance(value, BNode):
            # Could be a list - try to parse it
            items = self._parse_rdf_collection(value)
            if items:
                # Convert items to Python values
                py_items = []
                for item in items:
                    if isinstance(item, Literal):
                        py_items.append(item.toPython())
                    else:
                        py_items.append(str(item))
                return RightOperand.literal(tuple(py_items))
            return RightOperand.literal(str(value))
        
        return RightOperand.literal(str(value))
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _local_name(self, uri: Any) -> str:
        """Extract local name from URI."""
        if uri is None:
            return ""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str
    
    def _make_uid(self, node: Any, prefix: str) -> str:
        """Generate a unique ID for a node."""
        if isinstance(node, URIRef):
            local = self._local_name(node)
            if local and local != str(node):
                return local
        
        # Generate sequential ID
        self._constraint_counter += 1
        return f"{prefix}_{self._constraint_counter}"
    
    def _debug(self, message: str, data: Any = None):
        """Print debug message."""
        if self.debug:
            print(f"[PARSER] {message}")
            if data:
                print(f"         {data}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_ttl_file(filepath: str, debug: bool = False) -> ParseResult:
    """
    Parse an ODRL TTL file.
    
    Args:
        filepath: Path to TTL file
        debug: Enable debug output
        
    Returns:
        ParseResult with policies and constraints
        
    Example:
        result = parse_ttl_file("policy.ttl")
        if result.has_errors():
            print("Errors:", result.errors)
        for policy in result.policies:
            print(policy)
        for c in result.get_atomic_constraints():
            print(c)
    """
    parser = ODRLParser(debug=debug)
    return parser.parse_file(filepath)


def parse_ttl_string(ttl_string: str, debug: bool = False) -> ParseResult:
    """
    Parse ODRL from a TTL string.
    
    Args:
        ttl_string: TTL content
        debug: Enable debug output
        
    Returns:
        ParseResult with policies and constraints
        
    Example:
        result = parse_ttl_string(ttl_content)
        if not result.has_policies():
            print("No policies found")
    """
    parser = ODRLParser(debug=debug)
    return parser.parse_string(ttl_string)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    # Test with various constraint types
    test_ttl = '''
    @prefix odrl: <http://www.w3.org/ns/odrl/2/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix ex: <http://example.org/> .
    
    # Simple policy with atomic constraints
    ex:policy1 a odrl:Set ;
        odrl:permission [
            odrl:target ex:asset1 ;
            odrl:action odrl:use ;
            odrl:constraint [
                odrl:leftOperand odrl:count ;
                odrl:operator odrl:lteq ;
                odrl:rightOperand "10"^^xsd:integer
            ] ;
            odrl:constraint [
                odrl:leftOperand odrl:dateTime ;
                odrl:operator odrl:gteq ;
                odrl:rightOperand "2024-01-01T00:00:00Z"^^xsd:dateTime
            ]
        ] ;
        odrl:prohibition [
            odrl:target ex:asset1 ;
            odrl:action odrl:distribute ;
            odrl:constraint [
                odrl:leftOperand odrl:count ;
                odrl:operator odrl:gt ;
                odrl:rightOperand "5"^^xsd:integer
            ]
        ] .
    
    # Policy with AND composite constraint
    ex:policy2 a odrl:Set ;
        odrl:permission [
            odrl:action odrl:use ;
            odrl:constraint [
                odrl:and (
                    [ odrl:leftOperand odrl:count ;
                      odrl:operator odrl:gteq ;
                      odrl:rightOperand "1"^^xsd:integer ]
                    [ odrl:leftOperand odrl:count ;
                      odrl:operator odrl:lteq ;
                      odrl:rightOperand "5"^^xsd:integer ]
                )
            ]
        ] .
    
    # Policy with OR composite constraint
    ex:policy3 a odrl:Set ;
        odrl:permission [
            odrl:action odrl:play ;
            odrl:constraint [
                odrl:or (
                    [ odrl:leftOperand odrl:count ;
                      odrl:operator odrl:eq ;
                      odrl:rightOperand "1"^^xsd:integer ]
                    [ odrl:leftOperand odrl:count ;
                      odrl:operator odrl:eq ;
                      odrl:rightOperand "2"^^xsd:integer ]
                    [ odrl:leftOperand odrl:count ;
                      odrl:operator odrl:eq ;
                      odrl:rightOperand "3"^^xsd:integer ]
                )
            ]
        ] .
    
    # Policy with XONE (exactly one) constraint
    ex:policy4 a odrl:Set ;
        odrl:permission [
            odrl:action odrl:display ;
            odrl:constraint [
                odrl:xone (
                    [ odrl:leftOperand odrl:percentage ;
                      odrl:operator odrl:lteq ;
                      odrl:rightOperand "50"^^xsd:decimal ]
                    [ odrl:leftOperand odrl:percentage ;
                      odrl:operator odrl:gt ;
                      odrl:rightOperand "75"^^xsd:decimal ]
                )
            ]
        ] .
    
    # Policy with set operator
    ex:policy5 a odrl:Set ;
        odrl:permission [
            odrl:action odrl:use ;
            odrl:constraint [
                odrl:leftOperand odrl:language ;
                odrl:operator odrl:isAnyOf ;
                odrl:rightOperand ( "en" "de" "fr" )
            ]
        ] .
    '''
    
    print("=" * 70)
    print("ODRL Parser Test (Complete Implementation)")
    print("=" * 70)
    
    result = parse_ttl_string(test_ttl, debug=True)
    
    print(f"\n{result.summary()}")
    
    print(f"\n{'='*70}")
    print("POLICIES")
    print("=" * 70)
    for policy in result.policies:
        print(f"\nPolicy: {policy.uid}")
        print(f"  Type: {policy.policy_type}")
        print(f"  Rules: {len(policy.rules)}")
        for rule in policy.rules:
            print(f"    - {rule} -> constraints: {rule.constraint_ids}")
    
    print(f"\n{'='*70}")
    print("ATOMIC CONSTRAINTS")
    print("=" * 70)
    for c in result.get_atomic_constraints():
        print(f"  [{c.uid}] {c}")
    
    print(f"\n{'='*70}")
    print("COMPOSITE CONSTRAINTS")
    print("=" * 70)
    for c in result.get_composite_constraints():
        print(f"  [{c.uid}] {c.operator.value}({c.operands})")
    
    if result.errors:
        print(f"\n{'='*70}")
        print("ERRORS")
        print("=" * 70)
        for e in result.errors:
            print(f"  - {e}")
    
    if result.warnings:
        print(f"\n{'='*70}")
        print("WARNINGS")
        print("=" * 70)
        for w in result.warnings:
            print(f"  - {w}")
    
    print("\n" + "=" * 70)