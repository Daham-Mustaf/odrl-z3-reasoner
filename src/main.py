# src/main.py
import sys
from .parser.ttl_parser import TTLParser
from .parser.rdf_extractor import RDFExtractor
from .normalizer.constraint_normalizer import ConstraintNormalizer
from .normalizer.canonical_normalizer import ConstraintCanonicalizer
from .encoder.z3_encoder import Z3Encoder, ClassHierarchy
from .reasoner.conflict_detector import ConflictDetector
from .analyzer.policy_analyzer import PolicyAnalyzer  # NEW

def main():
    # Get policy file
    if len(sys.argv) > 1:
        policy_file = sys.argv[1]
    else:
        policy_file = "examples/example_policy.ttl"
    
    debug = "--debug" in sys.argv
    
    print(f"Parsing {policy_file}...")
    
    # Parse TTL
    parser = TTLParser(debug=debug)
    graph = parser.parse_file(policy_file)
    
    # Extract policy
    policies = parser.get_policies()
    if not policies:
        print("No policies found!")
        return
    
    policy_uri = policies[0]
    print(f"Extracting policy: {policy_uri}")
    
    extractor = RDFExtractor(graph, debug=debug)
    policy = extractor.extract_policy(policy_uri)
    
    print(f"  Rules: {len(policy.rules)}")
    print(f"  Constraints: {len(policy.constraints)}")
    
    # Normalize
    print("Normalizing constraint values...")
    normalizer = ConstraintNormalizer(debug=debug)
    policy.constraints = normalizer.normalize_all(policy.constraints)
    
    # Canonicalize
    print("Canonicalizing constraint structure...")
    canonicalizer = ConstraintCanonicalizer(debug=debug)
    policy.constraints = canonicalizer.canonicalize(policy.constraints)
    
    # Detect conflicts
    print("Detecting conflicts...")
    hierarchy = ClassHierarchy(graph)
    encoder = Z3Encoder(hierarchy=hierarchy, debug=debug)
    
    detector = ConflictDetector(debug=debug)
    detector.encoder = encoder
    conflicts = detector.detect_all_conflicts(policy)
    
    if debug:
        encoder.print_encoding_summary()
    
    # NEW: Generate detailed analysis
    print("\nGenerating detailed analysis...")
    analyzer = PolicyAnalyzer(debug=debug)
    analysis = analyzer.analyze(policy, conflicts)
    analyzer.print_full_report(analysis)

if __name__ == '__main__':
    main()