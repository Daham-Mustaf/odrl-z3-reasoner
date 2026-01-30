# Systems and Projects Using the SZS Ontology

## Overview

The SZS (Sutcliffe-Zimmer-Suttner) ontology has become the **de facto standard** for automated reasoning software to communicate results. It is used extensively throughout the TPTP ecosystem and by major theorem provers worldwide.

---
# Systems Using SZS Ontology - Verified Links

## Theorem Provers (ATP)

| System | Website | GitHub/Source | Description |
|--------|---------|---------------|-------------|
| **Vampire** | https://vprover.github.io/ | https://github.com/vprover/vampire | First-order logic, CASC champion |
| **E Prover** | https://www.eprover.org/ | https://github.com/eprover/eprover | Equational theorem prover |
| **SPASS** | https://www.mpi-inf.mpg.de/departments/automation-of-logic/software/spass-workbench | https://webspass.spass-prover.org/ | First-order with equality (MPI) |
| **Leo-III** | — | https://github.com/leoprover/Leo-III | Higher-order logic |
| **Leo-II** | — | https://github.com/leoprover/LEO-II | Higher-order logic (predecessor) |
| **iProver** | http://www.cs.man.ac.uk/~korovink/iprover/ | https://gitlab.com/korovin/iprover | Instantiation-based prover |
| **Prover9** | https://www.cs.unm.edu/~mccune/prover9/ | — | Resolution/paramodulation |

## SMT Solvers

| System | Website | GitHub/Source | Description |
|--------|---------|---------------|-------------|
| **Z3** | https://github.com/Z3Prover/z3 | https://github.com/Z3Prover/z3 | Microsoft Research SMT solver |
| **CVC5** | https://cvc5.github.io/ | https://github.com/cvc5/cvc5 | SMT solver with proofs |
| **veriT** | https://verit.loria.fr/ | — | Proof-producing SMT solver |

## Interactive Theorem Provers

| System | Website | Documentation | Description |
|--------|---------|---------------|-------------|
| **Isabelle/HOL** | https://isabelle.in.tum.de/ | https://isabelle.in.tum.de/documentation.html | Proof assistant |
| **Sledgehammer** | (part of Isabelle) | https://isabelle.in.tum.de/dist/doc/sledgehammer.pdf | ATP bridge for Isabelle |

## TPTP Infrastructure

| Resource | URL | Description |
|----------|-----|-------------|
| **TPTP Library** | https://www.tptp.org/ | Problem library (38,000+ problems) |
| **SZS Ontology Spec** | https://tptp.org/UserDocs/SZSOntology/ | Official SZS documentation |
| **CASC Competition** | https://tptp.org/CASC/ | Annual ATP competition |
| **SystemOnTPTP** | https://www.tptp.org/cgi-bin/SystemOnTPTP | Online ATP service |
| **TSTP Solutions** | https://www.tptp.org/TSTP/ | Solution library |

## Key Papers

| Paper | URL |
|-------|-----|
| SZS Ontologies (Sutcliffe 2008) | https://www.cs.miami.edu/home/geoff/Papers/Conference/2008_Sut08_KEAPPA-38-49.pdf |
| TPTP World (Sutcliffe 2024) | https://link.springer.com/chapter/10.1007/978-3-031-63498-7_3 |
| Vampire (Kovács & Voronkov) | https://link.springer.com/chapter/10.1007/978-3-642-39799-8_1 |
| E Prover 2.3 | https://matryoshka-project.github.io/pubs/e_2.3.pdf |
| Sledgehammer (Paulson) | https://www.cl.cam.ac.uk/~lp15/papers/Automation/paar.pdf |

## Development Tools

| Tool | URL | Description |
|------|-----|-------------|
| **Tipi** | https://arxiv.org/abs/1204.0901 | Theory development with SZS |
| **Ontohub** | https://ontohub.org/ | Heterogeneous ontology repository |
| **TPTP Python Library** | https://github.com/leoprover/tptp | Python TPTP/SZS utilities |

## Example SZS Output Format

```
% SZS status Theorem for problem_name
% SZS output start Proof for problem_name
... proof steps ...
% SZS output end Proof for problem_name
```

## SZS Status Values (Most Common)

| Status | Meaning | When Used |
|--------|---------|-----------|
| `Theorem` (THM) | Conjecture follows from axioms | Proof found |
| `Unsatisfiable` (UNS) | Formula set has no models | Refutation found |
| `Satisfiable` (SAT) | Formula set has models | Model found |
| `CounterSatisfiable` (CSA) | Conjecture doesn't follow | Counter-model found |
| `Unknown` (UNK) | Could not determine | Timeout/gave up |
| `Timeout` (TMO) | Time limit exceeded | Resource limit |
| `GaveUp` (GUP) | Prover stopped voluntarily | Incompleteness |

