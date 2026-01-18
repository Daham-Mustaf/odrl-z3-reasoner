# src/semantics/hierarchy.py

from rdflib import Graph, RDFS, Namespace
from typing import Dict, Set

class ClassHierarchy:
    """
    Manage RDFS/OWL class hierarchies for isA reasoning.
    
    Precomputes transitive closure of rdfs:subClassOf.
    """
    
    def __init__(self, graph: Graph = None):
        self.graph = graph
        self.superclass_cache: Dict[str, Set[str]] = {}
        self.subclass_cache: Dict[str, Set[str]] = {}
        
        if graph:
            self._compute_closure()
    
    def _compute_closure(self):
        """Compute transitive closure of subClassOf"""
        # Get all classes
        classes = set()
        for s, p, o in self.graph.triples((None, RDFS.subClassOf, None)):
            classes.add(str(s))
            classes.add(str(o))
        
        # Compute superclasses for each class
        for cls in classes:
            self.superclass_cache[cls] = self._get_superclasses(cls)
        
        # Compute inverse (subclasses)
        for cls, supers in self.superclass_cache.items():
            for super_cls in supers:
                if super_cls not in self.subclass_cache:
                    self.subclass_cache[super_cls] = set()
                self.subclass_cache[super_cls].add(cls)
    
    def _get_superclasses(self, cls: str) -> Set[str]:
        """Get all superclasses of cls (transitive)"""
        superclasses = set()
        
        # Direct superclasses
        for super_cls in self.graph.objects(cls, RDFS.subClassOf):
            super_str = str(super_cls)
            superclasses.add(super_str)
            # Recursive: add their superclasses too
            superclasses.update(self._get_superclasses(super_str))
        
        return superclasses
    
    def is_a(self, instance_cls: str, target_cls: str) -> bool:
        """
        Check if instance_cls is-a target_cls (with transitivity).
        
        Examples:
            is_a('GraduateStudent', 'Person') → True
            is_a('GraduateStudent', 'GraduateStudent') → True (reflexive)
            is_a('Person', 'GraduateStudent') → False
        """
        # Reflexive: class is-a itself
        if instance_cls == target_cls:
            return True
        
        # Transitive: check cache
        return target_cls in self.superclass_cache.get(instance_cls, set())
    
    def get_all_subclasses(self, cls: str) -> Set[str]:
        """Get all subclasses of cls (transitive)"""
        return self.subclass_cache.get(cls, set())