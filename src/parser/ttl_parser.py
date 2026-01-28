# src/parser/ttl_parser.py
"""
ODRL-SA TTL Parser - Fixed for Anonymous Composite Children

Supports BOTH forms of composite constraints:
1. Named: odrl:or ex:c1, ex:c2
2. Anonymous: odrl:or ( [ ... ] [ ... ] )

The key fix is in _parse_rdf_list_nodes() which returns actual RDF nodes
(BNodes/URIRefs) instead of converting to strings, allowing recursive
constraint extraction.
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

from core.constraint_types import (
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
# RULE TYPE
# =============================================================================

class RuleType(Enum):
    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    DUTY = "duty"
    OBLIGATION = "obligation"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Rule:
    uid: str
    rule_type: RuleType
    action: Optional[str] = None
    target: Optional[str] = None
    assigner: Optional[str] = None
    assignee: Optional[str] = None
    constraint_ids: List[str] = field(default_factory=list)


@dataclass
class Policy:
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


@dataclass
class ParseResult:
    policies: List[Policy] = field(default_factory=list)
    constraints: Dict[str, Constraint] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    
    def get_atomic_constraints(self) -> List[AtomicConstraint]:
        return [c for c in self.constraints.values() if isinstance(c, AtomicConstraint)]
    
    def get_composite_constraints(self) -> List[CompositeConstraint]:
        return [c for c in self.constraints.values() if isinstance(c, CompositeConstraint)]
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def has_policies(self) -> bool:
        return len(self.policies) > 0


# =============================================================================
# PARSER
# =============================================================================

class ODRLParser:
    """
    Parser for ODRL Turtle files.
    
    FIXED: Now properly handles anonymous constraints inside RDF lists.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.graph: Optional[Graph] = None
        self._constraint_counter = 0
        self._rule_counter = 0
        self._processed_nodes: Set = set()
        self._node_to_uid: Dict[Any, str] = {}
    
    def parse_file(self, filepath: str) -> ParseResult:
        """Parse an ODRL TTL file."""
        result = ParseResult()
        
        if not os.path.exists(filepath):
            result.errors.append(f"File not found: {filepath}")
            return result
        
        ext = os.path.splitext(filepath)[1].lower()
        format_map = {'.ttl': 'turtle', '.rdf': 'xml', '.n3': 'n3', '.jsonld': 'json-ld'}
        rdf_format = format_map.get(ext, 'turtle')
        
        try:
            self.graph = Graph()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.graph.parse(filepath, format=rdf_format)
        except Exception as e:
            result.errors.append(f"Failed to parse RDF: {e}")
            return result
        
        return self._extract_all(result)
    
    def parse_string(self, ttl_string: str, format: str = 'turtle') -> ParseResult:
        """Parse ODRL from a string."""
        result = ParseResult()
        
        if not ttl_string or not ttl_string.strip():
            result.warnings.append("Empty TTL string")
            return result
        
        try:
            self.graph = Graph()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.graph.parse(data=ttl_string, format=format)
        except Exception as e:
            result.errors.append(f"Failed to parse RDF: {e}")
            return result
        
        return self._extract_all(result)
    
    def _extract_all(self, result: ParseResult) -> ParseResult:
        """Extract all ODRL structures."""
        self._constraint_counter = 0
        self._rule_counter = 0
        self._processed_nodes = set()
        self._node_to_uid = {}
        
        policy_uris = self._find_policies()
        
        if not policy_uris:
            result.warnings.append("No ODRL policies found")
            return result
        
        for policy_uri in policy_uris:
            try:
                policy = self._extract_policy(policy_uri, result)
                if policy:
                    result.policies.append(policy)
            except Exception as e:
                result.errors.append(f"Failed to extract policy: {e}")
        
        return result
    
    def _find_policies(self) -> List[URIRef]:
        """Find all policy URIs."""
        policies = set()
        
        policy_types = [ODRL.Policy, ODRL.Set, ODRL.Offer, ODRL.Agreement, ODRL.Request]
        
        for ptype in policy_types:
            for s in self.graph.subjects(RDF.type, ptype):
                if isinstance(s, (URIRef, BNode)):
                    policies.add(s)
        
        for pred in [ODRL.permission, ODRL.prohibition, ODRL.duty]:
            for s in self.graph.subjects(pred, None):
                if isinstance(s, URIRef):
                    policies.add(s)
        
        return list(policies)
    
    def _extract_policy(self, policy_uri: Any, result: ParseResult) -> Optional[Policy]:
        """Extract a single policy."""
        policy_type = None
        for ptype in self.graph.objects(policy_uri, RDF.type):
            if str(ptype).startswith(str(ODRL)):
                policy_type = self._local_name(ptype)
                break
        
        inherits_from = None
        for parent in self.graph.objects(policy_uri, ODRL.inheritFrom):
            inherits_from = str(parent)
            break
        
        policy = Policy(
            uid=str(policy_uri),
            policy_type=policy_type,
            inherits_from=inherits_from
        )
        
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
        
        return policy
    
    def _extract_rule(self, rule_node: Any, rule_type: RuleType, result: ParseResult) -> Optional[Rule]:
        """Extract a single rule."""
        self._rule_counter += 1
        rule_uid = f"rule_{self._rule_counter}"
        
        if isinstance(rule_node, URIRef):
            rule_uid = self._local_name(rule_node)
        
        action = None
        for a in self.graph.objects(rule_node, ODRL.action):
            action = self._local_name(a)
            break
        
        target = None
        for t in self.graph.objects(rule_node, ODRL.target):
            target = str(t)
            break
        
        rule = Rule(
            uid=rule_uid,
            rule_type=rule_type,
            action=action,
            target=target
        )
        
        # Extract constraints
        for constraint_node in self.graph.objects(rule_node, ODRL.constraint):
            try:
                constraint_uid = self._extract_constraint(constraint_node, result)
                if constraint_uid:
                    rule.constraint_ids.append(constraint_uid)
            except Exception as e:
                result.warnings.append(f"Failed to extract constraint: {e}")
        
        return rule
    
    def _extract_constraint(self, node: Any, result: ParseResult) -> Optional[str]:
        """
        Extract a constraint (atomic or composite).
        
        FIXED: Now properly handles anonymous blank nodes inside RDF lists.
        """
        # Check if already processed
        if node in self._node_to_uid:
            return self._node_to_uid[node]
        
        # Check for logical operators (composite)
        logical_ops = [
            (ODRL['and'], LogicalOperator.AND),
            (ODRL['or'], LogicalOperator.OR),
            (ODRL.xone, LogicalOperator.XONE),
            (ODRL.andSequence, LogicalOperator.AND_SEQUENCE),
        ]
        
        for pred, op in logical_ops:
            # Get all objects for this predicate
            children = list(self.graph.objects(node, pred))
            if children:
                self._debug(f"Found {op.value} with {len(children)} direct children")
                return self._extract_composite(node, op, children, result)
        
        # Atomic constraint
        return self._extract_atomic(node, result)
    
    def _extract_composite(
        self, 
        node: Any, 
        operator: LogicalOperator,
        children: List,
        result: ParseResult
    ) -> str:
        """
        Extract a composite constraint.
        
        FIXED: Properly extracts anonymous children from RDF lists.
        """
        uid = self._make_uid(node, 'composite')
        self._node_to_uid[node] = uid
        
        self._debug(f"Extracting {operator.value} composite: {uid}")
        
        # Collect all child nodes
        all_child_nodes = []
        
        for child in children:
            if isinstance(child, BNode):
                # Check if it's an RDF list (Collection)
                list_items = self._parse_rdf_list_nodes(child)
                if list_items:
                    self._debug(f"  Found RDF list with {len(list_items)} items")
                    all_child_nodes.extend(list_items)
                else:
                    # Single blank node constraint
                    all_child_nodes.append(child)
            else:
                # URIRef - named constraint
                all_child_nodes.append(child)
        
        self._debug(f"  Total child nodes: {len(all_child_nodes)}")
        
        # Extract each child constraint recursively
        child_uids = []
        for i, child_node in enumerate(all_child_nodes):
            self._debug(f"  Processing child {i+1}: {type(child_node).__name__}")
            try:
                child_uid = self._extract_constraint(child_node, result)
                if child_uid:
                    child_uids.append(child_uid)
                    self._debug(f"    -> {child_uid}")
                else:
                    self._debug(f"    -> FAILED (no UID returned)")
            except Exception as e:
                self._debug(f"    -> ERROR: {e}")
                result.warnings.append(f"Failed to extract child constraint: {e}")
        
        if not child_uids:
            result.warnings.append(f"Composite {uid} has no valid children")
        
        composite = CompositeConstraint(
            uid=uid,
            operator=operator,
            operands=tuple(child_uids)
        )
        
        result.constraints[uid] = composite
        self._debug(f"Created {operator.value} composite with {len(child_uids)} children: {child_uids}")
        
        return uid
    
    def _parse_rdf_list_nodes(self, node: Any) -> List[Any]:
        """
        Parse an RDF list and return the actual nodes (not strings).
        
        This is the KEY FIX - returns BNode/URIRef objects for recursive processing.
        """
        # First try rdflib's Collection helper
        try:
            items = list(Collection(self.graph, node))
            if items:
                self._debug(f"  Parsed RDF Collection: {len(items)} items")
                return items
        except Exception:
            pass
        
        # Manual parsing as fallback
        items = []
        current = node
        visited = set()
        max_iter = 100
        
        for _ in range(max_iter):
            if current is None or current == RDF.nil:
                break
            if current in visited:
                break
            visited.add(current)
            
            # Get rdf:first - THIS RETURNS THE ACTUAL NODE
            first = self.graph.value(current, RDF.first)
            if first is not None:
                items.append(first)  # Keep as BNode/URIRef, don't convert to string!
            
            # Move to rdf:rest
            current = self.graph.value(current, RDF.rest)
        
        return items
    
    def _extract_atomic(self, node: Any, result: ParseResult) -> Optional[str]:
        """Extract an atomic constraint."""
        uid = self._make_uid(node, 'constraint')
        self._node_to_uid[node] = uid
        
        # leftOperand (REQUIRED)
        left_op = self.graph.value(node, ODRL.leftOperand)
        if not left_op:
            self._debug(f"Constraint {node} missing leftOperand")
            result.warnings.append(f"Constraint missing leftOperand: {node}")
            return None
        
        # operator (REQUIRED)
        op_uri = self.graph.value(node, ODRL.operator)
        if not op_uri:
            self._debug(f"Constraint {node} missing operator")
            result.warnings.append(f"Constraint missing operator: {node}")
            return None
        
        try:
            operator = OperatorType.from_string(str(op_uri))
        except ValueError:
            result.warnings.append(f"Unknown operator: {op_uri}")
            return None
        
        # rightOperand
        right_op = self.graph.value(node, ODRL.rightOperand)
        right_op_ref = self.graph.value(node, ODRL.rightOperandReference)
        
        if right_op is None and right_op_ref is None:
            result.warnings.append(f"Constraint missing rightOperand: {node}")
            return None
        
        if right_op_ref:
            right_operand = RightOperand.iri(str(right_op_ref))
        else:
            right_operand = self._parse_right_operand(right_op)
        
        # Metadata
        metadata = self._extract_metadata(node)
        
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
        """Extract ODRL metadata."""
        unit = self.graph.value(node, ODRL.unit)
        datatype = self.graph.value(node, ODRL.dataType)
        unit_of_count = self.graph.value(node, ODRL.unitOfCount)
        
        return ConstraintMetadata(
            unit=str(unit) if unit else None,
            datatype=str(datatype) if datatype else None,
            unit_of_count=str(unit_of_count) if unit_of_count else None
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
            # Could be a list of values
            items = self._parse_rdf_list_values(value)
            if items:
                return RightOperand.literal(items)
            return RightOperand.literal(str(value))
        return RightOperand.literal(str(value))
    
    def _parse_rdf_list_values(self, node: Any) -> List[Any]:
        """Parse RDF list and convert to Python values (for rightOperand lists)."""
        items = []
        current = node
        max_iter = 100
        
        for _ in range(max_iter):
            if current is None or current == RDF.nil:
                break
            
            first = self.graph.value(current, RDF.first)
            if first is not None:
                if isinstance(first, Literal):
                    items.append(first.toPython())
                else:
                    items.append(str(first))
            
            current = self.graph.value(current, RDF.rest)
        
        return items
    
    def _local_name(self, uri: Any) -> str:
        """Extract local name from URI."""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str
    
    def _make_uid(self, node: Any, prefix: str) -> str:
        """Generate a unique ID."""
        if isinstance(node, URIRef):
            return self._local_name(node)
        
        self._constraint_counter += 1
        return f"{prefix}_{self._constraint_counter}"
    
    def _debug(self, message: str):
        """Print debug message."""
        if self.debug:
            print(f"[PARSER] {message}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_ttl_file(filepath: str, debug: bool = False) -> ParseResult:
    """Parse an ODRL TTL file."""
    parser = ODRLParser(debug=debug)
    return parser.parse_file(filepath)


def parse_ttl_string(ttl_string: str, debug: bool = False) -> ParseResult:
    """Parse ODRL from a TTL string."""
    parser = ODRLParser(debug=debug)
    return parser.parse_string(ttl_string)