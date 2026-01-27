# src/parser/rdf_extractor.py
"""
Extract structured ODRL data from RDF graph.
Converts RDF triples to Python objects.

IMPORTANT: Each policy extraction is isolated - constraints are NOT shared
between policies unless explicitly linked via odrl:inheritFrom.
"""
from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, XSD
from typing import Dict, List, Optional, Any, Union, Set
from collections import Counter
import logging

from ..semantics.constraint_types import (
    PolicyRuleType, ConstraintType, OperatorType,
    PolicyRule, AtomicConstraint, CompositeConstraint, Policy,
    NormalizedValue, SemanticInfo, ODRLMetadata,
    get_operand_semantics, debug_print, is_debug_mode
)

logger = logging.getLogger(__name__)

# Namespaces
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


class RDFExtractorError(Exception):
    """Custom exception for RDF extraction failures."""
    pass


class RDFExtractor:
    """
    Extract ODRL structures from RDF graph.
    
    Responsibilities:
    1. Identify policy rules (permissions, prohibitions, duties)
    2. Extract constraints and their relationships
    3. Parse operands, operators, values with full metadata
    4. Build constraint tree (atomic + composite)
    5. Extract policy inheritance relationships
    
    IMPORTANT: Each policy extraction creates ISOLATED constraints.
    Constraints are NOT shared between policies. This ensures:
    - Parent policy has only its own constraints
    - Child policy has only its own constraints
    - Inheritance checking compares them correctly
    """
    
    def __init__(self, graph: Graph, debug: bool = False):
        """
        Initialize extractor.
        
        Args:
            graph: RDFLib Graph containing ODRL policy
            debug: Enable debug output (--dev mode)
        """
        self.graph = graph
        self.debug = debug
        
        # Per-policy constraint storage
        self._policy_constraints: Dict[str, Dict[str, Union[AtomicConstraint, CompositeConstraint]]] = {}
        
        # Current extraction context (reset for each policy)
        self._current_policy_uri: Optional[str] = None
        self._current_constraints: Dict[str, Union[AtomicConstraint, CompositeConstraint]] = {}
        
        if len(graph) == 0:
            logger.warning("RDFExtractor initialized with an empty graph.")
            self._debug("WARNING: Empty graph provided")
    
    # Backwards compatibility property
    @property
    def constraints(self) -> Dict[str, Union[AtomicConstraint, CompositeConstraint]]:
        """Return current policy's constraints"""
        return self._current_constraints
    
    @constraints.setter
    def constraints(self, value):
        """Set constraints (for backwards compatibility)"""
        self._current_constraints = value
    
    def get_policy_constraints(self, policy_uri: str) -> Dict[str, Union[AtomicConstraint, CompositeConstraint]]:
        """Get constraints for a specific policy."""
        return self._policy_constraints.get(policy_uri, {})
    
    def get_all_policies(self) -> List[str]:
        """Get list of all extracted policy URIs."""
        return list(self._policy_constraints.keys())
    
    # ==========================================================================
    # POLICY EXTRACTION
    # ==========================================================================
    
    def extract_policy(self, policy_uri: URIRef) -> Policy:
        """
        Extract complete policy structure.
        
        IMPORTANT: Each call creates an ISOLATED constraint set for this policy.
        
        Args:
            policy_uri: URI of the policy to extract
            
        Returns:
            Policy object with rules, constraints, and metadata
            
        Raises:
            RDFExtractorError: If policy not found or empty.
        """
        policy_uri_str = str(policy_uri)
        policy_name = self._uri_to_string(policy_uri)
        self._debug(f"Starting extraction: {policy_name}")
        
        # CRITICAL: Reset current constraints for this policy extraction
        self._current_policy_uri = policy_uri_str
        self._current_constraints = {}
        
        # 1. Validation
        if (policy_uri, None, None) not in self.graph:
            raise RDFExtractorError(
                f"Policy URI '{policy_uri}' not found in the provided graph."
            )
        
        # 2. Extract policy-level metadata (including inheritFrom)
        policy_metadata = self._extract_policy_metadata(policy_uri)
        
        # 3. Extract Rules (this populates self._current_constraints)
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
        
        # Obligations (alias for duty in some profiles)
        for oblig_uri in self.graph.objects(policy_uri, ODRL.obligation):
            rules.append(self._extract_rule(oblig_uri, PolicyRuleType.OBLIGATION))
            rule_counts["Obligation"] += 1
        
        # 4. Empty Policy Check
        if not rules:
            error_msg = (
                f"Policy '{policy_name}' exists but contains no Rules "
                f"(Permissions, Prohibitions, or Duties)."
            )
            logger.error(error_msg)
            raise RDFExtractorError(error_msg)
        
        # 5. Store constraints for this policy
        self._policy_constraints[policy_uri_str] = self._current_constraints.copy()
        
        # 6. Debug Summary
        self._debug(f"Extraction complete for '{policy_name}'", {
            'rules': len(rules),
            'permissions': rule_counts['Permission'],
            'prohibitions': rule_counts['Prohibition'],
            'duties': rule_counts['Duty'],
            'constraints': len(self._current_constraints),
            'inheritFrom': policy_metadata.get('inheritFrom')
        })
        
        # 7. Build Policy object
        return Policy(
            id=str(policy_uri),
            rules=rules,
            constraints=self._current_constraints.copy(),  # Copy to isolate
            inherits_from=policy_metadata.get('inheritFrom'),
            odrl_metadata=ODRLMetadata(),
            metadata={
                'source': 'rdf',
                'graph_size': len(self.graph),
                'policy_type': policy_metadata.get('type'),
                'profile': policy_metadata.get('profile'),
                'conflict': policy_metadata.get('conflict'),
            }
        )
    
    def _extract_policy_metadata(self, policy_uri: URIRef) -> Dict[str, Any]:
        """
        Extract policy-level metadata.
        
        Returns:
            Dict with type, profile, inheritFrom, conflict
        """
        metadata = {
            'type': None,
            'profile': None,
            'inheritFrom': None,
            'conflict': None,
        }
        
        # Get policy type
        for policy_type in self.graph.objects(policy_uri, RDF.type):
            type_str = str(policy_type)
            if str(ODRL) in type_str:
                metadata['type'] = self._uri_to_string(policy_type)
                break
        
        # Get profile
        for profile in self.graph.objects(policy_uri, ODRL.profile):
            metadata['profile'] = str(profile)
            break
        
        # Get inheritFrom (IMPORTANT for inheritance checking)
        for parent in self.graph.objects(policy_uri, ODRL.inheritFrom):
            metadata['inheritFrom'] = str(parent)
            self._debug(f"Found inheritFrom: {parent}")
            break
        
        # Get conflict resolution strategy
        for conflict in self.graph.objects(policy_uri, ODRL.conflict):
            metadata['conflict'] = self._uri_to_string(conflict)
            break
        
        return metadata
    
    # ==========================================================================
    # RULE EXTRACTION
    # ==========================================================================
    
    def _extract_rule(self, rule_uri: URIRef, rule_type: PolicyRuleType) -> PolicyRule:
        """Extract a single rule with full details"""
        
        # Get action
        action_uri = self.graph.value(rule_uri, ODRL.action)
        action = self._uri_to_string(action_uri) if action_uri else "unknown"
        
        self._debug(f"Processing {rule_type.value}: action='{action}'")
        
        # Get target (asset)
        target_uri = self.graph.value(rule_uri, ODRL.target)
        target = str(target_uri) if target_uri else None
        
        # Get assigner
        assigner_uri = self.graph.value(rule_uri, ODRL.assigner)
        assigner = str(assigner_uri) if assigner_uri else None
        
        # Get assignee
        assignee_uri = self.graph.value(rule_uri, ODRL.assignee)
        assignee = str(assignee_uri) if assignee_uri else None
        
        # Get constraint
        constraint_uri = self.graph.value(rule_uri, ODRL.constraint)
        constraint_id = None
        
        if constraint_uri:
            try:
                self._extract_constraint(constraint_uri)
                constraint_id = str(constraint_uri)
            except Exception as e:
                logger.error(f"Failed to parse constraint for rule {rule_uri}: {e}")
                self._debug(f"Constraint extraction failed: {e}")
        
        return PolicyRule(
            id=str(rule_uri),
            rule_type=rule_type,
            action=action,
            constraint_id=constraint_id,
            target=target,
            assigner=assigner,
            assignee=assignee,
            odrl_metadata=ODRLMetadata(),
            metadata={
                'action_uri': str(action_uri) if action_uri else None,
                'target_uri': str(target_uri) if target_uri else None,
            }
        )
    
    # ==========================================================================
    # CONSTRAINT EXTRACTION
    # ==========================================================================
    
    def _extract_constraint(self, constraint_uri: Union[URIRef, BNode]) -> str:
        """
        Extract constraint recursively.
        
        Handles:
        - Atomic constraints
        - Composite constraints (AND, OR, XONE, ANDSEQUENCE)
        
        Returns:
            Constraint ID
        """
        constraint_id = str(constraint_uri)
        
        # Skip if already extracted IN THIS POLICY CONTEXT
        if constraint_id in self._current_constraints:
            return constraint_id
        
        # Check for logical operators (composite constraints)
        logical_operators = [
            ('and', ConstraintType.AND),
            ('or', ConstraintType.OR),
            ('xone', ConstraintType.XONE),
            ('andSequence', ConstraintType.ANDSEQUENCE),
        ]
        
        for op_name, c_type in logical_operators:
            children = list(self.graph.objects(constraint_uri, ODRL[op_name]))
            if children:
                self._extract_composite(constraint_id, c_type, children)
                return constraint_id
        
        # Atomic constraint
        self._extract_atomic_constraint(constraint_uri, constraint_id)
        return constraint_id
    
    def _extract_composite(
        self, 
        constraint_id: str, 
        c_type: ConstraintType, 
        children_uris: List[Union[URIRef, BNode]]
    ):
        """Extract composite constraint (AND/OR/XONE/ANDSEQUENCE)"""
        
        self._debug(f"Composite constraint ({c_type.value}) with {len(children_uris)} children")
        
        # Recursively extract children
        child_ids = [self._extract_constraint(c) for c in children_uris]
        
        self._current_constraints[constraint_id] = CompositeConstraint(
            id=constraint_id,
            constraint_type=c_type,
            children=child_ids,
            odrl_metadata=ODRLMetadata(),
            metadata={
                'child_count': len(child_ids),
                'is_sequential': c_type == ConstraintType.ANDSEQUENCE,
            }
        )
    
    def _extract_atomic_constraint(
        self, 
        constraint_uri: Union[URIRef, BNode], 
        constraint_id: str
    ):
        """
        Extract atomic constraint with full ODRL metadata.
        """
        
        # leftOperand (REQUIRED)
        left_operand_uri = self.graph.value(constraint_uri, ODRL.leftOperand)
        if not left_operand_uri:
            msg = f"Invalid Constraint {constraint_id}: Missing 'leftOperand'"
            logger.error(msg)
            raise ValueError(msg)
        
        left_operand = self._uri_to_string(left_operand_uri)
        
        # operator (REQUIRED)
        operator_uri = self.graph.value(constraint_uri, ODRL.operator)
        if not operator_uri:
            msg = f"Invalid Constraint {constraint_id}: Missing 'operator'"
            logger.error(msg)
            raise ValueError(msg)
        
        operator_str = self._uri_to_string(operator_uri)
        operator = self._parse_operator(operator_str)
        
        # rightOperand
        right_value, right_datatype = self._extract_right_value(constraint_uri)
        
        if right_value is None:
            logger.warning(f"Constraint {constraint_id} has no rightOperand.")
        
        # ODRL Metadata
        unit_uri = self.graph.value(constraint_uri, ODRL.unit)
        unit = self._uri_to_string(unit_uri) if unit_uri else None
        
        unit_of_count_uri = self.graph.value(constraint_uri, ODRL.unitOfCount)
        unit_of_count = self._uri_to_string(unit_of_count_uri) if unit_of_count_uri else None
        
        status_value = self.graph.value(constraint_uri, ODRL.status)
        status = self._literal_to_python(status_value) if status_value else None
        
        datatype_uri = self.graph.value(constraint_uri, ODRL.dataType)
        datatype = str(datatype_uri) if datatype_uri else right_datatype
        
        right_ref_uri = self.graph.value(constraint_uri, ODRL.rightOperandReference)
        right_operand_ref = str(right_ref_uri) if right_ref_uri else None
        
        # Get semantic info
        semantics = get_operand_semantics(left_operand)
        
        # Create ODRL metadata
        odrl_metadata = ODRLMetadata(
            unit=unit,
            unit_of_count=unit_of_count,
            status=status,
            datatype=datatype,
            operator_reference=right_operand_ref,
        )
        
        # Create normalized value
        normalized_value = NormalizedValue(
            canonical_value=right_value,
            original_value=right_value,
            original_unit=unit,
            canonical_unit=semantics.base_unit if semantics else 'unknown',
            metadata={
                'datatype': datatype,
                'needs_normalization': True,
            }
        )
        
        self._debug(f"Atomic constraint: {left_operand} {operator_str} {right_value}", {
            'unit': unit,
            'unitOfCount': unit_of_count,
            'status': status,
            'dataType': datatype,
        })
        
        self._current_constraints[constraint_id] = AtomicConstraint(
            id=constraint_id,
            left_operand=left_operand,
            operator=operator,
            right_value=normalized_value,
            semantics=semantics,
            odrl_metadata=odrl_metadata,
            metadata={
                'original_operator': operator_str,
                'left_operand_uri': str(left_operand_uri),
                'operator_uri': str(operator_uri),
            }
        )
    
    def _extract_right_value(
        self, 
        constraint_uri: Union[URIRef, BNode]
    ) -> tuple[Any, Optional[str]]:
        """Extract right operand value and its datatype."""
        datatype = None
        
        right_operand = self.graph.value(constraint_uri, ODRL.rightOperand)
        if right_operand:
            if isinstance(right_operand, Literal) and right_operand.datatype:
                datatype = str(right_operand.datatype)
            return self._literal_to_python(right_operand), datatype
        
        right_refs = list(self.graph.objects(constraint_uri, ODRL.rightOperandReference))
        if right_refs:
            values = [self._literal_to_python(v) for v in right_refs]
            return values if len(values) > 1 else values[0], None
        
        for right_list in self.graph.objects(constraint_uri, ODRL.rightOperand):
            if isinstance(right_list, BNode):
                items = self._extract_rdf_list(right_list)
                if items:
                    return items, None
        
        return None, None
    
    def _extract_rdf_list(self, node: BNode) -> Optional[List]:
        """Extract items from an RDF list"""
        items = []
        current = node
        RDF_NS = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        
        max_iterations = 100
        iteration = 0
        
        while current and current != RDF_NS.nil and iteration < max_iterations:
            iteration += 1
            
            first = self.graph.value(current, RDF_NS.first)
            if first is not None:
                items.append(self._literal_to_python(first))
            
            rest = self.graph.value(current, RDF_NS.rest)
            if rest is None or rest == RDF_NS.nil:
                break
            
            current = rest
        
        return items if items else None
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def _uri_to_string(self, uri: Union[URIRef, Literal, BNode, None]) -> str:
        """Convert URI to short string (local name)"""
        if uri is None:
            return ""
        if isinstance(uri, Literal):
            return str(uri)
        if isinstance(uri, BNode):
            return str(uri)
        
        uri_str = str(uri)
        
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        
        return uri_str
    
    def _literal_to_python(self, literal: Union[Literal, URIRef, BNode, None]) -> Any:
        """Convert RDF literal to Python value"""
        if literal is None:
            return None
        
        if isinstance(literal, URIRef):
            return str(literal)
        
        if isinstance(literal, BNode):
            items = self._extract_rdf_list(literal)
            if items:
                return items
            return str(literal)
        
        if isinstance(literal, Literal):
            if literal.datatype:
                datatype_str = str(literal.datatype).lower()
                
                if 'integer' in datatype_str or 'int' in datatype_str:
                    try:
                        return int(literal)
                    except (ValueError, TypeError):
                        pass
                elif 'decimal' in datatype_str or 'float' in datatype_str or 'double' in datatype_str:
                    try:
                        return float(literal)
                    except (ValueError, TypeError):
                        pass
                elif 'boolean' in datatype_str:
                    return str(literal).lower() in ('true', '1', 'yes')
                elif 'date' in datatype_str:
                    return str(literal)
            
            val_str = str(literal)
            try:
                if '.' in val_str:
                    return float(val_str)
                return int(val_str)
            except ValueError:
                return val_str
        
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
            'isanyof': OperatorType.IS_ANY_OF,
            'isAllOf': OperatorType.IS_ALL_OF,
            'isallof': OperatorType.IS_ALL_OF,
            'isNoneOf': OperatorType.IS_NONE_OF,
            'isnoneof': OperatorType.IS_NONE_OF,
            'hasPart': OperatorType.HAS_PART,
            'haspart': OperatorType.HAS_PART,
            'isPartOf': OperatorType.IS_PART_OF,
            'ispartof': OperatorType.IS_PART_OF,
            'isA': OperatorType.IS_A,
            'isa': OperatorType.IS_A,
        }
        
        op = operator_map.get(operator_str)
        if not op:
            logger.warning(f"Unknown operator '{operator_str}', defaulting to EQ")
            self._debug(f"Unknown operator: {operator_str}")
            return OperatorType.EQ
        return op
    
    # ==========================================================================
    # DEBUG METHODS
    # ==========================================================================
    
    def _debug(self, message: str, data: Any = None):
        """Print debug message if debug mode enabled"""
        if self.debug:
            debug_print("EXTRACTOR", message, data)
            logger.debug(f"[EXTRACTOR] {message}")
    
    def print_extraction_summary(self):
        """Print a summary of extracted constraints"""
        if not self.debug:
            return
        
        print("\n" + "=" * 70)
        print("EXTRACTION SUMMARY")
        print("=" * 70)
        
        for policy_uri, constraints in self._policy_constraints.items():
            policy_name = policy_uri.split('/')[-1] if '/' in policy_uri else policy_uri
            atomic_count = sum(1 for c in constraints.values() if isinstance(c, AtomicConstraint))
            composite_count = len(constraints) - atomic_count
            
            print(f"\n  Policy: {policy_name}")
            print(f"    Total constraints: {len(constraints)}")
            print(f"    Atomic: {atomic_count}")
            print(f"    Composite: {composite_count}")
        
        print("=" * 70 + "\n")