# src/parser/rdf_extractor.py
"""
Extract structured ODRL data from RDF graph.
Converts RDF triples to Python objects.
"""

from rdflib import Graph, URIRef, Literal, Namespace
from typing import Dict, List, Optional, Any, Union
from collections import Counter
import logging

from ..semantics.constraint_types import (
    PolicyRuleType, ConstraintType, OperatorType,
    PolicyRule, AtomicConstraint, CompositeConstraint, Policy
)

logger = logging.getLogger(__name__)

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

class RDFExtractorError(Exception):
    """Custom exception for RDF extraction failures."""
    pass

class RDFExtractor:
    """
    Extract ODRL structures from RDF graph.
    
    Responsibilities:
    1. Identify policy rules (permissions, prohibitions, duties)
    2. Extract constraints and their relationships
    3. Parse operands, operators, values, units
    4. Build constraint tree (atomic + composite)
    """
    
    def __init__(self, graph: Graph, debug: bool = False):
        self.graph = graph
        self.debug = debug
        self.constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]] = {}
        
        if len(graph) == 0:
            logger.warning("RDFExtractor initialized with an empty graph.")
    
    def extract_policy(self, policy_uri: URIRef) -> Policy:
        """
        Extract complete policy structure.
        
        Args:
            policy_uri: URI of the policy to extract
            
        Returns:
            Policy object with rules and constraints
            
        Raises:
            RDFExtractorError: If policy not found or empty.
        """
        policy_name = self._uri_to_string(policy_uri)
        if self.debug:
            logger.info(f"--- Starting Extraction: {policy_name} ---")

        # 1. Validation: Check if URI exists as a subject in the graph
        if not (policy_uri, None, None) in self.graph:
            raise RDFExtractorError(f"Policy URI '{policy_uri}' not found in the provided graph.")

        # 2. Extract Rules
        rules = []
        rule_counts = Counter()
        
        # Permissions
        for perm_uri in self.graph.objects(policy_uri, ODRL.permission):
            rules.append(self._extract_rule(perm_uri, PolicyRuleType.PERMISSION))
            rule_counts["Permission"] += 1
        
        # Prohibitions
        for prohib_uri in self.graph.objects(policy_uri, ODRL.prohibition):
            rules.append(self._extract_rule(prohib_uri, PolicyRuleType.PROHIBITION))
            rule_counts["Prohibition"] += 1
        
        # Duties
        for duty_uri in self.graph.objects(policy_uri, ODRL.duty):
            rules.append(self._extract_rule(duty_uri, PolicyRuleType.DUTY))
            rule_counts["Duty"] += 1
        
        # 3. Empty Policy Check
        if not rules:
            error_msg = f"Policy '{policy_name}' exists but contains no Rules (Permissions, Prohibitions, or Duties)."
            logger.error(error_msg)
            raise RDFExtractorError(error_msg)

        # 4. Debug Summary
        if self.debug:
            summary = (
                f"Extraction Complete for '{policy_name}':\n"
                f"    - Rules Found: {len(rules)} "
                f"(Perm: {rule_counts['Permission']}, Prohib: {rule_counts['Prohibition']}, Duty: {rule_counts['Duty']})\n"
                f"    - Unique Constraints: {len(self.constraints)}"
            )
            logger.info(summary)
        
        return Policy(
            id=str(policy_uri),
            rules=rules,
            constraints=self.constraints,
            metadata={'source': 'rdf', 'graph_size': len(self.graph)}
        )
    
    def _extract_rule(self, rule_uri: URIRef, rule_type: PolicyRuleType) -> PolicyRule:
        """Extract a single rule"""
        # Get action
        action_uri = self.graph.value(rule_uri, ODRL.action)
        action = self._uri_to_string(action_uri) if action_uri else "unknown"
        
        if self.debug:
            logger.debug(f"  > Processing {rule_type.name}: Action='{action}' (ID: {self._uri_to_string(rule_uri)})")

        # Get constraint
        constraint_uri = self.graph.value(rule_uri, ODRL.constraint)
        constraint_id = None
        
        if constraint_uri:
            try:
                self._extract_constraint(constraint_uri)
                constraint_id = str(constraint_uri)
            except Exception as e:
                logger.error(f"Failed to parse constraint for rule {rule_uri}: {e}")
                # We do not stop the whole policy, but this rule might be invalid. 
                # Depending on strictness, we could raise here.
        
        return PolicyRule(
            id=str(rule_uri),
            rule_type=rule_type,
            action=action,
            constraint_id=constraint_id,
            metadata={'action_uri': str(action_uri) if action_uri else None}
        )
    
    def _extract_constraint(self, constraint_uri: URIRef) -> str:
        """
        Extract constraint recursively.
        Returns: Constraint ID
        """
        constraint_id = str(constraint_uri)
        
        # Skip if already extracted
        if constraint_id in self.constraints:
            return constraint_id
        
        # Check if composite (has AND/OR/XONE)
        and_children = list(self.graph.objects(constraint_uri, ODRL['and']))
        or_children = list(self.graph.objects(constraint_uri, ODRL['or']))
        xone_children = list(self.graph.objects(constraint_uri, ODRL.xone))
        
        if and_children:
            self._extract_composite(constraint_id, ConstraintType.AND, and_children)
        elif or_children:
            self._extract_composite(constraint_id, ConstraintType.OR, or_children)
        elif xone_children:
            self._extract_composite(constraint_id, ConstraintType.XONE, xone_children)
        else:
            # Atomic constraint
            self._extract_atomic_constraint(constraint_uri, constraint_id)
        
        return constraint_id

    def _extract_composite(self, constraint_id: str, c_type: ConstraintType, children_uris: List[URIRef]):
        """Helper to extract composite constraints"""
        if self.debug:
            logger.debug(f"    + Composite Constraint ({c_type.name}) with {len(children_uris)} children")
            
        child_ids = [self._extract_constraint(c) for c in children_uris]
        
        self.constraints[constraint_id] = CompositeConstraint(
            id=constraint_id,
            constraint_type=c_type,
            children=child_ids
        )
    
    def _extract_atomic_constraint(self, constraint_uri: URIRef, constraint_id: str):
        """Extract atomic constraint components"""
        # Get leftOperand
        left_operand_uri = self.graph.value(constraint_uri, ODRL.leftOperand)
        if not left_operand_uri:
            msg = f"Invalid Constraint {constraint_id}: Missing 'leftOperand'"
            logger.error(msg)
            raise ValueError(msg)
        
        left_operand = self._uri_to_string(left_operand_uri)
        
        # Get operator
        operator_uri = self.graph.value(constraint_uri, ODRL.operator)
        if not operator_uri:
            msg = f"Invalid Constraint {constraint_id}: Missing 'operator'"
            logger.error(msg)
            raise ValueError(msg)
        
        operator_str = self._uri_to_string(operator_uri)
        operator = self._parse_operator(operator_str)
        
        # Get rightOperand (can be value, value set, or interval)
        right_value = self._extract_right_value(constraint_uri)
        if right_value is None:
             # Some ODRL profiles allow missing rightOperand for certain operators, but usually it's an error
             logger.warning(f"Constraint {constraint_id} has no rightOperand. Assuming None.")

        # Get unit (optional)
        unit_uri = self.graph.value(constraint_uri, ODRL.unit)
        unit = self._uri_to_string(unit_uri) if unit_uri else None
        
        # Get datatype (optional)
        datatype_uri = self.graph.value(constraint_uri, ODRL.dataType)
        datatype = self._uri_to_string(datatype_uri) if datatype_uri else None
        
        # Semantics
        from ..semantics.constraint_types import get_operand_semantics, NormalizedValue
        semantics = get_operand_semantics(left_operand)
        
        # Create normalized value placeholder
        normalized_value = NormalizedValue(
            canonical_value=right_value,
            original_value=right_value,
            original_unit=unit,
            canonical_unit='pending'
        )
        
        self.constraints[constraint_id] = AtomicConstraint(
            id=constraint_id,
            left_operand=left_operand,
            operator=operator,
            right_value=normalized_value,
            semantics=semantics,
            metadata={
                'unit': unit,
                'datatype': datatype,
                'needs_normalization': True
            }
        )

    def _extract_right_value(self, constraint_uri: URIRef) -> Any:
        """Extract right operand value"""
        # Try rightOperand (single value)
        right_operand = self.graph.value(constraint_uri, ODRL.rightOperand)
        if right_operand:
            return self._literal_to_python(right_operand)
        
        # Try rightOperandReference (set of values)
        right_ref = list(self.graph.objects(constraint_uri, ODRL.rightOperandReference))
        if right_ref:
            return [self._literal_to_python(v) for v in right_ref]
        
        return None
    
    def _uri_to_string(self, uri: Union[URIRef, Literal]) -> str:
        """Convert URI to short string (last component)"""
        if not uri:
            return ""
        if isinstance(uri, Literal):
            return str(uri)
        
        uri_str = str(uri)
        
        # Extract last component after # or /
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        
        return uri_str
    
    def _literal_to_python(self, literal: Union[Literal, URIRef]) -> Any:
        """Convert RDF literal to Python value"""
        if isinstance(literal, URIRef):
            return str(literal)
        
        if isinstance(literal, Literal):
            # Try to infer Python type from XSD datatype
            if literal.datatype:
                datatype_str = str(literal.datatype)
                
                if 'integer' in datatype_str or 'int' in datatype_str:
                    return int(literal)
                elif 'decimal' in datatype_str or 'float' in datatype_str or 'double' in datatype_str:
                    return float(literal)
                elif 'boolean' in datatype_str:
                    return bool(literal)
            
            # Try parsing as number
            try:
                return int(literal)
            except ValueError:
                try:
                    return float(literal)
                except ValueError:
                    return str(literal)
        
        return str(literal)
    
    def _parse_operator(self, operator_str: str) -> OperatorType:
        """Parse operator string to enum"""
        operator_map = {
            'eq': OperatorType.EQ,
            'neq': OperatorType.NEQ,
            'lt': OperatorType.LT,
            'lteq': OperatorType.LTEQ,
            'gt': OperatorType.GT,
            'gteq': OperatorType.GTEQ,
            'isAnyOf': OperatorType.IS_ANY_OF,
            'isAllOf': OperatorType.IS_ALL_OF,
            'isNoneOf': OperatorType.IS_NONE_OF,
            'hasPart': OperatorType.HAS_PART,
            'isPartOf': OperatorType.IS_PART_OF,
            'isA': OperatorType.IS_A,
        }
        
        op = operator_map.get(operator_str)
        if not op:
            logger.warning(f"Unknown operator '{operator_str}', defaulting to EQ")
            return OperatorType.EQ
        return op