# src/parser/ttl_parser.py
"""
ODRL-SA TTL Parser (Enhanced)

Parses ODRL policies from Turtle (TTL) files and extracts:
- Policy structure (permissions, prohibitions, duties)
- Constraints (atomic and composite)
- Full ODRL metadata (unit, unitOfCount, status, dataType)
- Inheritance relationships (odrl:inheritFrom)

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

from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import RDF, RDFS, XSD

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


@dataclass
class ParseResult:
    """Complete result of parsing an ODRL TTL file."""
    
    # Policies
    policies: List[Policy] = field(default_factory=list)
    
    # All constraints (keyed by UID)
    constraints: Dict[str, Constraint] = field(default_factory=dict)
    
    # Parsing errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
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


# =============================================================================
# ODRL PARSER
# =============================================================================

class ODRLParser:
    """
    Parser for ODRL Turtle files.
    
    Features:
    - Full policy structure extraction
    - Atomic and composite constraints
    - Complete ODRL metadata
    - Inheritance relationships
    - Debug mode with detailed output
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
        self._processed_nodes: Set = set()
    
    def parse_file(self, filepath: str) -> ParseResult:
        """
        Parse an ODRL TTL file.
        
        Args:
            filepath: Path to .ttl file
            
        Returns:
            ParseResult with policies and constraints
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
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
        
        self.graph = Graph()
        self.graph.parse(filepath, format=rdf_format)
        
        self._debug(f"Loaded {len(self.graph)} triples")
        
        return self._extract_all()
    
    def parse_string(self, ttl_string: str, format: str = 'turtle') -> ParseResult:
        """
        Parse ODRL from a string.
        
        Args:
            ttl_string: TTL content
            format: RDF format ('turtle', 'xml', 'json-ld')
            
        Returns:
            ParseResult with policies and constraints
        """
        self.graph = Graph()
        self.graph.parse(data=ttl_string, format=format)
        
        self._debug(f"Parsed {len(self.graph)} triples from string")
        
        return self._extract_all()
    
    # =========================================================================
    # EXTRACTION
    # =========================================================================
    
    def _extract_all(self) -> ParseResult:
        """Extract all ODRL structures from the graph."""
        self._constraint_counter = 0
        self._processed_nodes = set()
        
        result = ParseResult()
        
        # Find all policies
        policy_uris = self._find_policies()
        self._debug(f"Found {len(policy_uris)} policies")
        
        # Extract each policy
        for policy_uri in policy_uris:
            try:
                policy = self._extract_policy(policy_uri, result)
                result.policies.append(policy)
            except Exception as e:
                error_msg = f"Failed to extract policy {policy_uri}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
        
        return result
    
    def _find_policies(self) -> List[URIRef]:
        """Find all policy URIs in the graph."""
        policies = set()
        
        # ODRL policy types
        policy_types = [
            ODRL.Policy, ODRL.Set, ODRL.Offer, 
            ODRL.Agreement, ODRL.Request, ODRL.Privacy
        ]
        
        for ptype in policy_types:
            for s in self.graph.subjects(RDF.type, ptype):
                policies.add(s)
        
        # Also check for subjects with rules (implicit policies)
        for pred in [ODRL.permission, ODRL.prohibition, ODRL.duty, ODRL.obligation]:
            for s in self.graph.subjects(pred, None):
                if isinstance(s, URIRef):
                    policies.add(s)
        
        return list(policies)
    
    def _extract_policy(self, policy_uri: URIRef, result: ParseResult) -> Policy:
        """Extract a single policy."""
        self._debug(f"Extracting policy: {policy_uri}")
        
        # Get policy type
        policy_type = None
        for ptype in self.graph.objects(policy_uri, RDF.type):
            if str(ptype).startswith(str(ODRL)):
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
                rule = self._extract_rule(rule_node, rule_type, result)
                policy.rules.append(rule)
        
        self._debug(f"Extracted policy with {len(policy.rules)} rules")
        
        return policy
    
    def _extract_rule(
        self, 
        rule_node: Any, 
        rule_type: RuleType, 
        result: ParseResult
    ) -> Rule:
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
        
        # Get assigner
        assigner = None
        for a in self.graph.objects(rule_node, ODRL.assigner):
            assigner = str(a)
            break
        
        # Get assignee
        assignee = None
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
        
        # Extract constraints
        for constraint_node in self.graph.objects(rule_node, ODRL.constraint):
            constraint_uid = self._extract_constraint(constraint_node, result)
            if constraint_uid:
                rule.constraint_ids.append(constraint_uid)
        
        # Also check refinements
        for constraint_node in self.graph.objects(rule_node, ODRL.refinement):
            constraint_uid = self._extract_constraint(constraint_node, result)
            if constraint_uid:
                rule.constraint_ids.append(constraint_uid)
        
        self._debug(f"Extracted {rule_type.value} with {len(rule.constraint_ids)} constraints")
        
        return rule
    
    def _extract_constraint(
        self, 
        node: Any, 
        result: ParseResult
    ) -> Optional[str]:
        """
        Extract a constraint (atomic or composite).
        
        Returns the constraint UID.
        """
        if node in self._processed_nodes:
            # Already processed - find existing UID
            for uid, c in result.constraints.items():
                if hasattr(c, '_node') and c._node == node:
                    return uid
            return self._make_uid(node, 'constraint')
        
        self._processed_nodes.add(node)
        
        # Check for logical operators (composite)
        logical_ops = [
            (ODRL['and'], LogicalOperator.AND),
            (ODRL['or'], LogicalOperator.OR),
            (ODRL.xone, LogicalOperator.XONE),
            (ODRL.andSequence, LogicalOperator.AND_SEQUENCE),
        ]
        
        for pred, op in logical_ops:
            children = list(self.graph.objects(node, pred))
            if children:
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
        """Extract a composite constraint."""
        uid = self._make_uid(node, 'composite')
        
        # Parse RDF list if needed
        all_children = []
        for child in children:
            if isinstance(child, BNode):
                # Could be RDF list
                list_items = self._parse_rdf_list(child)
                if list_items:
                    all_children.extend(list_items)
                else:
                    all_children.append(child)
            else:
                all_children.append(child)
        
        # Extract each child
        child_uids = []
        for child in all_children:
            child_uid = self._extract_constraint(child, result)
            if child_uid:
                child_uids.append(child_uid)
        
        composite = CompositeConstraint(
            uid=uid,
            operator=operator,
            operands=tuple(child_uids)
        )
        
        result.constraints[uid] = composite
        self._debug(f"Extracted {operator.value} composite with {len(child_uids)} children")
        
        return uid
    
    def _extract_atomic(self, node: Any, result: ParseResult) -> Optional[str]:
        """Extract an atomic constraint."""
        uid = self._make_uid(node, 'constraint')
        
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
            self._debug(f"Unknown operator: {op_uri}")
            result.warnings.append(f"Unknown operator: {op_uri}")
            return None
        
        # rightOperand
        right_op = self.graph.value(node, ODRL.rightOperand)
        right_op_ref = self.graph.value(node, ODRL.rightOperandReference)
        
        if right_op is None and right_op_ref is None:
            # Check for policyUsage
            if (node, ODRL.rightOperand, ODRL.policyUsage) in self.graph:
                right_operand = RightOperand.policy_usage()
            else:
                self._debug(f"Constraint {node} missing rightOperand")
                result.warnings.append(f"Constraint missing rightOperand: {node}")
                return None
        elif right_op_ref:
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
        
        return ConstraintMetadata(
            unit=str(unit) if unit else None,
            datatype=str(datatype) if datatype else None,
            right_operand_reference=str(right_op_ref) if right_op_ref else None,
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
            # Could be a list
            items = self._parse_rdf_list(value)
            if items:
                return RightOperand.literal(items)
            return RightOperand.literal(str(value))
        
        return RightOperand.literal(str(value))
    
    def _parse_rdf_list(self, node: Any) -> List[Any]:
        """Parse an RDF list."""
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
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
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
    
    def _debug(self, message: str, data: Any = None):
        """Print debug message."""
        if self.debug:
            print(f"[PARSER] {message}")
            if data:
                print(f"         {data}")
            logger.debug(f"[PARSER] {message}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_ttl_file(filepath: str, debug: bool = False) -> ParseResult:
    """
    Parse an ODRL TTL file.
    
    Example:
        result = parse_ttl_file("policy.ttl")
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
    
    Example:
        result = parse_ttl_string(ttl_content)
    """
    parser = ODRLParser(debug=debug)
    return parser.parse_string(ttl_string)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    test_ttl = '''
    @prefix odrl: <http://www.w3.org/ns/odrl/2/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix ex: <http://example.org/> .
    
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
    
    ex:policy2 a odrl:Set ;
        odrl:inheritFrom ex:policy1 ;
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
    '''
    
    print("=" * 60)
    print("ODRL Parser Test (Enhanced)")
    print("=" * 60)
    
    result = parse_ttl_string(test_ttl, debug=True)
    
    print(f"\nPolicies: {len(result.policies)}")
    for policy in result.policies:
        print(f"\n  Policy: {policy.uid}")
        print(f"    Type: {policy.policy_type}")
        print(f"    Inherits: {policy.inherits_from}")
        print(f"    Rules: {len(policy.rules)}")
        for rule in policy.rules:
            print(f"      - {rule}")
    
    print(f"\nAtomic Constraints: {len(result.get_atomic_constraints())}")
    for c in result.get_atomic_constraints():
        print(f"  - {c}")
    
    print(f"\nComposite Constraints: {len(result.get_composite_constraints())}")
    for c in result.get_composite_constraints():
        print(f"  - {c}")
    
    if result.errors:
        print(f"\nErrors: {result.errors}")
    if result.warnings:
        print(f"\nWarnings: {result.warnings}")
    
    print("\n" + "=" * 60)