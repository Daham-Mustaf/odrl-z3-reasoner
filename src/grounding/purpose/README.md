# Purpose Grounding Module (OWL Only)

Loads W3C DPV purpose ontologies for ODRL constraint grounding.

## Why OWL Only?

| Format | Predicate | Use Case |
|--------|-----------|----------|
| **OWL** | `rdfs:subClassOf` | Reasoning, constraints |
| SKOS | `skos:broader` | Browsing, UI |

For ODRL constraint reasoning, OWL gives us:
- Guaranteed transitivity
- Native multiple inheritance  
- Direct Z3/SMT mapping

DPV provides both formats with **identical content** - we just use OWL.

## Download DPV Files

```bash
mkdir -p data

# Core DPV
curl -L -o data/dpv/dpv-owl.ttl https://w3id.org/dpv/2.2/dpv-owl.ttl

# Sector extensions (optional)
curl -L -o data/dpv/sector-law-owl.ttl https://w3id.org/dpv/2.2/sector/law/sector-law-owl.ttl
curl -L -o data/dpv/sector-health-owl.ttl https://w3id.org/dpv/2.2/sector/health/sector-health-owl.ttl
curl -L -o data/dpv/sector-finance-owl.ttl https://w3id.org/dpv/2.2/sector/finance/sector-finance-owl.ttl
```

## Usage

```python
from grounding.purpose import DPVPurposeLoader

# Load
loader = DPVPurposeLoader()
loader.load("data/dpv-owl.ttl")
loader.load("data/sector-law-owl.ttl")

# Get graph for reasoning
graph = loader.get_graph()

# Stats
stats = loader.get_stats()
print(f"Purposes: {stats.purpose_concepts}")
print(f"Hierarchy edges: {stats.subclass_edges}")
```

## Structure

```
purpose/
├── __init__.py    # Exports
├── loader.py      # DPVPurposeLoader
├── README.md      # This file
└── data/          # DPV files (git-ignored)
    ├── dpv-owl.ttl
    └── sector-law-owl.ttl
```

## DPV Hierarchy Example

```
dpv-owl:Purpose
└── sector-law-owl:JusticeManagement
    ├── sector-law-owl:LawEnforcement
    │   ├── sector-law-owl:CriminalLawEnforcement
    │   │   ├── sector-law-owl:CrimeDetection
    │   │   └── sector-law-owl:CrimeInvestigation
    │   └── sector-law-owl:TransportLawEnforcement
    └── sector-law-owl:ImmigrationManagement
```

## Next Stage: Reasoning

The loader provides the RDF graph. Reasoning (oracle) comes later:

```python
# Grounding stage (this module)
graph = loader.get_graph()

# Reasoning stage (separate module)  
oracle = PurposeOracle(graph)
oracle.is_a("CrimeDetection", "LawEnforcement")  # True
```

## References

- [DPV Specification](https://w3id.org/dpv)
- [DPV GitHub](https://github.com/w3c/dpv)
- [DPV Purposes](https://w3c.github.io/dpv/2.2/dpv/#vocab-purposes)