# src/parser/ttl_parser.py
"""
Parse ODRL policies from TTL/RDF files.
Uses RDFLib for robust RDF handling.
"""

from rdflib import Graph, Namespace, URIRef, Literal
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ODRL Namespace
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

class TTLParser:
    """
    Parse ODRL policies from TTL files.
    
    Features:
    - Robust RDF parsing via RDFLib
    - Namespace handling
    - Error reporting with line numbers
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.graph = Graph()
        
        # Bind common namespaces
        self.graph.bind("odrl", ODRL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("xsd", XSD)
    
    def parse_file(self, filepath: str) -> Graph:
        """
        Parse TTL file into RDF graph.
        
        Args:
            filepath: Path to .ttl file
            
        Returns:
            RDFLib Graph object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If TTL is malformed
        """
        try:
            logger.info(f"Parsing TTL file: {filepath}")
            self.graph.parse(filepath, format='turtle')
            
            if self.debug:
                logger.debug(f"Parsed {len(self.graph)} triples")
                self._debug_print_triples()
            
            return self.graph
            
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            raise
        
        except Exception as e:
            logger.error(f"Failed to parse TTL: {e}")
            raise ValueError(f"Malformed TTL file: {e}")
    
    def parse_string(self, ttl_content: str) -> Graph:
        """Parse TTL from string"""
        try:
            self.graph.parse(data=ttl_content, format='turtle')
            
            if self.debug:
                logger.debug(f"Parsed {len(self.graph)} triples from string")
            
            return self.graph
            
        except Exception as e:
            logger.error(f"Failed to parse TTL string: {e}")
            raise ValueError(f"Malformed TTL content: {e}")
    
    def _debug_print_triples(self):
        """Print all triples for debugging"""
        logger.debug("=" * 60)
        logger.debug("RDF TRIPLES:")
        logger.debug("=" * 60)
        
        for i, (s, p, o) in enumerate(self.graph, 1):
            logger.debug(f"{i:3d}. {s} {p} {o}")
        
        logger.debug("=" * 60)
    
    def get_policies(self) -> List[URIRef]:
        """Get all policy URIs"""
        return list(self.graph.subjects(RDF.type, ODRL.Policy))
    
    def get_rules(self, policy_uri: URIRef) -> Dict[str, List[URIRef]]:
        """Get all rules for a policy"""
        return {
            'permissions': list(self.graph.objects(policy_uri, ODRL.permission)),
            'prohibitions': list(self.graph.objects(policy_uri, ODRL.prohibition)),
            'duties': list(self.graph.objects(policy_uri, ODRL.duty))
        }
    
    def get_constraints(self, rule_uri: URIRef) -> List[URIRef]:
        """Get all constraints for a rule"""
        return list(self.graph.objects(rule_uri, ODRL.constraint))