# src/reasoner/inheritance_resolver.py
"""
ODRL Inheritance Resolver

Resolves odrl:inheritFrom relationships and merges constraints
for complete policy analysis.

ODRL Inheritance Semantics (ODRL 2.2 §2.6):
  - A Policy may inherit from another Policy using odrl:inheritFrom
  - The child policy inherits ALL rules from the parent
  - Child can add NEW rules (permissions, prohibitions, duties)
  - Child can add NEW constraints to refine inherited rules
  - Effective policy = Parent rules + Child rules (cumulative)

This module:
  1. Detects inheritance relationships
  2. Resolves inheritance chains (handles multi-level)
  3. Merges parent constraints into child for analysis
  4. Detects inheritance conflicts (child contradicts parent)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from rdflib import Graph, Namespace, URIRef
import logging

logger = logging.getLogger(__name__)

# ODRL Namespace
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


@dataclass
class ResolvedPolicy:
    """A policy with all inherited constraints resolved."""
    policy_id: str
    policy_type: str
    
    # Direct rules and constraints
    own_rules: List[Any] = field(default_factory=list)
    own_constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Inherited from parent(s)
    inherited_rules: List[Any] = field(default_factory=list)
    inherited_constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Effective (combined)
    effective_rules: List[Any] = field(default_factory=list)
    effective_constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Inheritance chain
    parent_ids: List[str] = field(default_factory=list)
    inheritance_chain: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class InheritanceResult:
    """Result of inheritance resolution."""
    resolved_policy: ResolvedPolicy
    has_inheritance: bool
    inheritance_depth: int
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class InheritanceResolver:
    """
    Resolves ODRL policy inheritance chains.
    
    Usage:
        resolver = InheritanceResolver()
        result = resolver.resolve(child_policy, all_policies)
        
        # result.resolved_policy.effective_constraints contains all constraints
        # result.conflicts contains any inheritance conflicts detected
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._resolution_cache: Dict[str, ResolvedPolicy] = {}
        self._in_progress: Set[str] = set()  # Cycle detection
    
    def _debug(self, message: str, data: Any = None):
        if self.debug:
            print(f"[INHERITANCE] {message}")
            if data:
                print(f"              {data}")
    
    # =========================================================================
    # MAIN RESOLUTION METHOD
    # =========================================================================
    
    def resolve(self, policy: Any, all_policies: Dict[str, Any]) -> InheritanceResult:
        """
        Resolve inheritance for a policy.
        
        Args:
            policy: The policy to resolve (parsed policy object)
            all_policies: Dict of all policies by ID (for parent lookup)
            
        Returns:
            InheritanceResult with resolved policy and any conflicts
        """
        policy_id = self._get_policy_id(policy)
        self._debug(f"Resolving inheritance for: {policy_id}")
        
        # Check cache
        if policy_id in self._resolution_cache:
            cached = self._resolution_cache[policy_id]
            return InheritanceResult(
                resolved_policy=cached,
                has_inheritance=len(cached.parent_ids) > 0,
                inheritance_depth=len(cached.inheritance_chain)
            )
        
        # Cycle detection
        if policy_id in self._in_progress:
            raise ValueError(f"Circular inheritance detected: {policy_id}")
        
        self._in_progress.add(policy_id)
        
        try:
            result = self._resolve_internal(policy, all_policies)
            self._resolution_cache[policy_id] = result.resolved_policy
            return result
        finally:
            self._in_progress.discard(policy_id)
    
    def _resolve_internal(self, policy: Any, all_policies: Dict[str, Any]) -> InheritanceResult:
        """Internal resolution logic."""
        policy_id = self._get_policy_id(policy)
        
        # Extract own rules and constraints
        own_rules = self._get_rules(policy)
        own_constraints = self._get_constraints(policy)
        
        self._debug(f"Own rules: {len(own_rules)}, Own constraints: {len(own_constraints)}")
        
        # Check for inheritance
        parent_id = self._get_inherit_from(policy)
        
        if not parent_id:
            # No inheritance - return policy as-is
            resolved = ResolvedPolicy(
                policy_id=policy_id,
                policy_type=self._get_policy_type(policy),
                own_rules=own_rules,
                own_constraints=own_constraints,
                inherited_rules=[],
                inherited_constraints={},
                effective_rules=own_rules,
                effective_constraints=own_constraints,
                parent_ids=[],
                inheritance_chain=[policy_id]
            )
            return InheritanceResult(
                resolved_policy=resolved,
                has_inheritance=False,
                inheritance_depth=1
            )
        
        self._debug(f"Found inheritance: {policy_id} -> {parent_id}")
        
        # Find parent policy
        parent = all_policies.get(parent_id)
        if not parent:
            # Parent not found - warn but continue
            self._debug(f"WARNING: Parent policy not found: {parent_id}")
            resolved = ResolvedPolicy(
                policy_id=policy_id,
                policy_type=self._get_policy_type(policy),
                own_rules=own_rules,
                own_constraints=own_constraints,
                inherited_rules=[],
                inherited_constraints={},
                effective_rules=own_rules,
                effective_constraints=own_constraints,
                parent_ids=[parent_id],
                inheritance_chain=[policy_id]
            )
            return InheritanceResult(
                resolved_policy=resolved,
                has_inheritance=True,
                inheritance_depth=1,
                warnings=[f"Parent policy not found: {parent_id}"]
            )
        
        # Recursively resolve parent
        parent_result = self.resolve(parent, all_policies)
        parent_resolved = parent_result.resolved_policy
        
        # Merge constraints (ODRL cumulative semantics)
        # Effective = parent effective + child own
        inherited_rules = parent_resolved.effective_rules.copy()
        inherited_constraints = parent_resolved.effective_constraints.copy()
        
        effective_rules = inherited_rules + own_rules
        effective_constraints = {**inherited_constraints, **own_constraints}
        
        self._debug(f"Inherited: {len(inherited_constraints)} constraints")
        self._debug(f"Effective: {len(effective_constraints)} total constraints")
        
        # Build inheritance chain
        inheritance_chain = parent_resolved.inheritance_chain + [policy_id]
        
        resolved = ResolvedPolicy(
            policy_id=policy_id,
            policy_type=self._get_policy_type(policy),
            own_rules=own_rules,
            own_constraints=own_constraints,
            inherited_rules=inherited_rules,
            inherited_constraints=inherited_constraints,
            effective_rules=effective_rules,
            effective_constraints=effective_constraints,
            parent_ids=[parent_id] + parent_resolved.parent_ids,
            inheritance_chain=inheritance_chain
        )
        
        # Detect conflicts (will be done by InheritanceChecker)
        conflicts = []
        warnings = parent_result.warnings.copy()
        
        return InheritanceResult(
            resolved_policy=resolved,
            has_inheritance=True,
            inheritance_depth=len(inheritance_chain),
            conflicts=conflicts,
            warnings=warnings
        )
    
    # =========================================================================
    # EXTRACTION HELPERS
    # =========================================================================
    
    def _get_policy_id(self, policy: Any) -> str:
        """Extract policy ID."""
        if hasattr(policy, 'uid'):
            return str(policy.uid)
        if hasattr(policy, 'id'):
            return str(policy.id)
        if isinstance(policy, dict):
            return policy.get('uid', policy.get('id', policy.get('@id', 'unknown')))
        return str(id(policy))
    
    def _get_policy_type(self, policy: Any) -> str:
        """Extract policy type (Set, Offer, Agreement)."""
        if hasattr(policy, 'policy_type'):
            return str(policy.policy_type)
        if hasattr(policy, 'type'):
            return str(policy.type)
        if isinstance(policy, dict):
            return policy.get('type', policy.get('@type', 'Set'))
        return 'Set'
    
    def _get_inherit_from(self, policy: Any) -> Optional[str]:
        """Extract odrl:inheritFrom value."""
        # Try attribute
        if hasattr(policy, 'inherit_from'):
            val = policy.inherit_from
            return str(val) if val else None
        
        if hasattr(policy, 'inheritFrom'):
            val = policy.inheritFrom
            return str(val) if val else None
        
        # Try dict
        if isinstance(policy, dict):
            val = policy.get('inheritFrom', policy.get('inherit_from'))
            return str(val) if val else None
        
        return None
    
    def _get_rules(self, policy: Any) -> List[Any]:
        """Extract rules from policy."""
        rules = []
        if hasattr(policy, 'rules'):
            rules = list(policy.rules) if policy.rules else []
        elif isinstance(policy, dict):
            rules = policy.get('rules', [])
        return rules
    
    def _get_constraints(self, policy: Any) -> Dict[str, Any]:
        """Extract constraints from policy."""
        if hasattr(policy, 'constraints'):
            return dict(policy.constraints) if policy.constraints else {}
        if isinstance(policy, dict):
            return policy.get('constraints', {})
        return {}
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def clear_cache(self):
        """Clear resolution cache."""
        self._resolution_cache.clear()
    
    def get_inheritance_chain(self, policy: Any, all_policies: Dict[str, Any]) -> List[str]:
        """Get the full inheritance chain for a policy."""
        result = self.resolve(policy, all_policies)
        return result.resolved_policy.inheritance_chain
    
    def has_inheritance(self, policy: Any) -> bool:
        """Check if policy has inheritance."""
        return self._get_inherit_from(policy) is not None


# =============================================================================
# INTEGRATION WITH PARSER
# =============================================================================

def resolve_policy_inheritance(parsed_policy, all_parsed_policies: Dict[str, Any],
                               debug: bool = False) -> ResolvedPolicy:
    """
    Convenience function to resolve inheritance for a parsed policy.
    
    Args:
        parsed_policy: The policy parsed from TTL
        all_parsed_policies: Dict of all policies by URI
        debug: Enable debug output
        
    Returns:
        ResolvedPolicy with effective constraints
    """
    resolver = InheritanceResolver(debug=debug)
    result = resolver.resolve(parsed_policy, all_parsed_policies)
    
    if result.warnings:
        for warning in result.warnings:
            logger.warning(warning)
    
    return result.resolved_policy


# =============================================================================
# GRAPH-BASED RESOLUTION (for RDF/TTL)
# =============================================================================

class GraphInheritanceResolver:
    """
    Resolve inheritance directly from RDF graph.
    
    Use this when you have the raw RDF graph and need to
    resolve inheritance before parsing rules.
    """
    
    def __init__(self, graph: Graph, debug: bool = False):
        self.graph = graph
        self.debug = debug
    
    def get_all_policies(self) -> List[URIRef]:
        """Get all policy URIs in the graph."""
        policies = []
        for policy_type in [ODRL.Set, ODRL.Offer, ODRL.Agreement]:
            for s in self.graph.subjects(predicate=None, object=policy_type):
                if isinstance(s, URIRef):
                    policies.append(s)
        return policies
    
    def get_parent(self, policy_uri: URIRef) -> Optional[URIRef]:
        """Get parent policy URI if any."""
        for parent in self.graph.objects(subject=policy_uri, predicate=ODRL.inheritFrom):
            if isinstance(parent, URIRef):
                return parent
        return None
    
    def get_inheritance_chain(self, policy_uri: URIRef) -> List[URIRef]:
        """Get full inheritance chain (child -> parent -> grandparent -> ...)."""
        chain = [policy_uri]
        visited = {policy_uri}
        
        current = policy_uri
        while True:
            parent = self.get_parent(current)
            if parent is None:
                break
            if parent in visited:
                raise ValueError(f"Circular inheritance detected: {parent}")
            chain.append(parent)
            visited.add(parent)
            current = parent
        
        return chain
    
    def get_effective_constraints(self, policy_uri: URIRef) -> Set[URIRef]:
        """
        Get all effective constraint URIs for a policy (including inherited).
        
        Returns set of constraint URIs from this policy and all ancestors.
        """
        chain = self.get_inheritance_chain(policy_uri)
        
        all_constraints = set()
        for p in chain:
            # Get direct constraints from rules
            for rule in self.graph.objects(subject=p, predicate=ODRL.permission):
                for constraint in self.graph.objects(subject=rule, predicate=ODRL.constraint):
                    if isinstance(constraint, URIRef):
                        all_constraints.add(constraint)
            
            for rule in self.graph.objects(subject=p, predicate=ODRL.prohibition):
                for constraint in self.graph.objects(subject=rule, predicate=ODRL.constraint):
                    if isinstance(constraint, URIRef):
                        all_constraints.add(constraint)
            
            for rule in self.graph.objects(subject=p, predicate=ODRL.obligation):
                for constraint in self.graph.objects(subject=rule, predicate=ODRL.constraint):
                    if isinstance(constraint, URIRef):
                        all_constraints.add(constraint)
        
        return all_constraints


# =============================================================================
# MAIN / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Inheritance Resolver Test")
    print("=" * 60)
    
    # Mock policy objects for testing
    @dataclass
    class MockPolicy:
        uid: str
        policy_type: str = "Set"
        inherit_from: Optional[str] = None
        rules: List = field(default_factory=list)
        constraints: Dict = field(default_factory=dict)
    
    @dataclass
    class MockConstraint:
        uid: str
        left_operand: str
        operator: str
        right_operand: Any
    
    # Create test policies
    base_policy = MockPolicy(
        uid="http://example.org/base_policy",
        constraints={
            "c1": MockConstraint("c1", "delayPeriod", "gteq", 2592000)  # 30 days
        }
    )
    
    child_policy = MockPolicy(
        uid="http://example.org/child_policy",
        inherit_from="http://example.org/base_policy",
        constraints={
            "c2": MockConstraint("c2", "elapsedTime", "lteq", 7776000)  # 90 days
        }
    )
    
    conflicting_child = MockPolicy(
        uid="http://example.org/conflicting_child",
        inherit_from="http://example.org/base_policy",
        constraints={
            "c3": MockConstraint("c3", "delayPeriod", "lteq", 604800)  # 7 days
        }
    )
    
    all_policies = {
        "http://example.org/base_policy": base_policy,
        "http://example.org/child_policy": child_policy,
        "http://example.org/conflicting_child": conflicting_child,
    }
    
    # Test resolution
    resolver = InheritanceResolver(debug=True)
    
    print("\n--- Test 1: Base Policy (no inheritance) ---")
    result = resolver.resolve(base_policy, all_policies)
    print(f"Has inheritance: {result.has_inheritance}")
    print(f"Effective constraints: {list(result.resolved_policy.effective_constraints.keys())}")
    
    print("\n--- Test 2: Child Policy (inherits base) ---")
    result = resolver.resolve(child_policy, all_policies)
    print(f"Has inheritance: {result.has_inheritance}")
    print(f"Inheritance chain: {result.resolved_policy.inheritance_chain}")
    print(f"Own constraints: {list(result.resolved_policy.own_constraints.keys())}")
    print(f"Inherited constraints: {list(result.resolved_policy.inherited_constraints.keys())}")
    print(f"Effective constraints: {list(result.resolved_policy.effective_constraints.keys())}")
    
    print("\n--- Test 3: Conflicting Child ---")
    result = resolver.resolve(conflicting_child, all_policies)
    print(f"Has inheritance: {result.has_inheritance}")
    print(f"Effective constraints: {list(result.resolved_policy.effective_constraints.keys())}")
    print("(Conflict detection would be done by InheritanceChecker)")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)